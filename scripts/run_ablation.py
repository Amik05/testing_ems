#!/usr/bin/env python3
"""Batch ablation: compare partial vs completed point clouds."""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ems_bridge.config import DEFAULT_CONFIG_PATH, load_config, load_yaml, resolve_path
from ems_bridge.downstream import compute_downstream_metrics
from ems_bridge.fit import fit_point_cloud
from ems_bridge.io import load_point_cloud, save_fit_result
from ems_bridge.metrics import compute_fit_metrics


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run partial vs completed EMS ablation.")
    parser.add_argument(
        "--experiment",
        type=Path,
        default=PROJECT_ROOT / "config" / "experiment.yaml",
        help="Experiment manifest YAML.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="EMS config YAML.",
    )
    args = parser.parse_args(argv)

    experiment = load_yaml(resolve_path(args.experiment))
    config = load_config(args.config)
    output_dir = resolve_path(experiment.get("output_dir", "results/ablation"))
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []

    for obj in experiment.get("objects", []):
        obj_id = obj["id"]
        fit_mode = obj.get("fit_mode", "single")
        obj_dir = output_dir / obj_id
        obj_dir.mkdir(parents=True, exist_ok=True)

        for condition, key in (("partial", "partial"), ("completed", "completed")):
            cloud_path = resolve_path(obj[key])
            if not cloud_path.exists():
                print(f"SKIP {obj_id}/{condition}: missing {cloud_path}")
                continue

            points = load_point_cloud(cloud_path)
            result = fit_point_cloud(points, config, fit_mode=fit_mode, source_cloud=str(cloud_path))
            result.metrics = compute_fit_metrics(points, result.superquadrics, config)
            result.downstream = compute_downstream_metrics(result.superquadrics, config)

            json_path = obj_dir / f"{condition}.json"
            save_fit_result(result, json_path)

            row = {
                "object_id": obj_id,
                "condition": condition,
                "fit_mode": fit_mode,
                "num_points": result.metrics.num_points if result.metrics else 0,
                "num_superquadrics": len(result.superquadrics),
                "chamfer": result.metrics.chamfer if result.metrics else "",
                "mean_point_to_surface": result.metrics.mean_point_to_surface if result.metrics else "",
                "fit_time_ms": f"{result.fit_time_ms:.2f}",
                "grasp_candidate_width": result.downstream.grasp_candidate_width if result.downstream else "",
                "grasp_feasible": result.downstream.grasp_feasible if result.downstream else "",
                "planning_proxy_clearance": result.downstream.planning_proxy_clearance if result.downstream else "",
                "result_json": str(json_path),
            }
            rows.append(row)
            print(
                f"{obj_id}/{condition}: chamfer={row['chamfer']:.6f} "
                f"parts={row['num_superquadrics']} time={row['fit_time_ms']}ms"
            )

    summary_path = output_dir / "ablation_summary.csv"
    if rows:
        with open(summary_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    report_path = output_dir / "report.md"
    _write_report(report_path, rows, output_dir)
    print(f"\nWrote {summary_path}")
    print(f"Wrote {report_path}")
    return 0


def _write_report(path: Path, rows: list[dict], output_dir: Path) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# EMS Ablation Report",
        "",
        f"Generated: {timestamp}",
        "",
        "## Summary",
        "",
        "| object | condition | chamfer | point-to-surface | parts | grasp feasible |",
        "|--------|-----------|---------|------------------|-------|----------------|",
    ]
    for row in rows:
        chamfer = row["chamfer"]
        pts = row["mean_point_to_surface"]
        lines.append(
            f"| {row['object_id']} | {row['condition']} | "
            f"{chamfer:.6f} | {pts:.6f} | {row['num_superquadrics']} | {row['grasp_feasible']} |"
        )

    lines.extend(
        [
            "",
            "## Partial vs completed delta",
            "",
        ]
    )

    by_object: dict[str, dict[str, dict]] = {}
    for row in rows:
        by_object.setdefault(row["object_id"], {})[row["condition"]] = row

    for obj_id, conditions in by_object.items():
        if "partial" not in conditions or "completed" not in conditions:
            continue
        partial = conditions["partial"]
        completed = conditions["completed"]
        delta_chamfer = float(completed["chamfer"]) - float(partial["chamfer"])
        lines.append(
            f"- **{obj_id}**: delta chamfer (completed - partial) = {delta_chamfer:+.6f}"
        )

    lines.extend(
        [
            "",
            "## Notes for thesis",
            "",
            "- Lower chamfer and point-to-surface error indicate better geometric fit.",
            "- Compare grasp/planning proxy columns once shape completion outputs are available.",
            f"- Full JSON results are under `{output_dir}`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
