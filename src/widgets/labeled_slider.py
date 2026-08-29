from typing import Callable, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QLabel, QSlider, QVBoxLayout, QWidget


class ResetableSlider(QSlider):
    """Native QSlider supporting double-click to reset."""

    def __init__(self, orientation: Qt.Orientation, default_val: int = 0, parent: QWidget = None):
        super().__init__(orientation, parent)
        self.default_val = default_val

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.setValue(self.default_val)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)


class LabeledSlider(QWidget):
    """
    Composite widget containing a dynamic label and a resetable slider.
    Handles float scale conversion and text formatting internally.
    """

    valueChanged = Signal(float)

    def __init__(
        self,
        name: str,
        min_val: float,
        max_val: float,
        default_val: float = 0.0,
        scale: float = 1.0,
        formatter: Optional[Callable[[float], str]] = None,
        parent: QWidget = None,
    ):
        """
        :param name: Base display name (e.g., 'Exposure', 'Contrast').
        :param min_val: Minimum floating-point value.
        :param max_val: Maximum floating-point value.
        :param default_val: Initial floating-point value.
        :param scale: Multiplier for integer slider steps (e.g. 10.0 for 0.1 increments, 100.0 for 0.01).
        :param formatter: Custom string formatter function `f(float_val) -> str`.
        """
        super().__init__(parent)
        self._name = name
        self._scale = float(scale)
        self._formatter = formatter or (lambda v: f"{self._name}: {v:+.2f}")
        self._default_float = default_val

        # Integer equivalents for QSlider
        self._int_min = int(round(min_val * self._scale))
        self._int_max = int(round(max_val * self._scale))
        self._int_default = int(round(default_val * self._scale))

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.label = QLabel(self._formatter(self._default_float), self)
        self.label.setStyleSheet("color: #e0e0e0; font-size: 12px;")

        self.slider = ResetableSlider(Qt.Orientation.Horizontal, default_val=self._int_default, parent=self)
        self.slider.setRange(self._int_min, self._int_max)
        self.slider.setValue(self._int_default)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self._on_slider_value_changed)

        layout.addWidget(self.label)
        layout.addWidget(self.slider)

    def _on_slider_value_changed(self, int_val: int) -> None:
        float_val = int_val / self._scale
        self.label.setText(self._formatter(float_val))
        self.valueChanged.emit(float_val)

    @property
    def value(self) -> float:
        return self.slider.value() / self._scale

    def set_value(self, val: float) -> None:
        int_val = int(round(val * self._scale))
        self.slider.setValue(int_val)

    def reset(self) -> None:
        """Resets the slider without emitting duplicate signals during mass updates."""
        self.slider.blockSignals(True)
        self.slider.setValue(self._int_default)
        self.label.setText(self._formatter(self._default_float))
        self.slider.blockSignals(False)

    def set_enabled(self, enabled: bool) -> None:
        self.slider.setEnabled(enabled)