"""Superquadric surface sampling aligned with EMS implicit (paper Eq. 1 / EMS_recovery Distance).

The vendor's mayavi helpers use spherical-product sampling; porting those loops is brittle.
Sampling along rays with Fibonacci lattice + bisection guarantees points satisfy the same
implicit equality (A == 1) that EMS treats as zero distance.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation


def _implicit_A(px: float, py: float, pz: float, e1: float, e2: float, ax: float, ay: float, az: float) -> float:
    """Same inner form as EMS; on-surface satisfies A ≈ 1 (see EMS_recovery Distance construction)."""
    a = (((px / ax) ** 2) ** (1.0 / e2) + ((py / ay) ** 2) ** (1.0 / e2)) ** (e2 / e1) + (
        (pz / az) ** 2
    ) ** (1.0 / e1)
    return float(a)


def _sample_unit_fibonacci(n: int) -> np.ndarray:
    """Fibonacci lattice on sphere, shape (n, 3)."""
    if n <= 0:
        return np.zeros((0, 3))
    indices = np.arange(n, dtype=float)
    phi = np.pi * (3.0 - np.sqrt(5.0))
    y_i = 1.0 - (2.0 * indices + 1.0) / n
    r = np.sqrt(np.clip(1.0 - y_i**2, 0.0, 1.0))
    theta = phi * indices
    xdir = np.cos(theta) * r
    zdir = np.sin(theta) * r
    dirs = np.stack([xdir, y_i, zdir], axis=1)
    norms = np.linalg.norm(dirs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return dirs / norms


def _bisect_radius_along_ray(
    direction: np.ndarray,
    e1: float,
    e2: float,
    scale: np.ndarray,
    *,
    max_iter: int = 48,
) -> np.ndarray | None:
    ax, ay, az = scale[0], scale[1], scale[2]
    d = np.asarray(direction, dtype=float).ravel()
    norm = np.linalg.norm(d)
    if norm < 1e-12:
        return None
    d = d / norm

    t_high = float(2.5 * np.sqrt(3.0 * max(ax, ay, az) ** 2))
    t_low = 0.0

    low_val = _implicit_A(*(t_low * d), e1, e2, ax, ay, az)
    high_val = _implicit_A(*(t_high * d), e1, e2, ax, ay, az)

    # Need bracket so A crosses 1 (convex SQ: inside < 1, outside > 1 along ray).
    if high_val < 1.0:
        scale_up = 2.0
        for _ in range(22):
            t_high *= scale_up
            high_val = _implicit_A(*(t_high * d), e1, e2, ax, ay, az)
            if high_val >= 1.0:
                break
        else:
            return None

    if low_val >= 1.0:
        # Origin should be strictly inside for positive scales — skip degenerate dirs.
        return None

    for _ in range(max_iter):
        t_mid = 0.5 * (t_low + t_high)
        mid_val = _implicit_A(*(t_mid * d), e1, e2, ax, ay, az)
        if mid_val >= 1.0:
            t_high = t_mid
        else:
            t_low = t_mid

    return 0.5 * (t_low + t_high) * d


def sample_superquadric_surface(
    epsilon1: float,
    epsilon2: float,
    scale: np.ndarray,
    euler_zyx: np.ndarray,
    translation: np.ndarray,
    arclength: float = 0.02,
    threshold: float = 1e-2,
    num_limit: int = 10000,
    *,
    fibonacci_points: int | None = None,
) -> np.ndarray:
    """Sample points on the SQ surface (implicit B=1 in EMS body frame).

    Uses a Fibonacci sphere in the body frame and radial bisection to land on B=1.
    Smaller ``arclength`` (legacy param) implies denser sampling unless
    ``fibonacci_points`` is set explicitly.
    """
    del threshold, num_limit  # unused; kept for API compatibility

    e1 = max(float(epsilon1), 0.007)
    e2 = max(float(epsilon2), 0.007)
    scale = np.asarray(scale, dtype=float)
    rotation = Rotation.from_euler("ZYX", euler_zyx).as_matrix()
    translation = np.asarray(translation, dtype=float)

    if fibonacci_points is None:
        # Denser sampling when arclength is small (paper / EMS demos use ~0.02–0.1).
        fibonacci_points = int(np.clip(6000.0 / max(float(arclength), 0.008), 2500, 20000))

    directions = _sample_unit_fibonacci(int(fibonacci_points))
    local_points = []
    for direc in directions:
        p_can = _bisect_radius_along_ray(direc, e1, e2, scale)
        if p_can is not None:
            local_points.append(p_can)

    if not local_points:
        return np.zeros((0, 3))

    local = np.vstack(local_points)
    world = (rotation @ local.T).T + translation
    return world.astype(float)
