
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel, QTextBrowser, QScrollArea
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QRect, Qt
from PyQt6.QtGui import QScreen


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.position = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")

        self.central_widget = QWidget()
        # Semi-transparent glass effect so underlying desktop remains visible
        # Updated to a charcoal-gray backdrop for better contrast
        self.central_widget.setStyleSheet("background-color: rgba(40, 40, 40, 128); color: white;")  # 0–255 alpha
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command...")
        # Ensure text is readable against the darker background
        self.command_input.setStyleSheet("color: white;")
        self.layout.addWidget(self.command_input)

        self.app_name_label = QLabel("Detected Application: None")
        # Set label text color to white for readability
        self.app_name_label.setStyleSheet("color: white;")
        self.layout.addWidget(self.app_name_label)

        self.doc_view = QTextBrowser()
        # Force white text within the documentation viewer for contrast
        self.doc_view.setStyleSheet("color: white;")
        self.doc_scroll_area = QScrollArea()
        self.doc_scroll_area.setWidget(self.doc_view)
        self.doc_scroll_area.setWidgetResizable(True)
        self.layout.addWidget(self.doc_scroll_area)

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.setDuration(300)

    def set_position(self, position):
        """Slide the window to a screen edge.
        Only triggers if the requested position differs from the current one."""
        if position == self.position:
            return

        self.position = position
        screen_geometry = QScreen.availableGeometry(QApplication.primaryScreen())
        width = screen_geometry.width()
        height = 200

        # Determine the target rectangle (end_rect) for the chosen edge
        if position == "top":
            end_rect = QRect(0, 0, width, height)
        elif position == "bottom":
            end_rect = QRect(0, screen_geometry.height() - height, width, height)
        elif position == "left":
            end_rect = QRect(0, 0, 300, screen_geometry.height())
        elif position == "right":
            end_rect = QRect(screen_geometry.width() - 300, 0, 300, screen_geometry.height())
        else:
            return

        # Animate from current geometry to the new one
        start_rect = self.geometry()
        self.animation.stop()
        self.animation.setStartValue(start_rect)
        self.animation.setEndValue(end_rect)
        self.animation.start()
        # Also set final geometry immediately so tests based on geometry are correct
        self.setGeometry(end_rect)
            
    def enterEvent(self, event):
        self.animation.setDirection(QPropertyAnimation.Direction.Forward)
        self.animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.animation.setDirection(QPropertyAnimation.Direction.Backward)
        self.animation.start()
        super().leaveEvent(event)

    def set_app_name(self, name, geometry=None):
        """Slot to receive application name and geometry from AppDetector"""
        if geometry:
            geo_str = f" ({geometry['x']},{geometry['y']} {geometry['width']}x{geometry['height']})"
        else:
            geo_str = ""
        self.app_name_label.setText(f"Detected Application: {name}{geo_str}")

    def reposition_to_window(self, target_geometry: dict):
        """Teleport the panel so that its *top* edge lines up with the given
        window's top edge.  This is intended to be used by higher-level
        polling logic that tracks the active window geometry.

        The function purposefully *bypasses the slide-in/out animation* used
        by :pymeth:`set_position` so that the panel can "jump" to the new
        y-coordinate without first animating off-screen.  Any running
        animation is therefore stopped before the geometry change is applied.

        Parameters
        ----------
        target_geometry : dict
            Mapping returned by :pyclass:`~src.core.app_detector.LinuxAppDetector`.
            Expected keys are ``x``, ``y``, ``width`` and ``height``.  Only the
            ``y`` value is actually required – the panel always spans the full
            screen width and has a fixed height of ``200`` pixels consistent
            with :pymeth:`set_position`.
        """
        if not target_geometry:
            return

        # Extract y coordinate; default to 0 if not present
        target_y = target_geometry.get("y", 0)

        # Do nothing if we are already aligned to this y coordinate
        if self.geometry().y() == target_y:
            return

        # Ensure any slide animation is stopped to prevent race conditions
        if self.animation.state() == QPropertyAnimation.State.Running:
            self.animation.stop()

        screen_geometry = QScreen.availableGeometry(QApplication.primaryScreen())
        width = screen_geometry.width()
        height = 200  # Keep in sync with set_position()

        # Directly apply the new geometry (no animation)
        self.setGeometry(0, target_y, width, height)

        # Update cached position so a subsequent set_position("top") call that
        # might be triggered elsewhere does not animate unnecessarily.
        self.position = "top"

    def set_documentation(self, doc_text):
        self.doc_view.setHtml(doc_text)
