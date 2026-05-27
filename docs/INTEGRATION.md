# Shape Completion Integration Contract

This document defines how the masters student connects a shape completion method to the EMS pipeline.

## Input formats

Place point clouds in:

- `data/partial/` — raw or partial-view clouds (before completion)
- `data/completed/` — shape completion outputs

Supported file types:

| Extension | Format |
|-----------|--------|
| `.ply` | ASCII/binary PLY with `x,y,z` vertices |
| `.npy` | `float64` array of shape `(N, 3)` |
| `.npz` | NumPy archive with key `points` shaped `(N, 3)` |

Requirements:

- Object-only cloud (background already removed)
- At least 11 points
- Coordinates in meters (or consistent unit across partial and completed pairs)

## Experiment manifest

Register object pairs in [`config/experiment.yaml`](../config/experiment.yaml):

```yaml
objects:
  - id: mug_01
    partial: data/partial/mug_01.ply
    completed: data/completed/mug_01.ply
    fit_mode: single   # or hierarchical
```

## Output format

Each fit produces `superquadrics.json`:

```json
{
  "source_cloud": "data/completed/mug_01.ply",
  "fit_mode": "single",
  "fit_time_ms": 142.3,
  "superquadrics": [
    {
      "epsilon1": 0.8,
      "epsilon2": 1.2,
      "scale": [0.05, 0.04, 0.12],
      "euler_zyx": [0.1, 0.0, -0.3],
      "translation": [0.01, -0.02, 0.15],
      "inlier_fraction": 0.72,
      "hierarchy_level": 0,
      "part_index": 0
    }
  ],
  "metrics": {
    "mean_point_to_surface": 0.0031,
    "chamfer": 0.0028,
    "num_points": 1500,
    "num_superquadrics": 1
  },
  "downstream": {
    "grasp_candidate_width": 0.048,
    "grasp_feasible": true,
    "planning_proxy_clearance": 0.015
  }
}
```

## Commands

```bash
pixi run fit -- data/completed/mug_01.ply -o results/mug_01.json --mode single
pixi run ablation
```

Ablation outputs:

- `results/ablation/<object_id>/partial.json`
- `results/ablation/<object_id>/completed.json`
- `results/ablation/ablation_summary.csv`
- `results/ablation/report.md`

## Thesis workflow

1. Student generates `data/completed/*.ply` from their completion method.
2. Update `config/experiment.yaml` with object pairs.
3. Run `pixi run ablation`.
4. Compare `chamfer`, `mean_point_to_surface`, and downstream proxy columns in the CSV.
5. Run full robot grasp/planning evaluation using exported superquadric parameters.

## Notes

- Do not duplicate EMS internal preprocessing (centering/rescale) — configure via `config/ems_default.yaml`.
- Use `fit_mode: hierarchical` for multi-part objects (bottles, animals); `single` for simple primitives.
- If completion outputs a mesh, sample the surface to a point cloud before fitting.
