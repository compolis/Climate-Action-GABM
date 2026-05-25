"""
Simulation runner for Climate-Action-GABM.
"""
from dataclasses import dataclass
import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from cag.abm.agent import PoliticalAgent
from cag.abm.attributes.opinion import (
    ALL_CLIMATE_POLICIES,
    ClimatePolicyID,
    PACKAGE_SCOPE,
    PRO_CLIMATE_INDEX_COLUMN,
    SURVEY_COLUMN_MAP,
    SURVEY_QUESTIONS,
    compute_package_index,
)
from cag.abm.political_messages import load_message_pool
from cag.io.llm import configure_local, load_api_key, ping_local


SIM_CONFIG = {
    "n_citizens": 100,
    # Default day plan is package-mode (alternating P-A/P-B order to
    # balance recency). No per-day ``policy`` key — that is single-policy
    # sugar and is silently ignored under ``communication_mode='package'``.
    "days": [
        {"phases": ["P-A", "P-B", "C"]},
        {"phases": ["P-B", "P-A", "C"]},
    ],
    "k_peers_per_day": 3,
    "network_type": "stochastic_block",
    # Per-type parameters for the pluggable network factory
    # (see cag.abm.networks). When None, builder defaults are used.
    # Legacy flat keys p_intra / p_inter / block_sizes are still read
    # for back-compat with stochastic_block.
    "network_params": None,
    "p_intra": 0.15,
    "p_inter": 0.02,
    "block_sizes": None,        # defaults to equal split
    # Wall-clock cap (seconds) for the conditional block of network
    # diagnostics (clustering / shortest-path / diameter). 0 or None
    # disables; per-metric size caps still apply.
    "diagnostics_timeout_s": 30.0,
    # Research-canon LLM defaults: local mlx_lm.server with Qwen3-8B-4bit.
    # API providers (openai / anthropic / google) remain supported as an
    # outsider option; override these two keys to use them.
    "llm_model": "mlx-community/Qwen3-8B-4bit",
    "llm_provider": "local",
    "llm_temperature": 0.5,
    "survey_model": None,       # override model for surveys (None → use llm_model)
    "survey_provider": None,    # override provider for surveys (None → use llm_provider)
    "thinking": False,
    # Research-canon since v0.3 (NB15 / Run 4): Condition B 2-step survey
    # to reduce LLM pro-climate bias on Day 0.
    "debias": True,
    # Research direction: all policies broadcast together each phase.
    "communication_mode": "package",
    "package_policies": ALL_CLIMATE_POLICIES,
    # Source of political-broadcast text. "offline" (default) pulls
    # pre-authored quotes/summaries from a versioned message set under
    # ``data/political_messages/``; "llm" generates messages live via the
    # configured LLM provider. There is no silent fallback: "offline" with
    # missing cells aborts the run at start.
    "political_message_source": "offline",
    "political_message_set": "v1",
    # Research canon: seed Day-0 numeric opinion from YouGov ground truth
    # (LLM only writes the rationale). Use "llm_survey" to preserve the
    # bias-measurement story (NB11-14) on new models.
    "day0_anchor": "ground_truth_with_rationale",
    "reach_a": 1.0,             # fraction of A-audience reached by political agent A broadcasts (0.0-1.0)
    "reach_b": 1.0,             # fraction of B-audience reached by political agent B broadcasts (0.0-1.0)
    "audience_cap": None,       # if int, cap each political agent's audience to this many citizens (uniform random) BEFORE reach subsample. None = no cap.
    # Political-exposure assignment. See cag.abm.environment for full
    # mode/preset semantics. Defaults: affinity-rank mode with the new
    # committed-minority symmetric target preset and the "balanced"
    # weight set.
    "political_exposure_mode": "rule_affinity_rank",
    "political_exposure_targets": None,       # None → committed_minority_symmetric. Accepts preset name or literal dict.
    "affinity_weights": None,                 # None → balanced. Accepts preset name or literal {"A":..., "B":...}.
    "random_seed": 42,
    "output_dir": "data/output/experiments",
    # Local-LLM provider (provider="local"). All optional.
    "local_base_url": None,     # None → CAG_LOCAL_BASE_URL env or http://localhost:8080/v1
    "local_extra_body": None,   # dict merged into every local request body (e.g. server-specific knobs)
    "local_timeout_s": None,    # None → CAG_LOCAL_TIMEOUT_S env or 600 s
}


VALID_DAY0_ANCHORS = ("llm_survey", "ground_truth", "ground_truth_with_rationale")


# Per-day phase-sugar keys understood by ``_resolve_day_phases``. Listed
# here so the validator can detect mixing with the canonical ``phases``
# key without depending on inspect.signature.
_PHASE_SUGAR_KEYS = (
    "broadcasts_a", "broadcasts_b", "peer", "interleave", "a_first",
)


def make_phases(broadcasts_a=1, broadcasts_b=1, peer=True,
                interleave=False, a_first=True):
    """Build a ``phases`` list from per-side broadcast counts.

    This is sugar over the canonical ``phases`` list consumed by
    :func:`_run_one_day`. The simulation loop iterates the produced list
    literally, so repeated entries (e.g. ``["P-A", "P-A", "P-B", "C"]``)
    cause the corresponding political agent to broadcast multiple times
    on the same day.

    Args:
        broadcasts_a: non-negative int. Number of P-A broadcasts.
        broadcasts_b: non-negative int. Number of P-B broadcasts.
        peer: if True, append a single ``"C"`` (peer-messaging) phase at
            the end.
        interleave: if True, interleave A and B broadcasts (A first when
            ``a_first`` is True). Leftovers from the longer side trail
            after the shorter side is exhausted. If False, all A
            broadcasts come first (or all B if ``a_first`` is False).
        a_first: ordering hint. With ``interleave=False`` decides whether
            P-A or P-B broadcasts come first; with ``interleave=True``
            decides which side leads the interleave.

    Returns:
        list[str] of phase tokens drawn from {"P-A", "P-B", "C"}.

    Examples:
        >>> make_phases()
        ['P-A', 'P-B', 'C']
        >>> make_phases(broadcasts_a=3)
        ['P-A', 'P-A', 'P-A', 'P-B', 'C']
        >>> make_phases(2, 1, interleave=True)
        ['P-A', 'P-B', 'P-A', 'C']
        >>> make_phases(broadcasts_b=0, peer=False)
        ['P-A']
    """
    for name, val in (("broadcasts_a", broadcasts_a),
                      ("broadcasts_b", broadcasts_b)):
        if isinstance(val, bool) or not isinstance(val, int) or val < 0:
            raise ValueError(
                f"{name} must be a non-negative int, got {val!r}"
            )
    for name, val in (("peer", peer), ("interleave", interleave),
                      ("a_first", a_first)):
        if not isinstance(val, bool):
            raise ValueError(f"{name} must be a bool, got {val!r}")

    phases = []
    if interleave:
        first, second = ("P-A", "P-B") if a_first else ("P-B", "P-A")
        n_first = broadcasts_a if a_first else broadcasts_b
        n_second = broadcasts_b if a_first else broadcasts_a
        for i in range(max(n_first, n_second)):
            if i < n_first:
                phases.append(first)
            if i < n_second:
                phases.append(second)
    else:
        if a_first:
            phases.extend(["P-A"] * broadcasts_a)
            phases.extend(["P-B"] * broadcasts_b)
        else:
            phases.extend(["P-B"] * broadcasts_b)
            phases.extend(["P-A"] * broadcasts_a)
    if peer:
        phases.append("C")
    return phases


