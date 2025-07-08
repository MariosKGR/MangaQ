import sys
import os
import json
import re
import uuid
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QListWidget, QListWidgetItem, QLabel, QListView, QStackedWidget,
    QLineEdit, QTextEdit, QDialog, QDialogButtonBox, QTableWidget,
    QTableWidgetItem, QButtonGroup, QHeaderView, QStyle, QSizePolicy,
    QMenu, QMessageBox, QSpacerItem
)
from PySide6.QtGui import QPixmap, QIcon, QColor, QPainter, QPen, QDesktopServices
from PySide6.QtCore import Qt, QSize, QMargins, QTimer, QRect, QUrl, QEvent


# --- Notification Popup Class ---
class NotificationPopup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint |       # No border or title bar
            Qt.WindowStaysOnTopHint |      # Always on top of other app windows
            Qt.BypassWindowManagerHint     # Don't show in taskbar
        )
        self.setAttribute(Qt.WA_TranslucentBackground) # Allow transparency for rounded corners

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 10, 15, 10) # Padding inside the popup

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("""
            color: white;
            padding: 8px 15px;
            border-radius: 8px;
            font-size: 14px;
        """)
        self.layout.addWidget(self.label)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        # Timer directly hides the widget when it times out
        self.timer.timeout.connect(self.hide) 

        self.hide() # Start hidden

    def show_message(self, message, is_error=False, duration_ms=3000): # Default duration changed to 3 seconds
        self.label.setText(message)
        if is_error:
            self.label.setStyleSheet(self.label.styleSheet() + "background-color: #e74c3c;") # Red for error
        else:
            self.label.setStyleSheet(self.label.styleSheet() + "background-color: #27ae60;") # Green for success

        # Position the popup
        self.adjustSize() # Adjust to text content
        # Use parent's current geometry to calculate position
        parent_rect = self.parent().geometry() if self.parent() else QApplication.primaryScreen().geometry()
        
        # Calculate position for bottom-right
        # 20px padding from right and bottom edges
        x = parent_rect.right() - self.width() - 20
        y = parent_rect.bottom() - self.height() - 20
        self.move(x, y)

        self.setWindowOpacity(1.0) # Make it instantly visible (no fade-in)
        self.show()

        # Start the timer to hide the notification after duration_ms
        if duration_ms > 0:
            self.timer.start(duration_ms)
        elif duration_ms == 0:
            self.timer.stop()


