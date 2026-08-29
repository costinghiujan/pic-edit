from typing import Dict, Optional
from PySide6.QtWidgets import QWidget

from src.widgets.base_section import BaseSection
from src.widgets.labeled_slider import LabeledSlider
from src.filters.general import ToneAdjustmentsFilter


class GeneralSection(BaseSection):
    """Collapsible section housing the tone adjustment sliders."""

    def __init__(self, parent: Optional[QWidget] = None):
        self._sliders: Dict[str, LabeledSlider] = {}
        super().__init__(title="General", parent=parent)
        self._build_ui()

    def _build_ui(self) -> None:
        specs = [
            ("exposure", "Exposure", -2.0, 2.0, 0.0, 10.0, lambda v: f"Exposure: {v:+.2f} EV"),
            ("contrast", "Contrast", -1.0, 1.0, 0.0, 100.0, lambda v: f"Contrast: {1.0 + v:.2f}x"),
            ("highlights", "Highlights", -1.0, 1.0, 0.0, 100.0, lambda v: f"Highlights: {v:+.2f}"),
            ("shadows", "Shadows", -1.0, 1.0, 0.0, 100.0, lambda v: f"Shadows: {v:+.2f}"),
            ("whites", "Whites", -1.0, 1.0, 0.0, 100.0, lambda v: f"Whites: {v:+.2f}"),
            ("blacks", "Blacks", -1.0, 1.0, 0.0, 100.0, lambda v: f"Blacks: {v:+.2f}"),
        ]

        for key, name, min_v, max_v, def_v, scale, fmt in specs:
            slider = LabeledSlider(name, min_v, max_v, def_v, scale, fmt, self)
            slider.valueChanged.connect(lambda _: self.adjustmentsChanged.emit())
            self._sliders[key] = slider
            self.add_widget(slider)

    def get_filter(self) -> Optional[ToneAdjustmentsFilter]:
        if not self.has_modifications():
            return None
        return ToneAdjustmentsFilter(
            exposure_ev=self._sliders["exposure"].value,
            contrast_factor=1.0 + self._sliders["contrast"].value,
            highlights=self._sliders["highlights"].value,
            shadows=self._sliders["shadows"].value,
            whites=self._sliders["whites"].value,
            blacks=self._sliders["blacks"].value,
        )

    def has_modifications(self) -> bool:
        return any(slider.value != slider._default_float for slider in self._sliders.values())

    def reset_adjustments(self) -> None:
        for slider in self._sliders.values():
            slider.reset()
        self.adjustmentsChanged.emit()

    def set_enabled(self, enabled: bool) -> None:
        self.set_reset_enabled(enabled)
        for slider in self._sliders.values():
            slider.set_enabled(enabled)