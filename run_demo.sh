#!/usr/bin/env bash
# Single entrypoint for the exhibition kiosk demo.
#
#   ./run_demo.sh                  # presenter mode (HITL): advances on space/click
#   DEMO_AUTOPLAY=1 ./run_demo.sh  # unattended kiosk loop: auto-advances gates
#   SKIP_BUILD=1 ./run_demo.sh     # reuse the existing frontend build
#   DEMO_SPEED=0.3 ./run_demo.sh   # faster loop for rehearsals
#
# Both processes are wrapped in auto-restart loops: if anything crashes, it is
# back within 2 seconds and the dashboard reconnects on its own.
set -u
cd "$(dirname "$0")"

if [ ! -f demo/data/demo.sqlite ] || [ ! -f demo/data/demo_set.json ]; then
  echo "Missing demo artifacts. Run (with network, once, before the show):"
  echo "  PYTHONPATH=. python demo/snapshot/export_snapshot.py"
  echo "  PYTHONPATH=. python demo/snapshot/prepare_demo.py"
  exit 1
fi

source .venv/bin/activate

# The explainer modules' measured strips. Cheap (a few SQLite scans, no
# network), and always regenerated so the wall cannot show numbers from a
# pipeline the code no longer runs.
PYTHONPATH=. python demo/snapshot/build_explainer_facts.py || {
  echo "[warn] explainer facts failed to build — modules will show diagrams only"
}

export DEMO_SPEED="${DEMO_SPEED:-1.0}"
# Presenter-controlled pacing by default (the show advances on space/click).
export DEMO_AUTOPLAY="${DEMO_AUTOPLAY:-0}"

if [ "${SKIP_BUILD:-}" != "1" ]; then
  echo "building frontend (SKIP_BUILD=1 to skip)..."
  (cd frontend && npm run build) || exit 1
fi

PIDS=()
cleanup() { for p in "${PIDS[@]}"; do pkill -P "$p" 2>/dev/null; kill "$p" 2>/dev/null; done; }
trap cleanup EXIT INT TERM

( while true; do
    PYTHONPATH=. python demo/server.py
    echo "[watchdog] demo server exited — restarting in 2s"; sleep 2
  done ) & PIDS+=($!)

( while true; do
    (cd frontend && npm run start)
    echo "[watchdog] frontend exited — restarting in 2s"; sleep 2
  done ) & PIDS+=($!)

echo "waiting for services..."
for i in $(seq 1 120); do
  curl -sf localhost:8010/state >/dev/null && curl -sf localhost:3000/demo >/dev/null && break
  sleep 1
done

URL="http://localhost:3000/demo"
echo "demo ready → $URL"
if [ "$(uname)" = "Darwin" ]; then
  open -na "Google Chrome" --args --kiosk --noerrdialogs --disable-session-crashed-bubble "$URL" \
    || open "$URL"
fi

wait
