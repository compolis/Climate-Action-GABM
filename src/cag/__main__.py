#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Headless entry point for running the Climate-Action-GABM simulation.

Composable CLI: every ``SIM_CONFIG`` knob that materially changes the run
is exposed as a flag, so an HPC sbatch submission line can pin every
research parameter without editing scripts. Convenience bundles live in
:mod:`cag.presets` and are selected with ``--preset NAME``.

Application order (lowest → highest precedence)::

    SIM_CONFIG defaults (sim.py)
        → preset bundle (cag/presets.py)
            → individual --flag overrides

Two flags are **required**: ``--outdir`` (where artefacts go) and a way to
size the run — either ``--n-citizens`` + ``--days`` directly, or a
``--preset`` that supplies them.

Inspection helpers:

* ``--list-presets`` prints all registered run bundles and exits.
* ``--dry-run`` resolves the final config (preset + CLI overrides),
  prints it as JSON, and exits without any LLM calls.

Usage (local Mac, mlx-lm server on :8080)::

    PYTHONPATH=src python3 -m cag \\
        --outdir data/output/experiments \\
        --n-citizens 10 --days 2

Usage (AIRE HPC, vLLM server on :8000)::

    PYTHONPATH=src python3 -m cag \\
        --outdir "$SCRATCH/cag/runs/run_$SLURM_JOB_ID" \\
        --n-citizens 50 --days 7 \\
        --provider local --model Qwen/Qwen3-8B \\
        --base-url http://localhost:8000/v1 \\
        --no-thinking --checkpoint-every-day \\
        --exposure-targets split50

