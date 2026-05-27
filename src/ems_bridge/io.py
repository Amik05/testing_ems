"""Point cloud I/O: PLY, NPY, NPZ, JSON."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import plyfile

from ems_bridge.schema import FitResult


def load_point_cloud(path: Path | str) -> np.ndarray:
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".ply":
        return _load_ply(path)
    if suffix == ".npy":
        points = np.asarray(np.load(path), dtype=float)
        return _ensure_nx3(points)
    if suffix == ".npz":
        data = np.load(path)
        if "points" not in data:
            raise ValueError(f"NPZ file {path} must contain a 'points' array.")
        return _ensure_nx3(np.asarray(data["points"], dtype=float))

    raise ValueError(f"Unsupported point cloud format: {path.suffix}")


def save_point_cloud(points: np.ndarray, path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    points = _ensure_nx3(np.asarray(points, dtype=float))

    if suffix == ".ply":
        _save_ply(points, path)
    elif suffix == ".npy":
        np.save(path, points)
    else:
        raise ValueError(f"Unsupported output format: {path.suffix}")


def save_fit_result(result: FitResult, path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(result.to_dict(), handle, indent=2)
        handle.write("\n")


def load_fit_result(path: Path | str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_json(payload: dict, path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def save_overlay_point_cloud(
    input_cloud: np.ndarray,
    sq_cloud: np.ndarray,
    path: Path | str,
    input_color: tuple[int, int, int] = (220, 20, 60),
    sq_color: tuple[int, int, int] = (30, 144, 255),
) -> None:
    """Save an overlay point cloud as colored PLY."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    input_cloud = np.asarray(input_cloud, dtype=float)
    sq_cloud = np.asarray(sq_cloud, dtype=float)
    all_points = np.vstack([input_cloud, sq_cloud]) if len(sq_cloud) else input_cloud

    colors = np.zeros((len(all_points), 3), dtype=np.uint8)
    colors[: len(input_cloud)] = np.array(input_color, dtype=np.uint8)
    if len(sq_cloud):
        colors[len(input_cloud) :] = np.array(sq_color, dtype=np.uint8)

    vertex = np.empty(
        len(all_points),
        dtype=[("x", "f4"), ("y", "f4"), ("z", "f4"), ("red", "u1"), ("green", "u1"), ("blue", "u1")],
    )
    vertex["x"] = all_points[:, 0]
    vertex["y"] = all_points[:, 1]
    vertex["z"] = all_points[:, 2]
    vertex["red"] = colors[:, 0]
    vertex["green"] = colors[:, 1]
    vertex["blue"] = colors[:, 2]
    plyfile.PlyData([plyfile.PlyElement.describe(vertex, "vertex")]).write(str(path))


def _load_ply(path: Path) -> np.ndarray:
    plydata = plyfile.PlyData.read(str(path))
    vertices = plydata["vertex"].data
    return np.array([[row["x"], row["y"], row["z"]] for row in vertices], dtype=float)


def _save_ply(points: np.ndarray, path: Path) -> None:
    vertex = np.empty(
        len(points),
        dtype=[("x", "f4"), ("y", "f4"), ("z", "f4")],
    )
    vertex["x"] = points[:, 0]
    vertex["y"] = points[:, 1]
    vertex["z"] = points[:, 2]
    plyfile.PlyData([plyfile.PlyElement.describe(vertex, "vertex")]).write(str(path))


def _ensure_nx3(points: np.ndarray) -> np.ndarray:
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"Expected Nx3 point cloud, got shape {points.shape}")
    if len(points) < 11:
        raise ValueError(f"Need at least 11 points for EMS, got {len(points)}")
    return points.astype(float, copy=False)