class FolderDialog(QDialog):
    def __init__(self, folder_path, manga_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Manga Info" if manga_data is None else "Edit Manga Info")
        self.folder_path = folder_path
        self.cover_path = None
        self.manga_data = manga_data # This now includes a 'uuid' if present

        # Ensure the icons folder path is correct and exists
        self._icons_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
        os.makedirs(self._icons_path, exist_ok=True) 
        print(f"DEBUG: Icons path: {self._icons_path}") # Debug print

        # Set the dialog's background to match the main app's general theme (e.g., #2e2e2e)
        self.setStyleSheet("background-color: #2e2e2e; color: white;") # Added white color for text
        
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # --- Top Section: Cover Image and Inputs ---
        top_layout = QHBoxLayout()

        # Left: Cover image area with button on top
        self.cover_container = QWidget()
        self.cover_container.setFixedSize(160, 200) # Fixed size for the container
        # Set a background for the container that matches the desired "transparent" fill
        # This dark background will show through areas not covered by the image
        self.cover_container.setStyleSheet("background-color: #1a1a1a; border-radius: 5px;") 
        
        self.cover_label = QLabel(self.cover_container) # Make container its parent
        self.cover_label.setGeometry(0, 0, 160, 200) # Fills the container
        # Initial stylesheet for "No Cover" state, or when no image is loaded
        self.cover_label.setStyleSheet("border: 1px dashed gray; color: lightgray;") # Removed background-color here
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setText("No Cover") # Set initial text

        self.cover_overlay = QLabel(self.cover_container) # Make container its parent
        self.cover_overlay.setGeometry(0, 0, 160, 200) # Fills the container
        self.cover_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0);") # Initially transparent
        self.cover_overlay.hide() # Initially hidden

        # The button to select cover - ONLY ICON
        self.cover_button = QPushButton(self.cover_container) # Make container its parent
        self.cover_button.clicked.connect(self.select_cover)
        
        # Set the icon for the choose cover button
        self.cover_button.setIcon(QIcon(os.path.join(self._icons_path, "add_circle.svg")))
        self.cover_button.setIconSize(QSize(32, 32)) # Slightly larger icon for emphasis
        self.cover_button.setText("") # NO TEXT
        
        self.cover_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(65, 105, 225, 180); /* Royal Blue with transparency */
                color: white;
                padding: 5px; /* Adjust padding for icon-only button */
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: rgba(50, 80, 200, 200);
            }
        """)
        self.cover_button.setFixedSize(45, 45) # Adjusted to be a square button for the icon

        top_layout.addWidget(self.cover_container) # Add the container to the main layout

        # Right: Metadata Inputs
        metadata_input_layout = QVBoxLayout()

        metadata_input_layout.addWidget(QLabel("Title:"))
        self.name_input = QLineEdit(os.path.basename(self.folder_path))
        # Style QLineEdit for dark theme
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #3a3a3a; /* Slightly lighter than main dialog for input field */
                border: 1px solid #555555;
                border-radius: 4px;
                color: white;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #3a72d2; /* Blue focus border */
            }
        """)
        metadata_input_layout.addWidget(self.name_input)

        metadata_input_layout.addWidget(QLabel("Description:"))
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter manga description here...")
        # Style QTextEdit for dark theme
        self.description_input.setStyleSheet("""
            QTextEdit {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 4px;
                color: white;
                padding: 5px;
            }
            QTextEdit:focus {
                border: 1px solid #3a72d2;
            }
        """)
        metadata_input_layout.addWidget(self.description_input)

        top_layout.addLayout(metadata_input_layout)
        main_layout.addLayout(top_layout)

        # --- Populate if editing ---
        if self.manga_data:
            self.name_input.setText(self.manga_data.get("name", ""))
            self.description_input.setText(self.manga_data.get("description", ""))
            self.cover_path = self.manga_data.get("cover")
        
        self._update_cover_preview() # Call new method to set initial state

        # --- Bottom Section: Dialog Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        # Style QDialogButtonBox buttons for dark theme
        self.button_box.setStyleSheet("""
            QPushButton {
                background-color: #3a72d2; /* Blue for OK */
                color: white;
                padding: 6px 15px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #305bbf;
            }
            QPushButton#qt_dialog_buttonbox_cancel { /* Specific ID for cancel button */
                background-color: #555555; /* Grey for Cancel */
            }
            QPushButton#qt_dialog_buttonbox_cancel:hover {
                background-color: #666666;
            }
        """)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        
        # Position the button and overlay after all layout is set
        self._position_cover_elements() 

    def _position_cover_elements(self):
        # Center the button horizontally and vertically on the cover_container
        btn_x = (self.cover_container.width() - self.cover_button.width()) // 2
        btn_y = (self.cover_container.height() - self.cover_button.height()) // 2
        self.cover_button.move(btn_x, btn_y)

        # Ensure overlay covers the label exactly
        self.cover_overlay.setGeometry(self.cover_label.geometry())
        
        # Bring elements to front in drawing order
        self.cover_label.lower() # Make sure label is at the bottom
        self.cover_overlay.raise_() # Bring overlay on top of label
        self.cover_button.raise_() # Bring button on top of overlay


    def _update_cover_preview(self):
        if self.cover_path and os.path.exists(self.cover_path):
            pixmap = QPixmap(self.cover_path)
            if pixmap.isNull():
                print(f"ERROR: Could not load pixmap from {self.cover_path}")
                # Fallback to 'no cover' state if loading fails
                self.cover_path = None
                self._update_cover_preview()
                return

            scaled_pixmap = pixmap.scaled(
                self.cover_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.cover_label.setPixmap(scaled_pixmap)
            # Remove border and ensure background is transparent for the image itself
            self.cover_label.setStyleSheet("border: none; background-color: transparent;")
            self.cover_label.setText("") # Clear "No Cover" text

            self.cover_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 80);") # Darker overlay (e.g., 80/255 opacity)
            self.cover_overlay.show()

            # --- START OF MODIFICATION ---
            # Now always use add_circle.svg for the cover button when a cover is present
            add_circle_icon_path = os.path.join(self._icons_path, "add_circle.svg")
            if os.path.exists(add_circle_icon_path):
                self.cover_button.setIcon(QIcon(add_circle_icon_path))
            else:
                print(f"ERROR: add_circle.svg not found at {add_circle_icon_path}. Cannot set icon for cover button.")
                self.cover_button.setIcon(QIcon()) # Set empty icon if not found
            # --- END OF MODIFICATION ---

            self.cover_button.setIconSize(QSize(32,32))
            self.cover_button.setFixedSize(45, 45) # Maintain square size
            self.cover_button.setText("") # Ensure text is empty
        else:
            self.cover_label.clear() # Clear any previous pixmap
            self.cover_label.setText("No Cover")
            # Revert to dashed border and dark background when no cover
            self.cover_label.setStyleSheet("border: 1px dashed gray; color: lightgray; background-color: transparent;")

            self.cover_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0);") # Transparent
            self.cover_overlay.hide()

            # Restore add_circle icon when no cover
            add_circle_icon_path = os.path.join(self._icons_path, "add_circle.svg")
            if os.path.exists(add_circle_icon_path):
                self.cover_button.setIcon(QIcon(add_circle_icon_path))
            else:
                print(f"ERROR: add_circle.svg not found at {add_circle_icon_path}.")
                self.cover_button.setIcon(QIcon()) # Set empty icon if not found

            self.cover_button.setIconSize(QSize(32,32))
            self.cover_button.setFixedSize(45, 45)
            self.cover_button.setText("") # Ensure text is empty
        
        self._position_cover_elements() # Re-position after state change
    
    def select_cover(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Cover", "", "Images (*.png *.webp *.jpg *.jpeg *.svg)") # Added SVG
        if file:
            self.cover_path = file
            self._update_cover_preview() # Update the preview immediately

    def get_data(self):
        data = {
            "name": self.name_input.text(),
            "description": self.description_input.toPlainText(),
            "cover": self.cover_path,
            "folder": self.folder_path
        }
        # Preserve the existing UUID if editing
        if self.manga_data and "uuid" in self.manga_data:
            data["uuid"] = self.manga_data["uuid"]
        return data

# --- Info Tab Widget ---
class InfoTabWidget(QWidget):
    def __init__(self, icons_path, parent=None):
        super().__init__(parent)
        self._icons_path = icons_path
        
        # Set the InfoTabWidget's background to match the QStackedWidget's background
        self.setStyleSheet("background-color: #1e1e1e; color: white;") # Ensuring text is visible

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter) # Center the entire layout

        # Spacer to push content to center vertically
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # --- Container for App Icon and App Name (side by side) ---
        app_header_layout = QHBoxLayout()
        app_header_layout.setAlignment(Qt.AlignCenter) # Center the icon and text horizontally

        # App Icon
        self.app_icon_label = QLabel(self)
        app_icon_path = os.path.join(self._icons_path, "logo.svg") # Using logo.svg
        if os.path.exists(app_icon_path):
            pixmap = QPixmap(app_icon_path)
            scaled_pixmap = pixmap.scaled(QSize(48, 48), Qt.KeepAspectRatio, Qt.SmoothTransformation) # Adjusted size for side-by-side
            self.app_icon_label.setPixmap(scaled_pixmap)
        else:
            self.app_icon_label.setText("Icon Missing")
            self.app_icon_label.setStyleSheet("color: red; font-size: 10px;")
        app_header_layout.addWidget(self.app_icon_label)

        # App Name
        self.app_name_label = QLabel("MangaQ")
        # Ensure text color is white on dark background
        self.app_name_label.setStyleSheet("font-size: 28px; font-weight: bold; margin-left: 5px; color: white;") 
        app_header_layout.addWidget(self.app_name_label)
        
        main_layout.addLayout(app_header_layout) # Add the horizontal layout to the main vertical layout

        # Made by
        self.made_by_label = QLabel("Made by MariosKGR")
        self.made_by_label.setAlignment(Qt.AlignCenter)
        self.made_by_label.setStyleSheet("font-size: 14px; color: gray; margin-top: 5px;")
        main_layout.addWidget(self.made_by_label)

        # Spacer to push content to center vertically
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # This will distribute the extra space above and below the content, effectively centering it.
        main_layout.setStretch(0, 1) # Give top spacer stretch factor
        main_layout.setStretch(main_layout.count() - 1, 1) # Give bottom spacer stretch factor


