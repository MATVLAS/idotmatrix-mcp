# LED Panel - iDotMatrix MCP Server & Claude Code Timer

Control an iDotMatrix LED panel (32x32) via Bluetooth from Claude Code.

## Project Structure

```
led_panel/
├── server.py          # MCP server exposing LED panel tools
├── timer/             # Claude Code use case: working timer daemon
│   ├── led_timer.py   # Background daemon that updates the LED display
│   └── led_status.py  # Hook script called by Claude Code hooks
└── .claude/
    └── settings.json  # MCP server config + hook definitions
```

## MCP Server (`server.py`)

A [FastMCP](https://github.com/jlowin/fastmcp) server that exposes iDotMatrix LED panel controls as tools available to Claude Code via the Model Context Protocol.

### Tools

| Tool | Description |
|------|-------------|
| `scan_devices` | Scan Bluetooth for nearby iDotMatrix panels |
| `screen_on` / `screen_off` | Turn the display on/off |
| `set_brightness` | Set brightness (5-100%) |
| `flip_screen` | Rotate 180 degrees |
| `toggle_freeze` | Toggle screen freeze |
| `reset_display` | Reset the display |
| `sync_time` | Sync panel clock to local time |
| `show_text` | Display text (custom color, font size) |
| `show_image` | Display an image file |
| `show_gif` | Display an animated GIF |
| `fullscreen_color` | Fill with a solid RGB color |
| `show_clock` | Show a clock face (8 styles, 12/24h) |
| `show_scoreboard` | Two-player scoreboard (0-999) |
| `countdown` | Countdown timer (start/pause/restart/disable) |
| `chronograph` | Stopwatch (start/pause/resume/reset) |
| `draw_frame` | Draw a custom 32x32 pixel frame |
| `clear_screen` | Turn all pixels off (black screen) |
| `show_effect` | Show animated effects (rainbow, random pixels, etc.) |
| `pixel_fill_start` | Start pixel fill animation (1 vivid pixel/sec, loops) |
| `pixel_fill_stop` | Stop pixel fill animation |
| `game_of_life_start` | Start Conway's Game of Life (smart seeds, death trails) |
| `game_of_life_stop` | Stop Game of Life |
| `timer_enable` | Enable the Claude Code timer daemon |
| `timer_disable` | Disable timer daemon and free the LED panel |

### Usage

The MCP server starts automatically when Claude Code launches (configured in `.claude/settings.json`). You can ask Claude to use any tool directly, e.g.:

> "Show 'HELLO' in blue on the LED panel"

> "Set brightness to 50%"

> "Display a scoreboard with 3 - 7"

## Claude Code Timer (`timer/`)

A background daemon that shows Claude Code's working status on the LED panel in real time.

### How It Works

- **`timer/led_status.py`** — Hook script triggered by Claude Code events:
  - `UserPromptSubmit` hook → sets status to "working" (starts daemon if needed)
  - `Stop` hook → sets status to "done"

- **`timer/led_timer.py`** — Background daemon that polls `/tmp/led_panel_status.json` every second:
  - **Working**: Shows elapsed time in blue (e.g. `2:35`)
  - **Waiting**: Shows `USER` in red when Claude needs user input
  - **Done**: Shows `IDLE` in green and keeps the BLE connection alive

### Setup

Hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "uv run python $CLAUDE_PROJECT_DIR/timer/led_status.py working",
        "async": true
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "uv run python $CLAUDE_PROJECT_DIR/timer/led_status.py done",
        "async": true
      }]
    }]
  }
}
```

## Installation

```bash
uv sync
```

Requires Python 3.11+, Bluetooth, and an iDotMatrix LED panel powered on and nearby.

## Credits

Built on top of [python3-idotmatrix-client](https://github.com/derkalle4/python3-idotmatrix-client) by:
- **Kalle Minkner** (Project Founder)
- **Jon-Mailes Graeffe** (Co-Founder)

Licensed under the GNU General Public License.
