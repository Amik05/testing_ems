"""EMS fitting wrappers: single and hierarchical modes."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from sklearn.cluster import DBSCAN

from EMS.EMS_recovery import EMS_recovery

from ems_bridge.preprocess import bbox_diagonal, preprocess_point_cloud
from ems_bridge.schema import FitResult, SuperquadricParams


def fit_point_cloud(
    points: np.ndarray,
    config: dict[str, Any],
    fit_mode: str = "single",
    source_cloud: str = "",
) -> FitResult:
    hierarchical = fit_mode == "hierarchical"
    processed = preprocess_point_cloud(points, config, hierarchical=hierarchical)

    start = time.perf_counter()
    if hierarchical:
        superquadrics = _fit_hierarchical(processed, config)
    else:
        superquadrics = [_fit_single(processed, config)]
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    return FitResult(
        source_cloud=source_cloud,
        fit_mode=fit_mode,
        fit_time_ms=elapsed_ms,
        superquadrics=superquadrics,
    )


def _fit_single(points: np.ndarray, config: dict[str, Any]) -> SuperquadricParams:
    cfg = config["ems_single"]
    sq, posteriors = EMS_recovery(
        points,
        OutlierRatio=float(cfg["outlier_ratio"]),
        MaxIterationEM=int(cfg["max_iteration_em"]),
        ToleranceEM=float(cfg["tolerance_em"]),
        RelativeToleranceEM=float(cfg["relative_tolerance_em"]),
        MaxOptiIterations=int(cfg["max_opti_iterations"]),
        Sigma=float(cfg["sigma"]),
        MaxiSwitch=int(cfg["max_switch"]),
        AdaptiveUpperBound=bool(cfg["adaptive_upper_bound"]),
        Rescale=bool(cfg["rescale"]),
    )
    return _sq_to_params(sq, posteriors, hierarchy_level=0, part_index=0)


def _fit_hierarchical(points: np.ndarray, config: dict[str, Any]) -> list[SuperquadricParams]:
    cfg = config["ems_hierarchical"]
    max_layer = int(cfg["max_layer"])
    min_points = int(cfg["min_points"])
    eps = float(cfg["eps_scale"]) * bbox_diagonal(points)
    inlier_threshold = float(cfg["inlier_threshold"])
    cluster_threshold = float(cfg["outlier_cluster_threshold"])

    point_seg: dict[int, list[np.ndarray]] = {0: [points]}
    results: list[SuperquadricParams] = []
    part_counter = 0

    for level in range(max_layer):
        if level not in point_seg or not point_seg[level]:
            break
        next_level: list[np.ndarray] = []

        for cluster in point_seg[level]:
            sq, posteriors = EMS_recovery(
                cluster,
                OutlierRatio=float(cfg["outlier_ratio"]),
                MaxIterationEM=int(cfg["max_iteration_em"]),
                ToleranceEM=float(cfg["tolerance_em"]),
                RelativeToleranceEM=float(cfg["relative_tolerance_em"]),
                MaxOptiIterations=int(cfg["max_opti_iterations"]),
                Sigma=float(cfg["sigma"]),
                MaxiSwitch=int(cfg["max_switch"]),
                AdaptiveUpperBound=bool(cfg["adaptive_upper_bound"]),
                Rescale=bool(cfg["rescale"]),
            )
            results.append(
                _sq_to_params(
                    sq,
                    posteriors,
                    hierarchy_level=level,
                    part_index=part_counter,
                )
            )
            part_counter += 1

            outliers = cluster[posteriors < inlier_threshold]
            if posteriors.sum() < cluster_threshold * len(cluster):
                if len(outliers) >= min_points:
                    labels = DBSCAN(eps=eps, min_samples=min_points).fit(outliers).labels_
                    for label in sorted(set(labels) - {-1}):
                        part = outliers[labels == label]
                        if len(part) >= min_points:
                            next_level.append(part)
            elif len(outliers) > 0:
                pass

        if next_level:
            point_seg[level + 1] = next_level

    return results


def _sq_to_params(
    sq: Any,
    posteriors: np.ndarray,
    hierarchy_level: int,
    part_index: int,
) -> SuperquadricParams:
    inlier_fraction = float(np.mean(posteriors > 0.5)) if len(posteriors) else 0.0
    return SuperquadricParams(
        epsilon1=float(sq.shape[0]),
        epsilon2=float(sq.shape[1]),
        scale=[float(v) for v in sq.scale],
        euler_zyx=[float(v) for v in sq.euler],
        translation=[float(v) for v in sq.translation],
        inlier_fraction=inlier_fraction,
        hierarchy_level=hierarchy_level,
        part_index=part_index,
    )