def _resolve_day_phases(day_config):
    """Return the ``phases`` list for a day, expanding sugar keys.

    Precedence: an explicit ``"phases"`` key always wins. Otherwise, any
    of the keys in :data:`_PHASE_SUGAR_KEYS` are forwarded to
    :func:`make_phases`. Mixing canonical ``phases`` with sugar keys is
    rejected.
    """
    has_phases = "phases" in day_config
    sugar = {k: day_config[k] for k in _PHASE_SUGAR_KEYS if k in day_config}
    if has_phases and sugar:
        raise ValueError(
            "day_config cannot mix 'phases' with broadcast-frequency "
            f"sugar keys ({sorted(sugar)}); use one or the other."
        )
    if has_phases:
        return list(day_config["phases"])
    return make_phases(**sugar)


def _is_package_mode(config):
    return config.get("communication_mode") == "package"


def _get_package_policies(config):
    return config.get("package_policies") or ALL_CLIMATE_POLICIES


def _resolve_network_params(cfg):
    """Build the params dict for the network factory.

    Reads the new ``network_params`` dict if present; otherwise falls back
    to the legacy flat keys (``p_intra``, ``p_inter``) so existing
    configurations and notebooks keep working.
    """
    params = dict(cfg.get("network_params") or {})
    network_type = cfg.get("network_type", "stochastic_block")
    if network_type == "stochastic_block":
        for legacy_key in ("p_intra", "p_inter"):
            if legacy_key in cfg and legacy_key not in params:
                val = cfg.get(legacy_key)
                if val is not None:
                    params[legacy_key] = val
    return params


def _safe_network_diagnostics(nation, config):
    """Compute network diagnostics, swallowing any error so a long
    simulation never aborts at the reporting stage.

    Returns ``None`` only when there is no graph on the nation. Otherwise
    always returns a dict with the always-on cheap-metric keys present;
    on failure those keys are filled with ``None`` and an ``error`` field
    is attached so downstream consumers can rely on a stable shape.
    """
    G = getattr(nation, "network", None)
    if G is None:
        return None
    try:
        from cag.abm.networks import compute_diagnostics
        timeout = config.get("diagnostics_timeout_s", 30.0)
        diag = compute_diagnostics(
            G, agents=list(nation.agents_active.values()),
            timeout_s=timeout,
        )
        diag["network_type"] = getattr(nation, "network_type", config.get("network_type"))
        diag["network_params"] = getattr(nation, "network_params", None) \
            or _resolve_network_params(config)
        return diag
    except Exception as e:  # noqa: BLE001
        logging.warning("Network diagnostics failed: %s", e)
        return {
            "n_nodes": None,
            "n_edges": None,
            "density": None,
            "mean_degree": None,
            "median_degree": None,
            "max_degree": None,
            "degree_histogram": None,
            "n_connected_components": None,
            "largest_component_size": None,
            "assortativity_political_exposure": None,
            "timed_out": False,
            "network_type": getattr(nation, "network_type", config.get("network_type")),
            "network_params": getattr(nation, "network_params", None)
                or _resolve_network_params(config),
            "error": str(e),
        }


def _run_baseline_surveys(nation, policies, api_key, model, provider,
                          temperature, thinking, debias):
    for agent in nation.agents_active.values():
        for policy_id in policies:
            agent.administer_survey(
                policy_id,
                day=0,
                api_key=api_key,
                model=model,
                provider=provider,
                temperature=temperature,
                thinking=thinking,
                debias=debias,
            )


def _run_day0(nation, policies, anchor_mode, api_key, model, provider,
              temperature, thinking, debias):
    """Initialise Day 0 opinions according to the configured anchor mode.

    - ``llm_survey``: existing behaviour (administer the survey via LLM).
    - ``ground_truth``: seed opinion_history from the real survey response;
      no LLM call.
    - ``ground_truth_with_rationale``: seed from ground truth and ask the
      LLM to rationalise the position; rationale stored in survey_reasoning.
    """
    if anchor_mode == "llm_survey":
        _run_baseline_surveys(
            nation, policies, api_key, model, provider,
            temperature, thinking, debias,
        )
        return

    if debias:
        logging.info(
            "day0_anchor=%s: debias flag is ignored on Day 0 "
            "(still applies to end-of-day surveys).",
            anchor_mode,
        )

    for agent in nation.agents_active.values():
        for policy_id in policies:
            if anchor_mode == "ground_truth":
                agent.seed_opinion_from_ground_truth(policy_id, day=0)
            else:  # ground_truth_with_rationale
                agent.seed_opinion_with_rationale(
                    policy_id, day=0,
                    api_key=api_key, model=model, provider=provider,
                    temperature=temperature, thinking=thinking,
                )


def _log_package_index(nation, policies, day):
    package_indices = []
    for agent in nation.agents_active.values():
        numeric_values = []
        for policy_id in policies:
            history = agent.opinion_history.get(policy_id, [])
            if not history or history[-1][0] != day:
                numeric_values = []
                break
            numeric_values.append(history[-1][1])
        if numeric_values:
            package_indices.append(compute_package_index(numeric_values))
    if package_indices:
        mean_index = sum(package_indices) / len(package_indices)
        logging.info(f"Day {day} mean package index: {mean_index:+.2f}")


# ── Runtime resolution ──────────────────────────────────────────

