
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel, QTextBrowser, QScrollArea, QPushButton, QHBoxLayout
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QRect, Qt, QTimer, QPoint
from PyQt6.QtGui import QScreen, QGuiApplication


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.position = None
        self.is_being_moved = False  # Track if panel is being interactively moved
        self.auto_positioning_enabled = True  # Track if auto-positioning is enabled
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        
        # Set minimum size to prevent WM from making it too small
        self.setMinimumSize(400, 200)

        self.central_widget = QWidget()
        # Semi-transparent glass effect so underlying desktop remains visible
        # Updated to a charcoal-gray backdrop for better contrast
        self.central_widget.setStyleSheet("background-color: rgba(40, 40, 40, 128); color: white;")  # 0–255 alpha
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command...")
        # Ensure text is readable against the darker background
        self.command_input.setStyleSheet("color: white;")
        self.main_layout.addWidget(self.command_input)

        # Create a horizontal layout for app name and toggle button
        info_layout = QHBoxLayout()
        
        self.app_name_label = QLabel("Detected Application: None")
        # Set label text color to white for readability
        self.app_name_label.setStyleSheet("color: white;")
        info_layout.addWidget(self.app_name_label)
        
        # Add toggle button for auto-positioning
        self.auto_pos_toggle = QPushButton("Auto-Position: ON")
        self.auto_pos_toggle.setStyleSheet(
            "QPushButton { background-color: rgba(60, 60, 60, 180); color: white; border: 1px solid gray; padding: 2px 8px; }"
            "QPushButton:hover { background-color: rgba(80, 80, 80, 180); }"
        )
        self.auto_pos_toggle.clicked.connect(self.toggle_auto_positioning)
        info_layout.addWidget(self.auto_pos_toggle)
        
        info_widget = QWidget()
        info_widget.setLayout(info_layout)
        self.main_layout.addWidget(info_widget)

        self.doc_view = QTextBrowser()
        # Force white text within the documentation viewer for contrast
        self.doc_view.setStyleSheet("color: white;")
        self.doc_scroll_area = QScrollArea()
        self.doc_scroll_area.setWidget(self.doc_view)
        self.doc_scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.doc_scroll_area)

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.setDuration(300)

    def mousePressEvent(self, event):
        """Track when the panel is being moved interactively"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_being_moved = True
            self.drag_start_position = event.globalPosition().toPoint()
            self.drag_start_geometry = self.geometry()
            self.fixed_size_during_drag = self.size()  # lock size while dragging
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle interactive panel movement"""
        if self.is_being_moved and event.buttons() == Qt.MouseButton.LeftButton:
            # Calculate new position
            delta = event.globalPosition().toPoint() - self.drag_start_position
            new_pos = self.drag_start_geometry.topLeft() + delta
            # keep the original size to avoid resize jitter
            self.resize(self.fixed_size_during_drag)
            self.move(new_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Stop tracking panel movement and disable auto-positioning"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_being_moved = False
            # Disable auto-positioning when manually moved
            if self.auto_positioning_enabled:
                self.auto_positioning_enabled = False
                self.update_toggle_button_text()
        super().mouseReleaseEvent(event)

    def toggle_auto_positioning(self):
        """Toggle auto-positioning on/off"""
        self.auto_positioning_enabled = not self.auto_positioning_enabled
        self.update_toggle_button_text()

    def update_toggle_button_text(self):
        """Update the toggle button text based on current state"""
        if self.auto_positioning_enabled:
            self.auto_pos_toggle.setText("Auto-Position: ON")
            self.auto_pos_toggle.setStyleSheet(
                "QPushButton { background-color: rgba(60, 120, 60, 180); color: white; border: 1px solid gray; padding: 2px 8px; }"
                "QPushButton:hover { background-color: rgba(80, 140, 80, 180); }"
            )
        else:
            self.auto_pos_toggle.setText("Auto-Position: OFF")
            self.auto_pos_toggle.setStyleSheet(
                "QPushButton { background-color: rgba(120, 60, 60, 180); color: white; border: 1px solid gray; padding: 2px 8px; }"
                "QPushButton:hover { background-color: rgba(140, 80, 80, 180); }"
            )

    def set_position(self, position):
        """Slide the window to a screen edge.
        Only triggers if the requested position differs from the current one."""
        if position == self.position:
            return

        self.position = position
        primary_screen = QApplication.primaryScreen()
        if primary_screen is None:
            return
        screen_geometry = primary_screen.availableGeometry()
        width = 600  # Fixed width instead of full screen
        height = 200

        # Determine the target rectangle (end_rect) for the chosen edge
        if position == "top":
            end_rect = QRect(0, 0, width, height)
        elif position == "bottom":
            end_rect = QRect(0, screen_geometry.height() - height, width, height)
        elif position == "left":
            end_rect = QRect(0, 0, width, screen_geometry.height())
        elif position == "right":
            end_rect = QRect(screen_geometry.width() - width, 0, width, screen_geometry.height())
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
        # Don't trigger animations if we're being moved or recently moved
        if not self.is_being_interactively_moved():
            self.animation.setDirection(QPropertyAnimation.Direction.Forward)
            self.animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Don't trigger animations if we're being moved or recently moved
        if not self.is_being_interactively_moved():
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

    def is_being_interactively_moved(self):
        """Return True if the panel is currently being moved by the user or auto-positioning is disabled"""
        return self.is_being_moved or not self.auto_positioning_enabled

    def reposition_to_window(self, target_geometry: dict):
        """Position the panel so that it aligns with the given window's position and size.
        Uses the active window's x position and width instead of always spanning full screen.
        Ensures the panel stays on the same monitor as the target window.

        The function purposefully *bypasses the slide-in/out animation* used
        by :pymeth:`set_position` so that the panel can "jump" to the new
        position without first animating off-screen.  Any running
        animation is therefore stopped before the geometry change is applied.

        Parameters
        ----------
        target_geometry : dict
            Mapping returned by :pyclass:`~src.core.app_detector.LinuxAppDetector`.
            Expected keys are ``x``, ``y``, ``width`` and ``height``.
        """
        if not target_geometry or not self.auto_positioning_enabled:
            return

        # Extract target window position and dimensions
        target_x = target_geometry.get("x", 0)
        target_y = target_geometry.get("y", 0)
        target_width = target_geometry.get("width", 600)

        # Find the screen that contains the target window
        origin_pt = QPoint(target_x, target_y)
        target_screen = None
        for screen in QGuiApplication.screens():
            if screen and screen.geometry().contains(origin_pt):
                target_screen = screen
                break
        
        if target_screen is None:
            target_screen = QGuiApplication.primaryScreen()
        
        if target_screen is None:
            return  # No screen available, can't position
            
        screen_geom = target_screen.geometry()

        # Calculate panel dimensions - use target window width but cap at reasonable size
        panel_width = min(target_width, 800)  # Cap at 800px max
        panel_width = max(panel_width, 400)   # Minimum 400px
        panel_height = 200  # Fixed height

        # Position panel at the top of the target window, but ensure it stays on the same screen
        panel_x = target_x
        panel_y = target_y
        
        # Ensure panel stays within the target screen bounds
        if panel_x + panel_width > screen_geom.right():
            panel_x = screen_geom.right() - panel_width
        if panel_x < screen_geom.left():
            panel_x = screen_geom.left()
            
        if panel_y + panel_height > screen_geom.bottom():
            panel_y = screen_geom.bottom() - panel_height
        if panel_y < screen_geom.top():
            panel_y = screen_geom.top()

        # Check if we need to reposition (avoid redundant moves)
        current_geom = self.geometry()
        if (current_geom.x() == panel_x and 
            current_geom.y() == panel_y and 
            current_geom.width() == panel_width and 
            current_geom.height() == panel_height):
            return

        # Ensure any slide animation is stopped to prevent race conditions
        if self.animation.state() == QPropertyAnimation.State.Running:
            self.animation.stop()

        # Directly apply the new geometry (no animation)
        self.setGeometry(panel_x, panel_y, panel_width, panel_height)

        # Update cached position 
        self.position = "custom"

    def set_documentation(self, doc_text):
        self.doc_view.setHtml(doc_text)
