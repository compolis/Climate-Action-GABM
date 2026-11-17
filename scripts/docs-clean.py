#!/usr/bin/env python3
"""Compatibility wrapper for scripts/dev/docs-clean.py."""

from pathlib import Path
import runpy

runpy.run_path(
    str(Path(__file__).resolve().parent / "dev" / "docs-clean.py"),
    run_name="__main__",
)