def _resolve_runtime(cfg):
    """Resolve config into a flat runtime dict used by the daily loop."""
    provider = cfg["llm_provider"]
    survey_provider = cfg.get("survey_provider") or provider

    # Configure the local-LLM provider once per run, before any send_chat call.
    if "local" in (provider, survey_provider):
        configure_local(
            base_url=cfg.get("local_base_url"),
            extra_body=cfg.get("local_extra_body"),
            timeout_s=cfg.get("local_timeout_s"),
        )
        # Fail fast if the local server is unreachable.
        ping_local()

    api_key = load_api_key(provider)
    survey_api_key = (
        load_api_key(survey_provider) if survey_provider != provider else api_key
    )

    # Offline political-broadcast pool. Loaded once per run and validated
    # eagerly against the policies/sides the run will exercise so that any
    # missing cell aborts before the first API call.
    message_pool = None
    source = cfg.get("political_message_source", "offline")
    if source not in ("offline", "llm"):
        raise ValueError(
            f"political_message_source must be 'offline' or 'llm', "
            f"got {source!r}"
        )
    if source == "offline":
        message_pool = load_message_pool(
            cfg["political_message_set"],
            seed=cfg["random_seed"],
        )
        if _is_package_mode(cfg):
            policy_ids_for_validation = []
            include_package = True
        else:
            seen = []
            for day_cfg in cfg["days"]:
                pid = day_cfg.get("policy")
                if pid is not None and pid not in seen:
                    seen.append(pid)
            policy_ids_for_validation = seen
            include_package = False
        message_pool.validate_required(
            sides=("A", "B"),
            policy_ids=policy_ids_for_validation,
            include_package=include_package,
        )

    return {
        "api_key": api_key,
        "model": cfg["llm_model"],
        "provider": provider,
        "temperature": cfg["llm_temperature"],
        "thinking": cfg["thinking"],
        "debias": cfg["debias"],
        "k_peers": cfg["k_peers_per_day"],
        "survey_api_key": survey_api_key,
        "survey_model": cfg.get("survey_model") or cfg["llm_model"],
        "survey_provider": survey_provider,
        "package_mode": _is_package_mode(cfg),
        "package_policies": _get_package_policies(cfg),
        "message_pool": message_pool,
    }


def _run_one_day(nation, day, day_config, n_days, rt):
    """Run a single simulation day end-to-end (phases → EOD survey → memory)."""
    phases = _resolve_day_phases(day_config)
    package_mode = rt["package_mode"]
    package_policies = rt["package_policies"]

    if package_mode:
        logging.info(
            "--- Day %s/%s (package=%s, phases=%s) ---",
            day, n_days, PACKAGE_SCOPE, phases,
        )
    else:
        policy = day_config["policy"]
        logging.info(f"--- Day {day}/{n_days} (policy={policy}, phases={phases}) ---")

    for phase in phases:
        if package_mode:
            if phase in ("P-A", "P-B"):
                nation.run_package_broadcast(
                    phase, package_policies, day,
                    api_key=rt["api_key"], model=rt["model"],
                    provider=rt["provider"], temperature=rt["temperature"],
                    message_pool=rt["message_pool"],
                )
            elif phase == "C":
                nation.run_package_peer_messaging(
                    package_policies, day, k_peers=rt["k_peers"],
                    api_key=rt["api_key"], model=rt["model"],
                    provider=rt["provider"], temperature=rt["temperature"],
                )
            else:
                logging.warning(f"Unknown phase '{phase}' on day {day}, skipping.")
        else:
            if phase in ("P-A", "P-B"):
                nation.run_political_broadcast(
                    phase, policy, day,
                    api_key=rt["api_key"], model=rt["model"],
                    provider=rt["provider"], temperature=rt["temperature"],
                    message_pool=rt["message_pool"],
                )
            elif phase == "C":
                nation.run_peer_messaging(
                    policy, day, k_peers=rt["k_peers"],
                    api_key=rt["api_key"], model=rt["model"],
                    provider=rt["provider"], temperature=rt["temperature"],
                )
            else:
                logging.warning(f"Unknown phase '{phase}' on day {day}, skipping.")

    if package_mode:
        for policy_id in package_policies:
            nation.run_end_of_day_survey(
                policy_id, day,
                api_key=rt["survey_api_key"], model=rt["survey_model"],
                provider=rt["survey_provider"], temperature=rt["temperature"],
                thinking=rt["thinking"], debias=rt["debias"],
            )
    else:
        nation.run_end_of_day_survey(
            policy, day,
            api_key=rt["survey_api_key"], model=rt["survey_model"],
            provider=rt["survey_provider"], temperature=rt["temperature"],
            thinking=rt["thinking"], debias=rt["debias"],
        )

    for agent in nation.agents_active.values():
        if package_mode:
            agent.manage_memory(
                day, PACKAGE_SCOPE,
                api_key=rt["api_key"], model=rt["model"],
                provider=rt["provider"], temperature=rt["temperature"],
            )
        else:
            agent.manage_memory(
                day, policy,
                api_key=rt["api_key"], model=rt["model"],
                provider=rt["provider"], temperature=rt["temperature"],
            )

    if package_mode:
        _log_package_index(nation, package_policies, day)
    else:
        opinions = [
            agent.opinion_history[policy][-1][1]
            for agent in nation.agents_active.values()
            if policy in agent.opinion_history and agent.opinion_history[policy]
        ]
        if opinions:
            mean_op = sum(opinions) / len(opinions)
            logging.info(f"Day {day} mean opinion: {mean_op:+.2f}")


# ── Main simulation loop ────────────────────────────────────────

