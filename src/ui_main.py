import sys
from typing import List, Optional
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFileDialog, QMessageBox, QScrollArea, QFrame,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QImage, QPixmap, QAction, QKeyEvent, QPainter, QWheelEvent
)

from src.engine import ImageEngine
from src.widgets import GeneralSection, CurvesSection


class ImageCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._current_pixmap: Optional[QPixmap] = None

        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("background-color: #1a1a1a; border: 1px solid #2d2d2d;")
        self._zoom_factor = 1.15

    def set_numpy_image(self, image_array: Optional[np.ndarray]) -> None:
        if image_array is None or image_array.size == 0:
            self.scene.clear()
            self._pixmap_item = None
            self._current_pixmap = None
            return

        h, w, ch = image_array.shape
        bytes_per_line = ch * w
        q_img = QImage(image_array.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self._current_pixmap = QPixmap.fromImage(q_img)

        if self._pixmap_item is None:
            self.scene.clear()
            self._pixmap_item = self.scene.addPixmap(self._current_pixmap)
            self.scene.setSceneRect(0, 0, w, h)
            self.fit_to_view()
        else:
            self._pixmap_item.setPixmap(self._current_pixmap)

    def fit_to_view(self) -> None:
        if self._pixmap_item is not None and not self._pixmap_item.pixmap().isNull():
            self.resetTransform()
            self.setSceneRect(self._pixmap_item.boundingRect())
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._pixmap_item is None:
            return
        if event.angleDelta().y() > 0:
            self.scale(self._zoom_factor, self._zoom_factor)
        else:
            self.scale(1.0 / self._zoom_factor, 1.0 / self._zoom_factor)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Raw Photo Editor")
        self.resize(1200, 800)

        self.engine = ImageEngine()

        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(16)
        self._render_timer.timeout.connect(self._execute_pipeline_update)

        self._init_menu()
        self._init_ui()

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

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.canvas = ImageCanvas(self)
        main_layout.addWidget(self.canvas, stretch=4)

        sidebar_scroll = QScrollArea(self)
        sidebar_scroll.setFixedWidth(310)
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sidebar_scroll.setStyleSheet("background-color: #1e1e1e;")

        sidebar_container = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(10)

        # Register modular editor sections
        self.general_section = GeneralSection(self)
        self.curves_section = CurvesSection(self)
        self.sections = [self.general_section, self.curves_section]

        for section in self.sections:
            section.adjustmentsChanged.connect(self._schedule_render)
            sidebar_layout.addWidget(section)

        sidebar_layout.addStretch()
        sidebar_scroll.setWidget(sidebar_container)
        main_layout.addWidget(sidebar_scroll, stretch=1)

    def _confirm_discard_changes(self) -> bool:
        if not self.engine.is_modified:
            return True

        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "There are unsaved adjustments on the current image. Do you want to discard them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def _set_ui_enabled(self, enabled: bool) -> None:
        for section in self.sections:
            section.set_enabled(enabled)

    def _handle_import(self) -> None:
        if not self._confirm_discard_changes():
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select RAW Image", "", "Canon RAW Files (*.CR2);;All Files (*)"
        )
        if not file_path:
            return

        if self.engine.load(file_path):
            for section in self.sections:
                section.reset_adjustments()

            self._set_ui_enabled(True)
            self.export_action.setEnabled(True)

            preview = self.engine.update_pipeline([], is_modified=False)
            self.canvas.set_numpy_image(preview)
            self.curves_section.set_histogram_image(preview)
        else:
            QMessageBox.critical(self, "Error", f"Failed to load image: {file_path}")

    def _schedule_render(self) -> None:
        if self.engine.has_image and not self._render_timer.isActive():
            self._render_timer.start()

    def _execute_pipeline_update(self) -> None:
        pipeline = [sec.get_filter() for sec in self.sections]
        is_modified = any(sec.has_modifications() for sec in self.sections)

        updated_preview = self.engine.update_pipeline(pipeline, is_modified=is_modified)
        self.canvas.set_numpy_image(updated_preview)

    def _handle_export(self) -> None:
        if not self.engine.has_image:
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Export Image as JPEG", "output.jpg", "JPEG Image (*.jpg *.jpeg)"
        )
        if not save_path:
            return

        if self.engine.export_jpeg(save_path):
            QMessageBox.information(self, "Export Complete", f"Image exported successfully to:\n{save_path}")
        else:
            QMessageBox.critical(self, "Export Failed", "Could not export image. Check application logs for details.")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_R:
            if self.engine.has_image:
                self.canvas.fit_to_view()
                self.statusBar().showMessage("View reset to Fit-to-Screen", 2000)
            event.accept()
        elif event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            if self.engine.has_image and self.engine._preview_base is not None:
                self.canvas.set_numpy_image(self.engine._preview_base)
                self.statusBar().showMessage("Showing: Original (Before)")
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            if self.engine.has_image and self.engine._current_preview is not None:
                self.canvas.set_numpy_image(self.engine._current_preview)
                self.statusBar().clearMessage()
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def closeEvent(self, event) -> None:
        if self._confirm_discard_changes():
            event.accept()
        else:
            event.ignore()