"""Demo backend: SSE stream + state snapshot + kiosk restart control.

    PYTHONPATH=. python demo/server.py          # port 8010 (DEMO_PORT)

Separate process from the product API (src/api/app.py) — never touches it.
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402

from demo import config  # noqa: E402
from demo.core.events import BROKER  # noqa: E402
from demo.runner import DemoLoop  # noqa: E402

_loop_task: asyncio.Task | None = None
_demo: DemoLoop | None = None


def _start_loop() -> None:
    global _loop_task
    _loop_task = asyncio.create_task(_demo.run_forever())


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _demo
    # Heavy init (embedding model) happens once, before the first round.
    _demo = await asyncio.to_thread(DemoLoop)
    _start_loop()
    yield
    if _loop_task:
        _loop_task.cancel()


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


@app.get("/events")
async def events() -> StreamingResponse:
    queue = BROKER.subscribe()

    async def stream():
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            BROKER.unsubscribe(queue)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/state")
async def state() -> dict:
    return BROKER.state(config.AGENTS)


@app.post("/control/restart")
async def restart() -> dict:
    global _loop_task
    if _loop_task:
        _loop_task.cancel()
        try:
            await _loop_task
        except asyncio.CancelledError:
            pass
    BROKER.emit("reset")
    _start_loop()
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=config.SERVER_PORT, log_level="warning")
