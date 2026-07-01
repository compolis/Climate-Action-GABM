"""Agent memory / prompt-assembly configuration.

Introduced in v0.8 to make the citizen prompt-assembly pipeline
(``SurveyedCitizen.assemble_context``) modular and ablatable for
scientific testing. Historically the six context sections (persona,
Day-0 anchor, daily summaries, recent reflections, own reasoning,
today-so-far) were hard-wired, and the "last two days" verbatim window
was duplicated across four call sites (two verbatim sections, the daily
summary cut-off, and ``manage_memory`` compression). This module lifts
all of that into a single declarative config so social scientists can
toggle sections on/off, widen/shrink the verbatim window, and override
any of it per prompt stage -- without editing agent code.

Shared shape (see :mod:`cag.abm.config`)::

    DEFAULT_MEMORY_CONFIG        # reproduces current v0.5 behaviour exactly
    MEMORY_PRESETS               # {name: partial-override dict}
    resolve_memory_config(spec)  # None | preset-name | dict -> full config
    validate_memory_config(cfg)  # raise ValueError on an incoherent config

The default MUST reproduce the previous hard-wired behaviour bit-for-bit
(guarded by golden regression tests); every preset here is expressed as a
*partial override* deep-merged onto ``DEFAULT_MEMORY_CONFIG``.

Config schema
-------------
Top-level keys::

    <section>: {"enabled": bool, ...}   # one entry per context section
    verbatim_window_days: int>=1 | None  # shared window W (None = unbounded)
    stages: {stage: {section: {param: value}}}  # per-stage overrides

Sections (``MEMORY_SECTIONS``): ``persona``, ``day0_anchor``,
``daily_summaries``, ``recent_reflections``, ``own_reasoning``,
``today_so_far``, ``opinion_trajectory``. All take ``enabled``;
``day0_anchor`` additionally takes ``ttl_days`` (None = anchor never
expires; int N = drop the anchor once ``day > N``).

The shared ``verbatim_window_days`` (W) couples four places that MUST
agree: recent reflections keep days ``{day-W+1 .. day}``; own reasoning
keeps the same window; daily summaries cover the *compressed* remainder
``d < day-W+1``; and ``manage_memory`` compresses day ``day-W`` once
``day > W``. Exposing them as one knob is deliberate -- separate per-section
windows would silently create gaps or overlaps between the verbatim and
summarised tiers. ``None`` means "unbounded verbatim / never compress".

Stages (``MEMORY_STAGES``): ``peer_message`` (generating a peer message),
``reflection`` (end-of-broadcast and end-of-peer reflections), ``survey``
(end-of-day survey). ``resolve_stage_memory(cfg, stage)`` deep-merges a
stage's overrides onto the global sections.
"""

from copy import deepcopy


# Ordered tuple of the context sections, in prompt-assembly order.
MEMORY_SECTIONS = (
    "persona",
    "day0_anchor",
    "daily_summaries",
    "recent_reflections",
    "own_reasoning",
    "today_so_far",
    "opinion_trajectory",
)

# Prompt stages that may carry per-stage overrides.
MEMORY_STAGES = ("peer_message", "reflection", "survey")

# Allowed parameter keys per section. Every section takes ``enabled``;
# only ``day0_anchor`` additionally exposes ``ttl_days``.
_SECTION_PARAMS = {name: {"enabled"} for name in MEMORY_SECTIONS}
_SECTION_PARAMS["day0_anchor"] = {"enabled", "ttl_days"}


# The default config reproduces the previous hard-wired v0.5 behaviour:
# all six original sections on, opinion_trajectory off, W = 2, no per-stage
# overrides, and the Day-0 anchor never expiring.
DEFAULT_MEMORY_CONFIG = {
    "persona": {"enabled": True},
    "day0_anchor": {"enabled": True, "ttl_days": None},
    "daily_summaries": {"enabled": True},
    "recent_reflections": {"enabled": True},
    "own_reasoning": {"enabled": True},
    "today_so_far": {"enabled": True},
    "opinion_trajectory": {"enabled": False},
    "verbatim_window_days": 2,
    "stages": {"peer_message": {}, "reflection": {}, "survey": {}},
}


