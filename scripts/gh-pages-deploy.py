#!/usr/bin/env python3
"""Compatibility wrapper for scripts/dev/gh-pages-deploy.py."""

from pathlib import Path
import runpy

runpy.run_path(
    str(Path(__file__).resolve().parent / "dev" / "gh-pages-deploy.py"),
    run_name="__main__",
)

