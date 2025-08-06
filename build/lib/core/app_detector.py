import Xlib
import Xlib.display
import subprocess
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


class LinuxAppDetector(QObject):
    app_changed = pyqtSignal(str, dict)

    def __init__(self):
        super().__init__()
        self.display = Xlib.display.Display()
        self.last_app_name = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_active_window)

    def start(self, interval=1000):
        self.timer.start(interval)

        self.timer.stop()

    def check_active_window(self):
        info = self.get_active_window_info()
        app_name = info.get("app_name")
        geometry = info.get("geometry")
        if app_name and app_name != self.last_app_name:
            self.last_app_name = app_name
            self.app_changed.emit(app_name, geometry)

    def get_active_window_info(self):
        root = self.display.screen().root
        window_id = root.get_full_property(
            self.display.intern_atom("_NET_ACTIVE_WINDOW"), Xlib.X.AnyPropertyType
        ).value[0]
        window = self.display.create_resource_object("window", window_id)

        title = self._get_window_title(window)
        pid = self._get_window_pid(window)
        process_name = self._get_process_name(pid)
        app_name = self._get_app_name(window)
        geometry = self._get_window_geometry(window)

        if "gnome-terminal" in process_name:
            app_name = self._get_terminal_command(pid) or app_name

        return {
            "title": title,
            "app_name": app_name,
            "process_name": process_name,
            "geometry": geometry,
        }

    def _get_window_title(self, window):
        try:
            return window.get_wm_name()
        except (Xlib.error.XError, UnicodeDecodeError):
            return "Unknown"

    def _get_window_pid(self, window):
        try:
            pid_prop = window.get_full_property(
                self.display.intern_atom("_NET_WM_PID"), Xlib.X.AnyPropertyType
            )
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
            abs_coords = window.translate_coords(self.display.screen().root, 0, 0)
            x = abs_coords.x
            y = abs_coords.y
            width = geom.width
            height = geom.height
            try:
                frame_prop = window.get_full_property(
                    self.display.intern_atom("_NET_FRAME_EXTENTS"),
                    Xlib.X.AnyPropertyType,
                )
                if frame_prop and len(frame_prop.value) >= 4:
                    left, right, top, bottom = frame_prop.value[:4]
                    x -= left
                    y -= top
                    width += left + right
                    height += top + bottom
            except Xlib.error.XError:
                pass
            return {
                "x": int(x),
                "y": int(y),
                "width": int(width),
                "height": int(height),
            }
        except Xlib.error.XError:
            return {"x": 0, "y": 0, "width": 0, "height": 0}

    def _get_terminal_command(self, pid):
        """
        Attempt to get the command running in the terminal.
        This is a bit of a hack and might not be reliable.
        """
        try:
            children_pids = (
                subprocess.check_output(["pgrep", "-P", str(pid)]).decode().split()
            )
            if children_pids:
                shell_pid = children_pids[0]
                command_pids = (
                    subprocess.check_output(["pgrep", "-P", str(shell_pid)])
                    .decode()
                    .split()
                )
                if command_pids:
                    command_pid = command_pids[0]
                    with open(f"/proc/{command_pid}/cmdline", "r") as f:
                        return f.read().strip().replace("\x00", " ")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return None