All run artefacts (CSVs, PNGs, config snapshot, run log) are written
under ``--outdir``; nothing is written into the repository tree, so the
output directory can point at ``$SCRATCH`` on a cluster.
"""
__author__ = [
    "Andy Turner <agdturner@gmail.com>",
    "Ajaykumar Manivannan <ashwamanivannan@gmail.com>",
    "Charlie Pilgrim <pilgrimcharlie2@gmail.com>",
]
__version__ = "0.9.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

import argparse
import json
import logging
import random
import sys
import time
from pathlib import Path

# Force a non-interactive backend before anything imports pyplot, so figure
# saving works on a headless compute node with no display.
import matplotlib
matplotlib.use("Agg")

# ── Agent / attribute imports ─────────────────────────────────────
from gabm.abm.attributes.gender import GenderMap, GenderID
from gabm.abm.attributes.politics import PoliticsID
from gabm.abm.democracy.election import ElectionID

from cag.io.survey import load
from cag.abm.agent import SurveyedCitizen
from cag.abm.environment import SurveyedNation
from cag.abm.attributes.opinion import ALL_CLIMATE_POLICIES, ClimatePolicyID
from cag.abm.attributes.region import UKRegionMap, RegionID
from cag.abm.attributes.education import SurveyEducationMap, EducationID
from cag.abm.attributes.ethnicity import SurveyEthnicityMap, EthnicityID
from cag.abm.attributes.income import SurveyIncomeMap, IncomeID
from cag.abm.attributes.politics import SurveyPoliticsMap
from cag.abm.attributes.family import SurveyFamilyMap, FamilyID
from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteMap, UKGE2019VoteID
from cag.abm.democracy.elections.brexit import BrexitVoteMap, BrexitVoteID
from cag.abm.attributes.narratives import (
    SelftranscMap, SelfenhMap, OpennessMap, ConformTradMap,
    SDOMap, EDOMap, RWAMap, rescale_1_6, rescale_1_7,
)
from cag.abm.sim import run_simulation, save_results, save_result_plots, make_phases
from cag.presets import RUN_BUNDLE_PRESETS, list_presets


# Only the survey CSV gets a hard default — every other knob has either
# a SIM_CONFIG default (sim.py) or must come from a preset / CLI flag.
DEFAULT_SURVEY_CSV = "data/yougov_survey_data/YouGovProcessedData.csv"


# Map argparse ``dest`` names → SIM_CONFIG keys. Only flags whose dest
# differs from the SIM_CONFIG key need an entry; everything else is
# passed through verbatim.
_ARG_TO_SIM = {
    "seed":                "random_seed",
    "k_peers":             "k_peers_per_day",
    "model":               "llm_model",
    "provider":            "llm_provider",
    "base_url":            "local_base_url",
    "temperature":         "llm_temperature",
    "exposure_mode":       "political_exposure_mode",
    "exposure_targets":    "political_exposure_targets",
    "message_source":      "political_message_source",
    "message_set":         "political_message_set",
    "diagnostics_timeout": "diagnostics_timeout_s",
    "local_timeout":       "local_timeout_s",
}

# Argparse dests that are NOT SIM_CONFIG keys (control flow / I/O).
_NON_SIM_DESTS = frozenset({
    "outdir", "data", "preset", "list_presets", "dry_run",
    "checkpoint_every_day", "resume",
})


# ── Argparse type helpers ─────────────────────────────────────────
def _maybe_json(value):
    """Either a JSON object literal (must start with ``{``) or a string.

    Used for flags that accept *either* a preset name (resolved downstream
    by ``cag.abm.environment``) *or* a literal dict.
    """
    value = value.strip()
    if value.startswith("{"):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise argparse.ArgumentTypeError(f"Invalid JSON: {exc}")
    return value


def _json_dict(value):
    """Strict JSON object → dict (no preset-name fallback)."""
    try:
        d = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"Invalid JSON: {exc}")
    if not isinstance(d, dict):
        raise argparse.ArgumentTypeError(
            f"Must be a JSON object, got {type(d).__name__}"
        )
    return d


def _int_or_none(value):
    """Accept ``none`` / ``null`` / empty as ``None``, else an int."""
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("", "none", "null"):
        return None
    return int(value)


def _package_policies_arg(value):
    """``all`` → every climate policy; else comma-separated policy IDs."""
    s = value.strip().lower()
    if s == "all":
        return list(ALL_CLIMATE_POLICIES)
    try:
        return [ClimatePolicyID(int(p.strip())) for p in value.split(",") if p.strip()]
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(
            f"--package-policies expects 'all' or comma-separated ints, "
            f"got {value!r}: {exc}"
        )


# ── Day plan + nation builders ───────────────────────────────────
def build_days(n_days, broadcasts_a=1, broadcasts_b=1, interleave=True):
    """Build an alternating package-mode day plan.

    Each day carries ``broadcasts_a`` P-A broadcasts and ``broadcasts_b``
    P-B broadcasts (default 1 each = the symmetric canon), always closing
    with a peer-messaging ("C") phase. The ``a_first`` hint alternates by
    day so recency is balanced across the run. No per-day ``policy`` key:
    package mode broadcasts every ``package_policies`` entry each phase.

    ``broadcasts_a != broadcasts_b`` is the frequency-asymmetry lever
    (distinct from ``--reach-a/-b``, which resends the same message to a
    wider audience). ``interleave`` mixes the two sides (A,B,A,...) when
    True, else blocks them (A,A,B). For the symmetric 1v1 case both modes
    collapse to ``['P-A','P-B','C']`` so the canonical schedule is
    unchanged.

    The "C" phase is always present; peer messaging is disabled at run
    time by ``--k-peers 0`` (the peer step is a no-op when ``k_peers==0``).
    """
    plan = []
    for i in range(n_days):
        plan.append({
            "phases": make_phases(
                broadcasts_a=broadcasts_a,
                broadcasts_b=broadcasts_b,
                peer=True,
                interleave=interleave,
                a_first=(i % 2 == 0),
            )
        })
    return plan


def build_nation(data, year=2026):
    """Create a SurveyedNation and populate it with citizens."""
    UKGE2019_ELECTION_ID = ElectionID(0)
    BREXIT_REFERENDUM_ID = ElectionID(1)

    sn = SurveyedNation(
        year=year, place="UK",
        gender_map=GenderMap(),
        region_map=UKRegionMap(),
        education_map=SurveyEducationMap(),
        ethnicity_map=SurveyEthnicityMap(),
        income_map=SurveyIncomeMap(),
        politics_map=SurveyPoliticsMap(),
        family_map=SurveyFamilyMap(),
        ukge2019_vote_map=UKGE2019VoteMap(UKGE2019_ELECTION_ID),
        brexit_vote_map=BrexitVoteMap(BREXIT_REFERENDUM_ID),
        selftransc_map=SelftranscMap,
        selfenh_map=SelfenhMap,
        openness_map=OpennessMap,
        conformtrad_map=ConformTradMap,
        sdo_map=SDOMap,
        edo_map=EDOMap,
        rwa_map=RWAMap,
    )

    for i in range(len(data)):
        row = data.iloc[i]
        sc = SurveyedCitizen(
            agent_id=row.get("ID", None),
            environment=sn,
            year_of_birth=year - int(row.get("age", 0)),
            gender_id=GenderID.MALE if int(row.get("male_dummy", 0)) == 1 else GenderID.FEMALE,
            region_id=RegionID(int(row.get("tprofile_GOR", 0))),
            education_id=EducationID(int(row.get("profile_education_level", 0))),
            income_id=IncomeID(int(row.get("tprofile_gross_household", 0))),
            ethnicity_id=EthnicityID(int(row.get("ethnicity_R", 0))),
            family_id=FamilyID.PARENT if int(row.get("parent_dummy", 0)) == 1 else FamilyID.NOT_PARENT,
            ukge2019_vote_id=UKGE2019VoteID(int(row.get("Vote2019R", 0))),
            brexit_vote_id=BrexitVoteID(int(row.get("pastvote_EURef", 0))),
            politics_id=PoliticsID(int(row.get("Political_Left_Right", 0))),
            selftransc_id=rescale_1_6(int(row.get("Selftransc_Val", 0))),
            selfenh_id=rescale_1_6(int(row.get("Selfenh_Values", 0))),
            openness_id=rescale_1_6(int(row.get("Openness", 0))),
            conformtrad_id=rescale_1_6(int(row.get("ConformTrad", 0))),
            sdo_id=rescale_1_7(int(row.get("SDO", 0))),
            edo_id=rescale_1_7(int(row.get("EDO", 0))),
            rwa_id=rescale_1_6(int(row.get("RWA", 0))),
            original_survey_data=data.iloc[i],
        )
        sn.agents_active[sc.id] = sc

    return sn


# ── Config assembly ───────────────────────────────────────────────
def _args_to_sim_dict(args):
    """Project argparse Namespace into SIM_CONFIG keyspace.

    Only attributes the user explicitly set survive (overridable flags
    use ``default=argparse.SUPPRESS``); the rest defer to preset /
    SIM_CONFIG. Control-flow flags are filtered out.
    """
    out = {}
    for dest, value in vars(args).items():
        if dest in _NON_SIM_DESTS:
            continue
        key = _ARG_TO_SIM.get(dest, dest)
        out[key] = value
    return out


def build_config(preset_dict, cli_dict):
    """Merge preset + CLI into a SIM_CONFIG-compatible override dict.

    CLI flags win over preset values. ``days`` is normalised: an integer
    (from either source) is expanded via :func:`build_days` into the
    canonical alternating-phases list, threading in the frequency-asymmetry
    knobs (``broadcasts_a`` / ``broadcasts_b`` / ``interleave``).

    Those three knobs are day-plan construction parameters, not
    ``SIM_CONFIG`` keys, so they are consumed (popped) here and never leak
    into the resolved config.
    """
    merged = {}
    if preset_dict:
        merged.update(preset_dict)
    merged.update(cli_dict)

    broadcasts_a = merged.pop("broadcasts_a", 1)
    broadcasts_b = merged.pop("broadcasts_b", 1)
    interleave = merged.pop("interleave", True)

    if "days" in merged and isinstance(merged["days"], int):
        merged["days"] = build_days(
            merged["days"],
            broadcasts_a=broadcasts_a,
            broadcasts_b=broadcasts_b,
            interleave=interleave,
        )
    elif (broadcasts_a, broadcasts_b, interleave) != (1, 1, True):
        logging.warning(
            "--broadcasts-a/--broadcasts-b/--interleave were set but 'days' "
            "is not an integer day-count (got %r); the frequency knobs are "
            "ignored. Pass --days N to use them.",
            merged.get("days"),
        )

    return merged


# ── Argparse ──────────────────────────────────────────────────────
def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m cag",
        description="Run the Climate-Action-GABM simulation headless "
                    "(package mode + offline messages by default).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # I/O. Not marked required at parse time because --list-presets and
    # --dry-run don't need it; validated in main() once we know the path.
    p.add_argument(
        "--outdir", default=None,
        help="Directory for all run artefacts (CSVs, PNGs, log, config). "
             "On a cluster point this at $SCRATCH, never the repo tree. "
             "Required for real runs; omitted for --list-presets / --dry-run.",
    )

    # Meta flags.
    p.add_argument(
        "--preset", default=None, choices=sorted(RUN_BUNDLE_PRESETS),
        help="Apply a named run bundle from cag.presets. CLI flags override "
             "preset values. Use --list-presets to see what each provides.",
    )
    p.add_argument(
        "--list-presets", dest="list_presets", action="store_true",
        help="Print all registered presets and exit.",
    )
    p.add_argument(
        "--dry-run", dest="dry_run", action="store_true",
        help="Resolve preset + CLI into the final SIM_CONFIG override dict, "
             "print it as JSON, and exit. No LLM / network / disk side effects.",
    )

    # Run sizing (required unless supplied by a preset).
    p.add_argument("--n-citizens", type=int, default=argparse.SUPPRESS,
                   dest="n_citizens",
                   help="Number of citizen agents to sample.")
    p.add_argument("--days", type=int, default=argparse.SUPPRESS,
                   help="Number of alternating package-mode days to simulate.")

    # Survey + repro.
    p.add_argument("--data", default=DEFAULT_SURVEY_CSV,
                   help="Path to the YouGov processed survey CSV.")
    p.add_argument("--seed", type=int, default=argparse.SUPPRESS,
                   help="Random seed. Default = SIM_CONFIG (42).")

    # Communication mode.
    p.add_argument("--communication-mode", default=argparse.SUPPRESS,
                   dest="communication_mode",
                   choices=("package", "single_policy"),
                   help="Broadcast scope. Default = SIM_CONFIG (package).")
    p.add_argument("--package-policies", type=_package_policies_arg,
                   default=argparse.SUPPRESS, dest="package_policies",
                   help="Policies broadcast each phase under package mode. "
                        "Use 'all' or a comma-separated list of policy IDs "
                        "(1=Renewable, 2=BanFossil, 3=BanPetrolCars, "
                        "4=GreenHousing, 5=CarbonTax, 6=Compensation).")
    p.add_argument("--day0-anchor", default=argparse.SUPPRESS,
                   dest="day0_anchor",
                   choices=("llm_survey", "ground_truth",
                            "ground_truth_with_rationale"),
                   help="Day-0 opinion seed. "
                        "Default = SIM_CONFIG (ground_truth_with_rationale).")
    p.add_argument("--k-peers", type=int, default=argparse.SUPPRESS,
                   dest="k_peers",
                   help="Peers each citizen messages per day in the C phase. "
                        "0 disables peer messaging entirely (broadcast-only).")

    # LLM.
    p.add_argument("--provider", default=argparse.SUPPRESS,
                   help="LLM provider: local / openai / anthropic / genai.")
    p.add_argument("--model", default=argparse.SUPPRESS,
                   help="Model name the server expects "
                        "(HPC/vLLM example: Qwen/Qwen3-8B).")
    p.add_argument("--base-url", default=argparse.SUPPRESS, dest="base_url",
                   help="OpenAI-compatible endpoint for provider=local "
                        "(HPC/vLLM example: http://localhost:8000/v1).")
    p.add_argument("--temperature", type=float, default=argparse.SUPPRESS,
                   help="Sampling temperature. Default = SIM_CONFIG (0.5).")
    p.add_argument("--survey-model", default=argparse.SUPPRESS,
                   dest="survey_model",
                   help="Override model used for end-of-day surveys "
                        "(None = use --model).")
    p.add_argument("--survey-provider", default=argparse.SUPPRESS,
                   dest="survey_provider",
                   help="Override provider used for end-of-day surveys "
                        "(None = use --provider).")
    p.add_argument("--thinking", dest="thinking",
                   action=argparse.BooleanOptionalAction,
                   default=argparse.SUPPRESS,
                   help="Enable / disable model thinking. "
                        "Default = SIM_CONFIG (False).")
    p.add_argument("--local-timeout", type=float, default=argparse.SUPPRESS,
                   dest="local_timeout",
                   help="Per-request timeout (s) for provider=local.")
    p.add_argument("--local-extra-body", type=_json_dict,
                   default=argparse.SUPPRESS, dest="local_extra_body",
                   help="JSON dict merged into every local-provider request body.")

    # Political-exposure assignment.
    p.add_argument("--exposure-mode", default=argparse.SUPPRESS,
                   dest="exposure_mode",
                   choices=("rule_priority_chain", "rule_signal_count",
                            "rule_affinity_rank"),
                   help="Exposure assignment algorithm. "
                        "Default = SIM_CONFIG (rule_affinity_rank).")
    p.add_argument("--exposure-targets", type=_maybe_json,
                   default=argparse.SUPPRESS, dest="exposure_targets",
                   help="Either a TARGET_PRESETS name (e.g. 'split50', "
                        "'neither', 'committed_minority_symmetric') or a "
                        "literal JSON dict of {A-only,B-only,both,neither} "
                        "weights summing to 1.0.")
    p.add_argument("--affinity-weights", type=_maybe_json,
                   default=argparse.SUPPRESS, dest="affinity_weights",
                   help="Either an AFFINITY_WEIGHT_PRESETS name "
                        "('balanced' / 'vote_dominant' / 'values_dominant') "
                        "or a literal JSON dict.")

    # Agent memory / prompt assembly.
    p.add_argument("--memory", type=_maybe_json,
                   default=argparse.SUPPRESS, dest="memory",
                   help="Agent memory config. Either a MEMORY_PRESETS name "
                        "('default' / 'short_memory' / 'wide_memory' / "
                        "'no_compression' / 'no_anchor' / 'anchor_ttl2' / "
                        "'no_own_reasoning' / 'reflections_only' / "
                        "'persona_only') or a literal JSON dict of section "
                        "toggles / verbatim_window_days / per-stage overrides.")

    # Broadcast reach + audience.
    p.add_argument("--reach-a", type=float, default=argparse.SUPPRESS,
                   dest="reach_a",
                   help="Fraction of agent_a's natural audience reached "
                        "per broadcast (0.0-1.0).")
    p.add_argument("--reach-b", type=float, default=argparse.SUPPRESS,
                   dest="reach_b",
                   help="Fraction of agent_b's natural audience reached "
                        "per broadcast (0.0-1.0).")
    p.add_argument("--reach-targeting-a",
                   choices=["random", "persuadable", "degree", "betweenness"],
                   default=argparse.SUPPRESS, dest="reach_targeting_a",
                   help="How agent_a selects its reached audience when "
                        "reach_a<1.0: 'random' (default), 'persuadable' (keep "
                        "the most undecided by |ground-truth package index|), "
                        "or 'degree'/'betweenness' (keep the most central on "
                        "the peer graph). No-op at reach_a=1.0.")
    p.add_argument("--reach-targeting-b",
                   choices=["random", "persuadable", "degree", "betweenness"],
                   default=argparse.SUPPRESS, dest="reach_targeting_b",
                   help="How agent_b selects its reached audience when "
                        "reach_b<1.0: 'random' (default), 'persuadable', "
                        "'degree', or 'betweenness'. No-op at reach_b=1.0.")
    p.add_argument("--audience-cap", type=_int_or_none,
                   default=argparse.SUPPRESS, dest="audience_cap",
                   help="Hard cap on each political agent's audience size "
                        "(applied before reach subsample). 'none' = no cap.")

    # Broadcast frequency (frequency-asymmetry lever; distinct from --reach).
    p.add_argument("--broadcasts-a", type=int, default=argparse.SUPPRESS,
                   dest="broadcasts_a",
                   help="Number of agent_a (pro-climate) broadcasts per day "
                        "(default 1). Repeated broadcasts pull distinct "
                        "offline messages until the pool wraps. Requires "
                        "--days N (ignored when 'days' is a literal plan).")
    p.add_argument("--broadcasts-b", type=int, default=argparse.SUPPRESS,
                   dest="broadcasts_b",
                   help="Number of agent_b (anti-climate) broadcasts per day "
                        "(default 1). See --broadcasts-a.")
    p.add_argument("--interleave", dest="interleave",
                   action=argparse.BooleanOptionalAction,
                   default=argparse.SUPPRESS,
                   help="Interleave A/B broadcasts (A,B,A,...) vs block them "
                        "(A,A,B). Default = interleave on. Only matters when "
                        "--broadcasts-a != --broadcasts-b.")

    # Persona ablation (Tier-P manipulation check).
    p.add_argument("--persona-mode", default=argparse.SUPPRESS,
                   dest="persona_mode",
                   choices=("real", "shuffled", "neutral"),
                   help="Persona ablation. 'real' (default) = each agent "
                        "keeps its own persona; 'shuffled' = each agent is "
                        "given another agent's whole persona; 'neutral' = "
                        "every agent gets a generic persona. Ground truth "
                        "is never altered.")

    # Political message pool.
    p.add_argument("--message-source", default=argparse.SUPPRESS,
                   dest="message_source",
                   choices=("offline", "llm"),
                   help="Source of political broadcast text. "
                        "Default = SIM_CONFIG (offline).")
    p.add_argument("--message-set", default=argparse.SUPPRESS,
                   dest="message_set",
                   help="Versioned offline message set under "
                        "data/political_messages/. "
                        "Default = SIM_CONFIG ('v1').")

    # Network.
    p.add_argument("--network-type", default=argparse.SUPPRESS,
                   dest="network_type",
                   help="Peer network factory key (stochastic_block / "
                        "watts_strogatz / barabasi_albert / erdos_renyi).")
    p.add_argument("--network-params", type=_json_dict,
                   default=argparse.SUPPRESS, dest="network_params",
                   help="JSON dict of per-factory parameters.")
    p.add_argument("--p-intra", type=float, default=argparse.SUPPRESS,
                   dest="p_intra",
                   help="Legacy stochastic-block intra-block edge probability.")
    p.add_argument("--p-inter", type=float, default=argparse.SUPPRESS,
                   dest="p_inter",
                   help="Legacy stochastic-block inter-block edge probability.")
    p.add_argument("--diagnostics-timeout", type=float,
                   default=argparse.SUPPRESS, dest="diagnostics_timeout",
                   help="Wall-clock cap (s) on the network diagnostics block.")

    # Checkpoint / resume.
    p.add_argument(
        "--checkpoint-every-day", dest="checkpoint_every_day",
        action=argparse.BooleanOptionalAction, default=True,
        help="After each day's manage_memory step, write the full CSV "
             "bundle to <outdir>/checkpoints/ so a killed job leaves "
             "the most recent completed day on disk. Default: ON. "
             "Use --no-checkpoint-every-day to disable.",
    )
    p.add_argument(
        "--resume", dest="resume", action="store_true",
        help="Resume from <outdir>/checkpoints/ (same --outdir as the "
             "killed run). Structural config keys must match the original.",
    )
    return p.parse_args(argv)


# ── Entry point ──────────────────────────────────────────────────
def _resolve_config(args):
    """Build the final SIM_CONFIG override dict from preset + CLI."""
    preset_dict = {}
    if args.preset:
        preset_dict = dict(RUN_BUNDLE_PRESETS[args.preset]["config"])
    cli_dict = _args_to_sim_dict(args)
    return build_config(preset_dict, cli_dict)


def _validate_required(config):
    """Run-sizing must come from either the preset or the CLI."""
    missing = [k for k in ("n_citizens", "days") if k not in config]
    if missing:
        raise SystemExit(
            f"error: missing required config key(s): {missing}. "
            f"Pass --n-citizens / --days, or select a --preset that supplies them."
        )


def _jsonable(v):
    """Best-effort coerce nested values to JSON-printable form for --dry-run."""
    if isinstance(v, list):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if hasattr(v, "value"):
        try:
            return int(v.value)
        except Exception:
            return repr(v)
    return v


def main(argv=None):
    overall_t0 = time.perf_counter()
    args = parse_args(argv)

    # Inspection-only paths: no I/O, no LLM, no logging setup.
    if args.list_presets:
        list_presets()
        return

    config = _resolve_config(args)

    if args.dry_run:
        _validate_required(config)
        preview = {k: _jsonable(v) for k, v in config.items()}
        print(json.dumps(preview, indent=2, default=str, sort_keys=True))
        return

    _validate_required(config)

    if args.outdir is None:
        raise SystemExit("error: --outdir is required for non-inspection runs.")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    log_file = outdir / "run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logging.info("--- Climate-Action-GABM v%s ---", __version__)
    if args.preset:
        logging.info("Preset: %s", args.preset)
    logging.info("Explicit overrides (preset + CLI):")
    for k in sorted(config):
        v = config[k]
        if k == "days" and isinstance(v, list):
            logging.info("  %-32s = <%d days>", k, len(v))
        else:
            logging.info("  %-32s = %r", k, v)
    logging.info("(Fully-resolved config printed by run_simulation below.)")
    logging.info("Output directory: %s", outdir.resolve())

    seed = config.get("random_seed", 42)
    random.seed(seed)

    # ── Stage 1: load + subsample survey data ────────────────────
    t0 = time.perf_counter()
    logging.info("Loading survey data from %s ...", args.data)
    data = load(args.data)
    data = data.sample(n=config["n_citizens"], random_state=seed).reset_index(drop=True)
    t_load = time.perf_counter() - t0
    logging.info("Sampled %d citizens [%.2fs]", len(data), t_load)

    # ── Stage 2: build the nation ────────────────────────────────
    t0 = time.perf_counter()
    logging.info("Building SurveyedNation ...")
    nation = build_nation(data)
    t_build = time.perf_counter() - t0
    logging.info("Nation ready: %d agents [%.2fs]",
                 len(nation.agents_active), t_build)

    # ── Stage 3: run the simulation ──────────────────────────────
    t0 = time.perf_counter()
    logging.info("Starting simulation ...")
    if args.resume:
        args.checkpoint_every_day = True
    checkpoint_dir = (
        outdir / "checkpoints" if args.checkpoint_every_day else None
    )
    if args.resume:
        logging.info("Resume mode: loading from %s", checkpoint_dir)
    results = run_simulation(
        config, nation,
        checkpoint_dir=checkpoint_dir,
        checkpoint_every_day=args.checkpoint_every_day,
        resume=args.resume,
    )
    t_sim = time.perf_counter() - t0
    logging.info("Simulation complete [%.1fs / %.1f min]",
                 t_sim, t_sim / 60.0)

    # ── Stage 4: save artefacts ──────────────────────────────────
    t0 = time.perf_counter()
    out_path = save_results(results, output_dir=str(outdir))
    plot_paths = save_result_plots(results, out_path)
    t_save = time.perf_counter() - t0
    logging.info("Artefacts saved to %s [%.2fs]", out_path, t_save)
    for plot_name, plot_path in plot_paths.items():
        logging.info("  plot %-28s -> %s", plot_name, plot_path)

    # ── Summary ──────────────────────────────────────────────────
    df = results["opinion_trajectories"]
    n_agents = df["agent_id"].nunique() if not df.empty else 0
    n_days = df["day"].nunique() if not df.empty else 0
    logging.info(
        "Trajectories: %d rows, %d agents, %d days, %d policies",
        len(df), n_agents, n_days,
        df["policy_id"].nunique() if not df.empty else 0,
    )

    overall = time.perf_counter() - overall_t0
    agent_days = max(n_agents * n_days, 1)
    logging.info("==================== TIMING ====================")
    logging.info("  data load        : %8.2fs", t_load)
    logging.info("  nation build     : %8.2fs", t_build)
    logging.info("  simulation       : %8.2fs  (%.1f min)", t_sim, t_sim / 60.0)
    logging.info("  save artefacts   : %8.2fs", t_save)
    logging.info("  ------------------------------------")
    logging.info("  TOTAL wall-clock : %8.2fs  (%.1f min)", overall, overall / 60.0)
    logging.info("  sim per agent-day: %8.2fs  (n_agents=%d x n_days=%d)",
                 t_sim / agent_days, n_agents, n_days)
    logging.info(
        "  estimate: a run of N agents x D days ~= %.2fs x N x D "
        "(plus ~%.0fs fixed setup)",
        t_sim / agent_days, t_load + t_build,
    )
    logging.info("================================================")


if __name__ == "__main__":
    main()
