#!/usr/bin/env python3
"""Compatibility module exporting symbols from scripts/dev/docs.py."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "dev" / "docs.py"
_SPEC = spec_from_file_location("_cag_docs_dev", _TARGET)
if _SPEC is None or _SPEC.loader is None:
    msg = f"Unable to load docs module at {_TARGET}"
    raise RuntimeError(msg)
_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

for _name in dir(_MODULE):
    if _name.startswith("_"):
        continue
    globals()[_name] = getattr(_MODULE, _name)

if __name__ == "__main__":
    _MODULE.main()
    if hasattr(_MODULE, "force_copy_contributors_license"):
        _MODULE.force_copy_contributors_license()