def run_simulation(config, nation, checkpoint_dir=None, resume=False,
                   checkpoint_every_day=False):
    """Run a full simulation and return results as a dict of DataFrames.

    Args:
        config: dict with simulation parameters (see SIM_CONFIG for keys).
            config["days"] is a list where each entry is either:
                {"policy": ClimatePolicyID, "phases": ["P-A", "P-B", "C"]}
            or, using the broadcast-frequency sugar (see
            :func:`make_phases`):
                {"policy": ClimatePolicyID, "broadcasts_a": 3,
                 "broadcasts_b": 1, "peer": True}
            ``phases`` and the sugar keys cannot be mixed in the same
            day entry.
        nation: a SurveyedNation with agents already loaded.
        checkpoint_dir: optional Path; directory to read/write per-day
            checkpoints. Required when ``resume=True`` or
            ``checkpoint_every_day=True``.
        resume: if True, hydrate agent + nation state from
            ``checkpoint_dir`` before running, skip Day 0, and continue
            day numbering from ``last_completed_day + 1``. Hard-fails if
            no checkpoint is found.
        checkpoint_every_day: if True, write a CSV checkpoint to
            ``checkpoint_dir`` after each day's ``manage_memory`` step.

    Returns:
        dict with simulation results (see ``_collect_results``).
    """
    cfg = {**SIM_CONFIG, **config}

    anchor_mode = cfg.get("day0_anchor", "llm_survey")
    if anchor_mode not in VALID_DAY0_ANCHORS:
        raise ValueError(
            f"day0_anchor must be one of {VALID_DAY0_ANCHORS}, got {anchor_mode!r}"
        )

    reach_a = cfg.get("reach_a", 1.0)
    reach_b = cfg.get("reach_b", 1.0)
    for name, val in (("reach_a", reach_a), ("reach_b", reach_b)):
        if not isinstance(val, (int, float)) or not (0.0 <= float(val) <= 1.0):
            raise ValueError(
                f"{name} must be a float in [0.0, 1.0], got {val!r}"
            )

    audience_cap = cfg.get("audience_cap", None)
    if audience_cap is not None and (
        not isinstance(audience_cap, int)
        or isinstance(audience_cap, bool)
        or audience_cap < 0
    ):
        raise ValueError(
            f"audience_cap must be a non-negative int or None, got {audience_cap!r}"
        )

    if (resume or checkpoint_every_day) and checkpoint_dir is None:
        raise ValueError(
            "checkpoint_dir is required when resume=True or "
            "checkpoint_every_day=True"
        )
    checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir is not None else None

    rt = _resolve_runtime(cfg)
    days = cfg["days"]
    n_days = len(days)

    # Setup deterministic structure (same on fresh run and on resume)
    nation.political_agent_a = PoliticalAgent("agent_a", "pro_climate")
    nation.political_agent_b = PoliticalAgent("agent_b", "anti_climate")
    nation.assign_political_exposure(
        mode=cfg.get("political_exposure_mode"),
        targets=cfg.get("political_exposure_targets"),
        weights=cfg.get("affinity_weights"),
        seed=cfg["random_seed"],
    )
    nation.apply_audience_cap(
        cap=audience_cap,
        seed=cfg["random_seed"],
    )
    nation.apply_reach_subsample(
        reach_a=float(reach_a),
        reach_b=float(reach_b),
        seed=cfg["random_seed"],
    )
    nation.create_network(
        network_type=cfg.get("network_type", "stochastic_block"),
        network_params=_resolve_network_params(cfg),
        seed=cfg["random_seed"],
    )
    nation.assign_network_blocks()

    n_agents = len(nation.agents_active)

    # Resume vs fresh start
    if resume:
        if checkpoint_dir is None or not (checkpoint_dir / "checkpoint_meta.json").exists():
            raise FileNotFoundError(
                f"resume=True but no checkpoint found at {checkpoint_dir}"
            )
        meta = _load_checkpoint_meta(checkpoint_dir)
        _validate_resume_config(meta, cfg, nation)
        last_day = _load_checkpoint(nation, checkpoint_dir)
        start_day_index = last_day  # next day to run is last_day + 1 (1-indexed)
        logging.info(
            f"Resuming from checkpoint at {checkpoint_dir} "
            f"(last completed day={last_day}); {n_agents} agents, "
            f"{n_days - start_day_index} day(s) remaining"
        )
    else:
        nation.message_log = []
        start_day_index = 0
        logging.info(f"Simulation: {n_agents} agents, {n_days} days")

        if not days:
            logging.warning("No days configured — nothing to simulate.")
            return _collect_results(nation, cfg)

        # Day 0
        if rt["package_mode"]:
            logging.info(
                "Running package baseline survey (day 0), policies=%s, anchor=%s",
                [str(policy_id) for policy_id in rt["package_policies"]],
                anchor_mode,
            )
            _run_day0(
                nation, rt["package_policies"], anchor_mode,
                rt["survey_api_key"], rt["survey_model"], rt["survey_provider"],
                rt["temperature"], rt["thinking"], rt["debias"],
            )
            _log_package_index(nation, rt["package_policies"], day=0)
        else:
            baseline_policy = days[0]["policy"]
            logging.info(
                f"Running baseline survey (day 0), policy={baseline_policy}, anchor={anchor_mode}"
            )
            _run_day0(
                nation, [baseline_policy], anchor_mode,
                rt["survey_api_key"], rt["survey_model"], rt["survey_provider"],
                rt["temperature"], rt["thinking"], rt["debias"],
            )

        if checkpoint_every_day:
            _write_checkpoint(nation, cfg, last_day=0, checkpoint_dir=checkpoint_dir)

    # Daily loop
    for day_index in range(start_day_index, n_days):
        day = day_index + 1
        _run_one_day(nation, day, days[day_index], n_days, rt)
        if checkpoint_every_day:
            _write_checkpoint(nation, cfg, last_day=day, checkpoint_dir=checkpoint_dir)

    return _collect_results(nation, cfg)


# ── Results collection ──────────────────────────────────────────

def _collect_results(nation, config):
    """Build DataFrames from agent state after simulation."""
    traj_rows = []
    package_rows = []
    ref_rows = []
    message_rows = []
    survey_reasoning_rows = []
    daily_summary_rows = []
    package_mode = _is_package_mode(config)
    package_policies = _get_package_policies(config) if package_mode else []
    agents = list(nation.agents_active.values())

    for event in getattr(nation, "message_log", []):
        policy_id = event.get("policy_id")
        policy_ids = event.get("policy_ids") or []
        message_rows.append({
            "day": event.get("day"),
            "phase": event.get("phase", ""),
            "message_type": event.get("message_type", ""),
            "sender_type": event.get("sender_type", ""),
            "sender_id": event.get("sender_id"),
            "sender_side": event.get("sender_side", ""),
            "recipient_id": event.get("recipient_id"),
            "recipient_scope": event.get("recipient_scope", ""),
            "policy_id": str(policy_id) if policy_id not in (None, "") else "",
            "package_scope": event.get("package_scope", ""),
            "policy_ids_json": json.dumps([str(pid) for pid in policy_ids]),
            "message_text": event.get("message_text", ""),
            "political_message_id": event.get("political_message_id", ""),
        })

    for agent in agents:
        for pid, history in agent.opinion_history.items():
            for day, numeric in history:
                traj_rows.append({
                    "agent_id": agent.id,
                    "day": day,
                    "policy_id": str(pid),
                    "numeric": numeric,
                })

        if package_mode:
            day_maps = {}
            for policy_id in package_policies:
                history = agent.opinion_history.get(policy_id, [])
                if not history:
                    day_maps = {}
                    break
                day_maps[policy_id] = {day: numeric for day, numeric in history}
            if day_maps:
                common_days = set.intersection(*(set(day_map.keys()) for day_map in day_maps.values()))
                for day in sorted(common_days):
                    numeric_values = [day_maps[policy_id][day] for policy_id in package_policies]
                    package_rows.append({
                        "agent_id": agent.id,
                        "day": day,
                        "index_name": PRO_CLIMATE_INDEX_COLUMN,
                        "package_scope": PACKAGE_SCOPE,
                        "package_index": compute_package_index(numeric_values),
                    })

        for policy_id, reasoning_entries in agent.survey_reasoning.items():
            for day, reasoning in reasoning_entries:
                survey_reasoning_rows.append({
                    "agent_id": agent.id,
                    "day": day,
                    "policy_id": str(policy_id),
                    "reasoning": reasoning,
                })

        for (day, policy_id), summary in agent.daily_summaries.items():
            daily_summary_rows.append({
                "agent_id": agent.id,
                "day": day,
                "policy_id": str(policy_id),
                "summary": summary,
            })

        for r in agent.reflections:
            policy_id = r.get("policy_id", "")
            policy_ids = r.get("policy_ids") or []
            messages_received = r.get("messages_received") or []
            ref_rows.append({
                "agent_id": agent.id,
                "day": r["day"],
                "phase": r["phase"],
                "policy_id": str(policy_id),
                "package_scope": PACKAGE_SCOPE if policy_id == PACKAGE_SCOPE else "",
                "policy_ids_json": json.dumps([str(pid) for pid in policy_ids]),
                "messages_received_json": json.dumps(messages_received),
                "messages_received_count": len(messages_received),
                "text": r["text"],
            })

    ground_truth_df = collect_ground_truth(agents)
    package_ground_truth_df = collect_package_ground_truth(agents)

    return {
        "opinion_trajectories": pd.DataFrame(
            traj_rows,
            columns=["agent_id", "day", "policy_id", "numeric"],
        ),
        "package_index_trajectories": pd.DataFrame(
            package_rows,
            columns=["agent_id", "day", "index_name", "package_scope", "package_index"],
        ),
        "reflections": pd.DataFrame(
            ref_rows,
            columns=[
                "agent_id",
                "day",
                "phase",
                "policy_id",
                "package_scope",
                "policy_ids_json",
                "messages_received_json",
                "messages_received_count",
                "text",
            ],
        ),
        "messages": pd.DataFrame(
            message_rows,
            columns=[
                "day",
                "phase",
                "message_type",
                "sender_type",
                "sender_id",
                "sender_side",
                "recipient_id",
                "recipient_scope",
                "policy_id",
                "package_scope",
                "policy_ids_json",
                "message_text",
                "political_message_id",
            ],
        ),
        "survey_reasoning": pd.DataFrame(
            survey_reasoning_rows,
            columns=["agent_id", "day", "policy_id", "reasoning"],
        ),
        "daily_summaries": pd.DataFrame(
            daily_summary_rows,
            columns=["agent_id", "day", "policy_id", "summary"],
        ),
        "ground_truth": ground_truth_df,
        "package_ground_truth": package_ground_truth_df,
        "config": config,
        "network_diagnostics": _safe_network_diagnostics(nation, config),
    }


