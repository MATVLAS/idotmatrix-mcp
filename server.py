from __future__ import annotations

import os
import tempfile
from datetime import datetime

from PIL import Image as PILImage, ImageDraw, ImageFont
from fastmcp import FastMCP
from idotmatrix import ConnectionManager
from idotmatrix.modules.chronograph import Chronograph
from idotmatrix.modules.clock import Clock
from idotmatrix.modules.common import Common
from idotmatrix.modules.countdown import Countdown
from idotmatrix.modules.fullscreenColor import FullscreenColor
from idotmatrix.modules.gif import Gif
from idotmatrix.modules.image import Image
from idotmatrix.modules.scoreboard import Scoreboard

SCREEN_SIZE = int(os.environ.get("IDOTMATRIX_SCREEN_SIZE", "32"))
IDOTMATRIX_ADDRESS = os.environ.get("IDOTMATRIX_ADDRESS", None)
SYSTEM_FONT = "/System/Library/Fonts/Menlo.ttc"

conn = ConnectionManager()


async def ensure_connected():
    """Auto-connect to the first available iDotMatrix device if not already connected."""
    if conn.client is not None and conn.client.is_connected:
        return
    if IDOTMATRIX_ADDRESS:
        await conn.connectByAddress(IDOTMATRIX_ADDRESS)
    else:
        await conn.connectBySearch()


