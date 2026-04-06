#!/usr/bin/env python3
"""Hook script for Claude Code to signal LED panel working status.

Called by UserPromptSubmit and Stop hooks.
Writes status to /tmp/led_panel_status.json and manages the timer daemon.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

STATUS_FILE = "/tmp/led_panel_status.json"
WAITING_FLAG = "/tmp/led_panel_waiting.flag"
TIMER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "led_timer.py")
PID_FILE = "/tmp/led_timer.pid"


def is_timer_running():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, ValueError, PermissionError):
            try:
                os.remove(PID_FILE)
            except OSError:
                pass
    return False


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "done"

    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    if mode == "done" and hook_input.get("stop_hook_active"):
        return

    if mode == "working":
        status = {
            "status": "working",
            "start_time": datetime.now(timezone.utc).isoformat(),
        }
    elif mode == "waiting":
        try:
            with open(STATUS_FILE, "r") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = {}
        status = {
            "status": "waiting",
            "start_time": existing.get("start_time", datetime.now(timezone.utc).isoformat()),
        }
        open(WAITING_FLAG, "w").close()
    elif mode == "resume":
        try:
            with open(STATUS_FILE, "r") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = {}
        status = {
            "status": "working",
            "start_time": existing.get("start_time", datetime.now(timezone.utc).isoformat()),
        }
        try:
            os.remove(WAITING_FLAG)
        except OSError:
            pass
    else:
        status = {"status": "done"}

    with open(STATUS_FILE, "w") as f:
        json.dump(status, f)

    if mode == "working" and not is_timer_running():
        subprocess.Popen(
            [sys.executable, TIMER_SCRIPT, "run"],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


if __name__ == "__main__":
    main()
