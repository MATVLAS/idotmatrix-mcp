#!/usr/bin/env python3
"""Background daemon that displays Claude Code working status on the LED panel.

Maintains a BLE connection and updates the display.
Polls /tmp/led_panel_status.json for state changes.
"""
import asyncio
import json
import logging
import os
import signal
import sys
import tempfile
from datetime import datetime, timezone

from PIL import Image as PILImage, ImageDraw, ImageFont

SCREEN_SIZE = 32
STATUS_FILE = "/tmp/led_panel_status.json"
WAITING_FLAG = "/tmp/led_panel_waiting.flag"
PID_FILE = "/tmp/led_timer.pid"
LOG_FILE = "/tmp/led_timer.log"
SYSTEM_FONT = "/System/Library/Fonts/Menlo.ttc"
POLL_INTERVAL = 1
DISPLAY_INTERVAL = 5

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def render_text_image(text: str, r: int, g: int, b: int, font_size: int = 14) -> str:
    img = PILImage.new("RGB", (SCREEN_SIZE, SCREEN_SIZE), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(SYSTEM_FONT, font_size)
    draw.text((SCREEN_SIZE // 2, SCREEN_SIZE // 2), text, fill=(r, g, b), font=font, anchor="mm")
    path = tempfile.mktemp(suffix=".png", prefix="led_")
    img.save(path)
    return path


def read_status():
    if not os.path.exists(STATUS_FILE):
        return "idle", None
    try:
        with open(STATUS_FILE, "r") as f:
            data = json.load(f)
        return data.get("status", "idle"), data.get("start_time")
    except (json.JSONDecodeError, IOError):
        return "idle", None


def is_waiting_flag_set():
    if not os.path.exists(WAITING_FLAG):
        return False
    try:
        mtime = os.path.getmtime(WAITING_FLAG)
        return (datetime.now().timestamp() - mtime) < 5
    except OSError:
        return False


async def upload_image(conn, text: str, r: int, g: int, b: int, font_size: int = 14) -> bool:
    from idotmatrix.modules.image import Image as LEDImage

    if not (conn.client and conn.client.is_connected):
        await conn.connectBySearch()
    path = render_text_image(text, r, g, b, font_size)
    try:
        img = LEDImage()
        await img.setMode(1)
        result = await img.uploadProcessed(path, pixel_size=SCREEN_SIZE)
        log.info(f"Upload '{text}': {result is not False}")
        return result is not False
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


async def run_loop():
    from idotmatrix import ConnectionManager
    from idotmatrix.modules.countdown import Countdown

    conn = ConnectionManager()
    last_status = "idle"
    last_display = 0
    start_time = None
    pause_start = None
    total_paused = 0.0
    showing_user = False
    log.info("Daemon started")

    while True:
        try:
            current_status, file_start_time = read_status()
            waiting_flag = is_waiting_flag_set()

            # idle → working
            if current_status == "working" and last_status != "working":
                start_time = file_start_time
                total_paused = 0.0
                pause_start = None
                showing_user = False
                last_display = 0
                log.info(f"Started working, start_time={start_time}")

            # waiting flag set → show USER
            if waiting_flag and not showing_user:
                pause_start = datetime.now(timezone.utc)
                showing_user = True
                log.info("Waiting for user - showing USER")
                await upload_image(conn, "USER", 255, 0, 0)

            # waiting flag cleared → resume timer
            elif not waiting_flag and showing_user:
                if pause_start:
                    total_paused += (datetime.now(timezone.utc) - pause_start).total_seconds()
                    pause_start = None
                showing_user = False
                last_display = 0
                log.info(f"Resuming timer (total_paused={total_paused:.1f}s)")

            # → done: disable countdown, show IDLE, stay alive to keep BLE
            elif current_status == "done" and last_status != "done":
                log.info("Done - showing IDLE")
                try:
                    await Countdown().setMode(0, 0, 0)
                except Exception:
                    pass
                await upload_image(conn, "IDLE", 0, 255, 0)

            # while working: update timer display
            if current_status == "working" and start_time and not showing_user:
                now = asyncio.get_event_loop().time()
                if now - last_display >= DISPLAY_INTERVAL:
                    elapsed = (
                        (datetime.now(timezone.utc) - datetime.fromisoformat(start_time)).total_seconds()
                        - total_paused
                    )
                    if pause_start:
                        elapsed -= (datetime.now(timezone.utc) - pause_start).total_seconds()
                    mins = int(elapsed) // 60
                    secs = int(elapsed) % 60
                    await upload_image(conn, f"{mins}:{secs:02d}", 0, 200, 255)
                    last_display = now

            last_status = current_status

        except Exception as e:
            log.error(f"Error: {e}")

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"

    if mode == "run":
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        try:
            asyncio.run(run_loop())
        except KeyboardInterrupt:
            pass
        finally:
            try:
                os.remove(PID_FILE)
            except OSError:
                pass

    elif mode == "stop":
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE) as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, ValueError, PermissionError):
                pass
            try:
                os.remove(PID_FILE)
            except OSError:
                pass
