import cv2
import numpy as np
from src.filters.base import ImageFilter


class ContrastFilter(ImageFilter):
    """Adjusts image contrast relative to mid-tone gray (128)."""

    def __init__(self, factor: float = 1.0):
        self.factor = max(0.0, float(factor))

    def apply(self, image: np.ndarray) -> np.ndarray:
        if image is None or image.size == 0:
            raise ValueError("Invalid image buffer provided to ContrastFilter.")

        if self.factor == 1.0:
            return image

        beta = 128.0 * (1.0 - self.factor)
        return cv2.convertScaleAbs(image, alpha=self.factor, beta=beta)