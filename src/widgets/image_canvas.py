from typing import Optional
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap, QWheelEvent
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QWidget


class ImageCanvas(QGraphicsView):
    """High-performance image viewport supporting zoom, drag-to-pan, and fit-to-view."""

    def __init__(self, parent: Optional[QWidget] = None):
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
        """Updates the scene image buffer while retaining current viewport zoom/pan transforms."""
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
        """Resets transform and centers image to fit the visible viewport."""
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