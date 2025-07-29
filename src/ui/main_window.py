
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel, QTextBrowser, QScrollArea, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QRect, Qt, QTimer, QPoint
from PyQt6.QtGui import QScreen, QGuiApplication, QKeySequence, QShortcut


class MainWindow(QMainWindow):
    def __init__(self, doc_retriever=None):
        super().__init__()
        self.position = None
        self.is_being_moved = False  # Track if panel is being interactively moved
        self.auto_positioning_enabled = True  # Track if auto-positioning is enabled
        self.doc_retriever = doc_retriever  # Documentation retriever instance
        
        # Timer and application state tracking
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.show_confirmation_dialog)
        self.countdown_timer.setSingleShot(True)  # Timer fires only once
        self.current_detected_app = None  # Track the current detected application
        
        # Documentation delay timer
        self.doc_delay_timer = QTimer()
        self.doc_delay_timer.setSingleShot(True)
        self.doc_delay_timer.timeout.connect(self._show_delayed_documentation)
        self.pending_doc_app = None
        
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

        # Create a horizontal layout for app name and buttons
        info_layout = QHBoxLayout()
        
        self.app_name_label = QLabel("Detected Application: None")
        # Set label text color to white for readability
        self.app_name_label.setStyleSheet("color: white;")
        info_layout.addWidget(self.app_name_label)
        
        # Add documentation load button
        self.load_docs_button = QPushButton("Load Docs")
        self.load_docs_button.setStyleSheet(
            "QPushButton { background-color: rgba(60, 100, 60, 180); color: white; border: 1px solid gray; padding: 2px 8px; }"
            "QPushButton:hover { background-color: rgba(80, 120, 80, 180); }"
            "QPushButton:disabled { background-color: rgba(40, 40, 40, 100); color: gray; }"
        )
        self.load_docs_button.clicked.connect(self.load_pending_documentation)
        self.load_docs_button.setVisible(False)  # Initially hidden
        info_layout.addWidget(self.load_docs_button)
        
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
        
        # Store the detected application name
        self.current_detected_app = name
        
        # Stop any existing timer
        if self.countdown_timer.isActive():
            self.countdown_timer.stop()
        
        # Start a new 30-second timer if we have a valid app name
        if name and name != "None":
            self.countdown_timer.start(30000)  # 30 seconds in milliseconds

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
    
    def show_confirmation_dialog(self):
        """Show a confirmation dialog after the 30-second countdown expires"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Action Required")
        msg_box.setText(f"Do you want to continue with the detected application:\n\n{self.current_detected_app}")
        msg_box.setInformativeText("Press 'Y' for Yes or 'N' for No")
        
        # Create custom buttons with keyboard shortcuts
        yes_button = msg_box.addButton("&Yes", QMessageBox.ButtonRole.YesRole)
        no_button = msg_box.addButton("&No", QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(yes_button)
        
        # Position dialog relative to main window center
        main_geometry = self.geometry()
        dialog_width = 400
        dialog_height = 150
        
        # Calculate center position relative to main window
        center_x = main_geometry.x() + (main_geometry.width() - dialog_width) // 2
        center_y = main_geometry.y() + (main_geometry.height() - dialog_height) // 2
        
        # Ensure dialog stays on screen
        screen = QApplication.screenAt(QPoint(center_x, center_y))
        if screen:
            screen_geometry = screen.availableGeometry()
            center_x = max(screen_geometry.x(), min(center_x, screen_geometry.x() + screen_geometry.width() - dialog_width))
            center_y = max(screen_geometry.y(), min(center_y, screen_geometry.y() + screen_geometry.height() - dialog_height))
        
        msg_box.setGeometry(center_x, center_y, dialog_width, dialog_height)
        
        # Enhanced dark theme styling to match the main application
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: rgba(40, 40, 40, 240);
                color: white;
                border: 2px solid rgba(80, 80, 80, 180);
                border-radius: 8px;
                font-size: 12px;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 12px;
                padding: 10px;
            }
            QMessageBox QPushButton {
                background-color: rgba(60, 60, 60, 200);
                color: white;
                border: 1px solid rgba(100, 100, 100, 180);
                border-radius: 4px;
                padding: 8px 20px;
                min-width: 80px;
                font-size: 11px;
                font-weight: bold;
                margin: 4px;
            }
            QMessageBox QPushButton:hover {
                background-color: rgba(80, 80, 80, 220);
                border: 1px solid rgba(120, 120, 120, 200);
            }
            QMessageBox QPushButton:pressed {
                background-color: rgba(100, 100, 100, 200);
                border: 1px solid rgba(140, 140, 140, 220);
            }
            QMessageBox QPushButton:default {
                background-color: rgba(70, 120, 70, 200);
                border: 1px solid rgba(100, 150, 100, 180);
            }
            QMessageBox QPushButton:default:hover {
                background-color: rgba(90, 140, 90, 220);
                border: 1px solid rgba(120, 170, 120, 200);
            }
        """)
        
        # Add keyboard shortcuts
        yes_shortcut = QShortcut(QKeySequence("Y"), msg_box)
        yes_shortcut.activated.connect(lambda: msg_box.done(QMessageBox.StandardButton.Yes.value))
        
        no_shortcut = QShortcut(QKeySequence("N"), msg_box)
        no_shortcut.activated.connect(lambda: msg_box.done(QMessageBox.StandardButton.No.value))
        
        result = msg_box.exec()
        return msg_box.clickedButton() == yes_button
    
    def start_countdown_timer(self):
        """Start the 30-second countdown timer"""
        self.countdown_timer.start(30000)  # 30 seconds in milliseconds
    
    def reset_timer_for_new_app(self, app_name):
        """Reset the timer when a new application is detected"""
        # Only reset if this is actually a different application
        if self.current_detected_app != app_name:
            self.current_detected_app = app_name
            
            # Stop any existing timer
            if self.countdown_timer.isActive():
                self.countdown_timer.stop()
            
            # Start a new countdown for the new application
            if app_name and app_name != "None":
                self.start_countdown_timer()
    
    def handle_auto_documentation(self, app_name):
        """Handle auto-documentation for detected applications.
        
        Stores the application name and starts a 5-second delay timer before showing
        the documentation load button. This gives users time to settle into the new application
        before being prompted.
        
        Args:
            app_name (str): The name of the detected application
        """
        # Cancel any pending documentation request and hide button
        if self.doc_delay_timer.isActive():
            self.doc_delay_timer.stop()
        self.load_docs_button.setVisible(False)
        
        if not self.doc_retriever or not app_name or app_name == "None":
            return
        
        # Extract clean application name (remove path and extension if present)
        clean_app_name = app_name
        if '/' in clean_app_name:
            clean_app_name = clean_app_name.split('/')[-1]
        if '.' in clean_app_name:
            clean_app_name = clean_app_name.split('.')[0]
        
        # Store the app name for the delayed documentation
        self.pending_doc_app = clean_app_name
        
        # Stop any existing delay timer
        if self.doc_delay_timer.isActive():
            self.doc_delay_timer.stop()
        
        # Start the 5-second delay timer
        self.doc_delay_timer.start(5000)  # 5 seconds in milliseconds
    
    def _show_delayed_documentation(self):
        """Called by the delay timer to show the documentation load button.
        
        This method is triggered after the 5-second delay to make the documentation
        load button visible for the pending application.
        """
        if not self.pending_doc_app:
            return
        
        # Update button text and make it visible
        self.load_docs_button.setText(f"Load Docs for {self.pending_doc_app}")
        self.load_docs_button.setVisible(True)
    
    def load_pending_documentation(self):
        """Load documentation for the pending application when button is clicked."""
        if not self.pending_doc_app:
            return
        
        app_name = self.pending_doc_app
        self.pending_doc_app = None  # Clear the pending app
        self.load_docs_button.setVisible(False)  # Hide the button
        
        # Retrieve and display documentation
        try:
            documentation = self.doc_retriever.get_documentation(app_name)
            self.set_documentation(documentation)
        except Exception as e:
            # Handle any errors gracefully
            error_msg = f"Error retrieving documentation for {app_name}: {str(e)}"
            self.set_documentation(error_msg)
    
    def show_documentation_dialog(self, app_name):
        """Show a non-intrusive dialog asking if the user wants documentation.
        
        Args:
            app_name (str): The name of the application
            
        Returns:
            bool: True if user wants documentation, False otherwise
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Documentation Available")
        msg_box.setText(f"Would you like to view documentation for '{app_name}'?")
        msg_box.setInformativeText("This will retrieve and display help information for the detected application.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)  # Non-intrusive default
        
        # Style the message box to match the main window theme
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: rgba(40, 40, 40, 200);
                color: white;
                border: 1px solid gray;
            }
            QMessageBox QLabel {
                color: white;
            }
            QMessageBox QPushButton {
                background-color: rgba(60, 60, 60, 180);
                color: white;
                border: 1px solid gray;
                padding: 5px 15px;
                min-width: 60px;
                margin: 2px;
            }
            QMessageBox QPushButton:hover {
                background-color: rgba(80, 80, 80, 180);
            }
            QMessageBox QPushButton:pressed {
                background-color: rgba(100, 100, 100, 180);
            }
        """)
        
        result = msg_box.exec()
        return result == QMessageBox.StandardButton.Yes
