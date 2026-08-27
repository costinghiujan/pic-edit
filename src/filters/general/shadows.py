import numpy as np
from src.filters.base import ImageFilter


class ShadowsFilter(ImageFilter):
    """Adjusts the darkest tonal regions (shadows) of the image."""

    def __init__(self, amount: float = 0.0):
        self.amount = max(-1.0, min(1.0, float(amount)))

    def apply(self, image: np.ndarray) -> np.ndarray:
        if image is None or image.size == 0:
            raise ValueError("Invalid image buffer provided to ShadowsFilter.")

        if self.amount == 0.0:
            return image

        img_float = image.astype(np.float32) / 255.0
        luminance = 0.2126 * img_float[:, :, 0] + 0.7152 * img_float[:, :, 1] + 0.0722 * img_float[:, :, 2]

        shadow_mask = np.clip((0.5 - luminance) / 0.5, 0.0, 1.0)[:, :, np.newaxis]
        adjusted = img_float + (self.amount * shadow_mask * 0.5)

        return np.clip(adjusted * 255.0, 0.0, 255.0).astype(np.uint8)