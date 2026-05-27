# Point cloud inputs

All PLY (and optional NPY/NPZ) inputs for fitting live under `data/`.

## Layout

```
data/
├── vendor/          # EMS paper demo clouds (committed)
│   ├── single/      # partial_* and noisy_* examples
│   └── multi/       # cat, dog, turtle
├── partial/         # partial-view clouds (gitignored — student adds)
└── completed/       # shape-completion outputs (gitignored — student adds)
```

## Usage

```bash
python run.py --partial data/vendor/multi/cat.ply --completed data/vendor/multi/cat.ply --mode hierarchical --object-id cat --output results
```

For real partial-vs-completed experiments, use one of these conventions:

1. Folder convention (recommended; no manifest):

```text
data/
├── object_01/
│   ├── partial.ply
│   └── completed.ply
└── object_02/
    ├── partial.ply
    └── completed.ply
```

Run:

```bash
python run.py --batch data
```

2. Manifest mode (optional):
Create your own manifest YAML and pass it via `--manifest <path>`.

## Refreshing vendor samples

If you update the vendored EMS copy, recopy demos:

```bash
cp vendor/EMS-superquadric_fitting/MATLAB/example_scripts/data/single_superquadric/*.ply data/vendor/single/
cp vendor/EMS-superquadric_fitting/MATLAB/example_scripts/data/multi_superquadrics/*.ply data/vendor/multi/
```
