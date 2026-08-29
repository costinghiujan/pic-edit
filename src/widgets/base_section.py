from abc import abstractmethod
from typing import Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from src.collapsible_section import CollapsibleSection
from src.filters.base import ImageFilter


class BaseSection(CollapsibleSection):
    """
    Abstract base class for all sidebar tool sections.
    Ensures uniform lifecycle, state querying, and filter emission across all tools.
    """

    adjustmentsChanged = Signal()

    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(title=title, on_reset=self.reset_adjustments, parent=parent)

    @abstractmethod
    def get_filter(self) -> Optional[ImageFilter]:
        """Builds and returns the configured ImageFilter instance, or None if inactive."""
        pass

    @abstractmethod
    def has_modifications(self) -> bool:
        """Returns True if the section values differ from their default states."""
        pass

    @abstractmethod
    def reset_adjustments(self) -> None:
        """Resets all internal controls to their default values and emits adjustmentsChanged."""
        pass

    @abstractmethod
    def set_enabled(self, enabled: bool) -> None:
        """Enables or disables user interaction for this entire section."""
        pass