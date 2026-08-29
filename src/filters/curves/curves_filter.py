from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from src.filters.base import ImageFilter
from src.utils import interpolate_curve_points


class CurvesFilter(ImageFilter):
    """Applies RGB and per-channel curve transformations using precomputed LUTs."""

    def __init__(
        self, 
        channel_points: Optional[Dict[str, List[Tuple[float, float]]]] = None,
        mode: str = "smooth"
    ):
        default_pts = [(0.0, 0.0), (1.0, 1.0)]
        self.points = {
            "RGB": channel_points.get("RGB", default_pts) if channel_points else default_pts,
            "R": channel_points.get("R", default_pts) if channel_points else default_pts,
            "G": channel_points.get("G", default_pts) if channel_points else default_pts,
            "B": channel_points.get("B", default_pts) if channel_points else default_pts,
        }
        self.mode = mode

    def apply(self, image: np.ndarray) -> np.ndarray:
        if image is None or image.size == 0:
            raise ValueError("Invalid image buffer provided to CurvesFilter.")

        is_default = all(
            len(pts) == 2 and pts[0] == (0.0, 0.0) and pts[1] == (1.0, 1.0)
            for pts in self.points.values()
        )
        if is_default:
            return image

        lut_rgb = interpolate_curve_points(self.points["RGB"], num_samples=256, mode=self.mode)
        lut_r = interpolate_curve_points(self.points["R"], num_samples=256, mode=self.mode)
        lut_g = interpolate_curve_points(self.points["G"], num_samples=256, mode=self.mode)
        lut_b = interpolate_curve_points(self.points["B"], num_samples=256, mode=self.mode)

        final_lut_r = lut_r[lut_rgb]
        final_lut_g = lut_g[lut_rgb]
        final_lut_b = lut_b[lut_rgb]

        merged_lut = np.dstack((final_lut_r, final_lut_g, final_lut_b))
        return cv2.LUT(image, merged_lut)