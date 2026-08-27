import cv2
import numpy as np
from src.filters.base import ImageFilter


class ExposureFilter(ImageFilter):
    """Adjusts exposure linearly using EV (Exposure Value) stops."""

    def __init__(self, ev_stops: float = 0.0):
        self.ev_stops = float(ev_stops)

    def apply(self, image: np.ndarray) -> np.ndarray:
        if image is None or image.size == 0:
            raise ValueError("Invalid image buffer provided to ExposureFilter.")

        if self.ev_stops == 0.0:
            return image

        scale_factor = 2.0 ** self.ev_stops
        return cv2.convertScaleAbs(image, alpha=scale_factor, beta=0)