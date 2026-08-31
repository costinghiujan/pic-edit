from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QPushButton, QVBoxLayout, QWidget


class ActivityButton(QPushButton):
    """Square icon-style button for the activity bar."""

    def __init__(self, text: str, tooltip: str, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedSize(38, 38)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                font-size: 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #333333;
                color: #3b82f6;
                border-right: 2px solid #3b82f6;
            }
        """)


class ActivityBar(QWidget):
    """Vertical bar holding navigation buttons to switch between workspaces."""

    tabChanged = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedWidth(44)
        self.setStyleSheet("background-color: #141414; border-left: 1px solid #242424;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 8, 3, 8)
        layout.setSpacing(6)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        # 1. Develop / Edit Icon
        self.edit_btn = ActivityButton("🎚", "Develop Adjustments", self)
        self.edit_btn.setChecked(True)
        self.btn_group.addButton(self.edit_btn, 0)
        layout.addWidget(self.edit_btn)

        # 2. Crop & Rotate Icon
        self.crop_btn = ActivityButton("⛶", "Crop & Rotate", self)
        self.btn_group.addButton(self.crop_btn, 1)
        layout.addWidget(self.crop_btn)

        layout.addStretch()

        self.btn_group.idClicked.connect(self.tabChanged.emit)