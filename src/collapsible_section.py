from typing import Callable, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt


class CollapsibleSection(QWidget):
    """
    A custom collapsible accordion widget with a toggle header and a reset action button.
    """

    def __init__(self, title: str = "", on_reset: Optional[Callable[[], None]] = None, parent: QWidget = None):
        super().__init__(parent)
        self._is_expanded = True
        self._title = title
        self._on_reset = on_reset

        # Main layout for this accordion block
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header Container
        header_container = QWidget(self)
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        # Header Toggle Button
        self.toggle_button = QPushButton(f"▼  {self._title}", self)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                padding: 8px 12px;
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #383838;
            }
        """)
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_button.clicked.connect(self.toggle)
        header_layout.addWidget(self.toggle_button, stretch=1)

        # Optional Reset Button in the header
        if self._on_reset is not None:
            self.reset_button = QPushButton("Reset", self)
            self.reset_button.setFixedWidth(55)
            self.reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.reset_button.setStyleSheet("""
                QPushButton {
                    font-size: 11px;
                    padding: 8px 4px;
                    background-color: #333333;
                    color: #b0b0b0;
                    border: 1px solid #3c3c3c;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #444444;
                    color: #ffffff;
                }
                QPushButton:disabled {
                    color: #555555;
                    background-color: #222222;
                }
            """)
            self.reset_button.clicked.connect(self._on_reset)
            self.reset_button.setEnabled(False)
            header_layout.addWidget(self.reset_button)
        else:
            self.reset_button = None

        self.main_layout.addWidget(header_container)

        # Container for the child controls
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(8, 12, 8, 12)
        self.content_layout.setSpacing(10)
        self.content_widget.setStyleSheet("""
            QWidget {
                background-color: #242424;
                border-left: 1px solid #3c3c3c;
                border-right: 1px solid #3c3c3c;
                border-bottom: 1px solid #3c3c3c;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }
        """)

        self.main_layout.addWidget(self.content_widget)

    def add_widget(self, widget: QWidget) -> None:
        """Adds a widget inside the collapsible section body."""
        self.content_layout.addWidget(widget)

    def set_reset_enabled(self, enabled: bool) -> None:
        if self.reset_button:
            self.reset_button.setEnabled(enabled)

    def toggle(self) -> None:
        """Expands or collapses the content container."""
        self._is_expanded = not self._is_expanded
        self.content_widget.setVisible(self._is_expanded)
        arrow = "▼" if self._is_expanded else "▶"
        self.toggle_button.setText(f"{arrow}  {self._title}")