def collect_ground_truth(agents, policy_ids=None):
    """Extract real survey responses for agents into a DataFrame.

    Args:
        agents: iterable of SurveyedCitizen instances.
        policy_ids: optional list of ClimatePolicyID.  If *None*, all
            policies in SURVEY_COLUMN_MAP are included.

    Returns:
        DataFrame with columns ``agent_id``, ``policy_id``, ``ground_truth``.
    """
    if policy_ids is None:
        policy_ids = list(SURVEY_COLUMN_MAP.keys())
    rows = []
    for agent in agents:
        for pid in policy_ids:
            rows.append({
                "agent_id": agent.id,
                "policy_id": str(pid),
                "ground_truth": agent.get_real_survey_response(pid),
            })
    return pd.DataFrame(rows, columns=["agent_id", "policy_id", "ground_truth"])


def collect_package_ground_truth(agents):
    """Extract the real package-level climate support index for each agent.

    Returns:
        DataFrame with columns ``agent_id``, ``index_name``, ``ground_truth``.
    """
    rows = []
    for agent in agents:
        if hasattr(agent, "get_real_package_index"):
            ground_truth = agent.get_real_package_index()
        else:
            numeric_values = [
                agent.get_real_survey_response(policy_id)
                for policy_id in ALL_CLIMATE_POLICIES
            ]
            ground_truth = compute_package_index(numeric_values)
        rows.append({
            "agent_id": agent.id,
            "index_name": PRO_CLIMATE_INDEX_COLUMN,
            "ground_truth": ground_truth,
        })
    return pd.DataFrame(rows, columns=["agent_id", "index_name", "ground_truth"])


# ── Output ──────────────────────────────────────────────────────

# Schema columns for each result CSV. Used by both save_results (final
# canonical output) and the per-day checkpoint writer/loader so the two
# stay in lockstep.
_RESULT_CSV_SCHEMAS = {
    "opinion_trajectories": ["agent_id", "day", "policy_id", "numeric"],
    "package_index_trajectories": [
        "agent_id", "day", "index_name", "package_scope", "package_index",
    ],
    "reflections": [
        "agent_id", "day", "phase", "policy_id", "package_scope",
        "policy_ids_json", "messages_received_json",
        "messages_received_count", "text",
    ],
    "messages": [
        "day", "phase", "message_type", "sender_type", "sender_id",
        "sender_side", "recipient_id", "recipient_scope", "policy_id",
        "package_scope", "policy_ids_json", "message_text",
        "political_message_id",
    ],
    "survey_reasoning": ["agent_id", "day", "policy_id", "reasoning"],
    "daily_summaries": ["agent_id", "day", "policy_id", "summary"],
    "ground_truth": ["agent_id", "policy_id", "ground_truth"],
    "package_ground_truth": ["agent_id", "index_name", "ground_truth"],
}


def _atomic_write_csv(df, path):
    """Write a DataFrame to ``path`` atomically (temp file + os.replace)."""
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def _atomic_write_json(obj, path):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)


def _write_all_csvs(out_path, results):
    """Write every result CSV (atomic per file). Returns dict of paths written."""
    out_path = Path(out_path)
    out_path.mkdir(parents=True, exist_ok=True)
    written = {}

    for key, columns in _RESULT_CSV_SCHEMAS.items():
        df = results.get(key)
        if df is None:
            df = pd.DataFrame(columns=columns)
        # Skip empty package frames to keep single-policy run dirs tidy.
        if key in ("package_index_trajectories", "package_ground_truth") and df.empty:
            continue
        path = out_path / f"{key}.csv"
        _atomic_write_csv(df, path)
        written[key] = path

    # Derived share frames (canonical end-of-run only); cheap to recompute.
    opinion_traj = results.get("opinion_trajectories")
    if opinion_traj is not None:
        _atomic_write_csv(
            build_opinion_shares({"opinion_trajectories": opinion_traj}),
            out_path / "opinion_shares.csv",
        )
    package_traj = results.get("package_index_trajectories")
    if package_traj is not None and not package_traj.empty:
        _atomic_write_csv(
            build_package_index_shares({"package_index_trajectories": package_traj}),
            out_path / "package_index_shares.csv",
        )

    return written


