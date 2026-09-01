#!/usr/bin/env python3
"""Start the read-only browse API and web UI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve News Polar browse API")
    parser.add_argument("--host", default="127.0.0.1")
    # PORT is what a host assigns us — Render's startCommand already passes
    # $PORT, and a local runner needs the same door when 8000 is taken.
    # An explicit --port still wins.
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT") or 8000))
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("ERROR: uvicorn not installed. Run: pip install fastapi uvicorn", file=sys.stderr)
        return 1

    uvicorn.run("src.api.app:app", host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
