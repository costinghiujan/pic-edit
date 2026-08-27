from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from src.filters.base import ImageFilter


class CurvesFilter(ImageFilter):
    """
    Applies RGB and individual channel (R, G, B) curve transformations using LUTs.
    """

    def __init__(self, channel_points: Optional[Dict[str, List[Tuple[float, float]]]] = None):
        """
        :param channel_points: Dict with keys 'RGB', 'R', 'G', 'B'.
                               Each containing sorted list of (x, y) points in [0.0, 1.0].
        """
        default_pts = [(0.0, 0.0), (1.0, 1.0)]
        self.points = {
            "RGB": channel_points.get("RGB", default_pts) if channel_points else default_pts,
            "R": channel_points.get("R", default_pts) if channel_points else default_pts,
            "G": channel_points.get("G", default_pts) if channel_points else default_pts,
            "B": channel_points.get("B", default_pts) if channel_points else default_pts,
        }

    @staticmethod
    def _interpolate_curve(points: List[Tuple[float, float]]) -> np.ndarray:
        """Interpolates control points into a 256-element uint8 LUT."""
        if not points:
            return np.arange(256, dtype=np.uint8)

        # Sort points by x coordinate
        sorted_pts = sorted(points, key=lambda p: p[0])
        x_pts = np.array([p[0] * 255.0 for p in sorted_pts], dtype=np.float32)
        y_pts = np.array([p[1] * 255.0 for p in sorted_pts], dtype=np.float32)

        # Ensure bounds
        if x_pts[0] > 0:
            x_pts = np.insert(x_pts, 0, 0.0)
            y_pts = np.insert(y_pts, 0, y_pts[0])
        if x_pts[-1] < 255:
            x_pts = np.append(x_pts, 255.0)
            y_pts = np.append(y_pts, y_pts[-1])

        x_vals = np.arange(256, dtype=np.float32)
        # Piecewise linear with smooth clipping as efficient curve approximation
        y_vals = np.interp(x_vals, x_pts, y_pts)
        return np.clip(y_vals, 0.0, 255.0).astype(np.uint8)

    def apply(self, image: np.ndarray) -> np.ndarray:
        if image is None or image.size == 0:
            raise ValueError("Invalid image buffer provided to CurvesFilter.")

        # If all curves are default diagonal [(0,0), (1,1)], return unmodified
        is_default = all(len(pts) == 2 and pts[0] == (0.0, 0.0) and pts[1] == (1.0, 1.0) for pts in self.points.values())
        if is_default:
            return image

        # 1. Build LUTs for each channel
        lut_rgb = self._interpolate_curve(self.points["RGB"])
        lut_r = self._interpolate_curve(self.points["R"])
        lut_g = self._interpolate_curve(self.points["G"])
        lut_b = self._interpolate_curve(self.points["B"])

        # Combine RGB master LUT with individual channels: Channel_LUT = LUT_channel(LUT_RGB)
        final_lut_r = lut_r[lut_rgb]
        final_lut_g = lut_g[lut_rgb]
        final_lut_b = lut_b[lut_rgb]

        # Merge into a single 3-channel LUT for cv2.LUT
        # Input image is RGB
        merged_lut = np.dstack((final_lut_r, final_lut_g, final_lut_b))
        return cv2.LUT(image, merged_lut)