def save_results(results, output_dir="data/output/experiments"):
    """Save simulation results to a timestamped directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(output_dir) / timestamp
    out_path.mkdir(parents=True, exist_ok=True)

    _write_all_csvs(out_path, results)

    # Serialise config (convert enums and lists of dicts to strings)
    config_serialisable = _serialise_config(results["config"])
    _atomic_write_json(config_serialisable, out_path / "config.json")

    # Network diagnostics (if a graph was attached to the results dict)
    diagnostics = results.get("network_diagnostics")
    if diagnostics is not None:
        _atomic_write_json(diagnostics, out_path / "network_diagnostics.json")

    logging.info(f"Results saved to {out_path}")
    return out_path


# ── Checkpointing ───────────────────────────────────────────────

CHECKPOINT_SCHEMA_VERSION = 1

# Config keys whose change must abort a resume (would silently corrupt
# the simulation if mismatched against the saved state).
# Note: ``p_intra`` and ``p_inter`` are *not* listed here — they are folded
# into the resolved ``network_params`` dict by ``_resolve_network_params``
# and compared in resolved form by ``_validate_resume_config`` so that
# upgrading a config from flat legacy keys to ``network_params={...}``
# (or vice versa) does not trigger a spurious resume mismatch.
_RESUME_HARD_KEYS = (
    "n_citizens", "random_seed", "network_type",
    "communication_mode", "package_policies", "day0_anchor",
    "reach_a", "reach_b", "audience_cap",
    "political_exposure_mode", "political_exposure_targets",
    "affinity_weights",
    "political_message_source", "political_message_set",
)
# Config keys we tolerate changing on resume but log a warning for.
_RESUME_SOFT_KEYS = (
    "llm_model", "llm_provider", "survey_model", "survey_provider",
    "debias", "thinking", "llm_temperature",
    "local_base_url", "local_extra_body", "local_timeout_s",
)


def _config_hash(serialised_config):
    """Stable hash of a serialised config dict for fingerprinting."""
    blob = json.dumps(serialised_config, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()


def _write_checkpoint(nation, cfg, last_day, checkpoint_dir):
    """Write a per-day checkpoint to ``checkpoint_dir`` (atomic)."""
    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    results = _collect_results(nation, cfg)
    _write_all_csvs(checkpoint_dir, results)

    serialised = _serialise_config(cfg)
    meta = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "last_completed_day": int(last_day),
        # Sort by string form for stable on-disk fingerprint across runs
        # whose agent IDs may be a mix of ints / floats / strings.
        "agent_ids": sorted(
            (str(aid) for aid in nation.agents_active.keys()),
        ),
        "config": serialised,
        "config_hash": _config_hash(serialised),
        "written_at": datetime.now().isoformat(timespec="seconds"),
    }
    _atomic_write_json(meta, checkpoint_dir / "checkpoint_meta.json")
    logging.info(
        f"Checkpoint written for day {last_day} to {checkpoint_dir}"
    )


def _load_checkpoint_meta(checkpoint_dir):
    with open(Path(checkpoint_dir) / "checkpoint_meta.json") as f:
        meta = json.load(f)
    if meta.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError(
            f"Incompatible checkpoint schema version "
            f"{meta.get('schema_version')!r} (expected "
            f"{CHECKPOINT_SCHEMA_VERSION}). Re-run from scratch."
        )
    return meta


def _validate_resume_config(meta, cfg, nation):
    """Hard-fail on incompatible config; warn on soft-key changes."""
    saved = meta["config"]
    new = _serialise_config(cfg)

    # Hard keys: structural, must match exactly.
    for key in _RESUME_HARD_KEYS:
        if saved.get(key) != new.get(key):
            raise ValueError(
                f"Cannot resume: config key '{key}' changed "
                f"(checkpoint={saved.get(key)!r}, new={new.get(key)!r}). "
                f"This would invalidate prior agent state."
            )

    # Network params: compared in *resolved* form so that a config which
    # previously used legacy flat keys (``p_intra``/``p_inter``) and is
    # later upgraded to ``network_params={...}`` (or vice versa) is not
    # rejected for a difference that has no effect on the actual graph.
    saved_net = _resolve_network_params(saved)
    new_net = _resolve_network_params(new)
    if saved_net != new_net:
        raise ValueError(
            f"Cannot resume: resolved network parameters changed "
            f"(checkpoint={saved_net!r}, new={new_net!r}). "
            f"This would invalidate the peer network."
        )

    # Days schedule: the new config must extend (or match) the checkpoint's
    # already-completed prefix. We allow future days to grow / change, but
    # the past is immutable.
    last_completed = int(meta.get("last_completed_day", 0))
    saved_days = saved.get("days") or []
    new_days = new.get("days") or []
    if last_completed > len(new_days):
        raise ValueError(
            f"Cannot resume: checkpoint completed through day "
            f"{last_completed} but new config only declares "
            f"{len(new_days)} day(s). The new config must extend (or "
            f"match) the checkpoint's day schedule."
        )
    if saved_days[:last_completed] != new_days[:last_completed]:
        raise ValueError(
            f"Cannot resume: cfg['days'][0:{last_completed}] differs "
            f"from the checkpoint's already-completed schedule. Past "
            f"days are immutable; only future entries may be added or "
            f"modified."
        )

    # Agent ID set must match.
    saved_ids = set(meta.get("agent_ids", []))
    current_ids = {str(aid) for aid in nation.agents_active.keys()}
    if saved_ids != current_ids:
        missing = saved_ids - current_ids
        extra = current_ids - saved_ids
        raise ValueError(
            f"Cannot resume: active agent set differs from checkpoint. "
            f"Missing: {sorted(missing)[:5]}{'...' if len(missing) > 5 else ''}, "
            f"Extra: {sorted(extra)[:5]}{'...' if len(extra) > 5 else ''}"
        )

    # Soft keys: warn only.
    for key in _RESUME_SOFT_KEYS:
        if saved.get(key) != new.get(key):
            logging.warning(
                "Resume: config key '%s' changed "
                "(checkpoint=%r, new=%r). Proceeding, but downstream "
                "analysis must account for this.",
                key, saved.get(key), new.get(key),
            )


def _load_checkpoint(nation, checkpoint_dir):
    """Hydrate ``nation`` and its agents from a checkpoint dir.

    Returns the ``last_completed_day`` from the checkpoint metadata.
    """
    checkpoint_dir = Path(checkpoint_dir)
    meta = _load_checkpoint_meta(checkpoint_dir)
    last_day = int(meta["last_completed_day"])

    # Build a str(policy_id) -> policy_id lookup so reloaded CSV strings
    # become the same ClimatePolicyID objects used by live code. Agents
    # key opinion_history / daily_summaries / survey_reasoning by the
    # enum object, not its str repr; mixing the two would silently create
    # parallel entries on the next day.
    policy_lookup = {str(pid): pid for pid in ALL_CLIMATE_POLICIES}
    policy_lookup[PACKAGE_SCOPE] = PACKAGE_SCOPE
    policy_lookup[""] = ""

    def _to_policy(value):
        # NaN can leak in from pd.read_csv on optional / package-mode columns
        # (e.g. messages.csv policy_id is empty in package mode). Without this
        # guard, str(NaN) -> 'nan' would propagate as a fake policy id and
        # poison opinion_history / message_log keys, getting strictly worse on
        # every resume cycle.
        if value is None or value == "" or (
            isinstance(value, float) and pd.isna(value)
        ):
            return ""
        return policy_lookup.get(str(value), str(value))

    def _str(value):
        """Coerce optional string-typed cells to '' (NaN/None -> '')."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return ""
        return value

    # Index agents by str(id) so loaded CSV ids (which may be float-stringified)
    # round-trip back to the original keys in agents_active.
    by_id = {str(aid): agent for aid, agent in nation.agents_active.items()}

    # Reset agent mutable state before hydration so re-loading is idempotent.
    for agent in by_id.values():
        agent.opinion_history = {}
        agent.reflections = []
        agent.daily_summaries = {}
        agent.survey_reasoning = {}

    def _read(name):
        path = checkpoint_dir / f"{name}.csv"
        if not path.exists():
            return pd.DataFrame(columns=_RESULT_CSV_SCHEMAS[name])
        df = pd.read_csv(path)
        # Replace NaN with None across the frame so str()/json.loads/dict-keys
        # don't see literal 'nan' or float NaN downstream. Critical for
        # messages.csv where package mode leaves policy_id empty.
        return df.where(pd.notna(df), None)

    # opinion_history
    opin = _read("opinion_trajectories")
    for row in opin.itertuples(index=False):
        agent = by_id.get(str(row.agent_id))
        if agent is None:
            continue
        pid = _to_policy(row.policy_id)
        agent.opinion_history.setdefault(pid, []).append(
            (int(row.day), int(row.numeric))
        )

    # reflections
    refl = _read("reflections")
    for row in refl.itertuples(index=False):
        agent = by_id.get(str(row.agent_id))
        if agent is None:
            continue
        try:
            messages_received = json.loads(row.messages_received_json)
        except (TypeError, ValueError):
            messages_received = []
        try:
            policy_ids = json.loads(row.policy_ids_json)
        except (TypeError, ValueError):
            policy_ids = []
        entry = {
            "day": int(row.day),
            "phase": row.phase,
            "policy_id": _to_policy(row.policy_id),
            "text": row.text,
            "messages_received": messages_received,
        }
        if policy_ids:
            entry["policy_ids"] = [_to_policy(p) for p in policy_ids]
        agent.reflections.append(entry)

    # daily_summaries
    summ = _read("daily_summaries")
    for row in summ.itertuples(index=False):
        agent = by_id.get(str(row.agent_id))
        if agent is None:
            continue
        agent.daily_summaries[(int(row.day), _to_policy(row.policy_id))] = row.summary

    # survey_reasoning
    sreas = _read("survey_reasoning")
    for row in sreas.itertuples(index=False):
        agent = by_id.get(str(row.agent_id))
        if agent is None:
            continue
        agent.survey_reasoning.setdefault(_to_policy(row.policy_id), []).append(
            (int(row.day), row.reasoning)
        )

    # nation.message_log
    msgs = _read("messages")
    nation.message_log = []
    for row in msgs.itertuples(index=False):
        try:
            policy_ids = json.loads(row.policy_ids_json)
        except (TypeError, ValueError):
            policy_ids = []
        nation.message_log.append({
            "day": int(row.day) if pd.notna(row.day) else None,
            "phase": _str(row.phase),
            "message_type": _str(row.message_type),
            "sender_type": _str(row.sender_type),
            "sender_id": row.sender_id,
            "sender_side": _str(row.sender_side),
            "policy_id": _to_policy(row.policy_id),
            "package_scope": _str(row.package_scope),
            "policy_ids": [_to_policy(p) for p in policy_ids],
            "recipient_id": row.recipient_id,
            "recipient_scope": _str(row.recipient_scope),
            "message_text": _str(row.message_text),
            "political_message_id": _str(getattr(row, "political_message_id", "")),
        })

    return last_day