class MangaReader(QWidget):
    def __init__(self):
        super().__init__()
        # Change Window Title (Top Bar)
        self.setWindowTitle("MangaQ")
        self.resize(900, 600)
        self._initial_load_done = False

        self._icons_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons") # Path to your icons folder
        os.makedirs(self._icons_path, exist_ok=True) # Ensure icons folder exists

        # Set main window background color explicitly for consistency.
        # This will be the background for the window frame, including top menu bar area and bottom bar.
        self.setStyleSheet("background-color: #2e2e2e;") # Medium-dark grey for overall window and bars

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Top menu bar ---
        menu_bar = QHBoxLayout()
        # Changed top and bottom margins to 5px
        menu_bar.setContentsMargins(10, 5, 10, 5)
        menu_bar.setSpacing(10)

        # Changed "Folders" to "Entries"
        self.btn_entries = QPushButton("Entries")
        self.btn_metadata = QPushButton("Metadata")
        self.btn_info = QPushButton("Info")
        
        # Select Folder button - NO ICON HERE, just text
        self.btn_select_folder = QPushButton("Select Folder") 
        
        self.btn_select_folder.setStyleSheet("""
            QPushButton {
                background-color: #3a72d2; color: white; padding: 6px 12px;
                border-radius: 5px; font-weight: bold;
            }
            QPushButton:hover { background-color: #305bbf; }
        """)

        # Connect btn_entries to the renamed show_entries_tab
        self.btn_entries.clicked.connect(self.show_entries_tab)
        self.btn_metadata.clicked.connect(self.show_metadata_tab)
        self.btn_info.clicked.connect(self.show_info_tab)
        self.btn_select_folder.clicked.connect(self.open_folder)

        self.main_nav_group = QButtonGroup(self)
        self.main_nav_group.setExclusive(True)

        # Iterate over new btn_entries
        for btn in (self.btn_entries, self.btn_metadata, self.btn_info):
            btn.setCheckable(True)
            btn.setMinimumWidth(90)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 12px; border: none; background-color: transparent;
                    color: #b0b0b0; /* Lighter grey for unselected tabs */
                }
                QPushButton:checked {
                    border-bottom: 3px solid #3a72d2; font-weight: bold; color: #3a72d2;
                }
                QPushButton:hover { 
                    background-color: #404040; /* Darker grey on hover */
                    color: white; /* White text on hover */
                }
            """)
            self.main_nav_group.addButton(btn)

        # Add btn_entries to menu bar
        menu_bar.addWidget(self.btn_entries)
        menu_bar.addWidget(self.btn_metadata)
        menu_bar.addWidget(self.btn_info)
        menu_bar.addStretch()
        menu_bar.addWidget(self.btn_select_folder)
        main_layout.addLayout(menu_bar)

        # --- Main content area (using QStackedWidget) ---
        self.stack = QStackedWidget()
        # Set the background for the stacked widget to be darker than the main window
        self.stack.setStyleSheet("background-color: #1e1e1e;") # Darker grey for content area
        main_layout.addWidget(self.stack)

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListView.IconMode)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSpacing(10)
        self.list_widget.setContentsMargins(10, 10, 10, 10)
        # Ensure list_widget inherits background from stack by setting its background to transparent
        self.list_widget.setStyleSheet("QListWidget { border: none; background-color: transparent; }")
        self.stack.addWidget(self.list_widget)

        # Connect double-click signal for opening folder
        self.list_widget.itemDoubleClicked.connect(self.open_manga_folder_in_browser)
        
        # --- Enable custom context menu for list_widget ---
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)


        # --- Empty State Label (Placeholder) ---
        self.empty_list_label = QLabel("No manga folders added yet.\nClick 'Select Folder' to get started!")
        self.empty_list_label.setAlignment(Qt.AlignCenter)
        self.empty_list_label.setStyleSheet("font-size: 16px; color: gray;") # Will inherit #1e1e1e background
        self.stack.addWidget(self.empty_list_label)

        self.metadata_table = QTableWidget()
        self.metadata_table.setColumnCount(2)
        self.metadata_table.setHorizontalHeaderLabels(["Title", "Description"])
        self.metadata_table.verticalHeader().setVisible(False)
        self.metadata_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.metadata_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.metadata_table.setSelectionMode(QTableWidget.SingleSelection)
        self.metadata_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.metadata_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        # Ensure metadata_table inherits background from stack
        self.metadata_table.setStyleSheet("""
            QTableWidget { 
                background-color: transparent; /* Inherit from QStackedWidget */
                color: white; /* Ensure text is visible */
                gridline-color: #444444; /* Darker grid lines */
                selection-background-color: #3a72d2; /* Blue selection */
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #3a3a3a; /* Darker header background */
                color: white;
                padding: 4px;
                border: 1px solid #555555;
            }
        """)
        self.stack.addWidget(self.metadata_table)

        # --- Instantiate InfoTabWidget ---
        self.info_tab_widget = InfoTabWidget(self._icons_path)
        self.stack.addWidget(self.info_tab_widget)
        
        # --- Bottom bar (now wrapped in its own QWidget) ---
        self.bottom_bar_widget = QWidget(self)
        # Setting a fixed height for the container widget to ensure consistency
        self.bottom_bar_widget.setFixedHeight(40) 
        # Adding a dark background to match the main window/top bar
        self.bottom_bar_widget.setStyleSheet("background-color: #2e2e2e;") # Medium-dark grey

        bottom_bar_layout = QHBoxLayout(self.bottom_bar_widget) # Layout for the new widget
        bottom_bar_layout.setContentsMargins(10, 5, 10, 5) # Apply margins to the layout
        bottom_bar_layout.setSpacing(5)

        # Use list.svg and border.svg for grid/list view buttons
        self.btn_grid = QPushButton(icon=QIcon(os.path.join(self._icons_path, "border.svg")), toolTip="Grid View")
        self.btn_grid.setCheckable(True)
        self.btn_grid.setFixedSize(28, 28)
        self.btn_grid.setStyleSheet("""
            QPushButton { 
                border: 1px solid #555555; /* Darker border for dark theme */
                border-radius: 4px; 
                background-color: transparent; 
                color: #b0b0b0; /* Light grey icon color for dark theme */
            }
            QPushButton:checked { 
                background-color: rgba(58, 114, 210, 128); /* #3a72d2 with 50% alpha (128/255) */
                border: 1px solid #3a72d2; 
                color: white; /* White icon color when checked */
            }
            QPushButton:hover { 
                background-color: #404040; /* Darker grey on hover */
                color: white; /* White icon on hover */
            }
        """)

        self.btn_list = QPushButton(icon=QIcon(os.path.join(self._icons_path, "list.svg")), toolTip="List View")
        self.btn_list.setCheckable(True)
        self.btn_list.setFixedSize(28, 28)
        self.btn_list.setStyleSheet(self.btn_grid.styleSheet()) # Apply the same style, including the checked state

        self.view_btn_group = QButtonGroup(self)
        self.view_btn_group.addButton(self.btn_grid)
        self.view_btn_group.addButton(self.btn_list)
        self.view_btn_group.setExclusive(True)

        self.btn_grid.clicked.connect(self.set_grid_view)
        self.btn_list.clicked.connect(self.set_list_view)

        # Add buttons to the new bottom_bar_layout
        bottom_bar_layout.addWidget(self.btn_grid)
        bottom_bar_layout.addWidget(self.btn_list)
        bottom_bar_layout.addStretch()
        # Changed version number to v1.0
        self.version_label = QLabel("v1.0") 
        self.version_label.setStyleSheet("color: gray; font-size: 10px;")
        bottom_bar_layout.addWidget(self.version_label)
        
        # Add the new bottom_bar_widget to the main layout
        main_layout.addWidget(self.bottom_bar_widget)

        # --- Notification Popup Instance ---
        self.notification_popup = NotificationPopup(parent=self)


        # --- Set initial state ---
        # Changed btn_folders to btn_entries
        self.btn_entries.setChecked(True)
        self.btn_grid.setChecked(True) # Grid view should be initially checked for Entries
        
        # Initially hide grid/list buttons, they'll be shown by show_entries_tab
        self.btn_grid.hide()
        self.btn_list.hide()


    def showEvent(self, event):
        """Triggers the initial data load only once after the window is shown."""
        super().showEvent(event)
        if not self._initial_load_done:
            # Call show_entries_tab to correctly set up the initial view and button visibility
            self.show_entries_tab() 
            self._initial_load_done = True

    def resizeEvent(self, event):
        """Uses a timer to avoid rapid layout recalculations while resizing."""
        super().resizeEvent(event)
        if hasattr(self, 'resize_timer'):
            self.resize_timer.stop()
        else:
            self.resize_timer = QTimer(self)
            self.resize_timer.setSingleShot(True)
            self.resize_timer.timeout.connect(self.update_view_layout)
        self.resize_timer.start(50)

        # Reposition notification popup if visible
        if self.notification_popup.isVisible():
            # Get current geometry of the main window (parent)
            parent_rect = self.geometry() 
            
            # Calculate new position for bottom-right corner of the popup
            # Subtract 20px for padding from right and bottom edges
            x = parent_rect.right() - self.notification_popup.width() - 20
            y = parent_rect.bottom() - self.notification_popup.height() - 20
            
            # Move the popup to the new calculated position
            self.notification_popup.move(x, y)


    def update_grid_columns(self):
        """Calculates grid dimensions based on widget width, ensuring full fill, accounting for spacing."""
        if self.stack.currentWidget() != self.list_widget:
            return

        if self.list_widget.viewMode() != QListView.IconMode:
            return

        cols = 5
        spacing = self.list_widget.spacing()
        margins = self.list_widget.contentsMargins()

        viewport_width = self.list_widget.viewport().width()
        effective_drawable_width = viewport_width - margins.left() - margins.right()
        total_spacing_width = (cols - 1) * spacing

        if cols > 0:
            item_width = (effective_drawable_width - total_spacing_width) // cols
        else:
            item_width = 0

        if item_width < 50:
            item_width = 50

        # Adjust aspect ratio for a more "manga cover" look
        cover_aspect_ratio = 160 / 120 
        icon_display_height = int(item_width * cover_aspect_ratio)
        text_height_allowance = 30 # For title
        item_height = icon_display_height + text_height_allowance

        self.list_widget.setIconSize(QSize(item_width, icon_display_height))
        self.list_widget.setGridSize(QSize(item_width, item_height))
        
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setSizeHint(QSize(item_width, item_height))

        self.list_widget.updateGeometries()
        self.list_widget.viewport().update()

    def update_view_layout(self):
        """Called after resizing to apply the correct layout."""
        if self.stack.currentWidget() is not self.list_widget:
            return
        
        # Only update grid columns if the grid view is active
        if self.btn_grid.isChecked():
            self.update_grid_columns()
        else: # Otherwise, ensure list view settings are applied
            self.set_list_view()

    def set_grid_view(self):
        self.list_widget.setViewMode(QListView.IconMode)
        self.list_widget.setFlow(QListView.LeftToRight)
        self.list_widget.setWrapping(True)
        self.update_grid_columns()

    def set_list_view(self):
        self.list_widget.setViewMode(QListView.ListMode)
        self.list_widget.setFlow(QListView.TopToBottom)
        self.list_widget.setWrapping(False)
        
        self.list_widget.setIconSize(QSize(60, 80))
        
        viewport_width = self.list_widget.viewport().width()
        margins = self.list_widget.contentsMargins()
        list_item_width = viewport_width - margins.left() - margins.right()
        list_item_height = 90
        
        self.list_widget.setGridSize(QSize(list_item_width, list_item_height))
        
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setSizeHint(QSize(list_item_width, list_item_height))
        self.list_widget.updateGeometries()
        self.list_widget.viewport().update()

    # Renamed from show_folders_tab to show_entries_tab
    def show_entries_tab(self):
        # Show grid/list buttons when on Entries tab
        self.btn_grid.show()
        self.btn_list.show()
        
        self.load_folders() 
        if self.list_widget.count() > 0:
            self.stack.setCurrentWidget(self.list_widget)
        else:
            self.stack.setCurrentWidget(self.empty_list_label)
        
        # Ensure the correct view layout is applied after loading and showing
        # This will either set grid or list based on which button is checked
        self.update_view_layout()

    def show_metadata_tab(self):
        # Hide grid/list buttons when not on Entries tab
        self.btn_grid.hide()
        self.btn_list.hide()
        self.stack.setCurrentWidget(self.metadata_table)
        self.load_metadata_table()

    def show_info_tab(self):
        # Hide grid/list buttons when not on Entries tab
        self.btn_grid.hide()
        self.btn_list.hide()
        self.stack.setCurrentWidget(self.info_tab_widget)

    # --- Folder and data handling functions ---
    def load_folders(self):
        self.list_widget.clear()
        metadata_dir = "metadata" 
        found_items = False
        loaded_folder_paths = set() 

        if os.path.exists(metadata_dir):
            for file_name in sorted(os.listdir(metadata_dir)):
                if not file_name.endswith(".json"): continue
                file_path = os.path.join(metadata_dir, file_name)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    folder_path_in_json = data.get("folder")
                    if not folder_path_in_json:
                        print(f"Warning: JSON file {file_name} is missing 'folder' key. Skipping.")
                        continue
                    
                    normalized_folder_path = os.path.normpath(folder_path_in_json)

                    if normalized_folder_path in loaded_folder_paths:
                        print(f"DEBUG: WARNING! Duplicate entry detected for folder: '{normalized_folder_path}'. "
                              f"Skipping JSON file: {file_name}. "
                              f"This usually means multiple metadata files point to the same folder.")
                        self.notification_popup.show_message(
                            f"Duplicate entry for '{os.path.basename(normalized_folder_path)}' detected in metadata!",
                            is_error=True, duration_ms=5000
                        )
                        continue

                    loaded_folder_paths.add(normalized_folder_path)

                    cover_path = data.get("cover")
                    name = data.get("name") or os.path.basename(folder_path_in_json)
                    
                    pixmap = QPixmap()
                    if not (cover_path and os.path.exists(cover_path) and pixmap.load(cover_path)):
                        pixmap = QPixmap(120, 160)
                        pixmap.fill(QColor("#1a1a1a")) # Use a dark color for "No Cover" background matching container
                        painter = QPainter(pixmap)
                        painter.setPen(QColor("lightgray")) # Light text on dark background
                        painter.setFont(self.font())
                        painter.drawText(pixmap.rect(), Qt.AlignCenter, "No Cover\nAvailable")
                        painter.end()
                        
                    
                    item = QListWidgetItem(QIcon(pixmap), name)
                    item.setData(Qt.UserRole, data)
                    self.list_widget.addItem(item)
                    found_items = True
                except json.JSONDecodeError:
                    print(f"Error: Corrupted JSON file detected: {file_path}")
                    self.notification_popup.show_message(f"Corrupted metadata file: {file_name}", is_error=True, duration_ms=5000)
                except Exception as e:
                    print(f"An unexpected error occurred while loading {file_path}: {e}")
        
        if not found_items:
            self.stack.setCurrentWidget(self.empty_list_label)
        else:
            self.stack.setCurrentWidget(self.list_widget)

        self.update_view_layout()


    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Manga Folder")
        if not folder: 
            self.notification_popup.show_message("Folder selection cancelled.", is_error=True, duration_ms=3000)
            return

        if self.metadata_exists(folder):
            self.notification_popup.show_message(f"Folder '{os.path.basename(folder)}' already exists in your library!", is_error=True, duration_ms=3000)
            return

        dialog = FolderDialog(folder, parent=self) 
        if dialog.exec() == QDialog.Accepted:
            try:
                manga_data = dialog.get_data()
                if "uuid" not in manga_data:
                    manga_data["uuid"] = str(uuid.uuid4())
                self.save_metadata(manga_data)
                self.notification_popup.show_message(f"'{manga_data['name']}' added to library!", is_error=False, duration_ms=3000)
                self.load_folders()
                # Changed btn_folders to btn_entries
                if not self.btn_entries.isChecked():
                    self.btn_entries.setChecked(True)
            except Exception as e:
                self.notification_popup.show_message(f"Failed to add manga: {e}", is_error=True, duration_ms=3000)
                print(f"Failed to add manga: {e}")
        else:
            self.notification_popup.show_message("Adding manga cancelled.", is_error=True, duration_ms=3000)


    def open_manga_folder_in_browser(self, item):
        """Opens the manga's folder in the system file browser when item is double-clicked."""
        manga_data = item.data(Qt.UserRole)
        if manga_data and "folder" in manga_data:
            folder_path = manga_data["folder"]
            if os.path.isdir(folder_path):
                try:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
                    self.notification_popup.show_message(f"Opened folder for '{item.text()}'", is_error=False, duration_ms=3000)
                except Exception as e:
                    self.notification_popup.show_message(f"Could not open folder: {e}", is_error=True, duration_ms=3000)
                    print(f"Error opening folder '{folder_path}': {e}")
            else:
                self.notification_popup.show_message(f"Folder '{folder_path}' not found! Metadata may be outdated.", is_error=True, duration_ms=5000)
                print(f"Error: Folder path does not exist: {folder_path}")
        else:
            self.notification_popup.show_message("Could not retrieve folder path for this item.", is_error=True, duration_ms=3000)
            print("Error: No folder data associated with this item.")


    def load_metadata_table(self):
        self.metadata_table.setRowCount(0)
        metadata_dir = "metadata" 
        if not os.path.exists(metadata_dir): return

        all_metadata = []
        for file_name in sorted(os.listdir(metadata_dir)):
            if not file_name.endswith(".json"): continue
            file_path = os.path.join(metadata_dir, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    all_metadata.append(data)
            except json.JSONDecodeError:
                print(f"Error: Corrupted JSON file detected in metadata table load: {file_path}")
            except Exception as e:
                print(f"An unexpected error occurred while loading metadata for table {file_path}: {e}")

        self.metadata_table.setRowCount(len(all_metadata))
        for row, data in enumerate(all_metadata):
            title = data.get("name", "Unknown")
            description = data.get("description", "")
            self.metadata_table.setItem(row, 0, QTableWidgetItem(title))
            self.metadata_table.setItem(row, 1, QTableWidgetItem(description))

    def _get_metadata_filename(self, manga_data):
        """
        Determines the filename for a manga's metadata JSON file.
        Prioritizes existing UUID, otherwise uses the folder's UUID.
        """
        metadata_dir = "metadata" 

        if "uuid" in manga_data and manga_data["uuid"]:
            return f"{manga_data['uuid']}.json"

        normalized_folder_path = os.path.normpath(manga_data["folder"])
        
        if os.path.exists(metadata_dir):
            for file_name in os.listdir(metadata_dir):
                if file_name.endswith(".json"):
                    file_path = os.path.join(metadata_dir, file_name)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            existing_data = json.load(f)
                            if os.path.normpath(existing_data.get("folder", "")) == normalized_folder_path:
                                if "uuid" in existing_data and existing_data["uuid"]:
                                    print(f"DEBUG: Found existing UUID for '{normalized_folder_path}': {existing_data['uuid']}")
                                    manga_data["uuid"] = existing_data["uuid"]
                                    return f"{existing_data['uuid']}.json"
                    except json.JSONDecodeError:
                        print(f"Warning: Corrupted JSON file detected during UUID lookup: {file_path}")
                    except Exception as e:
                        print(f"An unexpected error occurred during UUID lookup for {file_path}: {e}")

        new_uuid = str(uuid.uuid4())
        manga_data["uuid"] = new_uuid
        print(f"DEBUG: Generating new UUID for '{normalized_folder_path}': {new_uuid}")
        return f"{new_uuid}.json"

    def save_metadata(self, data):
        metadata_dir = "metadata" 
        os.makedirs(metadata_dir, exist_ok=True)
        
        file_name = self._get_metadata_filename(data) 
        path = os.path.join(metadata_dir, file_name)
        
        print(f"DEBUG: Saving metadata.")
        print(f"DEBUG: Data 'folder' key: {data['folder']}")
        print(f"DEBUG: Data 'uuid' key: {data.get('uuid')}")
        print(f"DEBUG: Determined filename for save: {file_name}")
        print(f"DEBUG: Full save path: {path}")

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"DEBUG: Successfully saved/overwritten {path}")
        except Exception as e:
            print(f"DEBUG: ERROR saving metadata: {e}")
            raise Exception(f"Failed to write metadata file for {data['folder']}: {e}")

    def metadata_exists(self, folder_path):
        metadata_dir = "metadata" 
        if not os.path.exists(metadata_dir):
            return False
        
        normalized_target_folder = os.path.normpath(folder_path)

        for file_name in os.listdir(metadata_dir):
            if not file_name.endswith(".json"): continue
            file_path = os.path.join(metadata_dir, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if os.path.normpath(data.get("folder", "")) == normalized_target_folder:
                        return True
            except json.JSONDecodeError:
                print(f"Warning: Corrupted JSON file found during existence check: {file_path}. Skipping.")
            except Exception as e:
                print(f"Warning: Error reading metadata during existence check for {file_path}: {e}")
        return False

    # --- New: Context Menu Methods ---
    def show_context_menu(self, position):
        item = self.list_widget.itemAt(position)
        if item:
            context_menu = QMenu(self)

            # No explicit icon set here, so no change needed related to edit.svg
            edit_action = context_menu.addAction("Edit Manga")
            delete_action = context_menu.addAction("Delete Manga")
            open_folder_action = context_menu.addAction("Open Folder in Explorer")

            action = context_menu.exec(self.list_widget.mapToGlobal(position))

            if action == edit_action:
                self.edit_selected_manga(item)
            elif action == delete_action:
                self.delete_selected_manga(item)
            elif action == open_folder_action:
                self.open_manga_folder_in_browser(item)

    def edit_selected_manga(self, item_to_edit):
        manga_data = item_to_edit.data(Qt.UserRole)
        if not manga_data:
            self.notification_popup.show_message("Could not retrieve manga data for editing.", is_error=True, duration_ms=3000)
            return

        dialog = FolderDialog(manga_data["folder"], manga_data=manga_data, parent=self)
        if dialog.exec() == QDialog.Accepted:
            try:
                new_data = dialog.get_data()
                
                original_folder_path = manga_data["folder"]
                new_folder_path = new_data["folder"]
                
                if os.path.normpath(original_folder_path) != os.path.normpath(new_folder_path) and "uuid" in manga_data:
                    metadata_dir = "metadata" 
                    old_file_name = f"{manga_data['uuid']}.json"
                    old_file_path = os.path.join(metadata_dir, old_file_name)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                        print(f"DEBUG: Deleted old metadata file: {old_file_path}")

                self.save_metadata(new_data) 
                self.notification_popup.show_message(f"'{new_data['name']}' updated successfully!", is_error=False, duration_ms=3000)
                self.load_folders()
            except Exception as e:
                self.notification_popup.show_message(f"Failed to update manga: {e}", is_error=True, duration_ms=3000)
                print(f"Failed to update manga: {e}")
        else:
            self.notification_popup.show_message("Editing manga cancelled.", is_error=True, duration_ms=3000)

    def delete_selected_manga(self, item_to_delete):
        manga_data = item_to_delete.data(Qt.UserRole)
        if not manga_data:
            self.notification_popup.show_message("Could not retrieve manga data for deletion.", is_error=True, duration_ms=3000)
            return

        manga_name = manga_data.get("name", os.path.basename(manga_data.get("folder", "Unknown Manga")))

        confirm_dialog = QMessageBox()
        confirm_dialog.setWindowTitle("Confirm Deletion")
        confirm_dialog.setText(f"Are you sure you want to delete '{manga_name}'?\nThis will remove it from your library and delete its metadata file.")
        confirm_dialog.setIcon(QMessageBox.Warning)
        confirm_dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm_dialog.setDefaultButton(QMessageBox.No)

        if confirm_dialog.exec() == QMessageBox.Yes:
            try:
                metadata_dir = "metadata" 
                file_to_delete_path = None
                if "uuid" in manga_data and manga_data["uuid"]:
                    file_to_delete_path = os.path.join(metadata_dir, f"{manga_data['uuid']}.json")
                else:
                    normalized_folder = os.path.normpath(manga_data["folder"])
                    safe_name = re.sub(r'[^\w\s.-]', '', os.path.basename(normalized_folder)).strip().replace(' ', '_')
                    if not safe_name: safe_name = "untitled_folder"
                    file_to_delete_path = os.path.join(metadata_dir, f"{safe_name}.json")


                if file_to_delete_path and os.path.exists(file_to_delete_path):
                    os.remove(file_to_delete_path)
                    self.notification_popup.show_message(f"'{manga_name}' deleted successfully!", is_error=False, duration_ms=3000)
                    self.load_folders()
                else:
                    self.notification_popup.show_message(f"Metadata file for '{manga_name}' not found (already deleted or renamed?).", is_error=True, duration_ms=5000)
                    self.load_folders() 
            except Exception as e:
                self.notification_popup.show_message(f"Failed to delete manga: {e}", is_error=True, duration_ms=3000)
                print(f"Failed to delete manga: {e}")
        else:
            self.notification_popup.show_message("Deletion cancelled.", is_error=True, duration_ms=3000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set the application's window icon (favicon)
    icons_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
    logo_icon_path = os.path.join(icons_path, "logo.svg")
    if os.path.exists(logo_icon_path):
        app.setWindowIcon(QIcon(logo_icon_path))
    else:
        print(f"WARNING: logo.svg not found at {logo_icon_path}. Application icon may not appear.")

    reader = MangaReader()
    reader.show()
    sys.exit(app.exec())