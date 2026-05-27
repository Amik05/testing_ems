#!/usr/bin/env python3
"""Visualize point cloud and fitted superquadric surfaces (matplotlib)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ems_bridge.config import resolve_path
from ems_bridge.io import load_fit_result, load_point_cloud
from ems_bridge.surface_sampling import sample_superquadric_surface


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Visualize EMS fit result.")
    parser.add_argument("cloud", type=Path, help="Input point cloud (.ply/.npy/.npz).")
    parser.add_argument("result", type=Path, help="Fit result JSON.")
    parser.add_argument("-o", "--output", type=Path, help="Optional PNG output path.")
    parser.add_argument(
        "--hide-cloud",
        action="store_true",
        help="Render only fitted superquadrics (no input points).",
    )
    parser.add_argument(
        "--surface-points",
        type=int,
        default=8000,
        help="Fibonacci sphere count for surface sampling (higher = smoother).",
    )
    args = parser.parse_args(argv)

    points = load_point_cloud(resolve_path(args.cloud))
    result = load_fit_result(resolve_path(args.result))

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    if not args.hide_cloud:
        ax.scatter(points[:, 0], points[:, 1], points[:, 2], s=1, c="red", alpha=0.5, label="cloud")

    all_surface = []
    for idx, sq in enumerate(result.get("superquadrics", [])):
        surface = sample_superquadric_surface(
            epsilon1=sq["epsilon1"],
            epsilon2=sq["epsilon2"],
            scale=np.array(sq["scale"]),
            euler_zyx=np.array(sq["euler_zyx"]),
            translation=np.array(sq["translation"]),
            arclength=0.03,
            fibonacci_points=args.surface_points,
        )
        all_surface.append(surface)
        ax.scatter(
            surface[:, 0],
            surface[:, 1],
            surface[:, 2],
            s=1,
            alpha=0.25,
            label=f"sq_{idx}",
        )

    # Matplotlib 3D default aspect is not 1:1:1 — force equal limits from combined bbox.
    if len(points) > 0 or all_surface:
        if all_surface:
            surf = np.vstack(all_surface)
            mins = surf.min(axis=0)
            maxs = surf.max(axis=0)
            if len(points) > 0:
                mins = np.minimum(mins, points.min(axis=0))
                maxs = np.maximum(maxs, points.max(axis=0))
        else:
            mins = points.min(axis=0)
            maxs = points.max(axis=0)
        center = 0.5 * (mins + maxs)
        span = float(np.max(maxs - mins)) * 0.55 + 1e-6
        ax.set_xlim(center[0] - span, center[0] + span)
        ax.set_ylim(center[1] - span, center[1] + span)
        ax.set_zlim(center[2] - span, center[2] + span)

    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title(result.get("source_cloud", "EMS fit"))

    if args.output:
        out = resolve_path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        print(f"Wrote {out}")
    else:
        plt.show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