def _serialise_config(config):
    """Make config JSON-safe by converting enums to strings."""
    out = {}
    for k, v in config.items():
        if isinstance(v, ClimatePolicyID):
            out[k] = str(v)
        elif isinstance(v, list) and v and all(isinstance(item, ClimatePolicyID) for item in v):
            out[k] = [str(item) for item in v]
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            # days list — convert policy enums inside each entry
            out[k] = [
                {dk: str(dv) if isinstance(dv, ClimatePolicyID) else dv
                 for dk, dv in entry.items()}
                for entry in v
            ]
        else:
            out[k] = v
    return out


def _policy_short_names():
    """Build a policy_id -> readable short name lookup."""
    return {
        str(ClimatePolicyID.RENEWABLE_ENERGY): "Renewable Energy",
        str(ClimatePolicyID.BAN_FOSSIL_FUEL): "Ban Fossil Fuels",
        str(ClimatePolicyID.BAN_PETROL_CARS): "Ban Petrol Cars",
        str(ClimatePolicyID.GREEN_HOUSING): "Green Housing",
        str(ClimatePolicyID.CARBON_TAX): "Carbon Tax",
        str(ClimatePolicyID.CLIMATE_COMPENSATION): "Climate Compensation",
    }


def build_opinion_shares(results):
    """Aggregate support, neutral, and against shares by policy and day."""
    columns = [
        "policy_id",
        "day",
        "n_agents",
        "n_support",
        "support_pct",
        "n_neutral",
        "neutral_pct",
        "n_against",
        "against_pct",
    ]
    df = results.get("opinion_trajectories")
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)

    share_df = (
        df.groupby(["policy_id", "day"])
        .agg(
            n_agents=("agent_id", "count"),
            n_support=("numeric", lambda values: int((values > 0).sum())),
            n_neutral=("numeric", lambda values: int((values == 0).sum())),
            n_against=("numeric", lambda values: int((values < 0).sum())),
        )
        .reset_index()
        .sort_values(["policy_id", "day"])
    )

    share_df["support_pct"] = share_df["n_support"] / share_df["n_agents"] * 100.0
    share_df["neutral_pct"] = share_df["n_neutral"] / share_df["n_agents"] * 100.0
    share_df["against_pct"] = share_df["n_against"] / share_df["n_agents"] * 100.0
    return share_df[columns]


