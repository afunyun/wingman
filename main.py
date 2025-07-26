import sys
import os
import json
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCursor
from src.ui.main_window import MainWindow
from src.ui.system_tray import SystemTray
from src.core.app_detector import LinuxAppDetector as AppDetector
from src.core.doc_retriever import DocRetriever

class Config:
    def __init__(self, path='config.json'):
        self.path = path
        self.data = self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, 'r') as f:
                return json.load(f)
        return {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def save(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=4)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    config = Config()
    app_detector = AppDetector()
    doc_retriever = DocRetriever(config)

    main_window = MainWindow()
    # Initialize dock at top so animation has valid start/end values
    main_window.set_position("top")

    app_detector.app_changed.connect(main_window.set_app_name)

    def handle_command():
        command = main_window.command_input.text()
        if command:
            doc = doc_retriever.get_documentation(command)
            main_window.set_documentation(doc)

    main_window.command_input.returnPressed.connect(handle_command)

    app_detector.start()
    main_window.show()

    system_tray = SystemTray(app, main_window)

    # Active window geometry polling logic (replaces mouse-edge detection)
    poll_timer = QTimer()
    # Track geometry stability across polls
    poll_state = {
        "last_geom": None,          # Tuple (x, y, w, h) from previous poll
        "stable_count": 0,          # Number of consecutive polls with unchanged geometry
        "last_docked_geom": None    # Geometry we most recently aligned to
    }

    def poll_active_window():
        """Poll the active window every 100 ms and reposition MainWindow once the
        target window has been stable (no geometry changes) for ≥ 300 ms.
        Skip repositioning if the panel is being interactively moved."""
        
        # Skip automatic repositioning while user is moving the panel
        if main_window.is_being_interactively_moved():
            return
            
        info = app_detector.get_active_window_info()
        geom = info.get("geometry", {})
        geom_tuple = (
            geom.get("x"),
            geom.get("y"),
            geom.get("width"),
            geom.get("height"),
        )

        # Update stability counter
        if geom_tuple == poll_state["last_geom"]:
            poll_state["stable_count"] += 1
        else:
            poll_state["stable_count"] = 1
            poll_state["last_geom"] = geom_tuple

        # If stable for 3 consecutive polls (~300 ms)
        if poll_state["stable_count"] >= 3:
            # Avoid redundant repositioning for the same geometry
            if geom_tuple != poll_state["last_docked_geom"] and None not in geom_tuple:
                poll_state["last_docked_geom"] = geom_tuple

                # Align MainWindow with active window position and size once stable.
                # Use the dedicated helper which safely stops any running animation
                # and positions the panel to match the active window.
                main_window.reposition_to_window(geom)

    poll_timer.timeout.connect(poll_active_window)
    poll_timer.start(100)  # Poll every 100 ms for geometry changes

    app.aboutToQuit.connect(app_detector.stop)

    sys.exit(app.exec())
