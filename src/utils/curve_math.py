from typing import List, Tuple
import numpy as np


def clamp(val: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamps a floating point value within [min_val, max_val]."""
    return max(min_val, min(max_val, float(val)))


def _monotone_cubic_spline(x_pts: np.ndarray, y_pts: np.ndarray, x_eval: np.ndarray) -> np.ndarray:
    """
    Evaluates a smooth Monotone Cubic Hermite Spline (PCHIP).
    Guarantees C1 continuity without overshoot or oscillations.
    """
    n = len(x_pts)
    if n == 2:
        return np.interp(x_eval, x_pts, y_pts)

    # 1. Calculate secants (slopes of secant lines)
    dx = np.diff(x_pts)
    dy = np.diff(y_pts)
    slopes = dy / dx

    # 2. Calculate tangents at control points
    tangents = np.zeros(n, dtype=np.float32)
    tangents[0] = slopes[0]
    tangents[-1] = slopes[-1]

    for i in range(1, n - 1):
        if slopes[i - 1] * slopes[i] <= 0:
            tangents[i] = 0.0
        else:
            # Weighted harmonic mean (PCHIP tangent)
            w1 = 2 * dx[i] + dx[i - 1]
            w2 = dx[i] + 2 * dx[i - 1]
            tangents[i] = (w1 + w2) / (w1 / slopes[i - 1] + w2 / slopes[i])

    # 3. Evaluate Hermite cubic basis polynomials
    # Find segment index for each x in x_eval
    idx = np.searchsorted(x_pts, x_eval) - 1
    idx = np.clip(idx, 0, n - 2)

    x0 = x_pts[idx]
    x1 = x_pts[idx + 1]
    y0 = y_pts[idx]
    y1 = y_pts[idx + 1]
    m0 = tangents[idx]
    m1 = tangents[idx + 1]

    h = x1 - x0
    t = (x_eval - x0) / h

    # Hermite basis functions
    h00 = 2 * (t ** 3) - 3 * (t ** 2) + 1
    h10 = (t ** 3) - 2 * (t ** 2) + t
    h01 = -2 * (t ** 3) + 3 * (t ** 2)
    h11 = (t ** 3) - (t ** 2)

    return h00 * y0 + h10 * h * m0 + h01 * y1 + h11 * h * m1


def interpolate_curve_points(
    points: List[Tuple[float, float]], 
    num_samples: int = 256, 
    mode: str = "smooth"
) -> np.ndarray:
    """
    Interpolates control points into sampled y-values [0..255].

    :param points: List of (x, y) control points normalized in [0.0, 1.0].
    :param num_samples: Output sample count (256 for LUT, 128 for UI canvas).
    :param mode: 'smooth' (monotone cubic spline) or 'linear' (piecewise linear).
    :return: 1D NumPy array of uint8 values [0..255].
    """
    if not points:
        return np.linspace(0, 255, num_samples, dtype=np.float32).astype(np.uint8)

    sorted_pts = sorted(points, key=lambda p: p[0])
    x_pts = np.array([p[0] * 255.0 for p in sorted_pts], dtype=np.float32)
    y_pts = np.array([p[1] * 255.0 for p in sorted_pts], dtype=np.float32)

    # Ensure endpoints at 0 and 255
    if x_pts[0] > 0:
        x_pts = np.insert(x_pts, 0, 0.0)
        y_pts = np.insert(y_pts, 0, y_pts[0])
    if x_pts[-1] < 255:
        x_pts = np.append(x_pts, 255.0)
        y_pts = np.append(y_pts, y_pts[-1])

    x_eval = np.linspace(0, 255, num_samples, dtype=np.float32)

    if mode == "linear":
        y_eval = np.interp(x_eval, x_pts, y_pts)
    else:
        y_eval = _monotone_cubic_spline(x_pts, y_pts, x_eval)

    return np.clip(y_eval, 0.0, 255.0).astype(np.uint8)