def _render_text_to_file(text: str, r: int, g: int, b: int, font_size: int = 14) -> str:
    """Render text onto a SCREEN_SIZE x SCREEN_SIZE image using Pillow. Returns temp file path."""
    img = PILImage.new("RGB", (SCREEN_SIZE, SCREEN_SIZE), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(SYSTEM_FONT, font_size)
    draw.text((SCREEN_SIZE // 2, SCREEN_SIZE // 2), text, fill=(r, g, b), font=font, anchor="mm")
    path = tempfile.mktemp(suffix=".png", prefix="led_")
    img.save(path)
    return path


mcp = FastMCP("iDotMatrix LED Panel")


# ---------------------------------------------------------------------------
# Connection / Discovery
# ---------------------------------------------------------------------------


@mcp.tool
async def scan_devices() -> list[str]:
    """Scan Bluetooth for nearby iDotMatrix LED panels (devices starting with 'IDM-').
    Returns a list of MAC addresses found."""
    devices = await ConnectionManager.scan()
    return devices if devices else []


# ---------------------------------------------------------------------------
# Display Control
# ---------------------------------------------------------------------------


@mcp.tool
async def screen_on() -> str:
    """Turn the LED panel screen on."""
    await ensure_connected()
    result = await Common().screenOn()
    return "Screen turned on" if result is not False else "Failed to turn screen on"


@mcp.tool
async def screen_off() -> str:
    """Turn the LED panel screen off."""
    await ensure_connected()
    result = await Common().screenOff()
    return "Screen turned off" if result is not False else "Failed to turn screen off"


@mcp.tool
async def set_brightness(brightness: int) -> str:
    """Set the LED panel brightness.

    Args:
        brightness: Brightness percentage (5-100).
    """
    await ensure_connected()
    brightness = max(5, min(100, brightness))
    result = await Common().setBrightness(brightness)
    return f"Brightness set to {brightness}%" if result is not False else "Failed to set brightness"


@mcp.tool
async def flip_screen(enabled: bool) -> str:
    """Rotate the display 180 degrees.

    Args:
        enabled: True to flip, False to restore normal orientation.
    """
    await ensure_connected()
    result = await Common().flipScreen(enabled)
    state = "flipped" if enabled else "normal orientation"
    return f"Screen {state}" if result is not False else "Failed to flip screen"


@mcp.tool
async def toggle_freeze() -> str:
    """Toggle screen freeze on the LED panel."""
    await ensure_connected()
    result = await Common().freezeScreen()
    return "Screen freeze toggled" if result is not False else "Failed to toggle freeze"


@mcp.tool
async def reset_display() -> str:
    """Reset the LED panel display. Useful for clearing glitches."""
    await ensure_connected()
    result = await Common().reset()
    return "Display reset" if result is not False else "Failed to reset display"


@mcp.tool
async def sync_time() -> str:
    """Sync the LED panel's clock to the current local time."""
    await ensure_connected()
    now = datetime.now()
    result = await Common().setTime(
        year=now.year,
        month=now.month,
        day=now.day,
        hour=now.hour,
        minute=now.minute,
        second=now.second,
    )
    return f"Time synced to {now.strftime('%Y-%m-%d %H:%M:%S')}" if result is not False else "Failed to sync time"


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------


@mcp.tool
async def show_text(
    text: str,
    r: int = 255,
    g: int = 0,
    b: int = 0,
    font_size: int = 14,
) -> str:
    """Display text on the LED panel.

    Args:
        text: The text string to display.
        r: Red color component (0-255). Default 255.
        g: Green color component (0-255). Default 0.
        b: Blue color component (0-255). Default 0.
        font_size: Font size in pixels. Default 14.
    """
    await ensure_connected()
    path = _render_text_to_file(text, r, g, b, font_size)
    try:
        img = Image()
        await img.setMode(1)
        result = await img.uploadProcessed(path, pixel_size=SCREEN_SIZE)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    return f"Showing text: '{text}'" if result is not False else "Failed to show text"


# ---------------------------------------------------------------------------
# Images & GIFs
# ---------------------------------------------------------------------------


@mcp.tool
async def show_image(image_path: str) -> str:
    """Display an image on the LED panel. The image is automatically resized to fit the screen.

    Args:
        image_path: Absolute path to the image file (PNG, JPG, etc.).
    """
    await ensure_connected()
    img = Image()
    await img.setMode(1)
    result = await img.uploadProcessed(image_path, pixel_size=SCREEN_SIZE)
    return f"Image displayed: {image_path}" if result is not False else "Failed to display image"


@mcp.tool
async def show_gif(gif_path: str) -> str:
    """Display an animated GIF on the LED panel. Each frame is resized to fit the screen.

    Args:
        gif_path: Absolute path to the GIF file.
    """
    await ensure_connected()
    result = await Gif().uploadProcessed(gif_path, pixel_size=SCREEN_SIZE)
    return f"GIF displayed: {gif_path}" if result is not False else "Failed to display GIF"


# ---------------------------------------------------------------------------
# Fullscreen Color
# ---------------------------------------------------------------------------


@mcp.tool
async def fullscreen_color(r: int, g: int, b: int) -> str:
    """Fill the entire LED panel with a single color.

    Args:
        r: Red component (0-255).
        g: Green component (0-255).
        b: Blue component (0-255).
    """
    await ensure_connected()
    result = await FullscreenColor().setMode(r=r, g=g, b=b)
    return f"Screen set to RGB({r}, {g}, {b})" if result is not False else "Failed to set color"


# ---------------------------------------------------------------------------
# Clock
# ---------------------------------------------------------------------------


@mcp.tool
async def show_clock(
    style: int = 0,
    r: int = 255,
    g: int = 255,
    b: int = 255,
    show_date: bool = True,
    hour_24: bool = True,
) -> str:
    """Show a clock face on the LED panel.

    Args:
        style: Clock style (0-7): 0=default, 1=christmas, 2=racing, 3=inverted fullscreen,
            4=animated hourglass, 5=frame1, 6=frame2, 7=frame3. Default 0.
        r: Red component (0-255). Default 255.
        g: Green component (0-255). Default 255.
        b: Blue component (0-255). Default 255.
        show_date: Show date alongside time. Default True.
        hour_24: Use 24-hour format. Default True.
    """
    await ensure_connected()
    style = max(0, min(7, style))
    result = await Clock().setMode(
        style=style,
        visibleDate=show_date,
        hour24=hour_24,
        r=r,
        g=g,
        b=b,
    )
    return f"Clock displayed (style {style})" if result is not False else "Failed to show clock"


# ---------------------------------------------------------------------------
# Scoreboard
# ---------------------------------------------------------------------------


@mcp.tool
async def show_scoreboard(left_score: int, right_score: int) -> str:
    """Display a two-player scoreboard on the LED panel.

    Args:
        left_score: Left player score (0-999).
        right_score: Right player score (0-999).
    """
    await ensure_connected()
    left_score = max(0, min(999, left_score))
    right_score = max(0, min(999, right_score))
    result = await Scoreboard().setMode(left_score, right_score)
    return f"Scoreboard: {left_score} - {right_score}" if result is not False else "Failed to show scoreboard"


# ---------------------------------------------------------------------------
# Countdown
# ---------------------------------------------------------------------------


@mcp.tool
async def countdown(
    action: int,
    minutes: int = 0,
    seconds: int = 0,
) -> str:
    """Control the countdown timer on the LED panel.

    Args:
        action: 0=disable, 1=start, 2=pause, 3=restart.
        minutes: Minutes for the countdown (used with action=1).
        seconds: Seconds for the countdown (0-59, used with action=1).
    """
    await ensure_connected()
    action = max(0, min(3, action))
    seconds = max(0, min(59, seconds))
    result = await Countdown().setMode(action, minutes, seconds)
    labels = {0: "disabled", 1: "started", 2: "paused", 3: "restarted"}
    return f"Countdown {labels[action]}" if result is not False else "Failed to control countdown"


# ---------------------------------------------------------------------------
# Chronograph (Stopwatch)
# ---------------------------------------------------------------------------


@mcp.tool
async def chronograph(action: int) -> str:
    """Control the stopwatch on the LED panel.

    Args:
        action: 0=reset, 1=start, 2=pause, 3=continue.
    """
    await ensure_connected()
    action = max(0, min(3, action))
    result = await Chronograph().setMode(action)
    labels = {0: "reset", 1: "started", 2: "paused", 3: "resumed"}
    return f"Stopwatch {labels[action]}" if result is not False else "Failed to control stopwatch"


if __name__ == "__main__":
    mcp.run()
