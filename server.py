from __future__ import annotations

import asyncio
import os
import random
import tempfile
from datetime import datetime

from fastmcp import FastMCP
from idotmatrix import ConnectionManager
from idotmatrix.modules.chronograph import Chronograph
from idotmatrix.modules.clock import Clock
from idotmatrix.modules.common import Common
from idotmatrix.modules.countdown import Countdown
from idotmatrix.modules.effect import Effect
from idotmatrix.modules.fullscreenColor import FullscreenColor
from idotmatrix.modules.gif import Gif
from idotmatrix.modules.image import Image
from idotmatrix.modules.scoreboard import Scoreboard
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

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
    draw.text(
        (SCREEN_SIZE // 2, SCREEN_SIZE // 2),
        text,
        fill=(r, g, b),
        font=font,
        anchor="mm",
    )
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
    return (
        f"Brightness set to {brightness}%"
        if result is not False
        else "Failed to set brightness"
    )


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
    return (
        f"Time synced to {now.strftime('%Y-%m-%d %H:%M:%S')}"
        if result is not False
        else "Failed to sync time"
    )


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
    return (
        f"Image displayed: {image_path}"
        if result is not False
        else "Failed to display image"
    )


@mcp.tool
async def show_gif(gif_path: str) -> str:
    """Display an animated GIF on the LED panel. Each frame is resized to fit the screen.

    Args:
        gif_path: Absolute path to the GIF file.
    """
    await ensure_connected()
    result = await Gif().uploadProcessed(gif_path, pixel_size=SCREEN_SIZE)
    return (
        f"GIF displayed: {gif_path}" if result is not False else "Failed to display GIF"
    )


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
    return (
        f"Screen set to RGB({r}, {g}, {b})"
        if result is not False
        else "Failed to set color"
    )


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
    return (
        f"Clock displayed (style {style})"
        if result is not False
        else "Failed to show clock"
    )


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
    return (
        f"Scoreboard: {left_score} - {right_score}"
        if result is not False
        else "Failed to show scoreboard"
    )


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
    return (
        f"Countdown {labels[action]}"
        if result is not False
        else "Failed to control countdown"
    )


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
    return (
        f"Stopwatch {labels[action]}"
        if result is not False
        else "Failed to control stopwatch"
    )


if __name__ == "__main__":
    mcp.run()


# ---------------------------------------------------------------------------
# Canvas / Pixel Control
# ---------------------------------------------------------------------------


@mcp.tool
async def draw_frame(pixels: list[list[list[int]]]) -> str:
    """Draw a custom frame on the LED panel pixel by pixel. Call repeatedly to animate.

    Each call renders one full frame. Use this for generative art, games, or animations
    by calling it in a loop with different pixel data each time.

    Args:
        pixels: A 32x32 grid where each element is [r, g, b] (0-255).
                Row 0 is the top of the screen, row 31 is the bottom.
                Column 0 is the left, column 31 is the right.
                Example for a single red pixel at top-left: [[[255,0,0], [0,0,0], ...], ...]
    """
    await ensure_connected()
    img = PILImage.new("RGB", (SCREEN_SIZE, SCREEN_SIZE), (0, 0, 0))
    for y, row in enumerate(pixels[:SCREEN_SIZE]):
        for x, color in enumerate(row[:SCREEN_SIZE]):
            r = max(0, min(255, color[0]))
            g = max(0, min(255, color[1]))
            b = max(0, min(255, color[2]))
            img.putpixel((x, y), (r, g, b))
    path = tempfile.mktemp(suffix=".png", prefix="led_frame_")
    img.save(path)
    try:
        led_img = Image()
        await led_img.setMode(1)
        result = await led_img.uploadProcessed(path, pixel_size=SCREEN_SIZE)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    return "Frame drawn" if result is not False else "Failed to draw frame"


@mcp.tool
async def clear_screen() -> str:
    """Clear the LED panel (turn all pixels off / black screen)."""
    await ensure_connected()
    result = await FullscreenColor().setMode(r=0, g=0, b=0)
    return "Screen cleared" if result is not False else "Failed to clear screen"


@mcp.tool
async def show_effect(style: int, colors: list[list[int]] | None = None) -> str:
    """Show an animated visual effect on the LED panel.

    Args:
        style: Effect style (0-6):
            0 = horizontal rainbow gradient,
            1 = random colored pixels on black,
            2 = random white pixels on changing background,
            3 = vertical rainbow gradient,
            4 = diagonal rainbow (right),
            5 = diagonal rainbow (left),
            6 = random colored pixels.
        colors: Optional list of [r, g, b] color tuples for the effect (2-7 colors).
    """
    await ensure_connected()
    style = max(0, min(6, style))
    rgb_values = []
    if colors:
        for c in colors[:7]:
            rgb_values.append(
                [max(0, min(255, c[0])), max(0, min(255, c[1])), max(0, min(255, c[2]))]
            )
    result = await Effect().setMode(style, rgb_values)
    labels = {
        0: "horizontal rainbow",
        1: "random colored pixels",
        2: "random white pixels",
        3: "vertical rainbow",
        4: "diagonal rainbow (right)",
        5: "diagonal rainbow (left)",
        6: "random colored pixels v2",
    }
    return (
        f"Effect: {labels[style]}" if result is not False else "Failed to show effect"
    )


# ---------------------------------------------------------------------------
# Pixel Fill Animation
# ---------------------------------------------------------------------------

_fill_task: asyncio.Task | None = None
_fill_running = False


async def _pixel_fill_loop():
    """Background loop: add 1 random pixel/second, pause 60s when full, repeat."""
    global _fill_running
    from idotmatrix.modules.countdown import Countdown as CD

    _fill_running = True
    try:
        await ensure_connected()
        # Stop any device countdown that would override display
        try:
            await CD().setMode(0, 0, 0)
        except Exception:
            pass

        while _fill_running:
            # Build pixel grid (black = empty)
            grid = [[(0, 0, 0)] * SCREEN_SIZE for _ in range(SCREEN_SIZE)]
            positions = [(x, y) for x in range(SCREEN_SIZE) for y in range(SCREEN_SIZE)]
            random.shuffle(positions)

            for i, (px, py) in enumerate(positions):
                if not _fill_running:
                    return
                import colorsys
                h = random.random()
                s = 1.0
                v = 1.0
                r, g, b = (int(c * 255) for c in colorsys.hsv_to_rgb(h, s, v))
                grid[py][px] = (r, g, b)

                # Build and upload frame
                img = PILImage.new("RGB", (SCREEN_SIZE, SCREEN_SIZE), (0, 0, 0))
                for gy in range(SCREEN_SIZE):
                    for gx in range(SCREEN_SIZE):
                        if grid[gy][gx] != (0, 0, 0):
                            img.putpixel((gx, gy), grid[gy][gx])

                path = tempfile.mktemp(suffix=".png", prefix="led_fill_")
                img.save(path)
                try:
                    led_img = Image()
                    await led_img.setMode(1)
                    await led_img.uploadProcessed(path, pixel_size=SCREEN_SIZE)
                finally:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

                # 1 pixel per second
                await asyncio.sleep(1)

            # Full — pause 60s then restart
            if _fill_running:
                await asyncio.sleep(60)
    except asyncio.CancelledError:
        pass
    finally:
        _fill_running = False


@mcp.tool
async def pixel_fill_start() -> str:
    """Start the pixel fill animation: one random-colored pixel per second on a 32x32 grid.
    When all pixels are filled, waits 60 seconds, wipes the screen, and starts over.
    Runs in the background until stopped with pixel_fill_stop.
    """
    global _fill_task, _fill_running
    if _fill_running:
        return "Pixel fill already running"
    _fill_task = asyncio.create_task(_pixel_fill_loop())
    return (
        "Pixel fill started — 1 random pixel/second, 60s pause when full, then restarts"
    )


@mcp.tool
async def pixel_fill_stop() -> str:
    """Stop the pixel fill animation."""
    global _fill_task, _fill_running
    _fill_running = False
    if _fill_task:
        _fill_task.cancel()
        _fill_task = None
    return "Pixel fill stopped"


# ---------------------------------------------------------------------------
# Game of Life
# ---------------------------------------------------------------------------

_gol_task: asyncio.Task | None = None
_gol_running = False


def _count_neighbors(grid, x, y):
    count = 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx = (x + dx) % SCREEN_SIZE
            ny = (y + dy) % SCREEN_SIZE
            if grid[ny][nx]:
                count += 1
    return count


def _next_generation(grid):
    new = [[False] * SCREEN_SIZE for _ in range(SCREEN_SIZE)]
    for y in range(SCREEN_SIZE):
        for x in range(SCREEN_SIZE):
            n = _count_neighbors(grid, x, y)
            if grid[y][x]:
                new[y][x] = n in (2, 3)
            else:
                new[y][x] = n == 3
    return new


# Smart seeds — famous long-running patterns (offsets relative to center)
_GOL_SEEDS = {
    "r_pentomino": [(0, -1), (1, -1), (-1, 0), (0, 0), (0, 1)],
    "acorn": [(0, 0), (1, 0), (1, -2), (3, -1), (4, 0), (5, 0), (6, 0)],
    "diehard": [(0, 1), (1, 1), (1, 2), (5, 0), (6, 0), (6, -2), (7, 0)],
    "glider_gun_arms": [],  # random fallback
    "pi_heptomino": [(-1, -1), (0, -1), (1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)],
    "b_heptomino": [(-1, 0), (0, -1), (0, 0), (0, 1), (1, -1), (1, 1), (2, 0)],
    "thunderbird": [(-2, -1), (-1, -1), (0, -1), (1, -1), (2, -1), (0, 0), (0, 1)],
}


def _smart_seed():
    """Place a known seed at center, or random cluster if pattern is empty."""
    name = random.choice(list(_GOL_SEEDS.keys()))
    offsets = _GOL_SEEDS[name]
    grid = [[False] * SCREEN_SIZE for _ in range(SCREEN_SIZE)]
    if not offsets:
        # random cluster fallback
        return [[random.random() < 0.3 for _ in range(SCREEN_SIZE)] for _ in range(SCREEN_SIZE)]
    cx, cy = SCREEN_SIZE // 2, SCREEN_SIZE // 2
    for dx, dy in offsets:
        x = (cx + dx) % SCREEN_SIZE
        y = (cy + dy) % SCREEN_SIZE
        grid[y][x] = True
    # Add random cells around for chaos
    for _ in range(random.randint(0, 5)):
        x = (cx + random.randint(-6, 6)) % SCREEN_SIZE
        y = (cy + random.randint(-6, 6)) % SCREEN_SIZE
        grid[y][x] = True
    return grid


def _count_alive(grid):
    return sum(cell for row in grid for cell in row)


async def _gol_loop():
    global _gol_running
    import colorsys

    _gol_running = True
    try:
        await ensure_connected()
        grid = _smart_seed()
        last_alive = -1

        # Death trail map: stores remaining fade ticks for recently dead cells
        trails: list[list[int]] = [[0] * SCREEN_SIZE for _ in range(SCREEN_SIZE)]
        TRAIL_LENGTH = 5

        low_pop_ticks = 0
        stagnant_ticks = 0
        last_alive_count = -1

        while _gol_running:
            try:
                alive = _count_alive(grid)

                # Re-seed when dead
                if alive == 0:
                    await asyncio.sleep(3)
                    grid = _smart_seed()
                    trails = [[0] * SCREEN_SIZE for _ in range(SCREEN_SIZE)]
                    low_pop_ticks = 0
                    stagnant_ticks = 0
                    last_alive_count = -1
                    continue

                # Debris: population too low for too long (gliders looping forever)
                if alive < 15:
                    low_pop_ticks += 1
                    if low_pop_ticks > 30:
                        await asyncio.sleep(2)
                        grid = _smart_seed()
                        trails = [[0] * SCREEN_SIZE for _ in range(SCREEN_SIZE)]
                        low_pop_ticks = 0
                        stagnant_ticks = 0
                        last_alive_count = -1
                        continue
                else:
                    low_pop_ticks = 0

                # Still life / oscillator: population unchanged for too long
                if alive == last_alive_count:
                    stagnant_ticks += 1
                    if stagnant_ticks > 20:
                        await asyncio.sleep(2)
                        grid = _smart_seed()
                        trails = [[0] * SCREEN_SIZE for _ in range(SCREEN_SIZE)]
                        low_pop_ticks = 0
                        stagnant_ticks = 0
                        last_alive_count = -1
                        continue
                else:
                    stagnant_ticks = 0
                last_alive_count = alive

                # Update trails: mark newly dead cells
                for y in range(SCREEN_SIZE):
                    for x in range(SCREEN_SIZE):
                        if not grid[y][x] and trails[y][x] == 0:
                            # Check if was alive last frame (trail just started)
                            pass  # will be set after next_gen comparison
                        if trails[y][x] > 0:
                            trails[y][x] -= 1

                # Compute next gen and mark newly dead cells
                new_grid = _next_generation(grid)
                for y in range(SCREEN_SIZE):
                    for x in range(SCREEN_SIZE):
                        if grid[y][x] and not new_grid[y][x]:
                            trails[y][x] = TRAIL_LENGTH
                grid = new_grid

                # Render frame with trails
                img = PILImage.new("RGB", (SCREEN_SIZE, SCREEN_SIZE), (0, 0, 0))
                for y in range(SCREEN_SIZE):
                    for x in range(SCREEN_SIZE):
                        if grid[y][x]:
                            h = ((x + y) / (SCREEN_SIZE * 2)) % 1.0
                            r, g, b = (int(c * 255) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0))
                            img.putpixel((x, y), (r, g, b))
                        elif trails[y][x] > 0:
                            fade = trails[y][x] / TRAIL_LENGTH
                            img.putpixel((x, y), (int(30 * fade), int(30 * fade), int(80 * fade)))

                path = tempfile.mktemp(suffix=".png", prefix="led_gol_")
                img.save(path)
                upload_start = asyncio.get_event_loop().time()
                try:
                    led_img = Image()
                    await led_img.setMode(1)
                    await led_img.uploadProcessed(path, pixel_size=SCREEN_SIZE)
                finally:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

                grid = _next_generation(grid)
                await asyncio.sleep(1)
            except Exception:
                # BLE dropped or upload failed — reconnect and retry
                await asyncio.sleep(1)
                try:
                    await ensure_connected()
                except Exception:
                    await asyncio.sleep(2)
    except asyncio.CancelledError:
        pass
    finally:
        _gol_running = False


