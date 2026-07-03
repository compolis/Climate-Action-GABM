"""Political-exposure vocabularies: target marginals + affinity weights.

Relocated from :mod:`cag.abm.environment` (v0.8) so the exposure
vocabularies live in one discoverable place alongside the other
subsystem configs (see :mod:`cag.abm.config`). The affinity *scoring* and
*assignment* logic (``_green_affinity_score`` / ``_reform_affinity_score``
/ ``assign_political_exposure``) remains in ``environment.py`` and imports
the data from here. ``environment.py`` also re-exports every public name
below for backward compatibility, so existing
``from cag.abm.environment import TARGET_PRESETS`` imports keep working.

This block supports three selection modes consumed by
``SurveyedNation.assign_political_exposure()``:
  - "rule_priority_chain"   : legacy v0.5 rule (kept for reproducibility)
  - "rule_signal_count"     : reserved (alias of priority_chain for now)
  - "rule_affinity_rank"    : NEW default; deterministic top-K on affinity

Design notes (see docs/Model_Design.md §18 and
docs/Literature_Political_Exposure.md §6-§7 for full reasoning):

WHY target marginals are not inherited from the YouGov sample. The
YouGov panel is recruited politically-engaged; left to its own devices
the four-cell split is ~A 27 / B 19 / both 49 / neither 5, which inverts
the UK media-reality asymmetry (B > A) and under-counts the disengaged
tier by an order of magnitude. We therefore calibrate the targets to
UK population-level evidence and re-sample the YouGov pool to hit them.

WHY a committed-minority symmetric default (45 % "neither"). Reuters
DNR 2024 selective news avoidance is 46 %; Hansard Audit of Political
Engagement 16 (2019) reports ~40 % "not much / not at all" interested in
politics; Britain Talks Climate disengaged segments together ~25-30 %.
The lit-supported band for "no party-attributed broadcast receipt" is
35-60 %. We adopt 45 % as a compromise between the lit (50-60 %) and
the user's earlier 30-40 % intuition; this is documented in
Literature_Political_Exposure.md §6.2.

WHY symmetric default with the April-2024 asymmetric preset as a named
override. Symmetric reach is the cleanest counter-factual for studying
committed-minority dynamics in isolation; asymmetry is then an
*experimental control*, not an embedded assumption. The April-2024
anchor uses JL Partners' GB News viewer panel (15-22 Apr 2024, n=518:
Con 39 % / Reform 20 % / Lab 8 %) for Reform reach, and the comparable
absence of any Green broadcast vehicle for the A side.
"""

import math


# Target marginal presets. Each dict's four cells must sum to 1.0.
TARGETS_COMMITTED_MINORITY_SYMMETRIC = {
    "A-only": 0.05, "B-only": 0.05, "both": 0.60, "neither": 0.30,
}
TARGETS_COMMITTED_MINORITY_UK_2024 = {
    "A-only": 0.08, "B-only": 0.14, "both": 0.33, "neither": 0.45,
}
TARGETS_LEGACY_V05 = {
    "A-only": 0.225, "B-only": 0.225, "both": 0.20, "neither": 0.35,
}
# Run-14-style cleanest persuasion test: every agent gets exactly one side
# of the broadcast feed and nothing else.
TARGETS_SPLIT_50 = {
    "A-only": 0.50, "B-only": 0.50, "both": 0.00, "neither": 0.00,
}
# Matched-horizon baseline: nobody hears any broadcast — isolates the
# prompt-chain / debias drift from any persuasion signal.
TARGETS_NEITHER = {
    "A-only": 0.00, "B-only": 0.00, "both": 0.00, "neither": 1.00,
}
TARGET_PRESETS = {
    "committed_minority_symmetric": TARGETS_COMMITTED_MINORITY_SYMMETRIC,
    "committed_minority_uk_2024": TARGETS_COMMITTED_MINORITY_UK_2024,
    "legacy_v05": TARGETS_LEGACY_V05,
    "split50": TARGETS_SPLIT_50,
    "neither": TARGETS_NEITHER,
}

