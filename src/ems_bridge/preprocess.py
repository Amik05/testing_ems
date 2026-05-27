"""Point cloud preprocessing before EMS."""

from __future__ import annotations

from typing import Any

import numpy as np


def preprocess_point_cloud(points: np.ndarray, config: dict[str, Any], hierarchical: bool = False) -> np.ndarray:
    cfg = config.get("preprocess", {})
    points = np.asarray(points, dtype=float)

    if cfg.get("statistical_outlier", {}).get("enabled", False):
        points = _statistical_outlier_removal(points, cfg["statistical_outlier"])

    target_key = "target_points_multi" if hierarchical else "target_points"
    target_points = cfg.get(target_key, 1500)
    voxel_size = cfg.get("voxel_size")

    if voxel_size is None and target_points:
        voxel_size = _estimate_voxel_size(points, int(target_points))
    elif voxel_size is None:
        return points

    return voxel_downsample(points, float(voxel_size))


def voxel_downsample(points: np.ndarray, voxel_size: float) -> np.ndarray:
    if voxel_size <= 0:
        return points
    coords = np.floor(points / voxel_size).astype(np.int64)
    _, unique_indices = np.unique(coords, axis=0, return_index=True)
    return points[np.sort(unique_indices)]


def bbox_diagonal(points: np.ndarray) -> float:
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    return float(np.linalg.norm(maxs - mins))


def _estimate_voxel_size(points: np.ndarray, target_points: int) -> float:
    if len(points) <= target_points:
        return 0.0
    volume = np.prod(points.max(axis=0) - points.min(axis=0))
    if volume <= 0:
        return 0.0
    voxel_size = (volume / target_points) ** (1.0 / 3.0)
    return max(voxel_size, 1e-6)


def _statistical_outlier_removal(points: np.ndarray, cfg: dict[str, Any]) -> np.ndarray:
    nb_neighbors = int(cfg.get("nb_neighbors", 20))
    std_ratio = float(cfg.get("std_ratio", 2.0))

    if len(points) <= nb_neighbors + 1:
        return points

    from sklearn.neighbors import NearestNeighbors

    nbrs = NearestNeighbors(n_neighbors=nb_neighbors + 1).fit(points)
    distances, _ = nbrs.kneighbors(points)
    mean_dist = distances[:, 1:].mean(axis=1)
    threshold = mean_dist.mean() + std_ratio * mean_dist.std()
    return points[mean_dist < threshold]
