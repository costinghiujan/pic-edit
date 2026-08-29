import sys
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QMainWindow, QWidget
)

from src.engine import ImageEngine
from src.utils import DialogService
from src.widgets import ImageCanvas, Sidebar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Raw Photo Editor")
        self.resize(1200, 800)

        # Core Services & State
        self.engine = ImageEngine()

        # UI Subcomponents
        self.canvas = ImageCanvas(self)
        self.sidebar = Sidebar(self)

        # 60 FPS Throttling Timer
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(16)
        self._render_timer.timeout.connect(self._execute_pipeline_update)

        self._init_menu()
        self._init_shortcuts()
        self._init_layout()

    def _init_menu(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        self.import_action = QAction("&Import CR2...", self)
        self.import_action.triggered.connect(self._handle_import)
        file_menu.addAction(self.import_action)

        self.export_action = QAction("&Export JPEG...", self)
        self.export_action.triggered.connect(self._handle_export)
        self.export_action.setEnabled(False)
        file_menu.addAction(self.export_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _init_shortcuts(self) -> None:
        # Tasta R resetează vizualizarea prin QShortcut curat
        self.fit_view_shortcut = QShortcut(QKeySequence("R"), self)
        self.fit_view_shortcut.activated.connect(self._on_reset_view)

    def _init_layout(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        main_layout.addWidget(self.canvas, stretch=4)
        main_layout.addWidget(self.sidebar, stretch=1)

        self.sidebar.adjustmentsChanged.connect(self._schedule_render)

    def _on_reset_view(self) -> None:
        if self.engine.has_image:
            self.canvas.fit_to_view()
            self.statusBar().showMessage("View reset to Fit-to-Screen", 2000)

    def _handle_import(self) -> None:
        if self.engine.is_modified and not DialogService.confirm_discard_changes(self):
            return

        file_path = DialogService.open_raw_file(self)
        if not file_path:
            return

        if self.engine.load(file_path):
            self.sidebar.reset_all()
            self.sidebar.set_enabled(True)
            self.export_action.setEnabled(True)

            preview = self.engine.update_pipeline([], is_modified=False)
            self.canvas.set_numpy_image(preview)
            self.sidebar.update_histograms(preview)
        else:
            DialogService.show_error("Error", f"Failed to load image: {file_path}", self)

    def _handle_export(self) -> None:
        if not self.engine.has_image:
            return

        save_path = DialogService.save_jpeg_file(self)
        if not save_path:
            return

        if self.engine.export_jpeg(save_path):
            DialogService.show_info("Export Complete", f"Image exported successfully to:\n{save_path}", self)
        else:
            DialogService.show_error("Export Failed", "Could not export image. Check application logs.", self)

    def _schedule_render(self) -> None:
        if self.engine.has_image and not self._render_timer.isActive():
            self._render_timer.start()

    def _execute_pipeline_update(self) -> None:
        active_filters = self.sidebar.get_active_filters()
        is_modified = self.sidebar.is_modified()

        updated_preview = self.engine.update_pipeline(active_filters, is_modified=is_modified)
        self.canvas.set_numpy_image(updated_preview)
        self.sidebar.update_histograms(updated_preview)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        # Space (hold) arată imaginea originală (Before)
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            if self.engine.has_image and self.engine._preview_base is not None:
                self.canvas.set_numpy_image(self.engine._preview_base)
                self.statusBar().showMessage("Showing: Original (Before)")
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        # Space (release) revine la imaginea editată
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            if self.engine.has_image and self.engine._current_preview is not None:
                self.canvas.set_numpy_image(self.engine._current_preview)
                self.statusBar().clearMessage()
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def closeEvent(self, event) -> None:
        if self.engine.is_modified and not DialogService.confirm_discard_changes(self):
            event.ignore()
        else:
            event.accept()