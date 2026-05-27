# EMS Shape Completion Bridge

Reproducible pipeline for [EMS superquadric fitting](https://arxiv.org/abs/2111.14517) (Liu et al., CVPR 2022), designed to compare partial vs shape-completed point clouds before downstream grasp/planning evaluation.

Python + pixi only — no ROS required.

## Quick start

```bash
# Install environment and vendor EMS
pixi install

# Baseline sanity check on vendor sample PLYs
pixi run reproduce

# Single-entry: compare one partial/completed pair
python run.py --partial data/partial/mug_01.ply --completed data/completed/mug_01.ply --mode single

# Batch compare from folder convention
python run.py --batch data

# (Optional) If you use a different folder layout, you can pass your own manifest:
# python run.py --batch data --manifest path/to/manifest.yaml

# Visualize a fit
pixi run visualize -- path/to/cloud.ply results/out.json -o results/viz.png
```

## Project layout

```
config/           params.yaml (primary) + compatibility configs
data/             Point cloud inputs (see data/README.md)
  vendor/         Demo PLYs from EMS paper repo (committed)
  partial/        Student partial-view clouds (gitignored)
  completed/      Student completion outputs (gitignored)
docs/             Integration contract for the student
scripts/          CLI entry points
src/ems_bridge/   Preprocess, fit, metrics, I/O wrappers
vendor/           Official EMS-superquadric_fitting Python package
results/          Generated outputs (gitignored)
```

## Investigation answers

### Preprocessing

EMS internally centers, optionally rescales, and initializes via PCA. This pipeline adds optional voxel downsampling and statistical outlier removal **before** calling EMS. See `config/params.yaml`.

### Point count

Not fixed. Target ~1500 points (single SQ) or ~5000 (multi SQ) via adaptive voxel size.

### Number of superquadrics

Automatic via hierarchical EMS (`fit_mode: hierarchical`). Controlled by `max_layer`, `min_points`, and scale-dependent DBSCAN `eps_scale`.

## Student integration

See [docs/INTEGRATION.md](docs/INTEGRATION.md) for the file-based contract.

## Output schema

Per object, the single-entry pipeline writes:

- `partial.json` and `completed.json` (raw arm-level EMS outputs)
- `results.json` (consolidated comparison with deltas)
- optional `partial_visual.ply` and `completed_visual.ply` (colored overlays)

Example consolidated shape:

```json
{
  "object": "mug_01",
  "partial": {
    "n_points_input": 4821,
    "n_points_after_preproc": 1024,
    "n_primitives": 2,
    "total_coverage": 0.71,
    "mean_fit_error": 0.0043,
    "chamfer": 0.0031,
    "elapsed_s": 1.2,
    "result_json": "results/mug_01/partial.json"
  },
  "completed": {
    "n_points_input": 8302,
    "n_points_after_preproc": 1024,
    "n_primitives": 3,
    "total_coverage": 0.89,
    "mean_fit_error": 0.0021,
    "chamfer": 0.0020,
    "elapsed_s": 1.4,
    "result_json": "results/mug_01/completed.json"
  },
  "delta_coverage": 0.18,
  "delta_fit_error": -0.0022,
  "delta_chamfer": -0.0011
}
```

## Role split

| You (pipeline) | Student (thesis) |
|----------------|------------------|
| EMS wrappers, CLI, configs | Shape completion method |
| Ablation scripts + report template | Dataset preparation |
| Baseline validation | Robot/sim experiments + analysis |

## Visualization notes

Superquadric plots use **implicit-surface sampling** (same formulation as EMS distance) plus **equal 3D axis limits**. Earlier versions used a brittle port of the vendor’s ellipse loop and matplotlib’s default aspect ratio, which made fits look wrong even when parameters were fine.

- Regenerate PNGs after updating: `pixi run visualize -- <cloud.ply> <result.json> -o out.png --surface-points 12000`
- **Hierarchical** mode fits several primitives to different regions; they are not guaranteed to “skin” the whole animal like a mesh — expect a union of blobs that approximate major parts.
- For **partial** point clouds, a single superquadric is only a coarse convex hull–style fit by design.

## Vendor patches (macOS / NumPy 2.x)

The upstream EMS package is vendored under `vendor/`. Two small patches are applied for compatibility:

1. **Lazy mayavi import** in `vendor/.../EMS/utilities.py` — avoids requiring mayavi at import time
2. **`np.int` → `int`** in `vendor/.../EMS/EMS_recovery.py` — NumPy 2.x compatibility

Re-apply these after updating the vendor submodule. See `patches/README.md`.

- Paper: [Robust and Accurate Superquadric Recovery (CVPR 2022)](https://arxiv.org/abs/2111.14517)
- Code: [bmlklwx/EMS-superquadric_fitting](https://github.com/bmlklwx/EMS-superquadric_fitting)
