"""Shared orchestration for single-object and batch comparison runs."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

from ems_bridge.config import PROJECT_ROOT, resolve_path
from ems_bridge.downstream import compute_downstream_metrics
from ems_bridge.fit import fit_preprocessed_point_cloud
from ems_bridge.io import load_point_cloud, save_fit_result, save_json, save_overlay_point_cloud
from ems_bridge.metrics import compute_fit_metrics
from ems_bridge.preprocess import preprocess_point_cloud
from ems_bridge.schema import ArmSummary, ComparisonResult, FitResult
from ems_bridge.surface_sampling import sample_superquadric_surface


def run_comparison(
    *,
    object_id: str,
    partial_path: Path,
    completed_path: Path,
    config: dict[str, Any],
    fit_mode: str,
    output_dir: Path,
    save_visual_ply: bool = False,
    sq_surface_n_points: int = 500,
) -> ComparisonResult:
    output_dir.mkdir(parents=True, exist_ok=True)

    partial_result, partial_summary = _run_arm(
        arm_name="partial",
        cloud_path=partial_path,
        config=config,
        fit_mode=fit_mode,
        output_dir=output_dir,
        save_visual_ply=save_visual_ply,
        sq_surface_n_points=sq_surface_n_points,
    )
    completed_result, completed_summary = _run_arm(
        arm_name="completed",
        cloud_path=completed_path,
        config=config,
        fit_mode=fit_mode,
        output_dir=output_dir,
        save_visual_ply=save_visual_ply,
        sq_surface_n_points=sq_surface_n_points,
    )

    _ = partial_result, completed_result  # keep for debugging symmetry
    comparison = ComparisonResult(
        object=object_id,
        partial=partial_summary,
        completed=completed_summary,
        delta_coverage=completed_summary.total_coverage - partial_summary.total_coverage,
        delta_fit_error=completed_summary.mean_fit_error - partial_summary.mean_fit_error,
        delta_chamfer=completed_summary.chamfer - partial_summary.chamfer,
    )
    save_json(comparison.to_dict(), output_dir / "results.json")
    return comparison


def discover_batch_pairs(
    batch_root: Path,
    *,
    partial_filename: str,
    completed_filename: str,
) -> list[dict[str, str]]:
    """Discover pairs in data/<object_id>/{partial.ply,completed.ply} format."""
    pairs: list[dict[str, str]] = []
    for obj_dir in sorted(batch_root.iterdir()):
        if not obj_dir.is_dir():
            continue
        partial = obj_dir / partial_filename
        completed = obj_dir / completed_filename
        if partial.exists() and completed.exists():
            pairs.append(
                {
                    "id": obj_dir.name,
                    "partial": str(partial),
                    "completed": str(completed),
                }
            )
    return pairs


def run_batch(
    *,
    objects: list[dict[str, str]],
    config: dict[str, Any],
    output_dir: Path,
    fit_mode: str | None = None,
    save_visual_ply: bool = False,
    sq_surface_n_points: int = 500,
) -> list[ComparisonResult]:
    results: list[ComparisonResult] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for obj in objects:
        object_id = obj["id"]
        mode = fit_mode or obj.get("fit_mode", "single")
        partial_path = resolve_path(obj["partial"])
        completed_path = resolve_path(obj["completed"])
        obj_dir = output_dir / object_id
        comparison = run_comparison(
            object_id=object_id,
            partial_path=partial_path,
            completed_path=completed_path,
            config=config,
            fit_mode=mode,
            output_dir=obj_dir,
            save_visual_ply=save_visual_ply,
            sq_surface_n_points=sq_surface_n_points,
        )
        results.append(comparison)

    _write_summary_csv(results, output_dir / "summary.csv")
    return results


def _run_arm(
    *,
    arm_name: str,
    cloud_path: Path,
    config: dict[str, Any],
    fit_mode: str,
    output_dir: Path,
    save_visual_ply: bool,
    sq_surface_n_points: int,
) -> tuple[FitResult, ArmSummary]:
    input_points = load_point_cloud(cloud_path)
    processed = preprocess_point_cloud(input_points, config, hierarchical=(fit_mode == "hierarchical"))
    fit_result = fit_preprocessed_point_cloud(
        processed,
        config,
        fit_mode=fit_mode,
        source_cloud=str(cloud_path),
    )
    # Keep metric semantics aligned with existing fit_cloud.py (evaluate against input cloud).
    fit_result.metrics = compute_fit_metrics(input_points, fit_result.superquadrics, config)
    fit_result.downstream = compute_downstream_metrics(fit_result.superquadrics, config)

    arm_json = output_dir / f"{arm_name}.json"
    save_fit_result(fit_result, arm_json)

    if save_visual_ply:
        sq_cloud = _stack_sq_surfaces(fit_result, max(100, sq_surface_n_points))
        save_overlay_point_cloud(
            processed,
            sq_cloud,
            output_dir / f"{arm_name}_visual.ply",
        )

    metrics = fit_result.metrics
    assert metrics is not None
    summary = ArmSummary(
        n_points_input=int(len(input_points)),
        n_points_after_preproc=int(len(processed)),
        n_primitives=int(len(fit_result.superquadrics)),
        total_coverage=float(np.mean([sq.inlier_fraction for sq in fit_result.superquadrics]) if fit_result.superquadrics else 0.0),
        mean_fit_error=float(metrics.mean_point_to_surface),
        chamfer=float(metrics.chamfer),
        elapsed_s=float(fit_result.fit_time_ms / 1000.0),
        result_json=str(arm_json.relative_to(PROJECT_ROOT)),
    )
    return fit_result, summary


def _stack_sq_surfaces(result: FitResult, surface_points: int) -> np.ndarray:
    clouds: list[np.ndarray] = []
    for sq in result.superquadrics:
        clouds.append(
            sample_superquadric_surface(
                epsilon1=sq.epsilon1,
                epsilon2=sq.epsilon2,
                scale=np.array(sq.scale),
                euler_zyx=np.array(sq.euler_zyx),
                translation=np.array(sq.translation),
                fibonacci_points=surface_points,
            )
        )
    if not clouds:
        return np.zeros((0, 3))
    return np.vstack(clouds)


def _write_summary_csv(results: list[ComparisonResult], path: Path) -> None:
    if not results:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for comp in results:
        rows.append(
            {
                "object": comp.object,
                "partial_points": comp.partial.n_points_after_preproc,
                "completed_points": comp.completed.n_points_after_preproc,
                "partial_primitives": comp.partial.n_primitives,
                "completed_primitives": comp.completed.n_primitives,
                "partial_fit_error": comp.partial.mean_fit_error,
                "completed_fit_error": comp.completed.mean_fit_error,
                "partial_chamfer": comp.partial.chamfer,
                "completed_chamfer": comp.completed.chamfer,
                "delta_fit_error": comp.delta_fit_error,
                "delta_chamfer": comp.delta_chamfer,
                "delta_coverage": comp.delta_coverage,
            }
        )

    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
