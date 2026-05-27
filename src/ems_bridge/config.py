"""Configuration loading from YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "params.yaml"
DATA_DIR = PROJECT_ROOT / "data"
VENDOR_DATA_DIR = DATA_DIR / "vendor"
PARTIAL_DATA_DIR = DATA_DIR / "partial"
COMPLETED_DATA_DIR = DATA_DIR / "completed"


def load_yaml(path: Path | str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_config(path: Path | str | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.is_absolute():
        candidate = PROJECT_ROOT / config_path
        if candidate.exists():
            config_path = candidate
    raw = load_yaml(config_path)
    return normalize_config(raw)


def resolve_path(path: Path | str, base: Path | None = None) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    root = base or PROJECT_ROOT
    return (root / p).resolve()


def normalize_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Accept both legacy ems_default.yaml and unified params.yaml layouts."""
    if "preprocess" in raw and "ems_single" in raw and "ems_hierarchical" in raw:
        return raw

    # Unified params.yaml style
    preprocessing = raw.get("preprocessing", {})
    ems = raw.get("ems", {})
    output = raw.get("output", {})
    input_cfg = raw.get("input", {})

    normalized = {
        "input": {
            "partial_filename": input_cfg.get("partial_filename", "partial.ply"),
            "completed_filename": input_cfg.get("completed_filename", "completed.ply"),
        },
        "preprocess": {
            "voxel_size": preprocessing.get("voxel_size"),
            "target_points": preprocessing.get("target_n_points", 1500),
            "target_points_multi": preprocessing.get("target_n_points_multi", 5000),
            "statistical_outlier": {
                "enabled": bool(preprocessing.get("sor_enabled", True)),
                "nb_neighbors": int(preprocessing.get("sor_nb_neighbors", 20)),
                "std_ratio": float(preprocessing.get("sor_std_ratio", 2.0)),
            },
        },
        "ems_single": {
            "outlier_ratio": float(ems.get("single_outlier_ratio", 0.2)),
            "max_iteration_em": int(ems.get("single_max_iteration_em", 20)),
            "tolerance_em": float(ems.get("single_tolerance_em", 1.0e-3)),
            "relative_tolerance_em": float(ems.get("single_relative_tolerance_em", 0.1)),
            "max_opti_iterations": int(ems.get("single_max_opti_iterations", 3)),
            "sigma": float(ems.get("single_sigma", 0.0)),
            "max_switch": int(ems.get("single_max_switch", 2)),
            "adaptive_upper_bound": bool(ems.get("single_adaptive_upper_bound", False)),
            "rescale": bool(ems.get("single_rescale", True)),
        },
        "ems_hierarchical": {
            "max_layer": int(ems.get("MaxLayer", 5)),
            "min_points": int(ems.get("MinPoints", 60)),
            "eps_scale": float(ems.get("eps_scale", 0.17)),
            "outlier_ratio": float(ems.get("OutlierRatio", 0.9)),
            "max_iteration_em": int(ems.get("MaxIterationEM", 20)),
            "tolerance_em": float(ems.get("ToleranceEM", 1.0e-3)),
            "relative_tolerance_em": float(ems.get("RelativeToleranceEM", 0.2)),
            "max_opti_iterations": int(ems.get("MaxOptiIterations", 2)),
            "sigma": float(ems.get("Sigma", 0.3)),
            "max_switch": int(ems.get("MaxiSwitch", 2)),
            "adaptive_upper_bound": bool(ems.get("AdaptiveUpperBound", True)),
            "rescale": bool(ems.get("Rescale", False)),
            "inlier_threshold": float(ems.get("inlier_threshold", 0.1)),
            "outlier_cluster_threshold": float(ems.get("outlier_cluster_threshold", 0.8)),
        },
        "metrics": {
            "surface_sample_arclength": float(output.get("surface_sample_arclength", 0.02)),
            "surface_sample_interval": float(output.get("surface_sample_interval", 0.1)),
        },
        "downstream": {
            "grasp_width_ratio": float(output.get("grasp_width_ratio", 0.6)),
            "planning_clearance_margin": float(output.get("planning_clearance_margin", 0.01)),
        },
        "output": {
            "results_dir": output.get("results_dir", "results"),
            "save_visual_ply": bool(output.get("save_visual_ply", False)),
            "sq_surface_n_points": int(output.get("sq_surface_n_points", 500)),
        },
    }
    return normalized
