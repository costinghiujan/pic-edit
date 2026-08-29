from typing import Optional
import numpy as np
from PySide6.QtWidgets import QWidget

from src.widgets.base_section import BaseSection
from src.curve_widget import CurveEditorWidget
from src.filters.curves import CurvesFilter


class CurvesSection(BaseSection):
    """Collapsible section housing the tone curves editor and live histogram."""

    def __init__(self, parent: Optional[QWidget] = None):
        self.editor: Optional[CurveEditorWidget] = None
        super().__init__(title="Curves", parent=parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.editor = CurveEditorWidget(self)
        self.editor.setEnabled(False)
        self.editor.curveChanged.connect(self.adjustmentsChanged.emit)
        self.add_widget(self.editor)

    def get_filter(self) -> Optional[CurvesFilter]:
        if not self.has_modifications():
            return None
        return CurvesFilter(
            channel_points=self.editor.get_points(),
            mode=self.editor.get_mode()
        )

    def has_modifications(self) -> bool:
        if self.editor is None:
            return False
        return self.editor.canvas.is_modified()

    def set_histogram_image(self, image: Optional[np.ndarray]) -> None:
        if self.editor is not None:
            self.editor.set_histogram_image(image)

    def reset_adjustments(self) -> None:
        if self.editor is not None:
            self.editor.reset()
        self.adjustmentsChanged.emit()

    def set_enabled(self, enabled: bool) -> None:
        self.set_reset_enabled(enabled)
        if self.editor is not None:
            self.editor.setEnabled(enabled)