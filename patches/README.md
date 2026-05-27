# Vendor patches

After `git submodule update` on `vendor/EMS-superquadric_fitting`, re-apply:

1. **Lazy mayavi import** — `Python/src/EMS/utilities.py`
   - Remove top-level `from mayavi import mlab`
   - Add `from mayavi import mlab` inside `showSuperquadrics` and `showPoints` only

2. **NumPy 2.x** — `Python/src/EMS/EMS_recovery.py`
   - Change `num_switch = np.int(0)` to `num_switch = 0`