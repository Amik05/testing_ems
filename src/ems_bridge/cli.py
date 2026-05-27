#!/usr/bin/env python3
"""CLI entry points for fit and ablation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ems_bridge.config import DEFAULT_CONFIG_PATH, PROJECT_ROOT, load_config, resolve_path
from ems_bridge.downstream import compute_downstream_metrics
from ems_bridge.fit import fit_point_cloud
from ems_bridge.io import load_point_cloud, save_fit_result
from ems_bridge.metrics import compute_fit_metrics


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to EMS YAML config.",
    )


def fit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fit superquadrics to a point cloud file.")
    parser.add_argument("input", type=Path, help="Input .ply, .npy, or .npz point cloud.")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output JSON path.")
    parser.add_argument(
        "--mode",
        choices=("single", "hierarchical"),
        default="single",
        help="Single or hierarchical EMS fit.",
    )
    _add_common_args(parser)
    args = parser.parse_args(argv)

    config = load_config(args.config)
    input_path = resolve_path(args.input)
    points = load_point_cloud(input_path)

    result = fit_point_cloud(
        points,
        config,
        fit_mode=args.mode,
        source_cloud=str(input_path),
    )
    result.metrics = compute_fit_metrics(points, result.superquadrics, config)
    result.downstream = compute_downstream_metrics(result.superquadrics, config)

    output_path = resolve_path(args.output)
    save_fit_result(result, output_path)
    print(f"Wrote {output_path}")
    if result.metrics:
        print(
            f"  chamfer={result.metrics.chamfer:.6f}  "
            f"point_to_surface={result.metrics.mean_point_to_surface:.6f}  "
            f"parts={len(result.superquadrics)}  "
            f"time={result.fit_time_ms:.1f}ms"
        )
    return 0


def ablation_main(argv: list[str] | None = None) -> int:
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "scripts"))
    from run_ablation import main as run_ablation_main

    return run_ablation_main(argv)


if __name__ == "__main__":
    raise SystemExit(fit_main())
