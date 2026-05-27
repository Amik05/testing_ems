"""Fit quality metrics: point-to-surface and Chamfer distance."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.spatial import cKDTree

from ems_bridge.schema import FitMetrics, SuperquadricParams
from ems_bridge.surface_sampling import sample_superquadric_surface


def compute_fit_metrics(
    points: np.ndarray,
    superquadrics: list[SuperquadricParams],
    config: dict[str, Any] | None = None,
) -> FitMetrics:
    cfg = (config or {}).get("metrics", {})
    arclength = float(cfg.get("surface_sample_arclength", 0.02))

    surface_points = []
    for sq in superquadrics:
        surface_points.append(
            sample_superquadric_surface(
                epsilon1=sq.epsilon1,
                epsilon2=sq.epsilon2,
                scale=np.array(sq.scale),
                euler_zyx=np.array(sq.euler_zyx),
                translation=np.array(sq.translation),
                arclength=arclength,
            )
        )
    if not surface_points:
        return FitMetrics(
            mean_point_to_surface=float("inf"),
            chamfer=float("inf"),
            num_points=len(points),
            num_superquadrics=0,
        )

    surface = np.vstack(surface_points)
    cloud_to_surface = _mean_min_distance(points, surface)
    surface_to_cloud = _mean_min_distance(surface, points)

    return FitMetrics(
        mean_point_to_surface=float(cloud_to_surface),
        chamfer=float(0.5 * (cloud_to_surface + surface_to_cloud)),
        num_points=len(points),
        num_superquadrics=len(superquadrics),
    )


def _mean_min_distance(source: np.ndarray, target: np.ndarray) -> float:
    tree = cKDTree(target)
    distances, _ = tree.query(source, k=1)
    return float(np.mean(distances))
