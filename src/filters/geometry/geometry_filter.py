import math
from typing import Optional, Tuple
import cv2
import numpy as np
from src.filters.base import ImageFilter


def _crop_largest_inner_rect(image: np.ndarray, angle_deg: float) -> np.ndarray:
    """
    Crops the image to the largest inscribed bounding box maintaining the exact
    original aspect ratio, mathematically eliminating any black border wedges.
    """
    angle_rad = math.radians(abs(angle_deg))
    if angle_rad < 1e-4:
        return image

    h, w = image.shape[:2]
    sin_a = math.sin(angle_rad)
    cos_a = math.cos(angle_rad)

    # Denominator for the two bounding constraints
    denom = w * sin_a + h * cos_a
    denom_inv = w * cos_a + h * sin_a

    # Calculate max possible width bounded by both rotated coordinate axes
    bound_1 = (w * w) / denom_inv
    bound_2 = (w * h) / denom
    max_w = min(bound_1, bound_2)

    # Keep exact original aspect ratio
    max_h = max_w * (h / float(w))

    # Subtract 2 pixels safety margin to eliminate subpixel interpolation bleed
    crop_w = int(math.floor(max_w)) - 2
    crop_h = int(math.floor(max_h)) - 2

    # Clamp safety bounds
    crop_w = max(2, min(w, crop_w))
    crop_h = max(2, min(h, crop_h))

    center_x = w // 2
    center_y = h // 2

    x1 = max(0, center_x - crop_w // 2)
    y1 = max(0, center_y - crop_h // 2)
    x2 = min(w, x1 + crop_w)
    y2 = min(h, y1 + crop_h)

    return image[y1:y2, x1:x2]


class GeometryFilter(ImageFilter):
    """
    Applies non-destructive spatial transformations:
    - Discrete rotation (0, 90, 180, 270 degrees)
    - Mirror flips (horizontal, vertical)
    - Fine angle rotation (-45 to +45 degrees) with strict auto-crop
    - Normalized interactive crop rect (x, y, width, height) in [0.0, 1.0]
    """

    def __init__(
        self,
        discrete_rotation: int = 0,
        flip_h: bool = False,
        flip_v: bool = False,
        angle_deg: float = 0.0,
        crop_rect: Optional[Tuple[float, float, float, float]] = None,
    ):
        self.discrete_rotation = discrete_rotation % 360
        self.flip_h = flip_h
        self.flip_v = flip_v
        self.angle_deg = angle_deg
        self.crop_rect = crop_rect

    def apply(self, image: np.ndarray) -> np.ndarray:
        if image is None or image.size == 0:
            raise ValueError("Invalid image buffer passed to GeometryFilter.")

        result = image

        # 1. Discrete 90-degree rotations
        if self.discrete_rotation == 90:
            result = cv2.rotate(result, cv2.ROTATE_90_CLOCKWISE)
        elif self.discrete_rotation == 180:
            result = cv2.rotate(result, cv2.ROTATE_180)
        elif self.discrete_rotation == 270:
            result = cv2.rotate(result, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # 2. Flips
        if self.flip_h and self.flip_v:
            result = cv2.flip(result, -1)
        elif self.flip_h:
            result = cv2.flip(result, 1)
        elif self.flip_v:
            result = cv2.flip(result, 0)

        # 3. Fine-angle rotation with guaranteed tight inner crop
        if abs(self.angle_deg) > 0.01:
            h, w = result.shape[:2]
            center = (w / 2.0, h / 2.0)
            rot_mat = cv2.getRotationMatrix2D(center, self.angle_deg, 1.0)
            rotated = cv2.warpAffine(
                result,
                rot_mat,
                (w, h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0)
            )
            result = _crop_largest_inner_rect(rotated, self.angle_deg)

        # 4. Interactive crop rect (normalized coordinates: x, y, w, h)
        if self.crop_rect is not None:
            cx, cy, cw, ch = self.crop_rect
            img_h, img_w = result.shape[:2]

            x1 = max(0, min(img_w - 1, int(round(cx * img_w))))
            y1 = max(0, min(img_h - 1, int(round(cy * img_h))))
            x2 = max(x1 + 1, min(img_w, int(round((cx + cw) * img_w))))
            y2 = max(y1 + 1, min(img_h, int(round((cy + ch) * img_h))))

            if (x2 - x1) > 2 and (y2 - y1) > 2:
                result = result[y1:y2, x1:x2]

        return np.ascontiguousarray(result)


class GeometryFilter(ImageFilter):
    """
    Applies non-destructive spatial transformations:
    - Discrete rotation (0, 90, 180, 270 degrees)
    - Mirror flips (horizontal, vertical)
    - Fine angle rotation (-45 to +45 degrees) with auto-crop (no black borders)
    - Normalized interactive crop rect (x, y, width, height) in [0.0, 1.0]
    """

    def __init__(
        self,
        discrete_rotation: int = 0,
        flip_h: bool = False,
        flip_v: bool = False,
        angle_deg: float = 0.0,
        crop_rect: Optional[Tuple[float, float, float, float]] = None,
    ):
        self.discrete_rotation = discrete_rotation % 360
        self.flip_h = flip_h
        self.flip_v = flip_v
        self.angle_deg = angle_deg
        self.crop_rect = crop_rect

    def apply(self, image: np.ndarray) -> np.ndarray:
        if image is None or image.size == 0:
            raise ValueError("Invalid image buffer passed to GeometryFilter.")

        result = image

        # 1. Discrete 90-degree rotations
        if self.discrete_rotation == 90:
            result = cv2.rotate(result, cv2.ROTATE_90_CLOCKWISE)
        elif self.discrete_rotation == 180:
            result = cv2.rotate(result, cv2.ROTATE_180)
        elif self.discrete_rotation == 270:
            result = cv2.rotate(result, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # 2. Flips
        if self.flip_h and self.flip_v:
            result = cv2.flip(result, -1)
        elif self.flip_h:
            result = cv2.flip(result, 1)
        elif self.flip_v:
            result = cv2.flip(result, 0)

        # 3. Fine-angle rotation with automatic inner crop (no black borders)
        if abs(self.angle_deg) > 0.01:
            h, w = result.shape[:2]
            center = (w / 2.0, h / 2.0)
            rot_mat = cv2.getRotationMatrix2D(center, self.angle_deg, 1.0)
            rotated = cv2.warpAffine(
                result,
                rot_mat,
                (w, h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0)
            )
            result = _crop_largest_inner_rect(rotated, self.angle_deg)

        # 4. Interactive crop rect (normalized coordinates: x, y, w, h)
        if self.crop_rect is not None:
            cx, cy, cw, ch = self.crop_rect
            img_h, img_w = result.shape[:2]

            x1 = max(0, min(img_w - 1, int(round(cx * img_w))))
            y1 = max(0, min(img_h - 1, int(round(cy * img_h))))
            x2 = max(x1 + 1, min(img_w, int(round((cx + cw) * img_w))))
            y2 = max(y1 + 1, min(img_h, int(round((cy + ch) * img_h))))

            if (x2 - x1) > 2 and (y2 - y1) > 2:
                result = result[y1:y2, x1:x2]

        return np.ascontiguousarray(result)