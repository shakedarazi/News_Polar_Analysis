"""In-process ingestion scheduler.

Root cause of the outage this replaces (see PR/commit message for the full
writeup): scheduling previously depended entirely on the OS `cron` daemon
(scripts/setup_cron.sh installing `0 */6 * * * scripts/run_ingestion.sh`).
On this machine (and any macOS host), `cron` runs as a background daemon
with no "Full Disk Access" grant, and this project lives under `~/Downloads`
— one of the folders macOS's TCC privacy layer protects. Every single cron
firing therefore failed immediately with `Operation not permitted` before
the script could even start (confirmed via `/var/mail/$USER`), so no log
file was ever written and no article was ever inserted by the scheduler.
That's an OS-level permission wall, not something any code change to this
repo can grant, and it wouldn't exist at all in a Linux/Docker deployment —
so depending on it is inherently unreliable.

The fix: the ingestion job now runs on a timer *inside the already-running
application process* (started from FastAPI's startup hook, see
src/api/app.py), using APScheduler's BackgroundScheduler. A subprocess
spawned by our own long-lived, already-permitted process is not subject to
the same daemon-specific TCC restriction, and this approach needs no OS
scheduler, no crontab, and no machine-specific permission grant — it works
identically on macOS, Linux, and inside a container, and it starts/stops
with the API server itself, which is what "the application" actually means
here.

scripts/run_ingestion.sh / setup_cron.sh are left in place and still work
on hosts where OS cron isn't blocked (e.g. a plain Linux server) — they're
just no longer the only mechanism this system relies on.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

ROOT = Path(__file__).resolve().parents[2]
RUN_SCRIPT = ROOT / "scripts" / "run_ingestion.sh"
LOG_DIR = ROOT / "logs" / "ingestion"
LOG_FILE = LOG_DIR / "scheduler.log"

# The spec: ingestion runs every 6 hours, automatically, for the life of the
# running application.
INGESTION_INTERVAL_HOURS = 6
# First run shortly after startup rather than waiting a full 6h — so a
# freshly (re)started server starts catching up immediately.
FIRST_RUN_DELAY_SECONDS = 30
# Kill the job rather than block a scheduler thread forever if a source
# hangs (crawl + comments + lexicon + analyze, across 6 sources, normally
# finishes in a few minutes; this is a generous safety ceiling, not a
# realistic expected duration).
JOB_TIMEOUT_SECONDS = 45 * 60

logger = logging.getLogger("ingestion")

_scheduler: BackgroundScheduler | None = None
_configure_lock = threading.Lock()

# Tracks the currently in-flight run_ingestion.sh subprocess (if any), so a
# clean app shutdown can terminate it instead of leaving it orphaned to run
# unsupervised in the background and potentially overlap with the next
# scheduled run after a restart.
_running_processes: set[subprocess.Popen] = set()
_running_processes_lock = threading.Lock()


def configure_logging() -> None:
    """Attach rotating-file + console handlers to the "ingestion" logger tree
    (pipeline/crawl.py etc. log as children of this logger). Idempotent —
    safe to call more than once (e.g. re-import during tests)."""
    with _configure_lock:
        if logger.handlers:
            return
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%dT%H:%M:%S%z"
        )

        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False


def _kill_process_group(process: subprocess.Popen, sig: signal.Signals) -> None:
    """Signal the whole process group (bash + its Python children) started
    with start_new_session=True — killing just `process` would only stop
    the bash wrapper and orphan crawl.py/fetch_comments.py underneath it."""
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass  # already exited
    except Exception:
        logger.warning("Could not signal process group for pid %d", process.pid, exc_info=True)


def run_ingestion_job() -> None:
    """One scheduled run: crawl all sources -> fetch comments -> analyze
    (scripts/run_ingestion.sh, unchanged). Subprocess output is relayed into
    this module's logger line-by-line in real time.

    Deliberately never lets an exception escape: APScheduler would log it,
    but a bug here must not be able to take down the recurring schedule —
    the next run 6 hours from now has to fire regardless of whether this
    one succeeded, crashed, or timed out.
    """
    logger.info("=== Scheduled ingestion run starting ===")
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            ["bash", str(RUN_SCRIPT)],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            # New session/process group so the whole tree (bash -> python
            # crawl.py/fetch_comments.py/...) can be killed together via
            # os.killpg — plain terminate()/kill() only signals the bash
            # wrapper itself, leaving its Python children orphaned.
            start_new_session=True,
        )
    except Exception:
        logger.error("Failed to start run_ingestion.sh", exc_info=True)
        return

    with _running_processes_lock:
        _running_processes.add(process)
    try:
        assert process.stdout is not None
        for line in process.stdout:
            line = line.rstrip()
            if line:
                logger.info(line)
        return_code = process.wait(timeout=JOB_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        _kill_process_group(process, signal.SIGKILL)
        process.wait()
        logger.error(
            "Ingestion run exceeded %d minute timeout and was killed",
            JOB_TIMEOUT_SECONDS // 60,
        )
        return
    except Exception:
        logger.error("Ingestion run crashed while streaming output", exc_info=True)
        _kill_process_group(process, signal.SIGKILL)
        return
    finally:
        with _running_processes_lock:
            _running_processes.discard(process)

    elapsed = time.monotonic() - started
    if return_code == 0:
        logger.info("=== Scheduled ingestion run finished OK in %.0fs ===", elapsed)
    else:
        logger.error(
            "=== Scheduled ingestion run FAILED (exit code %d) after %.0fs — "
            "will retry at the next scheduled interval ===",
            return_code,
            elapsed,
        )


def start_scheduler() -> BackgroundScheduler:
    """Idempotent: returns the existing scheduler if already started (e.g.
    a duplicate startup-event call), instead of registering the job twice."""
    global _scheduler
    configure_logging()

    if _scheduler is not None and _scheduler.running:
        logger.info("Scheduler already running — ignoring duplicate start request")
        return _scheduler

    scheduler = BackgroundScheduler(timezone=timezone.utc)
    scheduler.add_job(
        run_ingestion_job,
        trigger=IntervalTrigger(hours=INGESTION_INTERVAL_HOURS),
        id="news_ingestion",
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=FIRST_RUN_DELAY_SECONDS),
        coalesce=True,  # if a run is somehow missed, run once, not N times back-to-back
        max_instances=1,  # never overlap two ingestion runs
        misfire_grace_time=3600,
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "Scheduler started — ingestion runs every %d hours (first run in %ds)",
        INGESTION_INTERVAL_HOURS,
        FIRST_RUN_DELAY_SECONDS,
    )
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
        _scheduler = None

    with _running_processes_lock:
        in_flight = list(_running_processes)
    for process in in_flight:
        if process.poll() is None:
            logger.info("Terminating in-flight ingestion run (pid=%d) for clean shutdown", process.pid)
            _kill_process_group(process, signal.SIGTERM)