@mcp.tool
async def game_of_life_start() -> str:
    """Start Conway's Game of Life on the LED panel.
    Cells evolve automatically. Re-seeds when stagnant or dead.
    Runs in the background until stopped with game_of_life_stop.
    """
    global _gol_task, _gol_running
    if _gol_running:
        return "Game of Life already running"
    _gol_task = asyncio.create_task(_gol_loop())
    return "Game of Life started — auto re-seeds when stagnant"


@mcp.tool
async def game_of_life_stop() -> str:
    """Stop the Game of Life animation."""
    global _gol_task, _gol_running
    _gol_running = False
    if _gol_task:
        _gol_task.cancel()
        _gol_task = None
    return "Game of Life stopped"


@mcp.tool
async def timer_enable() -> str:
    """Enable the Claude Code timer daemon. It will start on next working status."""
    import subprocess
    import sys

    script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "timer", "led_status.py"
    )
    subprocess.run([sys.executable, script, "enable"], capture_output=True)
    return "Timer enabled"


@mcp.tool
async def timer_disable() -> str:
    """Disable the Claude Code timer daemon and kill it if running. Frees the LED panel."""
    import subprocess
    import sys

    script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "timer", "led_status.py"
    )
    subprocess.run([sys.executable, script, "disable"], capture_output=True)
    return "Timer disabled and stopped"
