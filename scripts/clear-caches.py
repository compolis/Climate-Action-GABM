#!/usr/bin/env python3
"""Compatibility wrapper for scripts/dev/clear-caches.py."""

from pathlib import Path
import runpy

runpy.run_path(
    str(Path(__file__).resolve().parent / "dev" / "clear-caches.py"),
    run_name="__main__",
)

