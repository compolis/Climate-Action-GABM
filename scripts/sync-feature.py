#!/usr/bin/env python3
"""Compatibility wrapper for scripts/dev/sync-feature.py."""

from pathlib import Path
import runpy

runpy.run_path(
    str(Path(__file__).resolve().parent / "dev" / "sync-feature.py"),
    run_name="__main__",
)

