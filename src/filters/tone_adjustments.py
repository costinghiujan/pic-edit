import cv2
import numpy as np
from src.filters.base import ImageFilter


class ToneAdjustmentsFilter(ImageFilter):
    """
    Combines Exposure, Contrast, Highlights, Shadows, Whites, and Blacks
    into a single precomputed 256-value Look-Up Table (LUT) for sub-millisecond execution.
    """

    def __init__(
        self,
        exposure_ev: float = 0.0,
        contrast_factor: float = 1.0,
        highlights: float = 0.0,
        shadows: float = 0.0,
        whites: float = 0.0,
        blacks: float = 0.0,
    ):
        self.exposure_ev = float(exposure_ev)
        self.contrast_factor = max(0.0, float(contrast_factor))
        self.highlights = max(-1.0, min(1.0, float(highlights)))
        self.shadows = max(-1.0, min(1.0, float(shadows)))
        self.whites = max(-1.0, min(1.0, float(whites)))
        self.blacks = max(-1.0, min(1.0, float(blacks)))

    def _build_lut(self) -> np.ndarray:
        """Computes the 256-entry mapping curve in float32 and returns uint8 LUT."""
        # 1. Base linear array [0.0 ... 1.0]
        curve = np.linspace(0.0, 1.0, 256, dtype=np.float32)

        # 2. Exposure scaling (2^EV)
        if self.exposure_ev != 0.0:
            curve *= (2.0 ** self.exposure_ev)

        # 3. Contrast adjustment centered at 0.5 (mid-gray)
        if self.contrast_factor != 1.0:
            curve = self.contrast_factor * (curve - 0.5) + 0.5

        # 4. Tonal Masks calculated on the curve itself
        if self.highlights != 0.0:
            # Targets 0.5 to 1.0
            hl_mask = np.clip((curve - 0.5) / 0.5, 0.0, 1.0)
            curve += self.highlights * hl_mask * 0.35

        if self.shadows != 0.0:
            # Targets 0.0 to 0.5
            sh_mask = np.clip((0.5 - curve) / 0.5, 0.0, 1.0)
            curve += self.shadows * sh_mask * 0.35

        if self.whites != 0.0:
            # Targets extreme brights (0.75 to 1.0)
            wh_mask = np.clip((curve - 0.75) / 0.25, 0.0, 1.0)
            curve += self.whites * wh_mask * 0.3

        if self.blacks != 0.0:
            # Targets extreme darks (0.0 to 0.25)
            bl_mask = np.clip((0.25 - curve) / 0.25, 0.0, 1.0)
            curve += self.blacks * bl_mask * 0.3

        # Clamp between [0, 255] and return 8-bit table
        lut_8u = np.clip(curve * 255.0, 0.0, 255.0).astype(np.uint8)
        return lut_8u

    def apply(self, image: np.ndarray) -> np.ndarray:
        if image is None or image.size == 0:
            raise ValueError("Invalid image buffer provided to ToneAdjustmentsFilter.")

        # If no adjustments are made, return immediately
        if (
            self.exposure_ev == 0.0
            and self.contrast_factor == 1.0
            and self.highlights == 0.0
            and self.shadows == 0.0
            and self.whites == 0.0
            and self.blacks == 0.0
        ):
            return image

        # Generate the LUT and apply it across all 3 channels in C++
        lut = self._build_lut()
        return cv2.LUT(image, lut)