def build_package_index_shares(results):
    """Aggregate support, neutral, and against shares for the package index by day."""
    columns = [
        "day",
        "index_name",
        "package_scope",
        "n_agents",
        "n_support",
        "support_pct",
        "n_neutral",
        "neutral_pct",
        "n_against",
        "against_pct",
    ]
    df = results.get("package_index_trajectories")
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)

    share_df = (
        df.groupby(["day", "index_name", "package_scope"])
        .agg(
            n_agents=("agent_id", "count"),
            n_support=("package_index", lambda values: int((values > 0).sum())),
            n_neutral=("package_index", lambda values: int(np.isclose(values, 0.0).sum())),
            n_against=("package_index", lambda values: int((values < 0).sum())),
        )
        .reset_index()
        .sort_values(["day", "index_name", "package_scope"])
    )

    share_df["support_pct"] = share_df["n_support"] / share_df["n_agents"] * 100.0
    share_df["neutral_pct"] = share_df["n_neutral"] / share_df["n_agents"] * 100.0
    share_df["against_pct"] = share_df["n_against"] / share_df["n_agents"] * 100.0
    return share_df[columns]


def plot_opinion_trajectories(results, output_path=None):
    """Plot opinion trajectories over time."""
    import matplotlib.pyplot as plt

    df = results["opinion_trajectories"]
    if df.empty:
        logging.warning("No opinion data to plot.")
        return

    policies = df["policy_id"].unique()
    n_policies = len(policies)
    ncols = min(n_policies, 3)
    nrows = (n_policies + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows), squeeze=False)

    policy_names = _policy_short_names()

    for i, pid in enumerate(policies):
        ax = axes[i // ncols, i % ncols]
        pdf = df[df["policy_id"] == pid]

        for agent_id in pdf["agent_id"].unique():
            agent_data = pdf[pdf["agent_id"] == agent_id].sort_values("day")
            ax.plot(agent_data["day"], agent_data["numeric"],
                    alpha=0.15, color="steelblue", linewidth=0.8)

        mean = pdf.groupby("day")["numeric"].mean()
        ax.plot(mean.index, mean.values, color="black", linewidth=2, label="Mean")

        ax.set_xlabel("Day")
        ax.set_ylabel("Opinion (-3 to +3)")
        ax.set_ylim(-3.5, 3.5)
        ax.set_title(policy_names.get(pid, str(pid))[:50])
        ax.legend()

    # Hide unused subplots
    for i in range(n_policies, nrows * ncols):
        axes[i // ncols, i % ncols].set_visible(False)

    fig.suptitle("Opinion Trajectories", fontsize=13)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()

    return fig


def plot_opinion_shares(results, output_path=None):
    """Plot support, neutral, and against shares over time."""
    import matplotlib.pyplot as plt

    share_df = build_opinion_shares(results)
    if share_df.empty:
        logging.warning("No opinion share data to plot.")
        return

    policies = share_df["policy_id"].unique()
    n_policies = len(policies)
    ncols = min(n_policies, 3)
    nrows = (n_policies + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows), squeeze=False)
    policy_names = _policy_short_names()

    for i, pid in enumerate(policies):
        ax = axes[i // ncols, i % ncols]
        pdf = share_df[share_df["policy_id"] == pid].sort_values("day")

        ax.plot(pdf["day"], pdf["support_pct"], color="forestgreen", linewidth=2, marker="o", label="Support (+1 to +3)")
        ax.plot(pdf["day"], pdf["neutral_pct"], color="dimgray", linewidth=2, marker="o", label="Neutral (0)")
        ax.plot(pdf["day"], pdf["against_pct"], color="firebrick", linewidth=2, marker="o", label="Against (-3 to -1)")

        ax.set_xlabel("Day")
        ax.set_ylabel("Share of agents (%)")
        ax.set_ylim(0, 100)
        ax.set_title(policy_names.get(pid, str(pid))[:50])
        ax.legend()

    for i in range(n_policies, nrows * ncols):
        axes[i // ncols, i % ncols].set_visible(False)

    fig.suptitle("Opinion Shares", fontsize=13)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()

    return fig


def plot_package_index_trajectories(results, output_path=None):
    """Plot package-index trajectories over time when package data is present."""
    import matplotlib.pyplot as plt

    df = results.get("package_index_trajectories")
    if df is None or df.empty:
        logging.warning("No package index data to plot.")
        return

    fig, ax = plt.subplots(figsize=(8, 5))

    for agent_id in df["agent_id"].unique():
        agent_data = df[df["agent_id"] == agent_id].sort_values("day")
        ax.plot(
            agent_data["day"],
            agent_data["package_index"],
            alpha=0.15,
            color="steelblue",
            linewidth=0.8,
        )

    mean = df.groupby("day")["package_index"].mean()
    ax.plot(mean.index, mean.values, color="black", linewidth=2, label="Mean")

    package_ground_truth_df = results.get("package_ground_truth")
    if package_ground_truth_df is not None and not package_ground_truth_df.empty:
        gt_mean = package_ground_truth_df["ground_truth"].mean()
        ax.axhline(
            gt_mean,
            color="red",
            linestyle="--",
            linewidth=1.5,
            label=f"Ground truth mean ({gt_mean:+.2f})",
        )

    ax.set_xlabel("Day")
    ax.set_ylabel("Package index (-3 to +3)")
    ax.set_ylim(-3.5, 3.5)
    ax.set_title("Package Index Trajectory")
    ax.legend()
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()

    return fig


def plot_package_index_shares(results, output_path=None):
    """Plot support, neutral, and against shares for the package index over time."""
    import matplotlib.pyplot as plt

    share_df = build_package_index_shares(results)
    if share_df.empty:
        logging.warning("No package index share data to plot.")
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    pdf = share_df.sort_values("day")

    ax.plot(pdf["day"], pdf["support_pct"], color="forestgreen", linewidth=2, marker="o", label="Support (> 0)")
    ax.plot(pdf["day"], pdf["neutral_pct"], color="dimgray", linewidth=2, marker="o", label="Neutral (0)")
    ax.plot(pdf["day"], pdf["against_pct"], color="firebrick", linewidth=2, marker="o", label="Against (< 0)")

    ax.set_xlabel("Day")
    ax.set_ylabel("Share of agents (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Package Index Shares")
    ax.legend()
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()

    return fig


def save_result_plots(results, out_path):
    """Write the standard PNG outputs for a completed run."""
    out_path = Path(out_path)
    plot_paths = {}

    trajectory_plot_path = out_path / "opinion_trajectories.png"
    if plot_opinion_trajectories(results, output_path=trajectory_plot_path) is not None:
        plot_paths["opinion_trajectories"] = trajectory_plot_path

    shares_plot_path = out_path / "opinion_shares.png"
    if plot_opinion_shares(results, output_path=shares_plot_path) is not None:
        plot_paths["opinion_shares"] = shares_plot_path

    package_plot_path = out_path / "package_index_trajectories.png"
    if plot_package_index_trajectories(results, output_path=package_plot_path) is not None:
        plot_paths["package_index_trajectories"] = package_plot_path

    package_shares_plot_path = out_path / "package_index_shares.png"
    if plot_package_index_shares(results, output_path=package_shares_plot_path) is not None:
        plot_paths["package_index_shares"] = package_shares_plot_path

    return plot_paths
