import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from ui.main_window import MainWindow
from ui.system_tray import SystemTray
from core.app_detector import LinuxAppDetector as AppDetector
from core.doc_retriever import DocRetriever
from config import Config


def main():
    """Main entry point for the wingman application."""
    app = QApplication(sys.argv)

    # Use shared config persisted under ~/.config/wingman/config.json
    config = Config()
    app_detector = AppDetector()
    doc_retriever = DocRetriever(config)

    main_window = MainWindow(doc_retriever)
    main_window.set_position("top")

    app_detector.app_changed.connect(main_window.set_app_name)

    def handle_app_change_for_docs(name, geometry):
        if name and name.lower() not in [
            "wingman",
            "main.py",
            "python",
            "python3",
            "python3.11",
            "python3.12",
            "pythonw",
        ]:
            name_lower = name.lower()
            if not any(term in name_lower for term in ["wingman", "python"]):
                main_window.handle_auto_documentation(name)

    app_detector.app_changed.connect(handle_app_change_for_docs)

    def handle_command():
        command = main_window.command_input.text()
        if command:
            doc = doc_retriever.get_documentation(command)
            main_window.set_documentation(doc)

    main_window.command_input.returnPressed.connect(handle_command)

    app_detector.start()
    main_window.show()

    # Keep a reference on the main window to avoid GC
    main_window.system_tray = SystemTray(app, main_window)

    poll_timer = QTimer()
    poll_state = {"last_geom": None, "stable_count": 0, "last_docked_geom": None}

    def poll_active_window():
        """Poll the active window every 100 ms and reposition MainWindow once the
        target window has been stable (no geometry changes) for ≥ 300 ms.
        Skip repositioning if the panel is being interactively moved."""

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

        if geom_tuple == poll_state["last_geom"]:
            poll_state["stable_count"] += 1
        else:
            poll_state["stable_count"] = 1
            poll_state["last_geom"] = geom_tuple

        if poll_state["stable_count"] >= 3:
            if geom_tuple != poll_state["last_docked_geom"] and None not in geom_tuple:
                poll_state["last_docked_geom"] = geom_tuple

                main_window.reposition_to_window(geom)

    poll_timer.timeout.connect(poll_active_window)
    poll_timer.start(100)

    app.aboutToQuit.connect(app_detector.stop)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
