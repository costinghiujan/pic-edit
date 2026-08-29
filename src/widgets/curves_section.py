from typing import Optional
import numpy as np
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget
from src.collapsible_section import CollapsibleSection
from src.curve_widget import CurveEditorWidget
from src.filters.curves import CurvesFilter


class CurvesSection(CollapsibleSection):
    """Encapsulates the curve editor widget and histogram controls into a collapsible panel."""

    adjustmentsChanged = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(title="Curves", on_reset=self.reset_adjustments, parent=parent)
        self.editor = CurveEditorWidget(self)
        self.editor.setEnabled(False)
        self.editor.curveChanged.connect(self.adjustmentsChanged.emit)
        self.add_widget(self.editor)

    def get_filter(self) -> CurvesFilter:
        return CurvesFilter(channel_points=self.editor.get_points())

    def has_modifications(self) -> bool:
        return self.editor.canvas.is_modified()

    def set_histogram_image(self, image: Optional[np.ndarray]) -> None:
        self.editor.set_histogram_image(image)

    def reset_adjustments(self) -> None:
        self.editor.reset()
        self.adjustmentsChanged.emit()

    def set_enabled(self, enabled: bool) -> None:
        self.set_reset_enabled(enabled)
        self.editor.setEnabled(enabled)