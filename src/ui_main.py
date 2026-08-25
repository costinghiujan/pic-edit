import sys
from typing import Optional
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QSlider, QFileDialog, QMessageBox, QScrollArea, QFrame,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QImage, QPixmap, QAction, QKeyEvent, QPainter, QWheelEvent, QMouseEvent
)

from src.engine import ImageEngine
from src.collapsible_section import CollapsibleSection
from src.filters import ToneAdjustmentsFilter


class ResetableSlider(QSlider):
    """
    A QSlider that resets to a default value upon double click.
    """

    def __init__(self, orientation: Qt.Orientation, default_value: int = 0, parent: QWidget = None):
        super().__init__(orientation, parent)
        self.default_value = default_value

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.setValue(self.default_value)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class ImageCanvas(QGraphicsView):
    """
    High-performance canvas supporting zoom, pan, and fit-to-view.
    """

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

        height, width, channels = image_array.shape
        bytes_per_line = channels * width
        q_img = QImage(
            image_array.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )
        self._current_pixmap = QPixmap.fromImage(q_img)

        is_initial_load = self._pixmap_item is None

        if is_initial_load:
            self.scene.clear()
            self._pixmap_item = self.scene.addPixmap(self._current_pixmap)
            self.scene.setSceneRect(0, 0, width, height)
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
        self.resize(1150, 750)

        self.engine = ImageEngine()

        # 60 FPS Render Throttle Timer
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

        # Left: Image Canvas
        self.canvas = ImageCanvas(self)
        main_layout.addWidget(self.canvas, stretch=4)

        # Right: Scrollable Sidebar
        sidebar_scroll = QScrollArea(self)
        sidebar_scroll.setFixedWidth(300)
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sidebar_scroll.setStyleSheet("background-color: #1e1e1e;")

        sidebar_container = QWidget()
        self.sidebar_layout = QVBoxLayout(sidebar_container)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(10)

        # --- Section: General with Reset button in header ---
        self.general_section = CollapsibleSection("General", on_reset=self._reset_and_apply_general, parent=self)
        self._build_general_controls()
        self.sidebar_layout.addWidget(self.general_section)

        self.sidebar_layout.addStretch()

        sidebar_scroll.setWidget(sidebar_container)
        main_layout.addWidget(sidebar_scroll, stretch=1)

    def _build_general_controls(self) -> None:
        self.exposure_label = QLabel("Exposure: 0.00 EV")
        self.exposure_slider = self._create_slider(-20, 20, 0)

        self.contrast_label = QLabel("Contrast: 1.00x")
        self.contrast_slider = self._create_slider(-100, 100, 0)

        self.highlights_label = QLabel("Highlights: 0.00")
        self.highlights_slider = self._create_slider(-100, 100, 0)

        self.shadows_label = QLabel("Shadows: 0.00")
        self.shadows_slider = self._create_slider(-100, 100, 0)

        self.whites_label = QLabel("Whites: 0.00")
        self.whites_slider = self._create_slider(-100, 100, 0)

        self.blacks_label = QLabel("Blacks: 0.00")
        self.blacks_slider = self._create_slider(-100, 100, 0)

        widgets = [
            (self.exposure_label, self.exposure_slider),
            (self.contrast_label, self.contrast_slider),
            (self.highlights_label, self.highlights_slider),
            (self.shadows_label, self.shadows_slider),
            (self.whites_label, self.whites_slider),
            (self.blacks_label, self.blacks_slider),
        ]

        for label, slider in widgets:
            self.general_section.add_widget(label)
            self.general_section.add_widget(slider)

    def _create_slider(self, min_val: int, max_val: int, default_val: int) -> ResetableSlider:
        slider = ResetableSlider(Qt.Orientation.Horizontal, default_value=default_val)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.setEnabled(False)
        slider.valueChanged.connect(self._on_slider_moved)
        return slider

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

    def _reset_controls(self) -> None:
        """Resets sliders and labels to defaults without triggering renders."""
        controls = [
            (self.exposure_slider, self.exposure_label, "Exposure: 0.00 EV"),
            (self.contrast_slider, self.contrast_label, "Contrast: 1.00x"),
            (self.highlights_slider, self.highlights_label, "Highlights: 0.00"),
            (self.shadows_slider, self.shadows_label, "Shadows: 0.00"),
            (self.whites_slider, self.whites_label, "Whites: 0.00"),
            (self.blacks_slider, self.blacks_label, "Blacks: 0.00"),
        ]

        for slider, label, default_text in controls:
            slider.blockSignals(True)
            slider.setValue(slider.default_value)
            label.setText(default_text)
            slider.blockSignals(False)

    def _reset_and_apply_general(self) -> None:
        """Called by the Reset button in General section header."""
        if not self.engine.has_image:
            return
        self._reset_controls()
        self._execute_pipeline_update()

    def _set_sliders_enabled(self, enabled: bool) -> None:
        self.exposure_slider.setEnabled(enabled)
        self.contrast_slider.setEnabled(enabled)
        self.highlights_slider.setEnabled(enabled)
        self.shadows_slider.setEnabled(enabled)
        self.whites_slider.setEnabled(enabled)
        self.blacks_slider.setEnabled(enabled)
        self.general_section.set_reset_enabled(enabled)

    def _handle_import(self) -> None:
        if not self._confirm_discard_changes():
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select RAW Image",
            "",
            "Canon RAW Files (*.CR2);;All Files (*)"
        )
        if not file_path:
            return

        if self.engine.load(file_path):
            self._reset_controls()
            self._set_sliders_enabled(True)
            self.export_action.setEnabled(True)

            preview = self.engine.update_pipeline([], is_modified=False)
            self.canvas.set_numpy_image(preview)
        else:
            QMessageBox.critical(self, "Error", f"Failed to load image: {file_path}")

    def _on_slider_moved(self) -> None:
        if not self.engine.has_image:
            return

        ev_val = self.exposure_slider.value() / 10.0
        contrast_val = 1.0 + (self.contrast_slider.value() / 100.0)
        highlights_val = self.highlights_slider.value() / 100.0
        shadows_val = self.shadows_slider.value() / 100.0
        whites_val = self.whites_slider.value() / 100.0
        blacks_val = self.blacks_slider.value() / 100.0

        self.exposure_label.setText(f"Exposure: {ev_val:+.2f} EV")
        self.contrast_label.setText(f"Contrast: {contrast_val:.2f}x")
        self.highlights_label.setText(f"Highlights: {highlights_val:+.2f}")
        self.shadows_label.setText(f"Shadows: {shadows_val:+.2f}")
        self.whites_label.setText(f"Whites: {whites_val:+.2f}")
        self.blacks_label.setText(f"Blacks: {blacks_val:+.2f}")

        if not self._render_timer.isActive():
            self._render_timer.start()

    def _execute_pipeline_update(self) -> None:
        ev_val = self.exposure_slider.value() / 10.0
        contrast_val = 1.0 + (self.contrast_slider.value() / 100.0)
        highlights_val = self.highlights_slider.value() / 100.0
        shadows_val = self.shadows_slider.value() / 100.0
        whites_val = self.whites_slider.value() / 100.0
        blacks_val = self.blacks_slider.value() / 100.0

        pipeline = [
            ToneAdjustmentsFilter(
                exposure_ev=ev_val,
                contrast_factor=contrast_val,
                highlights=highlights_val,
                shadows=shadows_val,
                whites=whites_val,
                blacks=blacks_val,
            )
        ]

        has_changes = any([
            ev_val != 0.0,
            self.contrast_slider.value() != 0,
            highlights_val != 0.0,
            shadows_val != 0.0,
            whites_val != 0.0,
            blacks_val != 0.0
        ])

        updated_preview = self.engine.update_pipeline(pipeline, is_modified=has_changes)
        self.canvas.set_numpy_image(updated_preview)

    def _handle_export(self) -> None:
        if not self.engine.has_image:
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Image as JPEG",
            "output.jpg",
            "JPEG Image (*.jpg *.jpeg)"
        )
        if not save_path:
            return

        success = self.engine.export_jpeg(save_path)
        if success:
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