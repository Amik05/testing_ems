# Vendor patches

The copy under `vendor/EMS-superquadric_fitting/` is **committed in this repo** (not a submodule). These patches are already applied:

1. **Lazy mayavi import** — `Python/src/EMS/utilities.py`
   - `from mayavi import mlab` only inside `showSuperquadrics` and `showPoints`

2. **NumPy 2.x** — `Python/src/EMS/EMS_recovery.py`
   - `num_switch = 0` instead of `np.int(0)`

If you replace vendor EMS with a fresh upstream checkout, re-apply the above before committing.
