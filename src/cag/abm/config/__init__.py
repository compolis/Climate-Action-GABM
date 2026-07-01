"""Configuration vocabularies for Climate-Action-GABM subsystems.

Each module in this package owns the *named vocabularies* (preset dicts)
and their resolve/validate helpers for one simulation subsystem, keeping
that data out of the large consumer modules (``environment.py``,
``agent.py``). The shared shape is::

    DEFAULT_*        # the default config / weights
    *_PRESETS        # {name: dict} registry of named alternatives
    resolve_*(spec)  # None | preset-name | literal dict -> normalised dict
    validate_*(cfg)  # raise ValueError on an incoherent config

This is distinct from :mod:`cag.presets` (whole-run ``SIM_CONFIG``
override bundles applied via ``--preset``). A subsystem vocabulary here is
referenced by a single ``SIM_CONFIG`` key (e.g.
``political_exposure_targets``, ``memory``); a run bundle in
``cag.presets`` composes many such keys into one named experiment.

Modules:
    exposure -- political-exposure target marginals + affinity weights.
    memory   -- agent memory / prompt-assembly configuration.
"""
