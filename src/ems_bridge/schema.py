"""Dataclasses for superquadric fit results and JSON schema."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SuperquadricParams:
    epsilon1: float
    epsilon2: float
    scale: list[float]
    euler_zyx: list[float]
    translation: list[float]
    inlier_fraction: float
    hierarchy_level: int = 0
    part_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FitMetrics:
    mean_point_to_surface: float
    chamfer: float
    num_points: int = 0
    num_superquadrics: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DownstreamMetrics:
    grasp_candidate_width: float | None = None
    grasp_feasible: bool | None = None
    planning_proxy_clearance: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FitResult:
    source_cloud: str
    fit_mode: str
    fit_time_ms: float
    superquadrics: list[SuperquadricParams] = field(default_factory=list)
    metrics: FitMetrics | None = None
    downstream: DownstreamMetrics | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_cloud": self.source_cloud,
            "fit_mode": self.fit_mode,
            "fit_time_ms": self.fit_time_ms,
            "superquadrics": [sq.to_dict() for sq in self.superquadrics],
        }
        if self.metrics is not None:
            payload["metrics"] = self.metrics.to_dict()
        if self.downstream is not None:
            payload["downstream"] = self.downstream.to_dict()
        return payload
