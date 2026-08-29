from typing import List, Optional
import numpy as np
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from src.filters.base import ImageFilter
from src.widgets.base_section import BaseSection
from src.widgets.curves_section import CurvesSection
from src.widgets.general_section import GeneralSection


class Sidebar(QScrollArea):
    """
    Scrollable tool sidebar that manages and aggregates all adjustment sections.
    """

    adjustmentsChanged = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedWidth(310)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background-color: #1e1e1e;")

        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)

        # Section instances
        self.general_section = GeneralSection(self)
        self.curves_section = CurvesSection(self)
        self.sections: List[BaseSection] = [self.general_section, self.curves_section]

        for section in self.sections:
            section.adjustmentsChanged.connect(self.adjustmentsChanged.emit)
            self.layout.addWidget(section)

        self.layout.addStretch()
        self.setWidget(container)

    def get_active_filters(self) -> List[ImageFilter]:
        """Collects valid filters from all modified sections."""
        filters = []
        for sec in self.sections:
            f = sec.get_filter()
            if f is not None:
                filters.append(f)
        return filters

    def is_modified(self) -> bool:
        """Returns True if any section has values differing from defaults."""
        return any(sec.has_modifications() for sec in self.sections)

    def set_enabled(self, enabled: bool) -> None:
        """Enables or disables user interaction for all sections."""
        for sec in self.sections:
            sec.set_enabled(enabled)

    def reset_all(self) -> None:
        """Resets all sections back to default values."""
        for sec in self.sections:
            sec.reset_adjustments()

    def update_histograms(self, image: Optional[np.ndarray]) -> None:
        """Propagates updated preview buffer to sections with histogram rendering."""
        self.curves_section.set_histogram_image(image)