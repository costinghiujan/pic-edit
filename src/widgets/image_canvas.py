from typing import Optional, Tuple
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush, QColor, QCursor, QImage, QPainter, QPainterPath, QPen, QPixmap, QWheelEvent
)
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsPixmapItem, QGraphicsScene,
    QGraphicsSceneMouseEvent, QGraphicsView, QWidget
)

from src.utils import clamp


class CropOverlayItem(QGraphicsItem):
    """Interactive bounding box overlay for image cropping with rule-of-thirds grid."""

    cropChanged = Signal()

    HANDLE_NONE = 0
    HANDLE_MOVE = 1
    HANDLE_TL = 2
    HANDLE_TR = 3
    HANDLE_BL = 4
    HANDLE_BR = 5
    HANDLE_T = 6
    HANDLE_B = 7
    HANDLE_L = 8
    HANDLE_R = 9

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptHoverEvents(True)
        self._image_rect = QRectF(0, 0, 0, 0)
        self._crop_rect = QRectF(0, 0, 0, 0)  # Pixel coords relative to image
        self._aspect_ratio: Optional[float] = None  # width / height

        self._active_handle = self.HANDLE_NONE
        self._drag_start_pos = QPointF()
        self._drag_start_crop = QRectF()
        self.handle_size = 12.0

    def boundingRect(self) -> QRectF:
        return self._image_rect

    def set_image_rect(self, rect: QRectF) -> None:
        self.prepareGeometryChange()
        self._image_rect = rect
        self.reset_crop()

    def set_aspect_ratio(self, ratio: Optional[float]) -> None:
        self._aspect_ratio = ratio
        if ratio is not None and self._crop_rect.isValid():
            self._apply_aspect_ratio_constraint()
        self.update()

    def reset_crop(self) -> None:
        self.prepareGeometryChange()
        self._crop_rect = QRectF(self._image_rect)
        if self._aspect_ratio is not None:
            self._apply_aspect_ratio_constraint()
        self.update()

    def get_normalized_crop(self) -> Tuple[float, float, float, float]:
        """Returns (x, y, width, height) in [0.0, 1.0] range."""
        if not self._image_rect.isValid() or self._image_rect.width() == 0:
            return (0.0, 0.0, 1.0, 1.0)

        nx = (self._crop_rect.left() - self._image_rect.left()) / self._image_rect.width()
        ny = (self._crop_rect.top() - self._image_rect.top()) / self._image_rect.height()
        nw = self._crop_rect.width() / self._image_rect.width()
        nh = self._crop_rect.height() / self._image_rect.height()
        return (clamp(nx, 0.0, 1.0), clamp(ny, 0.0, 1.0), clamp(nw, 0.01, 1.0), clamp(nh, 0.01, 1.0))

    def _apply_aspect_ratio_constraint(self) -> None:
        if self._aspect_ratio is None:
            return

        cx, cy = self._crop_rect.center().x(), self._crop_rect.center().y()
        max_w = self._image_rect.width()
        max_h = self._image_rect.height()

        target_w = max_w
        target_h = target_w / self._aspect_ratio

        if target_h > max_h:
            target_h = max_h
            target_w = target_h * self._aspect_ratio

        self._crop_rect = QRectF(cx - target_w / 2.0, cy - target_h / 2.0, target_w, target_h)
        self._clamp_to_image()

    def _clamp_to_image(self) -> None:
        cr = self._crop_rect
        ir = self._image_rect

        if cr.left() < ir.left():
            cr.moveLeft(ir.left())
        if cr.top() < ir.top():
            cr.moveTop(ir.top())
        if cr.right() > ir.right():
            cr.moveRight(ir.right())
        if cr.bottom() > ir.bottom():
            cr.moveBottom(ir.bottom())
        self._crop_rect = cr

    def _get_handle_at(self, pos: QPointF) -> int:
        cr = self._crop_rect
        hs = self.handle_size

        if not cr.isValid():
            return self.HANDLE_NONE

        # Corner handles
        if QRectF(cr.left() - hs, cr.top() - hs, 2 * hs, 2 * hs).contains(pos):
            return self.HANDLE_TL
        if QRectF(cr.right() - hs, cr.top() - hs, 2 * hs, 2 * hs).contains(pos):
            return self.HANDLE_TR
        if QRectF(cr.left() - hs, cr.bottom() - hs, 2 * hs, 2 * hs).contains(pos):
            return self.HANDLE_BL
        if QRectF(cr.right() - hs, cr.bottom() - hs, 2 * hs, 2 * hs).contains(pos):
            return self.HANDLE_BR

        # Edge handles
        if QRectF(cr.left() - hs, cr.center().y() - hs, 2 * hs, 2 * hs).contains(pos):
            return self.HANDLE_L
        if QRectF(cr.right() - hs, cr.center().y() - hs, 2 * hs, 2 * hs).contains(pos):
            return self.HANDLE_R
        if QRectF(cr.center().x() - hs, cr.top() - hs, 2 * hs, 2 * hs).contains(pos):
            return self.HANDLE_T
        if QRectF(cr.center().x() - hs, cr.bottom() - hs, 2 * hs, 2 * hs).contains(pos):
            return self.HANDLE_B

        # Inside crop rect (move)
        if cr.contains(pos):
            return self.HANDLE_MOVE

        return self.HANDLE_NONE

    def paint(self, painter: QPainter, option, widget=None) -> None:
        if not self._crop_rect.isValid() or not self._image_rect.isValid():
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 1. Darkened Dimmed Mask Outside Crop Rect
        mask_path = QPainterPath()
        mask_path.addRect(self._image_rect)
        mask_path.addRect(self._crop_rect)
        painter.fillPath(mask_path, QBrush(QColor(0, 0, 0, 160)))

        # 2. Main Crop Rect Border
        cr = self._crop_rect
        painter.setPen(QPen(QColor("#ffffff"), 1.5, Qt.PenStyle.SolidLine))
        painter.drawRect(cr)

        # 3. Rule of Thirds Grid
        grid_pen = QPen(QColor(255, 255, 255, 90), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        for i in range(1, 3):
            gx = cr.left() + i * (cr.width() / 3.0)
            gy = cr.top() + i * (cr.height() / 3.0)
            painter.drawLine(QPointF(gx, cr.top()), QPointF(gx, cr.bottom()))
            painter.drawLine(QPointF(cr.left(), gy), QPointF(cr.right(), gy))

        # 4. Corner Bracket Handles
        bracket_len = 16.0
        bracket_pen = QPen(QColor("#ffffff"), 3.0, Qt.PenStyle.SolidLine)
        painter.setPen(bracket_pen)

        # Top-Left
        painter.drawLine(QPointF(cr.left(), cr.top()), QPointF(cr.left() + bracket_len, cr.top()))
        painter.drawLine(QPointF(cr.left(), cr.top()), QPointF(cr.left(), cr.top() + bracket_len))

        # Top-Right
        painter.drawLine(QPointF(cr.right(), cr.top()), QPointF(cr.right() - bracket_len, cr.top()))
        painter.drawLine(QPointF(cr.right(), cr.top()), QPointF(cr.right(), cr.top() + bracket_len))

        # Bottom-Left
        painter.drawLine(QPointF(cr.left(), cr.bottom()), QPointF(cr.left() + bracket_len, cr.bottom()))
        painter.drawLine(QPointF(cr.left(), cr.bottom()), QPointF(cr.left(), cr.bottom() - bracket_len))

        # Bottom-Right
        painter.drawLine(QPointF(cr.right(), cr.bottom()), QPointF(cr.right() - bracket_len, cr.bottom()))
        painter.drawLine(QPointF(cr.right(), cr.bottom()), QPointF(cr.right(), cr.bottom() - bracket_len))

    def hoverMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        handle = self._get_handle_at(event.pos())
        if handle in (self.HANDLE_TL, self.HANDLE_BR):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif handle in (self.HANDLE_TR, self.HANDLE_BL):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif handle in (self.HANDLE_L, self.HANDLE_R):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif handle in (self.HANDLE_T, self.HANDLE_B):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif handle == self.HANDLE_MOVE:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._active_handle = self._get_handle_at(event.pos())
            self._drag_start_pos = event.pos()
            self._drag_start_crop = QRectF(self._crop_rect)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._active_handle == self.HANDLE_NONE:
            return

        delta = event.pos() - self._drag_start_pos
        orig = self._drag_start_crop
        new_cr = QRectF(orig)

        if self._active_handle == self.HANDLE_MOVE:
            new_cr.translate(delta.x(), delta.y())

        elif self._aspect_ratio is None:
            # Freeform resizing
            if self._active_handle in (self.HANDLE_L, self.HANDLE_TL, self.HANDLE_BL):
                new_cr.setLeft(min(orig.right() - 30, orig.left() + delta.x()))
            if self._active_handle in (self.HANDLE_R, self.HANDLE_TR, self.HANDLE_BR):
                new_cr.setRight(max(orig.left() + 30, orig.right() + delta.x()))
            if self._active_handle in (self.HANDLE_T, self.HANDLE_TL, self.HANDLE_TR):
                new_cr.setTop(min(orig.bottom() - 30, orig.top() + delta.y()))
            if self._active_handle in (self.HANDLE_B, self.HANDLE_BL, self.HANDLE_BR):
                new_cr.setBottom(max(orig.top() + 30, orig.bottom() + delta.y()))
        else:
            # Aspect-constrained resizing
            ratio = self._aspect_ratio
            if self._active_handle in (self.HANDLE_BR, self.HANDLE_R, self.HANDLE_B):
                new_w = max(40.0, orig.width() + delta.x())
                new_h = new_w / ratio
                new_cr.setWidth(new_w)
                new_cr.setHeight(new_h)
            elif self._active_handle in (self.HANDLE_TL, self.HANDLE_L, self.HANDLE_T):
                new_w = max(40.0, orig.width() - delta.x())
                new_h = new_w / ratio
                new_cr.setLeft(orig.right() - new_w)
                new_cr.setTop(orig.bottom() - new_h)
            elif self._active_handle == self.HANDLE_TR:
                new_w = max(40.0, orig.width() + delta.x())
                new_h = new_w / ratio
                new_cr.setWidth(new_w)
                new_cr.setTop(orig.bottom() - new_h)
            elif self._active_handle == self.HANDLE_BL:
                new_w = max(40.0, orig.width() - delta.x())
                new_h = new_w / ratio
                new_cr.setLeft(orig.right() - new_w)
                new_cr.setHeight(new_h)

        self._crop_rect = new_cr
        self._clamp_to_image()
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._active_handle != self.HANDLE_NONE:
            self._active_handle = self.HANDLE_NONE
            self.scene().views()[0].cropBoxChanged.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class ImageCanvas(QGraphicsView):
    """High-performance image viewport supporting zoom, pan, and interactive crop overlay."""

    cropBoxChanged = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._current_pixmap: Optional[QPixmap] = None

        self._crop_overlay = CropOverlayItem()
        self._crop_overlay.setVisible(False)
        self.scene.addItem(self._crop_overlay)

        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("background-color: #1a1a1a; border: 1px solid #2d2d2d;")
        self._zoom_factor = 1.15

    def set_crop_mode(self, enabled: bool, aspect_ratio: Optional[float] = None) -> None:
        """Toggles interactive crop rectangle and handles."""
        self._crop_overlay.setVisible(enabled)
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self._crop_overlay.set_aspect_ratio(aspect_ratio)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.scene.update()

    def set_aspect_ratio(self, ratio: Optional[float]) -> None:
        self._crop_overlay.set_aspect_ratio(ratio)

    def get_crop_rect(self) -> Tuple[float, float, float, float]:
        return self._crop_overlay.get_normalized_crop()

    def reset_crop_overlay(self) -> None:
        self._crop_overlay.reset_crop()

    def set_numpy_image(self, image_array: Optional[np.ndarray]) -> None:
        if image_array is None or image_array.size == 0:
            self.scene.clear()
            self._pixmap_item = None
            self._current_pixmap = None
            return

        contiguous_array = np.ascontiguousarray(image_array)
        h, w, ch = contiguous_array.shape
        bytes_per_line = ch * w
        q_img = QImage(contiguous_array.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self._current_pixmap = QPixmap.fromImage(q_img)

        is_new_image = self._pixmap_item is None
        if is_new_image:
            self._pixmap_item = self.scene.addPixmap(self._current_pixmap)
            self._crop_overlay.setZValue(100)
        else:
            self._pixmap_item.setPixmap(self._current_pixmap)

        self.scene.setSceneRect(0, 0, w, h)
        self._crop_overlay.set_image_rect(QRectF(0, 0, w, h))

        if is_new_image:
            self.fit_to_view()

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