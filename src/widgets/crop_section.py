from typing import Dict, Optional, Tuple
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget
)

from src.filters.geometry import GeometryFilter
from src.widgets.base_section import BaseSection
from src.widgets.labeled_slider import LabeledSlider


class AspectRatioButton(QPushButton):
    def __init__(self, name: str, ratio: Optional[float], parent: Optional[QWidget] = None):
        super().__init__(name, parent)
        self.base_name = name
        self.base_ratio = ratio
        self.is_portrait = False
        self._is_active_workspace = False
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #262626;
                color: #cccccc;
                font-size: 11px;
                border: 1px solid #383838;
                border-radius: 3px;
                padding: 5px 2px;
            }
            QPushButton:hover {
                background-color: #303030;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #3b82f6;
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #60a5fa;
            }
        """)


class CropSection(BaseSection):
    """Collapsible section housing Aspect Ratio, Straighten, and Orientation controls."""

    aspectRatioChanged = Signal(object)  # Emits Optional[float]

    def __init__(self, parent: Optional[QWidget] = None):
        self._discrete_rot = 0
        self._flip_h = False
        self._flip_v = False
        self._active_ratio: Optional[float] = None
        self._crop_rect: Optional[Tuple[float, float, float, float]] = None
        self._selected_btn: Optional[AspectRatioButton] = None

        super().__init__(title="Crop & Transform", parent=parent)
        self._build_ui()

    def _build_ui(self) -> None:
        # 1. Aspect Ratio
        ar_title = QLabel("ASPECT RATIO", self)
        ar_title.setStyleSheet("color: #888888; font-size: 10px; font-weight: bold; margin-top: 4px;")
        self.add_widget(ar_title)

        grid_widget = QWidget(self)
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)

        ratios = [
            ("Free", None),
            ("Original", -1.0),
            ("1:1", 1.0),
            ("5:4", 5.0 / 4.0),
            ("4:3", 4.0 / 3.0),
            ("3:2", 3.0 / 2.0),
            ("16:9", 16.0 / 9.0),
            ("21:9", 21.0 / 9.0),
            ("2:1", 2.0 / 1.0),
        ]

        self.ar_buttons: list[AspectRatioButton] = []
        for idx, (name, ratio) in enumerate(ratios):
            btn = AspectRatioButton(name, ratio, self)
            btn.clicked.connect(lambda _, b=btn: self._on_aspect_ratio_clicked(b))
            self.ar_buttons.append(btn)
            grid.addWidget(btn, idx // 3, idx % 3)

        self.ar_buttons[0].setChecked(True)
        self._selected_btn = self.ar_buttons[0]
        self.add_widget(grid_widget)

        # 2. Rotation Slider
        rot_title = QLabel("STRAIGHTEN & ROTATION", self)
        rot_title.setStyleSheet("color: #888888; font-size: 10px; font-weight: bold; margin-top: 10px;")
        self.add_widget(rot_title)

        self.rotation_slider = LabeledSlider(
            name="Angle",
            min_val=-45.0,
            max_val=45.0,
            default_val=0.0,
            scale=10.0,
            formatter=lambda v: f"Angle: {v:+.1f}°",
            parent=self
        )
        self.rotation_slider.valueChanged.connect(lambda _: self.adjustmentsChanged.emit())
        self.add_widget(self.rotation_slider)

        # 3. Orientation Tools
        orient_title = QLabel("ORIENTATION", self)
        orient_title.setStyleSheet("color: #888888; font-size: 10px; font-weight: bold; margin-top: 10px;")
        self.add_widget(orient_title)

        orient_widget = QWidget(self)
        orient_layout = QHBoxLayout(orient_widget)
        orient_layout.setContentsMargins(0, 0, 0, 0)
        orient_layout.setSpacing(4)

        btn_style = """
            QPushButton {
                background-color: #262626;
                color: #e0e0e0;
                font-size: 11px;
                border: 1px solid #383838;
                border-radius: 3px;
                padding: 5px 0px;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """

        self.btn_rot_left = QPushButton("↺ 90°", self)
        self.btn_rot_left.setStyleSheet(btn_style)
        self.btn_rot_left.clicked.connect(self._rotate_left)
        orient_layout.addWidget(self.btn_rot_left)

        self.btn_rot_right = QPushButton("↻ 90°", self)
        self.btn_rot_right.setStyleSheet(btn_style)
        self.btn_rot_right.clicked.connect(self._rotate_right)
        orient_layout.addWidget(self.btn_rot_right)

        self.btn_flip_h = QPushButton("⇄ Flip H", self)
        self.btn_flip_h.setStyleSheet(btn_style)
        self.btn_flip_h.clicked.connect(self._toggle_flip_h)
        orient_layout.addWidget(self.btn_flip_h)

        self.btn_flip_v = QPushButton("⇅ Flip V", self)
        self.btn_flip_v.setStyleSheet(btn_style)
        self.btn_flip_v.clicked.connect(self._toggle_flip_v)
        orient_layout.addWidget(self.btn_flip_v)

        self.add_widget(orient_widget)

    def _on_aspect_ratio_clicked(self, clicked_btn: AspectRatioButton) -> None:
        for btn in self.ar_buttons:
            if btn != clicked_btn:
                btn.setChecked(False)
                btn.is_portrait = False
                btn.setText(btn.base_name)

        if self._selected_btn == clicked_btn and clicked_btn.base_ratio not in (None, 1.0, -1.0):
            clicked_btn.is_portrait = not clicked_btn.is_portrait
            w, h = clicked_btn.base_name.split(":")
            clicked_btn.setText(f"{h}:{w}" if clicked_btn.is_portrait else clicked_btn.base_name)
        else:
            self._selected_btn = clicked_btn
            clicked_btn.setChecked(True)

        if clicked_btn.base_ratio is None or clicked_btn.base_ratio == -1.0:
            self._active_ratio = None
        else:
            ratio = clicked_btn.base_ratio
            self._active_ratio = (1.0 / ratio) if clicked_btn.is_portrait else ratio

        self.aspectRatioChanged.emit(self._active_ratio)

    def _rotate_left(self) -> None:
        self._discrete_rot = (self._discrete_rot + 90) % 360
        self.adjustmentsChanged.emit()

    def _rotate_right(self) -> None:
        self._discrete_rot = (self._discrete_rot - 90) % 360
        self.adjustmentsChanged.emit()

    def _toggle_flip_h(self) -> None:
        self._flip_h = not self._flip_h
        self.adjustmentsChanged.emit()

    def _toggle_flip_v(self) -> None:
        self._flip_v = not self._flip_v
        self.adjustmentsChanged.emit()

    def set_crop_rect(self, rect: Optional[Tuple[float, float, float, float]]) -> None:
        self._crop_rect = rect

    def get_filter(self) -> Optional[GeometryFilter]:
        if not self.has_modifications():
            return None
        return GeometryFilter(
            discrete_rotation=self._discrete_rot,
            flip_h=self._flip_h,
            flip_v=self._flip_v,
            angle_deg=self.rotation_slider.value,
            crop_rect=self._crop_rect,
        )

    def has_modifications(self) -> bool:
        return (
            self._discrete_rot != 0
            or self._flip_h
            or self._flip_v
            or abs(self.rotation_slider.value) > 0.01
            or (self._crop_rect is not None and self._crop_rect != (0.0, 0.0, 1.0, 1.0))
        )

    def reset_adjustments(self) -> None:
        self._discrete_rot = 0
        self._flip_h = False
        self._flip_v = False
        self._active_ratio = None
        self._crop_rect = None
        self.rotation_slider.reset()

        for btn in self.ar_buttons:
            btn.setChecked(False)
            btn.is_portrait = False
            btn.setText(btn.base_name)
        self.ar_buttons[0].setChecked(True)
        self._selected_btn = self.ar_buttons[0]

        self.aspectRatioChanged.emit(None)
        self.adjustmentsChanged.emit()

    def set_enabled(self, enabled: bool) -> None:
        self.set_reset_enabled(enabled)
        self.rotation_slider.set_enabled(enabled)
        for btn in self.ar_buttons:
            btn.setEnabled(enabled)
        self.btn_rot_left.setEnabled(enabled)
        self.btn_rot_right.setEnabled(enabled)
        self.btn_flip_h.setEnabled(enabled)
        self.btn_flip_v.setEnabled(enabled)

    def set_workspace_active(self, active: bool) -> None:
        """Sets whether the crop tool workspace is actively being manipulated."""
        self._is_active_workspace = active
        self.adjustmentsChanged.emit()

    def get_filter(self) -> Optional[GeometryFilter]:
        if not self.has_modifications():
            return None

        # When active inside the crop workspace, do not slice the buffer so the user can see the full image.
        # When outside the crop workspace (Develop tab or Export), apply the physical crop slice.
        effective_crop = None if getattr(self, "_is_active_workspace", False) else self._crop_rect

        return GeometryFilter(
            discrete_rotation=self._discrete_rot,
            flip_h=self._flip_h,
            flip_v=self._flip_v,
            angle_deg=self.rotation_slider.value,
            crop_rect=effective_crop,
        )