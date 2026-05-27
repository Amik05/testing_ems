#!/usr/bin/env python3
"""Single entry point for EMS comparison pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ems_bridge.config import DEFAULT_CONFIG_PATH, load_config, load_yaml, resolve_path
from ems_bridge.pipeline import discover_batch_pairs, run_batch, run_comparison


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EMS superquadric comparison pipeline")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--batch", type=Path, help="Batch root folder (data/<object>/partial.ply + completed.ply).")
    mode.add_argument("--partial", type=Path, help="Path to partial point cloud for single-object run.")
    parser.add_argument("--completed", type=Path, help="Path to completed point cloud for single-object run.")
    parser.add_argument("--object-id", type=str, help="Optional object id for single-object run.")
    parser.add_argument("--manifest", type=Path, help="Optional experiment manifest (fallback or explicit batch mode).")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to config YAML.")
    parser.add_argument("--mode", choices=("single", "hierarchical"), help="Override fit mode.")
    parser.add_argument("--output", type=Path, help="Output directory override.")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    output_cfg = config.get("output", {})
    output_dir = resolve_path(args.output or output_cfg.get("results_dir", "results"))
    save_visual = bool(output_cfg.get("save_visual_ply", False))
    surface_points = int(output_cfg.get("sq_surface_n_points", 500))

    if args.partial:
        if args.completed is None:
            raise SystemExit("--completed is required when using --partial.")
        fit_mode = args.mode or "single"
        partial_path = resolve_path(args.partial)
        completed_path = resolve_path(args.completed)
        object_id = args.object_id or partial_path.stem
        obj_output = output_dir / object_id
        result = run_comparison(
            object_id=object_id,
            partial_path=partial_path,
            completed_path=completed_path,
            config=config,
            fit_mode=fit_mode,
            output_dir=obj_output,
            save_visual_ply=save_visual,
            sq_surface_n_points=surface_points,
        )
        print(f"Wrote {obj_output / 'results.json'}")
        print(
            f"{object_id}: delta_fit_error={result.delta_fit_error:+.6f} "
            f"delta_chamfer={result.delta_chamfer:+.6f} "
            f"delta_coverage={result.delta_coverage:+.6f}"
        )
        return 0

    # Batch mode
    assert args.batch is not None
    batch_root = resolve_path(args.batch)
    objects: list[dict[str, str]]
    if args.manifest:
        manifest = load_yaml(resolve_path(args.manifest))
        objects = manifest.get("objects", [])
    else:
        input_cfg = config.get("input", {})
        objects = discover_batch_pairs(
            batch_root,
            partial_filename=input_cfg.get("partial_filename", "partial.ply"),
            completed_filename=input_cfg.get("completed_filename", "completed.ply"),
        )

    if not objects:
        print("No object pairs discovered. Provide --manifest or check --batch folder convention.")
        return 1

    batch_output = output_dir / "batch"
    comparisons = run_batch(
        objects=objects,
        config=config,
        output_dir=batch_output,
        fit_mode=args.mode,
        save_visual_ply=save_visual,
        sq_surface_n_points=surface_points,
    )
    print(f"Wrote {batch_output / 'summary.csv'}")
    print(f"Processed {len(comparisons)} objects.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
