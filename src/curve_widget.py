from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QVBoxLayout, QWidget


class CurveCanvas(QWidget):
    """Interactive canvas for drawing and manipulating spline curve control points."""

    curveChanged = Signal()

    CHANNEL_COLORS = {
        "RGB": QColor(220, 220, 220),
        "R": QColor(235, 75, 75),
        "G": QColor(75, 200, 75),
        "B": QColor(75, 130, 235),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._active_channel = "RGB"
        self._points: Dict[str, List[Tuple[float, float]]] = {
            "RGB": [(0.0, 0.0), (1.0, 1.0)],
            "R": [(0.0, 0.0), (1.0, 1.0)],
            "G": [(0.0, 0.0), (1.0, 1.0)],
            "B": [(0.0, 0.0), (1.0, 1.0)],
        }

        self._selected_pt_idx: Optional[int] = None
        self._histogram_data: Optional[Dict[str, np.ndarray]] = None

    def set_active_channel(self, channel: str) -> None:
        if channel in self._points:
            self._active_channel = channel
            self._selected_pt_idx = None
            self.update()

    def set_histogram(self, image: Optional[np.ndarray]) -> None:
        """Computes histogram bins [0..255] for RGB/Luma channels."""
        if image is None or image.size == 0:
            self._histogram_data = None
            self.update()
            return

        hist_data = {}
        # Luma / Gray
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        hist_data["RGB"] = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()

        # Channels
        for idx, ch in enumerate(["R", "G", "B"]):
            hist_data[ch] = cv2.calcHist([image], [idx], None, [256], [0, 256]).flatten()

        # Normalize histograms to [0, 1] relative to maximum
        for k in hist_data:
            max_val = np.max(hist_data[k])
            if max_val > 0:
                hist_data[k] = hist_data[k] / max_val

        self._histogram_data = hist_data
        self.update()

    def get_all_points(self) -> Dict[str, List[Tuple[float, float]]]:
        return self._points

    def reset_active_curve(self) -> None:
        self._points[self._active_channel] = [(0.0, 0.0), (1.0, 1.0)]
        self._selected_pt_idx = None
        self.update()
        self.curveChanged.emit()

    def reset_all_curves(self) -> None:
        for ch in self._points:
            self._points[ch] = [(0.0, 0.0), (1.0, 1.0)]
        self._selected_pt_idx = None
        self.update()
        self.curveChanged.emit()

    def _to_screen_coords(self, pt: Tuple[float, float], rect: QRectF) -> QPointF:
        x = rect.left() + pt[0] * rect.width()
        y = rect.bottom() - pt[1] * rect.height()
        return QPointF(x, y)

    def _to_normalized_coords(self, pos: QPointF, rect: QRectF) -> Tuple[float, float]:
        norm_x = (pos.x() - rect.left()) / rect.width()
        norm_y = (rect.bottom() - pos.y()) / rect.height()
        return max(0.0, min(1.0, norm_x)), max(0.0, min(1.0, norm_y))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        margin = 10
        rect = QRectF(margin, margin, self.width() - 2 * margin, self.height() - 2 * margin)

        # Background
        painter.fillRect(self.rect(), QColor("#1c1c1c"))
        painter.fillRect(rect, QColor("#121212"))

        # Grid lines (4x4)
        grid_pen = QPen(QColor("#2c2c2c"), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        for i in range(1, 4):
            x = rect.left() + i * (rect.width() / 4.0)
            y = rect.top() + i * (rect.height() / 4.0)
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

        # Diagonal baseline
        painter.setPen(QPen(QColor("#383838"), 1, Qt.PenStyle.SolidLine))
        painter.drawLine(rect.bottomLeft(), rect.topRight())

        # Render Background Histogram
        if self._histogram_data and self._active_channel in self._histogram_data:
            hist = self._histogram_data[self._active_channel]
            color = self.CHANNEL_COLORS[self._active_channel]
            hist_color = QColor(color.red(), color.green(), color.blue(), 45)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(hist_color))

            hist_path = QPainterPath()
            hist_path.moveTo(rect.bottomLeft())
            for idx, val in enumerate(hist):
                bin_x = rect.left() + (idx / 255.0) * rect.width()
                bin_y = rect.bottom() - (val * rect.height() * 0.85)  # scale slightly below ceiling
                hist_path.lineTo(bin_x, bin_y)
            hist_path.lineTo(rect.bottomRight())
            hist_path.closeSubpath()
            painter.drawPath(hist_path)

        # Render Curve Lines
        active_color = self.CHANNEL_COLORS[self._active_channel]
        pts = sorted(self._points[self._active_channel], key=lambda p: p[0])

        x_pts = np.array([p[0] * 255.0 for p in pts], dtype=np.float32)
        y_pts = np.array([p[1] * 255.0 for p in pts], dtype=np.float32)
        if x_pts[0] > 0:
            x_pts = np.insert(x_pts, 0, 0.0)
            y_pts = np.insert(y_pts, 0, y_pts[0])
        if x_pts[-1] < 255:
            x_pts = np.append(x_pts, 255.0)
            y_pts = np.append(y_pts, y_pts[-1])

        x_eval = np.linspace(0, 255, 128)
        y_eval = np.interp(x_eval, x_pts, y_pts)

        curve_path = QPainterPath()
        start_pt = self._to_screen_coords((x_eval[0] / 255.0, y_eval[0] / 255.0), rect)
        curve_path.moveTo(start_pt)
        for i in range(1, len(x_eval)):
            pt = self._to_screen_coords((x_eval[i] / 255.0, y_eval[i] / 255.0), rect)
            curve_path.lineTo(pt)

        painter.setPen(QPen(active_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(curve_path)

        # Render Control Points
        for idx, pt in enumerate(pts):
            screen_pt = self._to_screen_coords(pt, rect)
            is_selected = idx == self._selected_pt_idx

            painter.setPen(QPen(QColor("#ffffff") if is_selected else active_color, 2))
            painter.setBrush(QBrush(active_color if is_selected else QColor("#1e1e1e")))
            painter.drawEllipse(screen_pt, 4.5, 4.5)

        # Outer border
        painter.setPen(QPen(QColor("#3c3c3c"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        margin = 10
        rect = QRectF(margin, margin, self.width() - 2 * margin, self.height() - 2 * margin)
        norm_x, norm_y = self._to_normalized_coords(event.position(), rect)

        pts = self._points[self._active_channel]

        # Check if an existing point was clicked
        hit_radius = 8.0
        clicked_idx = None
        for idx, pt in enumerate(pts):
            screen_pt = self._to_screen_coords(pt, rect)
            dist = (screen_pt - event.position()).manhattanLength()
            if dist <= hit_radius:
                clicked_idx = idx
                break

        if clicked_idx is not None:
            self._selected_pt_idx = clicked_idx
        else:
            # Add new control point (limit to maximum 8 points per channel)
            if len(pts) < 8:
                pts.append((norm_x, norm_y))
                pts.sort(key=lambda p: p[0])
                self._selected_pt_idx = pts.index((norm_x, norm_y))
                self.curveChanged.emit()

        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._selected_pt_idx is None:
            return

        margin = 10
        rect = QRectF(margin, margin, self.width() - 2 * margin, self.height() - 2 * margin)
        norm_x, norm_y = self._to_normalized_coords(event.position(), rect)

        pts = self._points[self._active_channel]

        # Pin endpoints x-coordinates to 0.0 and 1.0
        if self._selected_pt_idx == 0:
            norm_x = 0.0
        elif self._selected_pt_idx == len(pts) - 1:
            norm_x = 1.0
        else:
            # Keep ordered between neighbors
            min_x = pts[self._selected_pt_idx - 1][0] + 0.02
            max_x = pts[self._selected_pt_idx + 1][0] - 0.02
            norm_x = max(min_x, min(max_x, norm_x))

        pts[self._selected_pt_idx] = (norm_x, norm_y)
        self.update()
        self.curveChanged.emit()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Resets the currently active channel curve on double click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.reset_active_curve()
            event.accept()


class CurveEditorWidget(QWidget):
    """Container widget pairing channel buttons with the CurveCanvas."""

    curveChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Channel Selector Buttons (RGB, R, G, B)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        channels = [("RGB", "#e0e0e0"), ("R", "#ff5555"), ("G", "#55ff55"), ("B", "#5599ff")]
        for ch_name, color_hex in channels:
            btn = QPushButton(ch_name, self)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2b2b2b;
                    color: {color_hex};
                    font-weight: bold;
                    border: 1px solid #3c3c3c;
                    border-radius: 3px;
                    padding: 4px;
                }}
                QPushButton:checked {{
                    background-color: #404040;
                    border: 1px solid {color_hex};
                }}
            """)
            if ch_name == "RGB":
                btn.setChecked(True)

            btn.clicked.connect(lambda _, ch=ch_name: self.canvas.set_active_channel(ch))
            self.btn_group.addButton(btn)
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

        # Canvas
        self.canvas = CurveCanvas(self)
        self.canvas.curveChanged.connect(self.curveChanged.emit)
        layout.addWidget(self.canvas)

    def set_histogram_image(self, image: Optional[np.ndarray]) -> None:
        self.canvas.set_histogram(image)

    def get_points(self) -> Dict[str, List[Tuple[float, float]]]:
        return self.canvas.get_all_points()

    def reset(self) -> None:
        self.canvas.reset_all_curves()