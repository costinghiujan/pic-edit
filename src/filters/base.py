from abc import ABC, abstractmethod
import numpy as np


class ImageFilter(ABC):
    """Abstract base class for all image processing filters (Strategy Pattern)."""

    @abstractmethod
    def apply(self, image: np.ndarray) -> np.ndarray:
        """
        Applies a transformation to an RGB image array.

        :param image: Input NumPy array (uint8).
        :return: Transformed NumPy array (uint8).
        """
        pass