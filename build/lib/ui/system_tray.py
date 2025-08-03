from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction

class SystemTray:
    def __init__(self, app, main_window):
        self.app = app
        self.main_window = main_window

        self.tray_icon = QSystemTrayIcon(QIcon.fromTheme("applications-utilities"), self.app)
        self.tray_icon.setToolTip("WingMAN")

        self.menu = QMenu()
        self.create_actions()
        self.tray_icon.setContextMenu(self.menu)

        self.tray_icon.show()

    def create_actions(self):
        show_hide_action = QAction("Show/Hide", self.app)
        show_hide_action.triggered.connect(self.toggle_window)
        self.menu.addAction(show_hide_action)

        settings_action = QAction("Settings", self.app)
        settings_action.triggered.connect(self.open_settings)
        self.menu.addAction(settings_action)

        position_menu = self.menu.addMenu("Position")
        top_action = QAction("Top", self.app)
        top_action.triggered.connect(lambda: self.main_window.set_position("top"))
        position_menu.addAction(top_action)

        bottom_action = QAction("Bottom", self.app)
        bottom_action.triggered.connect(lambda: self.main_window.set_position("bottom"))
        position_menu.addAction(bottom_action)

        self.menu.addSeparator()
7
        exit_action = QAction("Exit", self.app)
        exit_action.triggered.connect(self.app.quit)
        self.menu.addAction(exit_action)

    def toggle_window(self):
        if self.main_window.isVisible():
            self.main_window.hide()
        else:
            self.main_window.show()

    def open_settings(self):
        # Placeholder for settings dialog
        pass
