"""Platform-specific active window detection utilities.

This module previously targeted only X11 via :mod:`python-xlib`, which meant
that running the application under a Wayland compositor resulted in the panel
always receiving a ``(0, 0)`` geometry.  The panel would consequently jump to
the top left corner of the current monitor.

The detector now chooses an appropriate backend at runtime.  On traditional
X11 environments the existing :mod:`python-xlib` implementation is used.  When
``WAYLAND_DISPLAY`` is present we attempt to query the compositor for the
focused window using common command line tools:

* ``swaymsg`` – Sway/other wlroots compositors
* ``hyprctl`` – Hyprland

If none of the Wayland helpers are available we gracefully fall back to the
X11 path so that the application still functions when running under XWayland.
"""

from __future__ import annotations

import json
import os
import subprocess
import shutil

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

try:  # Optional import, only required on X11
    import Xlib  # type: ignore
    import Xlib.display  # type: ignore
except Exception:  # pragma: no cover - only triggered on systems without Xlib
    Xlib = None

class LinuxAppDetector(QObject):
    """Emit information about the currently focused window.

    The detector polls the active window at a configurable interval and emits
    :pyattr:`app_changed` whenever the window's application name changes.  A
    backend is chosen depending on the environment:

    * **X11** – Uses :mod:`python-xlib` as before.
    * **Wayland** – Queries the compositor using ``swaymsg`` or ``hyprctl``.

    The public API remains the same regardless of backend.
    """

    # Emits the application name and a geometry dict {"x": int, "y": int, "width": int, "height": int}
    app_changed = pyqtSignal(str, dict)

    def __init__(self):
        super().__init__()

        self.backend = self._detect_backend()
        self.display = None
        if self.backend == "x11" and Xlib is not None:
            try:
                self.display = Xlib.display.Display()
            except Exception:
                # If we cannot connect to an X server fall back to Wayland
                self.backend = "wayland"

        self.tracking_available = self._determine_tracking_capability()

        self.last_app_name = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_active_window)

    def _detect_backend(self) -> str:
        """Return ``"wayland"`` if a Wayland session is detected, ``"x11"`` otherwise."""
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        return "x11"

    def _determine_tracking_capability(self) -> bool:
        """Return True if active window geometry can be queried."""
        if self.backend == "x11":
            return self.display is not None
        return (shutil.which("swaymsg") is not None or
                shutil.which("hyprctl") is not None or
                self.display is not None)

    def tracking_supported(self) -> bool:
        """Expose whether window tracking is available."""
        return self.tracking_available

    def start(self, interval=1000):
        self.timer.start(interval)

    def stop(self):
        self.timer.stop()

    def check_active_window(self):
        """Poll the backend and emit :pyattr:`app_changed` when necessary."""
        info = self.get_active_window_info()
        app_name = info.get("app_name")
        geometry = info.get("geometry")
        if app_name and app_name != self.last_app_name:
            self.last_app_name = app_name
            self.app_changed.emit(app_name, geometry)

    # ------------------------------------------------------------------
    # Backend specific implementations
    # ------------------------------------------------------------------
    def get_active_window_info(self):
        """Return information about the active window for the current backend."""
        if self.backend == "wayland":
            info = self._get_wayland_active_window_info()
            if info:
                return info

        # Default to X11
        if not self.display:
            return {"title": "Unknown", "app_name": None, "process_name": "Unknown", "geometry": {}}

        root = self.display.screen().root
        window_id = root.get_full_property(self.display.intern_atom('_NET_ACTIVE_WINDOW'), Xlib.X.AnyPropertyType).value[0]
        window = self.display.create_resource_object('window', window_id)

        title = self._get_window_title(window)
        pid = self._get_window_pid(window)
        process_name = self._get_process_name(pid)
        app_name = self._get_app_name(window)
        geometry = self._get_window_geometry(window)

        if "gnome-terminal" in process_name:
            # Special handling for terminal windows
            app_name = self._get_terminal_command(pid) or app_name

        return {
            "title": title,
            "app_name": app_name,
            "process_name": process_name,
            "geometry": geometry
        }

    # ---------------------- Wayland helpers ---------------------------------
    def _get_wayland_active_window_info(self):
        """Try a series of compositor specific commands to obtain window info."""

        info = self._query_swaymsg() or self._query_hyprctl()
        return info

    def _query_swaymsg(self):
        """Return focused window info using ``swaymsg -t get_tree`` if available."""
        if shutil.which("swaymsg") is None:
            return None
        try:
            output = subprocess.check_output(["swaymsg", "-t", "get_tree"], text=True)
            tree = json.loads(output)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return None

        node = self._find_focused_node(tree)
        if not node:
            return None

        rect = node.get("rect", {})
        geometry = {
            "x": rect.get("x", 0),
            "y": rect.get("y", 0),
            "width": rect.get("width", 0),
            "height": rect.get("height", 0),
        }
        app_name = node.get("app_id") or node.get("name") or "Unknown"
        return {
            "title": node.get("name", ""),
            "app_name": app_name,
            "process_name": app_name,
            "geometry": geometry,
        }

    def _find_focused_node(self, node):
        if node.get("focused"):
            return node
        for child in node.get("nodes", []) + node.get("floating_nodes", []):
            found = self._find_focused_node(child)
            if found:
                return found
        return None

    def _query_hyprctl(self):
        """Return focused window info using ``hyprctl activewindow -j`` if available."""
        if shutil.which("hyprctl") is None:
            return None
        try:
            output = subprocess.check_output(["hyprctl", "activewindow", "-j"], text=True)
            data = json.loads(output)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return None

        at = data.get("at", [0, 0])
        size = data.get("size", [0, 0])
        geometry = {"x": at[0], "y": at[1], "width": size[0], "height": size[1]}
        app_name = data.get("class") or data.get("initialClass") or "Unknown"
        return {
            "title": data.get("title", ""),
            "app_name": app_name,
            "process_name": app_name,
            "geometry": geometry,
        }

    def _get_window_title(self, window):
        try:
            return window.get_wm_name()
        except (Xlib.error.XError, UnicodeDecodeError):
            return "Unknown"

    def _get_window_pid(self, window):
        try:
            pid_prop = window.get_full_property(self.display.intern_atom('_NET_WM_PID'), Xlib.X.AnyPropertyType)
            if pid_prop:
                return pid_prop.value[0]
        except Xlib.error.XError:
            pass
        return None

    def _get_process_name(self, pid):
        if pid:
            try:
                with open(f"/proc/{pid}/comm", "r") as f:
                    return f.read().strip()
            except FileNotFoundError:
                pass
        return "Unknown"

    def _get_app_name(self, window):
        try:
            class_prop = window.get_wm_class()
            if class_prop:
                return class_prop[1]
        except (Xlib.error.XError, UnicodeDecodeError):
            pass
        return "Unknown"

    def _get_window_geometry(self, window):
        """Return a dict with absolute geometry taking frame extents into account."""
        try:
            geom = window.get_geometry()
            # Translate window coordinates to root window (absolute screen position)
            abs_coords = window.translate_coords(self.display.screen().root, 0, 0)
            # translate_coords returns a TranslateCoords object with x, y attributes
            x = abs_coords.x
            y = abs_coords.y
            width = geom.width
            height = geom.height
            # Adjust for frame extents if available
            try:
                frame_prop = window.get_full_property(
                    self.display.intern_atom('_NET_FRAME_EXTENTS'),
                    Xlib.X.AnyPropertyType
                )
                if frame_prop and len(frame_prop.value) >= 4:
                    left, right, top, bottom = frame_prop.value[:4]
                    x -= left
                    y -= top
                    width += left + right
                    height += top + bottom
            except Xlib.error.XError:
                pass
            return {"x": int(x), "y": int(y), "width": int(width), "height": int(height)}
        except Xlib.error.XError:
            return {"x": 0, "y": 0, "width": 0, "height": 0}

    def _get_terminal_command(self, pid):
        """
        Attempt to get the command running in the terminal.
        This is a bit of a hack and might not be reliable.
        """
        try:
            # Find the child process of the terminal
            # This assumes the shell is a direct child of the terminal process
            children_pids = subprocess.check_output(['pgrep', '-P', str(pid)]).decode().split()
            if children_pids:
                # Let's take the first child, which should be the shell
                shell_pid = children_pids[0]
                # Now find the child of the shell
                command_pids = subprocess.check_output(['pgrep', '-P', str(shell_pid)]).decode().split()
                if command_pids:
                    command_pid = command_pids[0]
                    with open(f"/proc/{command_pid}/cmdline", "r") as f:
                        return f.read().strip().replace('\x00', ' ')
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return None
