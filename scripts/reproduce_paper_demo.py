#!/usr/bin/env python3
"""Reproduce EMS on vendor sample PLY files."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ems_bridge.config import DEFAULT_CONFIG_PATH, PROJECT_ROOT as ROOT, load_config, resolve_path
from ems_bridge.downstream import compute_downstream_metrics
from ems_bridge.fit import fit_point_cloud
from ems_bridge.io import load_point_cloud, save_fit_result
from ems_bridge.metrics import compute_fit_metrics

VENDOR_DATA = ROOT / "vendor" / "EMS-superquadric_fitting" / "MATLAB" / "example_scripts" / "data"

SAMPLES = [
    ("single", VENDOR_DATA / "single_superquadric" / "noisy_pointCloud_example_1.ply"),
    ("single", VENDOR_DATA / "single_superquadric" / "partial_pointCloud_example_1.ply"),
    ("hierarchical", VENDOR_DATA / "multi_superquadrics" / "dog.ply"),
]


def main() -> int:
    config = load_config(DEFAULT_CONFIG_PATH)
    output_dir = ROOT / "results" / "reproduce"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("EMS baseline reproduction")
    print("=" * 60)

    for mode, ply_path in SAMPLES:
        if not ply_path.exists():
            print(f"SKIP missing sample: {ply_path}")
            continue

        points = load_point_cloud(ply_path)
        result = fit_point_cloud(points, config, fit_mode=mode, source_cloud=str(ply_path))
        result.metrics = compute_fit_metrics(points, result.superquadrics, config)
        result.downstream = compute_downstream_metrics(result.superquadrics, config)

        out_path = output_dir / f"{ply_path.stem}_{mode}.json"
        save_fit_result(result, out_path)

        assert result.metrics is not None
        print(f"{ply_path.name} [{mode}]")
        print(f"  points={result.metrics.num_points}  parts={result.metrics.num_superquadrics}")
        print(f"  chamfer={result.metrics.chamfer:.6f}")
        print(f"  point_to_surface={result.metrics.mean_point_to_surface:.6f}")
        print(f"  fit_time={result.fit_time_ms:.1f}ms")
        print(f"  -> {out_path}")
        print()

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
