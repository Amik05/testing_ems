# Shape Completion Integration Contract

This document defines how the masters student connects a shape completion method to the EMS pipeline.

## Input layout

| Folder | Purpose |
|--------|---------|
| `data/vendor/single/` | EMS demo clouds (partial/noisy examples) |
| `data/vendor/multi/` | EMS demo clouds (cat, dog, turtle) |
| `data/partial/` | Your partial-view clouds (before completion) |
| `data/completed/` | Your shape-completion outputs |

See [`data/README.md`](../data/README.md) for details.

## Input formats

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

## Manifest (optional)

If you don’t want to use folder convention (`data/<object_id>/partial.ply` and `completed.ply`), create your own manifest YAML and pass it to `run.py --manifest <path>`.

Example `manifest.yaml`:

```yaml
objects:
  - id: mug_01
    partial: data/partial/mug_01.ply
    completed: data/completed/mug_01.ply
    fit_mode: single   # or hierarchical
```

Primary single-entry command:

```bash
python run.py --partial data/partial/mug_01.ply --completed data/completed/mug_01.ply --mode single
```

Primary batch command (manifest mode):

```bash
python run.py --batch data --manifest path/to/manifest.yaml
```

You can also use folder convention without a manifest:

```text
data/
├── mug_01/
│   ├── partial.ply
│   └── completed.ply
├── mug_02/
│   ├── partial.ply
│   └── completed.ply
```

then run:

```bash
python run.py --batch data
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
python run.py --partial data/partial/mug_01.ply --completed data/completed/mug_01.ply --mode single
python run.py --batch data
```

Ablation outputs:

- `results/batch/<object_id>/partial.json`
- `results/batch/<object_id>/completed.json`
- `results/batch/<object_id>/results.json`
- `results/batch/summary.csv`

## Thesis workflow

1. Student generates `data/completed/*.ply` from their completion method.
2. Either:
   - use per-object folder convention and run `python run.py --batch data`, or
   - create your own manifest YAML and pass it via `--manifest`.
3. Compare `delta_fit_error`, `delta_chamfer`, and `delta_coverage` from each object's `results.json`.
4. Use `results/batch/summary.csv` for aggregate reporting.
5. Run full robot grasp/planning evaluation using exported superquadric parameters.

## Notes

- Do not duplicate EMS internal preprocessing (centering/rescale) — configure via `config/params.yaml`.
- Use `fit_mode: hierarchical` for multi-part objects (bottles, animals); `single` for simple primitives.
- If completion outputs a mesh, sample the surface to a point cloud before fitting.
