import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QWidget

from src.editor_controller import EditorController
from src.engine import ImageEngine
from src.widgets import ActivityBar, ImageCanvas, Sidebar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Raw Photo Editor")
        self.resize(1200, 800)

        # Core Components
        self.engine = ImageEngine()
        self.activity_bar = ActivityBar(self)
        self.canvas = ImageCanvas(self)
        self.sidebar = Sidebar(self)

        # Controller (Business Logic & State Management)
        self.controller = EditorController(self.engine, self.canvas, self.sidebar, parent=self)

        self._init_menu()
        self._init_shortcuts()
        self._init_layout()

    def _init_menu(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        self.import_action = QAction("&Import CR2...", self)
        self.import_action.triggered.connect(self._on_import)
        file_menu.addAction(self.import_action)

        self.export_action = QAction("&Export JPEG...", self)
        self.export_action.triggered.connect(self.controller.export_image)
        self.export_action.setEnabled(False)
        file_menu.addAction(self.export_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _init_shortcuts(self) -> None:
        self.fit_view_shortcut = QShortcut(QKeySequence("R"), self)
        self.fit_view_shortcut.activated.connect(self.canvas.fit_to_view)

    def _init_layout(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 0, 10)
        main_layout.setSpacing(10)

        # 1. Main Viewport Canvas (Left)
        main_layout.addWidget(self.canvas, stretch=4)

        # 2. Stacked Sidebar Panel (Middle-Right)
        main_layout.addWidget(self.sidebar, stretch=1)

        # 3. Activity Bar (Rightmost)
        main_layout.addWidget(self.activity_bar)

        # Connect tab switching
        self.activity_bar.tabChanged.connect(self.sidebar.set_current_tab)

        # Switch tabs via activity bar through controller
        self.activity_bar.tabChanged.connect(self.controller.set_workspace_tab)

    def _on_import(self) -> None:
        if self.controller.import_image():
            self.export_action.setEnabled(True)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            if self.controller.show_original_preview():
                self.statusBar().showMessage("Showing: Original (Before)")
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.controller.restore_edited_preview()
            self.statusBar().clearMessage()
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def closeEvent(self, event) -> None:
        if self.controller.confirm_close():
            event.accept()
        else:
            event.ignore()