#!/usr/bin/env python3
"""Fit superquadrics to a point cloud and export JSON."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ems_bridge.cli import fit_main


if __name__ == "__main__":
    raise SystemExit(fit_main())
