from typing import List, Tuple
import numpy as np


def clamp(val: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamps a floating point value within [min_val, max_val]."""
    return max(min_val, min(max_val, float(val)))


def interpolate_curve_points(points: List[Tuple[float, float]], num_samples: int = 256) -> np.ndarray:
    """
    Interpolates a list of normalized control points [(x, y), ...] where x, y in [0.0, 1.0]
    into an array of evaluated y-values mapped to the output domain [0, 255].

    :param points: List of (x, y) control points.
    :param num_samples: Output sample count (256 for LUT, 128 for UI drawing).
    :return: 1D NumPy array of interpolated uint8 values.
    """
    if not points:
        return np.linspace(0, 255, num_samples, dtype=np.float32).astype(np.uint8)

    sorted_pts = sorted(points, key=lambda p: p[0])
    x_pts = np.array([p[0] * 255.0 for p in sorted_pts], dtype=np.float32)
    y_pts = np.array([p[1] * 255.0 for p in sorted_pts], dtype=np.float32)

    # Guarantee boundary coverage at 0 and 255
    if x_pts[0] > 0:
        x_pts = np.insert(x_pts, 0, 0.0)
        y_pts = np.insert(y_pts, 0, y_pts[0])
    if x_pts[-1] < 255:
        x_pts = np.append(x_pts, 255.0)
        y_pts = np.append(y_pts, y_pts[-1])

    x_vals = np.linspace(0, 255, num_samples, dtype=np.float32)
    y_vals = np.interp(x_vals, x_pts, y_pts)
    return np.clip(y_vals, 0.0, 255.0).astype(np.uint8)