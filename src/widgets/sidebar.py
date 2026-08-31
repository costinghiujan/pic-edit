from typing import List, Optional
import numpy as np
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from src.filters.base import ImageFilter
from src.widgets.base_section import BaseSection
from src.widgets.curves_section import CurvesSection
from src.widgets.general_section import GeneralSection
from src.widgets.crop_section import CropSection


class Sidebar(QWidget):
    """
    Multi-tab sidebar containing stacked panels (Develop, Crop, etc.).
    """

    adjustmentsChanged = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedWidth(310)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.stack = QStackedWidget(self)

        # Tab 0: Develop Panel (Scrollable General + Curves)
        develop_scroll = QScrollArea(self)
        develop_scroll.setWidgetResizable(True)
        develop_scroll.setFrameShape(QFrame.Shape.NoFrame)
        develop_scroll.setStyleSheet("background-color: #1e1e1e;")

        develop_container = QWidget()
        develop_layout = QVBoxLayout(develop_container)
        develop_layout.setContentsMargins(0, 0, 0, 0)
        develop_layout.setSpacing(10)

        self.general_section = GeneralSection(self)
        self.curves_section = CurvesSection(self)
        self.develop_sections: List[BaseSection] = [self.general_section, self.curves_section]

        for section in self.develop_sections:
            section.adjustmentsChanged.connect(self.adjustmentsChanged.emit)
            develop_layout.addWidget(section)

        develop_layout.addStretch()
        develop_scroll.setWidget(develop_container)
        self.stack.addWidget(develop_scroll)

        # Tab 1: Crop Panel (Scrollable)
        crop_scroll = QScrollArea(self)
        crop_scroll.setWidgetResizable(True)
        crop_scroll.setFrameShape(QFrame.Shape.NoFrame)
        crop_scroll.setStyleSheet("background-color: #1e1e1e;")

        crop_container = QWidget()
        crop_layout = QVBoxLayout(crop_container)
        crop_layout.setContentsMargins(0, 0, 0, 0)
        crop_layout.setSpacing(10)

        self.crop_section = CropSection(self)
        self.crop_section.adjustmentsChanged.connect(self.adjustmentsChanged.emit)
        crop_layout.addWidget(self.crop_section)
        crop_layout.addStretch()

        crop_scroll.setWidget(crop_container)
        self.stack.addWidget(crop_scroll)

        main_layout.addWidget(self.stack)

    @property
    def all_sections(self) -> List[BaseSection]:
        return self.develop_sections + [self.crop_section]

    def set_current_tab(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def get_active_filters(self) -> List[ImageFilter]:
        filters = []
        for sec in self.all_sections:
            f = sec.get_filter()
            if f is not None:
                filters.append(f)
        return filters

    def is_modified(self) -> bool:
        return any(sec.has_modifications() for sec in self.all_sections)

    def set_enabled(self, enabled: bool) -> None:
        for sec in self.all_sections:
            sec.set_enabled(enabled)

    def reset_all(self) -> None:
        for sec in self.all_sections:
            sec.reset_adjustments()

    def update_histograms(self, image: Optional[np.ndarray]) -> None:
        self.curves_section.set_histogram_image(image)