# Affinity-score weight presets. Each preset is a dict {"A": {...}, "B": {...}}
# of weights applied to the per-signal contributions in
# ``_green_affinity_score`` / ``_reform_affinity_score``.
#
# WHY hand-picked weights, not fitted. No UK individual-level ground
# truth exists for who is in which echo chamber, so any fitted
# coefficients would be circular. Hand-picked priors anchored to
# published correlations are honest about the uncertainty and remain
# overridable via ``SIM_CONFIG["affinity_weights"]``.
#
# WHY a three-tier, factor-2 scheme (political 2.0 / values 1.0 /
# demographics 0.5). Only the *relative ordering* of the weights matters
# for the rank-based assignment (absolute magnitude is a nuisance
# parameter), so the default uses a clean, easily-defended tier ladder
# rather than a table of finely-tuned decimals:
#
#   Tier 1 — political self-report (brexit, politics, vote_bonus) = 2.0
#     Vote choice and left-right / Leave-Remain self-placement are the
#     strongest empirical proxies for partisan media diet
#     (Fletcher & Nielsen 2017), so they carry the heaviest tier. The
#     tier is still bounded, so values + demographics together can
#     out-vote a single political signal — satisfying the "more than
#     just voting history" requirement.
#
#   Tier 2 — psychological values (openness, selftransc, conformtrad,
#     sdo, rwa) = 1.0. Schwartz-values and authoritarianism scales are
#     robust attitudinal predictors of pro-/anti-environmental stance
#     (Steg & de Groot 2010 line of work) but are one step removed from
#     the media-consumption behaviour we are ranking on.
#
#   Tier 3 — demographics (age, education, region) = 0.5. Proxies rather
#     than direct attitudinal indicators, so weighted at half the values
#     tier.
#
# The "vote_dominant" / "values_dominant" presets below deliberately
# break this ladder to probe robustness (NB 27); the factor-2 spacing
# here keeps the default's narrative simple.
DEFAULT_AFFINITY_WEIGHTS = {
    "A": {
        "openness": 1.0, "selftransc": 1.0, "conformtrad": 1.0,
        "sdo": 1.0, "rwa": 1.0,
        "age": 0.5, "education": 0.5, "region": 0.5,
        "brexit": 2.0, "politics": 2.0, "vote_bonus": 2.0,
    },
    "B": {
        "openness": 1.0, "selftransc": 1.0, "conformtrad": 1.0,
        "sdo": 1.0, "rwa": 1.0,
        "age": 0.5, "education": 0.5, "region": 0.5,
        "brexit": 2.0, "politics": 2.0, "vote_bonus": 2.0,
    },
}
# Vote-dominant preset. Same three-tier ladder as ``balanced`` but with
# the political tier pushed from 2.0 to 4.0 (4× the values tier instead
# of 2×). Demographics stay pinned at the weakest rung (0.5). Tests the
# "is everything just vote choice?" hypothesis.
AFFINITY_WEIGHTS_VOTE_DOMINANT = {
    side: {
        "openness": 1.0, "selftransc": 1.0, "conformtrad": 1.0,
        "sdo": 1.0, "rwa": 1.0,
        "age": 0.5, "education": 0.5, "region": 0.5,
        "brexit": 4.0, "politics": 4.0, "vote_bonus": 4.0,
    }
    for side in ("A", "B")
}
# Values-dominant preset. The same ladder with the top two tiers
# *swapped*: values become the dominant tier (4.0), the political tier
# drops to the non-dominant rung (1.0), demographics stay weakest (0.5).
# Tests whether a values-only signature reproduces the cells the
# vote-anchored signature finds.
AFFINITY_WEIGHTS_VALUES_DOMINANT = {
    side: {
        "openness": 4.0, "selftransc": 4.0, "conformtrad": 4.0,
        "sdo": 4.0, "rwa": 4.0,
        "age": 0.5, "education": 0.5, "region": 0.5,
        "brexit": 1.0, "politics": 1.0, "vote_bonus": 1.0,
    }
    for side in ("A", "B")
}
AFFINITY_WEIGHT_PRESETS = {
    "balanced": DEFAULT_AFFINITY_WEIGHTS,
    "vote_dominant": AFFINITY_WEIGHTS_VOTE_DOMINANT,
    "values_dominant": AFFINITY_WEIGHTS_VALUES_DOMINANT,
}

VALID_EXPOSURE_MODES = (
    "rule_priority_chain",
    "rule_signal_count",
    "rule_affinity_rank",
)


def _resolve_targets(targets):
    """Normalise a targets argument to a dict with the four canonical cells.

    Accepts a preset name (string), a literal dict, or None (returns the
    new committed-minority symmetric default).
    """
    if targets is None:
        targets = TARGETS_COMMITTED_MINORITY_SYMMETRIC
    if isinstance(targets, str):
        if targets not in TARGET_PRESETS:
            raise ValueError(
                f"unknown target preset {targets!r}; valid: "
                f"{sorted(TARGET_PRESETS)}"
            )
        targets = TARGET_PRESETS[targets]
    required = {"A-only", "B-only", "both", "neither"}
    if set(targets) != required:
        raise ValueError(
            f"targets dict must have keys {sorted(required)}, got {sorted(targets)}"
        )
    total = sum(targets.values())
    if not math.isclose(total, 1.0, abs_tol=1e-6):
        raise ValueError(f"targets must sum to 1.0, got {total}")
    return dict(targets)


def _resolve_weights(weights):
    """Normalise a weights argument: preset name, literal dict, or None."""
    if weights is None:
        return DEFAULT_AFFINITY_WEIGHTS
    if isinstance(weights, str):
        if weights not in AFFINITY_WEIGHT_PRESETS:
            raise ValueError(
                f"unknown weight preset {weights!r}; valid: "
                f"{sorted(AFFINITY_WEIGHT_PRESETS)}"
            )
        return AFFINITY_WEIGHT_PRESETS[weights]
    if not isinstance(weights, dict) or set(weights) != {"A", "B"}:
        raise ValueError(
            "weights must be a dict with keys 'A' and 'B' (or a preset name)"
        )
    return weights
