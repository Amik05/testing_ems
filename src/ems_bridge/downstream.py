"""Lightweight downstream metric stubs for grasp and planning evaluation."""

from __future__ import annotations

from typing import Any

import numpy as np

from ems_bridge.schema import DownstreamMetrics, SuperquadricParams


def compute_downstream_metrics(
    superquadrics: list[SuperquadricParams],
    config: dict[str, Any] | None = None,
) -> DownstreamMetrics:
    if not superquadrics:
        return DownstreamMetrics()

    cfg = (config or {}).get("downstream", {})
    primary = _largest_superquadric(superquadrics)
    scale = np.array(primary.scale, dtype=float)
    width_ratio = float(cfg.get("grasp_width_ratio", 0.6))
    clearance_margin = float(cfg.get("planning_clearance_margin", 0.01))

    # Antipodal grasp proxy: grip on the two smallest scale axes.
    sorted_scales = np.sort(scale)
    grasp_width = float(2.0 * sorted_scales[0] * width_ratio)
    grasp_feasible = grasp_width > 0.005

    # Planning proxy: minimum semi-axis minus clearance margin.
    planning_clearance = float(sorted_scales[0] - clearance_margin)

    return DownstreamMetrics(
        grasp_candidate_width=grasp_width,
        grasp_feasible=grasp_feasible,
        planning_proxy_clearance=planning_clearance,
    )


def _largest_superquadric(superquadrics: list[SuperquadricParams]) -> SuperquadricParams:
    volumes = [sq.scale[0] * sq.scale[1] * sq.scale[2] for sq in superquadrics]
    return superquadrics[int(np.argmax(volumes))]
