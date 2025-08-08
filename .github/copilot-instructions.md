# Copilot instructions for this repo

Purpose: Wingman shows context-relevant documentation (man/--help/online) in a small, always-on-top panel that docks near the currently active window on Linux/X11.

## Big picture

- Entry point: `src/main.py:main()` (installed console script: `wingman = main:main` with `package-dir = {"" = "src"}`).
- Components:
  - App detection: `src/core/app_detector.py` (Linux/X11 only) emits `app_changed(name: str, geometry: dict)` via Qt signal.
  - UI panel: `src/ui/main_window.py` frameless, translucent `QMainWindow` that:
    - Displays docs in a `QTextBrowser`.
    - Auto-docks to the active window after geometry is stable for ~300ms.
    - Disables auto-positioning when user drags the panel.
  - System tray: `src/ui/system_tray.py` adds quick actions (show/hide, position, quit).
  - Docs: `src/core/doc_retriever.py` fetches docs in order: `man` → `--help`/`-h` → fallback string (optional `requests`-based online fetch helper exists).

Data flow (happy path): X11 detects active window → `LinuxAppDetector.app_changed(name, geometry)` → `MainWindow.set_app_name(...)` and `MainWindow.handle_auto_documentation(name)` → after delay, user clicks “Load Docs” → `DocRetriever.get_documentation(app)` → UI renders in `QTextBrowser`.

## Developer workflows

- Run from source (recommended during dev):
  - Set `PYTHONPATH=src:.` because code uses absolute imports like `from ui...` and imports top-level `config`.
  - Example: `PYTHONPATH=src:. python src/main.py`
- Console script (fixed):
  - `pyproject.toml` uses src layout via `package-dir = {"" = "src"}` so the console script target is `wingman = "main:main"`.
  - Install and run: `pip install -e .` (or `uv pip install -e .`), then `wingman`.
- Dependencies: Python 3.12+, PyQt6, python-xlib (requires X11), requests. Linux only. Wayland isn’t supported (uses Xlib atoms like `_NET_ACTIVE_WINDOW`).

## Project conventions and patterns

- Active window polling: `src/main.py` sets a `QTimer` at 100ms, and only repositions when the same geometry repeats 3 times (debounce). See `poll_active_window()`.
- Filtering noisy apps: `main.py` ignores names like `wingman`, `python*` when triggering auto docs.
- Geometry: `LinuxAppDetector._get_window_geometry` corrects for frame extents (`_NET_FRAME_EXTENTS`) and returns absolute `{x,y,width,height}` used by `MainWindow.reposition_to_window`.
- Terminal heuristics: If process name contains `gnome-terminal`, `LinuxAppDetector` attempts to replace the app name with the foreground child command via `/proc` and `pgrep`.
- Auto-positioning lifecycle:
  - Manual drag sets `auto_positioning_enabled=False` until toggled back on via the UI button.
  - System tray exposes Top/Bottom positions; `MainWindow.set_position` also supports Left/Right.
- Docs rendering: `MainWindow.set_documentation` calls `QTextBrowser.setHtml`. `DocRetriever.format_documentation` currently returns plain text; wrap content in minimal HTML or `<pre>` if adding richer formatting.
- Config: Use `config.py` (persists to `~/.config/wingman/config.json`). `src/main.py` imports `Config` from `config`.

## Integration points (where to extend)

- New doc sources or ordering: edit `src/core/doc_retriever.py::DocRetriever.get_documentation`. Example: call your new fetcher before/after `get_man_page`.
- Different app name rules: adjust filters in `src/main.py::handle_app_change_for_docs`.
- Positioning behavior: tweak debounce (timer/threshold) in `src/main.py` and layout bounds in `MainWindow.reposition_to_window`.
- Tray actions/shortcuts: `src/ui/system_tray.py` and buttons in `MainWindow`.

## Gotchas

- X11-only: running under Wayland will fail (Xlib queries for `_NET_ACTIVE_WINDOW`, `_NET_WM_PID`).
- `DocRetriever.get_online_docs` isn’t wired by default; use it explicitly if needed.
- Packaging uses `src` layout but top-level modules (`main.py`) ship directly; entry point is `main:main` by design.

If any of the above seems off or incomplete (e.g., you’re targeting Wayland or need tests), ask for clarification before large refactors.