# Named presets, expressed as partial overrides deep-merged onto the default.
MEMORY_PRESETS = {
    # Current production behaviour.
    "default": {},
    # Verbatim window ablations (the shared W knob).
    "short_memory": {"verbatim_window_days": 1},
    "wide_memory": {"verbatim_window_days": 4},
    "no_compression": {"verbatim_window_days": None},
    # Single-section ablations for responsiveness testing.
    "no_anchor": {"day0_anchor": {"enabled": False}},
    "anchor_ttl2": {"day0_anchor": {"ttl_days": 2}},
    "no_own_reasoning": {"own_reasoning": {"enabled": False}},
    # Coarser ablations.
    "reflections_only": {
        "day0_anchor": {"enabled": False},
        "own_reasoning": {"enabled": False},
        "today_so_far": {"enabled": False},
    },
    "persona_only": {
        "day0_anchor": {"enabled": False},
        "daily_summaries": {"enabled": False},
        "recent_reflections": {"enabled": False},
        "own_reasoning": {"enabled": False},
        "today_so_far": {"enabled": False},
        "opinion_trajectory": {"enabled": False},
    },
}


def _deep_merge(base, override):
    """Recursively merge ``override`` into ``base`` in place and return it.

    Nested dicts are merged; every other value (including ``None``) is
    overwritten. ``base`` is mutated, so callers pass a deepcopy.
    """
    for key, value in override.items():
        if (
            isinstance(value, dict)
            and isinstance(base.get(key), dict)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = deepcopy(value)
    return base


def resolve_memory_config(spec=None):
    """Normalise a memory-config ``spec`` into a full, validated config.

    ``spec`` may be:
      - ``None``  -> a deepcopy of :data:`DEFAULT_MEMORY_CONFIG`;
      - ``str``   -> a name in :data:`MEMORY_PRESETS`, merged onto the default;
      - ``dict``  -> a partial override deep-merged onto the default.

    The result is always a fresh, fully-populated dict (never a shared
    reference to a preset) and is validated before return.
    """
    cfg = deepcopy(DEFAULT_MEMORY_CONFIG)
    if spec is None:
        override = {}
    elif isinstance(spec, str):
        if spec not in MEMORY_PRESETS:
            raise ValueError(
                f"unknown memory preset {spec!r}; "
                f"choose from {sorted(MEMORY_PRESETS)}"
            )
        override = MEMORY_PRESETS[spec]
    elif isinstance(spec, dict):
        override = spec
    else:
        raise ValueError(
            f"memory spec must be None, a preset name, or a dict; "
            f"got {type(spec).__name__}"
        )
    _deep_merge(cfg, override)
    validate_memory_config(cfg)
    return cfg


def _validate_section(name, params):
    """Validate one section's parameter dict (raise ValueError on error)."""
    if not isinstance(params, dict):
        raise ValueError(
            f"memory section {name!r} must map to a dict, got "
            f"{type(params).__name__}"
        )
    allowed = _SECTION_PARAMS[name]
    unknown = set(params) - allowed
    if unknown:
        raise ValueError(
            f"memory section {name!r} has unknown keys {sorted(unknown)}; "
            f"allowed: {sorted(allowed)}"
        )
    if "enabled" in params and not isinstance(params["enabled"], bool):
        raise ValueError(
            f"memory section {name!r} 'enabled' must be a bool, got "
            f"{type(params['enabled']).__name__}"
        )
    if "ttl_days" in params:
        ttl = params["ttl_days"]
        if ttl is not None and (isinstance(ttl, bool) or not isinstance(ttl, int)):
            raise ValueError(
                f"memory section {name!r} 'ttl_days' must be None or an int, "
                f"got {type(ttl).__name__}"
            )
        if isinstance(ttl, int) and not isinstance(ttl, bool) and ttl < 0:
            raise ValueError(
                f"memory section {name!r} 'ttl_days' must be >= 0, got {ttl}"
            )


def validate_memory_config(cfg):
    """Raise ``ValueError`` if ``cfg`` is not a coherent memory config."""
    if not isinstance(cfg, dict):
        raise ValueError(
            f"memory config must be a dict, got {type(cfg).__name__}"
        )

    allowed_top = set(MEMORY_SECTIONS) | {"verbatim_window_days", "stages"}
    unknown = set(cfg) - allowed_top
    if unknown:
        raise ValueError(
            f"memory config has unknown keys {sorted(unknown)}; "
            f"allowed: {sorted(allowed_top)}"
        )

    for name in MEMORY_SECTIONS:
        if name in cfg:
            _validate_section(name, cfg[name])

    window = cfg.get("verbatim_window_days")
    if window is not None:
        if isinstance(window, bool) or not isinstance(window, int):
            raise ValueError(
                f"'verbatim_window_days' must be None or an int, got "
                f"{type(window).__name__}"
            )
        if window < 1:
            raise ValueError(
                f"'verbatim_window_days' must be >= 1, got {window}"
            )

    stages = cfg.get("stages", {})
    if not isinstance(stages, dict):
        raise ValueError(
            f"'stages' must be a dict, got {type(stages).__name__}"
        )
    unknown_stages = set(stages) - set(MEMORY_STAGES)
    if unknown_stages:
        raise ValueError(
            f"'stages' has unknown stages {sorted(unknown_stages)}; "
            f"allowed: {sorted(MEMORY_STAGES)}"
        )
    for stage, overrides in stages.items():
        if not isinstance(overrides, dict):
            raise ValueError(
                f"stage {stage!r} overrides must be a dict, got "
                f"{type(overrides).__name__}"
            )
        unknown_sections = set(overrides) - set(MEMORY_SECTIONS)
        if unknown_sections:
            raise ValueError(
                f"stage {stage!r} overrides unknown sections "
                f"{sorted(unknown_sections)}; allowed: {sorted(MEMORY_SECTIONS)}"
            )
        for name, params in overrides.items():
            _validate_section(name, params)


def resolve_stage_memory(cfg, stage):
    """Return the effective per-stage config: globals merged with a stage.

    The returned dict has the same section/``verbatim_window_days`` layout
    as ``cfg`` minus the ``stages`` key, with ``cfg['stages'][stage]``
    deep-merged over the global sections. Section params are flat, so a
    per-section update is sufficient.
    """
    if stage is not None and stage not in MEMORY_STAGES:
        raise ValueError(
            f"unknown memory stage {stage!r}; choose from {sorted(MEMORY_STAGES)}"
        )
    eff = {key: deepcopy(value) for key, value in cfg.items() if key != "stages"}
    overrides = cfg.get("stages", {}).get(stage, {}) if stage else {}
    for name, params in overrides.items():
        eff.setdefault(name, {}).update(deepcopy(params))
    return eff


# --- Verbatim-window helpers (single source of truth for the W coupling) ---

def verbatim_days(window, day):
    """Day-numbers shown verbatim at ``day`` for window ``window``.

    ``window`` int W -> ``{day-W+1 .. day}`` (lower-clamped to 0, so Day-0
    entries can fall in the window; recent reflections keep Day-0, own
    reasoning drops it via its own ``d > 0`` filter since Day-0 reasoning
    lives in the anchor section).
    ``window`` None  -> every day ``0 .. day`` (unbounded / never compress).
    """
    if window is None:
        return set(range(0, day + 1))
    return set(range(max(0, day - window + 1), day + 1))


def summary_upper_exclusive(window, day):
    """Daily summaries cover days ``d`` with ``1 <= d < <this bound>``.

    This is the lower edge of the verbatim window: ``day-W+1``. With
    ``window=None`` (unbounded verbatim) the bound is 1, so no day is
    summarised.
    """
    if window is None:
        return 1
    return day - window + 1


def compression_target_day(window, day):
    """Day to compress at the start of ``day``, or ``None`` if none.

    Mirrors the verbatim window: once ``day > W`` the day falling out of
    the window (``day - W``) is compressed. ``window=None`` never compresses.
    """
    if window is None:
        return None
    if day > window:
        return day - window
    return None
