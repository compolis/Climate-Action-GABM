"""
Simulation runner for Climate-Action-GABM.
"""
from dataclasses import dataclass
import hashlib
import json
import logging
import math
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
    # p_inter raised from 0.02 to 0.05 (v0.6, 2026-06-22) so the
    # within/cross block ratio is 3:1 (~25% cross-cutting exposure),
    # matching Bakshy et al. 2015 (Facebook ~24%) and Halberstam & Knight
    # 2016 (Twitter ~18-26%). The old 7.5:1 ratio gave only ~12%
    # cross-cutting, below all major empirical estimates, and produced
    # disconnected networks on small populations (n<100).
    "p_inter": 0.05,
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
    # Per-agent diagnostic timeline. Writes `agent_timeline.csv` listing
    # every event a sampled agent experienced (broadcasts received,
    # reflections, peer messages sent/received, the EXACT assembled survey
    # context, debias trace, daily summaries) in true execution order.
    # Final-output only (not checkpointed). See `build_agent_timeline`.
    "timeline_sample_size": 3,        # int >= 0; 0 disables the timeline
    "timeline_sample_agent_ids": None,  # None → auto-stratified by bucket; else list of agent IDs
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


def _adjust_network_params_for_small_n(cfg, n_agents):
    """Layer 1: bump network params to reduce disjoint-graph risk on small n.

    Only raises values; never lowers. Logs every adjustment. Skips
    network types that are always connected by construction
    (watts_strogatz, barabasi_albert).

    SBM thresholds (empirical sweep, p_intra=0.15, 100 trials):
      - n<30:        ~0% connectivity even at p_inter=0.15 -> bump to 0.10 + warn
      - n in [30,100): p_inter=0.05 gives ~80%, 0.06 gives ~89%
      - n>=100:      p_inter=0.05 gives 100% connectivity

    ER thresholds (classical ln(n)/n):
      - n=30  -> 0.113
      - n=50  -> 0.078
      - n=100 -> 0.046
    """
    network_type = cfg.get("network_type", "stochastic_block")
    if network_type in ("watts_strogatz", "barabasi_albert"):
        return  # always connected by construction

    params = dict(cfg.get("network_params") or {})

    if network_type == "stochastic_block":
        current_p_inter = float(
            params.get("p_inter", cfg.get("p_inter", 0.05))
        )
        if n_agents < 30:
            target = 0.10
            if current_p_inter < target:
                logging.warning(
                    "Small population (n=%d): 2-block SBM is unreliable. "
                    "Bumping p_inter %.3f -> %.3f. Consider n>=50 or "
                    "network_type='barabasi_albert'.",
                    n_agents, current_p_inter, target,
                )
                cfg["p_inter"] = target
                params["p_inter"] = target
                cfg["network_params"] = params
        elif n_agents < 100:
            target = 0.06
            if current_p_inter < target:
                logging.info(
                    "Small population (n=%d): bumping p_inter %.3f -> %.3f "
                    "to keep SBM connected (~90%% probability).",
                    n_agents, current_p_inter, target,
                )
                cfg["p_inter"] = target
                params["p_inter"] = target
                cfg["network_params"] = params

    elif network_type == "erdos_renyi":
        current_p = float(params.get("p", 0.10))
        if n_agents < 30:
            target = 0.20
            if current_p < target:
                logging.warning(
                    "Small population (n=%d): Erdos-Renyi connectivity "
                    "threshold is %.3f. Bumping p %.3f -> %.3f.",
                    n_agents, math.log(max(n_agents, 2)) / max(n_agents, 2),
                    current_p, target,
                )
                params["p"] = target
                cfg["network_params"] = params
        elif n_agents < 100:
            target = 0.10
            if current_p < target:
                logging.info(
                    "Small population (n=%d): bumping ER p %.3f -> %.3f "
                    "to stay well above connectivity threshold.",
                    n_agents, current_p, target,
                )
                params["p"] = target
                cfg["network_params"] = params


def _auto_connect_components(nation, seed):
    """Layer 2: if the network is disjoint, add the minimum bridging edges.

    Adds one deterministic edge per smaller component, connecting it to
    the largest component. Sets ``nation._auto_connected_edges`` to the
    number of edges added (0 if the graph was already connected).
    Logs a WARNING when repair is needed so the run is transparent.
    """
    import networkx as nx

    G = getattr(nation, "network", None)
    if not isinstance(G, nx.Graph) or G.number_of_nodes() == 0:
        nation._auto_connected_edges = 0
        return

    if nx.is_connected(G):
        nation._auto_connected_edges = 0
        return

    components = sorted(
        (sorted(c) for c in nx.connected_components(G)),
        key=lambda c: (-len(c), c[0]),  # largest first; tie-break for determinism
    )
    largest = components[0]
    rng = np.random.default_rng(seed)

    n_added = 0
    for comp in components[1:]:
        u_idx = int(rng.integers(0, len(largest)))
        v_idx = int(rng.integers(0, len(comp)))
        u = largest[u_idx]
        v = comp[v_idx]
        G.add_edge(u, v)
        n_added += 1

    # Refresh each agent's network_neighbors so peer messaging picks up
    # the new edges. assign_network_blocks() populates from G's adjacency.
    if hasattr(nation, "assign_network_blocks"):
        nation.assign_network_blocks()

    nation._auto_connected_edges = n_added
    logging.warning(
        "Network was disjoint (%d components, largest=%d/%d nodes). "
        "Auto-connected by adding %d bridging edge(s) (seed=%d).",
        len(components), len(largest), G.number_of_nodes(), n_added, seed,
    )


def _log_network_summary(nation):
    """Layer 3: one-line stdout summary after network setup is final."""
    import networkx as nx

    G = getattr(nation, "network", None)
    if not isinstance(G, nx.Graph) or G.number_of_nodes() == 0:
        return
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    n_comp = nx.number_connected_components(G)
    mean_deg = (2 * n_edges) / n_nodes if n_nodes else 0.0
    auto_added = getattr(nation, "_auto_connected_edges", 0)
    logging.info(
        "Network: n_nodes=%d, n_edges=%d, n_components=%d, "
        "mean_degree=%.2f, auto_connected_edges=%d",
        n_nodes, n_edges, n_comp, mean_deg, auto_added,
    )


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
        diag["auto_connected_edges"] = int(
            getattr(nation, "_auto_connected_edges", 0)
        )
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
            "auto_connected_edges": int(
                getattr(nation, "_auto_connected_edges", 0)
            ),
            "error": str(e),
        }


def _safe_network_snapshot(nation):
    """Serialise the peer graph to a JSON-friendly node/edge list.

    Returns None when there is no graph (e.g. tests that skip network
    creation). Each node carries its bucket and degree so a downstream
    plotter can colour/scale without re-reading agent state.
    """
    G = getattr(nation, "network", None)
    if G is None:
        return None
    try:
        bucket = {a.id: getattr(a, "political_exposure", None)
                  for a in nation.agents_active.values()}
        nodes = [
            {
                "id": str(n),
                "bucket": bucket.get(n),
                "degree": int(G.degree(n)),
            }
            for n in G.nodes()
        ]
        edges = [[str(u), str(v)] for u, v in G.edges()]
        return {"nodes": nodes, "edges": edges}
    except Exception as e:  # noqa: BLE001
        logging.warning("Network snapshot failed: %s", e)
        return None


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
                context_policy_id=PACKAGE_SCOPE,
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

def _log_experiment_config(cfg, resume, checkpoint_dir):
    """Print the fully-resolved experiment configuration at startup.

    Pulls from the merged ``{SIM_CONFIG | preset | CLI}`` dict, so every
    knob shown is the value the simulation will actually use — including
    silent defaults (e.g. ``reach_a=1.0`` when the user didn't pass it).
    Grouped into seven categories so a researcher can spot a misconfigured
    experiment without opening ``config.json``.
    """
    pkg_policies = cfg.get("package_policies") or []
    pkg_count = len(pkg_policies) if pkg_policies else 0
    pkg_short = [str(p).replace("ClimatePolicyID(", "").rstrip(")")
                 for p in pkg_policies]
    days_val = cfg.get("days")
    n_days = len(days_val) if isinstance(days_val, list) else days_val

    survey_model = cfg.get("survey_model") or cfg.get("llm_model")
    survey_provider = cfg.get("survey_provider") or cfg.get("llm_provider")
    survey_same = (survey_model == cfg.get("llm_model")
                   and survey_provider == cfg.get("llm_provider"))

    bar = "=" * 79
    logging.info(bar)
    logging.info("                            EXPERIMENT CONFIG")
    logging.info(bar)
    logging.info(
        "[run-shape]  n_citizens=%s  days=%s  seed=%s  communication_mode=%s",
        cfg.get("n_citizens"), n_days, cfg.get("random_seed"),
        cfg.get("communication_mode"),
    )
    logging.info(
        "[exposure]   mode=%s  targets=%s  weights=%s  audience_cap=%s",
        cfg.get("political_exposure_mode"),
        cfg.get("political_exposure_targets"),
        cfg.get("affinity_weights"),
        cfg.get("audience_cap"),
    )
    logging.info(
        "[broadcast]  reach_a=%.2f  reach_b=%.2f  message_source=%s  message_set=%s",
        float(cfg.get("reach_a", 1.0)), float(cfg.get("reach_b", 1.0)),
        cfg.get("political_message_source"),
        cfg.get("political_message_set"),
    )
    logging.info(
        "[peer]       k_peers_per_day=%s  network_type=%s  p_intra=%s  p_inter=%s",
        cfg.get("k_peers_per_day"), cfg.get("network_type"),
        cfg.get("p_intra"), cfg.get("p_inter"),
    )
    logging.info(
        "[day0]       anchor=%s",
        cfg.get("day0_anchor"),
    )
    logging.info(
        "[llm]        provider=%s  model=%s  temp=%s  thinking=%s  debias=%s",
        cfg.get("llm_provider"), cfg.get("llm_model"),
        cfg.get("llm_temperature"), cfg.get("thinking"), cfg.get("debias"),
    )
    if cfg.get("llm_provider") == "local":
        logging.info(
            "[llm]        base_url=%s  timeout_s=%s",
            cfg.get("local_base_url"), cfg.get("local_timeout_s"),
        )
    if survey_same:
        logging.info("[survey-llm] same as [llm]")
    else:
        logging.info(
            "[survey-llm] provider=%s  model=%s",
            survey_provider, survey_model,
        )
    logging.info(
        "[package]    %d of 6 policies: %s",
        pkg_count, pkg_short if pkg_count and pkg_count < 6 else "all",
    )
    logging.info(
        "[runtime]    checkpoint_dir=%s  resume=%s",
        checkpoint_dir if checkpoint_dir else "off",
        resume,
    )
    logging.info(bar)


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
    _log_experiment_config(cfg, resume=resume, checkpoint_dir=checkpoint_dir)

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
    # Layer 1: bump network params to keep small populations connected.
    _adjust_network_params_for_small_n(cfg, len(nation.agents_active))
    nation.create_network(
        network_type=cfg.get("network_type", "stochastic_block"),
        network_params=_resolve_network_params(cfg),
        seed=cfg["random_seed"],
    )
    nation.assign_network_blocks()
    # Layer 2: post-creation safety net.
    _auto_connect_components(nation, seed=cfg["random_seed"])
    # Layer 3: visibility log line (always emitted).
    _log_network_summary(nation)

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
    survey_raw_response_rows = []
    survey_assembled_context_rows = []
    daily_summary_rows = []
    package_mode = _is_package_mode(config)
    package_policies = _get_package_policies(config) if package_mode else []
    agents = list(nation.agents_active.values())

    for event in getattr(nation, "message_log", []):
        policy_id = event.get("policy_id")
        policy_ids = event.get("policy_ids") or []
        message_rows.append({
            "sim_step": _safe_step(event.get("sim_step", 0)),
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
            steps = getattr(agent, "_survey_reasoning_steps", {}).get(policy_id, [])
            if not isinstance(steps, list):
                steps = []
            for idx, (day, reasoning) in enumerate(reasoning_entries):
                survey_reasoning_rows.append({
                    "agent_id": agent.id,
                    "sim_step": _safe_step(steps[idx] if idx < len(steps) else 0),
                    "day": day,
                    "policy_id": str(policy_id),
                    "reasoning": reasoning,
                })

        for policy_id, raw_entries in getattr(agent, "survey_raw_response", {}).items():
            steps = getattr(agent, "_survey_raw_response_steps", {}).get(policy_id, [])
            if not isinstance(steps, list):
                steps = []
            for idx, (day, raw) in enumerate(raw_entries):
                survey_raw_response_rows.append({
                    "agent_id": agent.id,
                    "sim_step": _safe_step(steps[idx] if idx < len(steps) else 0),
                    "day": day,
                    "policy_id": str(policy_id),
                    "raw_response": raw,
                })

        for policy_id, ctx_entries in getattr(agent, "survey_assembled_context", {}).items():
            steps = getattr(agent, "_survey_assembled_context_steps", {}).get(policy_id, [])
            if not isinstance(steps, list):
                steps = []
            for idx, (day, ctx) in enumerate(ctx_entries):
                survey_assembled_context_rows.append({
                    "agent_id": agent.id,
                    "sim_step": _safe_step(steps[idx] if idx < len(steps) else 0),
                    "day": day,
                    "policy_id": str(policy_id),
                    "assembled_context": ctx,
                })

        for (day, policy_id), summary in agent.daily_summaries.items():
            steps_map = getattr(agent, "_daily_summary_steps", {})
            step = steps_map.get((day, policy_id), 0) if isinstance(steps_map, dict) else 0
            daily_summary_rows.append({
                "agent_id": agent.id,
                "sim_step": _safe_step(step),
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
                "sim_step": _safe_step(r.get("sim_step", 0)),
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
    agent_attributes_df = collect_agent_attributes(nation)
    sample_ids = _resolve_timeline_sample_ids(
        agent_attributes_df,
        sample_size=config.get("timeline_sample_size", 3),
        explicit_ids=config.get("timeline_sample_agent_ids"),
    )

    results = {
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
            columns=_RESULT_CSV_SCHEMAS["reflections"],
        ),
        "messages": pd.DataFrame(
            message_rows,
            columns=_RESULT_CSV_SCHEMAS["messages"],
        ),
        "survey_reasoning": pd.DataFrame(
            survey_reasoning_rows,
            columns=_RESULT_CSV_SCHEMAS["survey_reasoning"],
        ),
        "survey_raw_response": pd.DataFrame(
            survey_raw_response_rows,
            columns=_RESULT_CSV_SCHEMAS["survey_raw_response"],
        ),
        "survey_assembled_context": pd.DataFrame(
            survey_assembled_context_rows,
            columns=_RESULT_CSV_SCHEMAS["survey_assembled_context"],
        ),
        "daily_summaries": pd.DataFrame(
            daily_summary_rows,
            columns=_RESULT_CSV_SCHEMAS["daily_summaries"],
        ),
        "ground_truth": ground_truth_df,
        "package_ground_truth": package_ground_truth_df,
        "agent_attributes": agent_attributes_df,
        "config": config,
        "network_diagnostics": _safe_network_diagnostics(nation, config),
        "network_snapshot": _safe_network_snapshot(nation),
        "_timeline_sample_ids": sample_ids,
    }
    results["agent_timeline"] = build_agent_timeline(results, sample_ids)
    return results


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


def collect_agent_attributes(nation):
    """Snapshot every active agent's identity + assignment metadata.

    One row per agent. Source of truth for every bucket-stratified
    analysis (`political_exposure`), and the only place affinity scores
    are persisted (computed once during exposure assignment, cached on
    each citizen as `_affinity_score_a/b`). `persona_text` is the full
    `get_persona()` string the LLM sees in every system prompt, captured
    here so reviewers can audit who each agent is without re-running.
    """
    rows = []
    for agent in nation.agents_active.values():
        try:
            persona_text = agent.get_persona()
        except Exception:  # noqa: BLE001 — audit artefact must not crash a run
            persona_text = ""
        rows.append({
            "agent_id": agent.id,
            "political_exposure": getattr(agent, "political_exposure", None),
            "affinity_score_a": getattr(agent, "_affinity_score_a", None),
            "affinity_score_b": getattr(agent, "_affinity_score_b", None),
            "year_of_birth": getattr(agent, "year_of_birth", None),
            "gender_id": _enum_value(getattr(agent, "gender_id", None)),
            "region_id": _enum_value(getattr(agent, "region_id", None)),
            "education_id": _enum_value(getattr(agent, "education_id", None)),
            "ukge2019_vote_id": _enum_value(getattr(agent, "ukge2019_vote_id", None)),
            "brexit_vote_id": _enum_value(getattr(agent, "brexit_vote_id", None)),
            "persona_text": persona_text,
        })
    return pd.DataFrame(rows, columns=_RESULT_CSV_SCHEMAS["agent_attributes"])


def _enum_value(obj):
    """Best-effort scalar conversion for attribute-map IDs."""
    if obj is None:
        return None
    for attr in ("value", "id"):
        v = getattr(obj, attr, None)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                return v
    try:
        return int(obj)
    except (TypeError, ValueError):
        return str(obj)


def _safe_step(value):
    """Coerce a sim_step cell to int; ``0`` for anything non-coercible.

    Defensive both at collect-time (MagicMock-shaped agents in unit tests
    auto-create attributes that are not real ints) and load-time (older
    checkpoints lack the column entirely).
    """
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# ── Output ──────────────────────────────────────────────────────

# Schema columns for each result CSV. Used by both save_results (final
# canonical output) and the per-day checkpoint writer/loader so the two
# stay in lockstep.
#
# `sim_step` columns added in this version are how downstream consumers
# (esp. `agent_timeline.csv`) interleave events from different sources
# into true execution order without assuming a fixed phase sequence.
_RESULT_CSV_SCHEMAS = {
    "opinion_trajectories": ["agent_id", "day", "policy_id", "numeric"],
    "package_index_trajectories": [
        "agent_id", "day", "index_name", "package_scope", "package_index",
    ],
    "reflections": [
        "agent_id", "sim_step", "day", "phase", "policy_id", "package_scope",
        "policy_ids_json", "messages_received_json",
        "messages_received_count", "text",
    ],
    "messages": [
        "sim_step", "day", "phase", "message_type", "sender_type", "sender_id",
        "sender_side", "recipient_id", "recipient_scope", "policy_id",
        "package_scope", "policy_ids_json", "message_text",
        "political_message_id",
    ],
    "survey_reasoning": ["agent_id", "sim_step", "day", "policy_id", "reasoning"],
    "survey_raw_response": ["agent_id", "sim_step", "day", "policy_id", "raw_response"],
    "survey_assembled_context": [
        "agent_id", "sim_step", "day", "policy_id", "assembled_context",
    ],
    "daily_summaries": ["agent_id", "sim_step", "day", "policy_id", "summary"],
    "ground_truth": ["agent_id", "policy_id", "ground_truth"],
    "package_ground_truth": ["agent_id", "index_name", "ground_truth"],
    "agent_attributes": [
        "agent_id", "political_exposure", "affinity_score_a", "affinity_score_b",
        "year_of_birth", "gender_id", "region_id", "education_id",
        "ukge2019_vote_id", "brexit_vote_id", "persona_text",
    ],
    "agent_timeline": [
        "agent_id", "political_exposure", "sim_step", "day", "phase",
        "event_type", "policy_id", "counterparty_id", "counterparty_role",
        "content", "metadata_json",
    ],
}

# Keys that are written only on the final save_results() call, never by
# per-day checkpoints. Diagnostic artefacts the simulation does NOT need
# to resume from (and which can be expensive to recompute every day).
_CHECKPOINT_SKIP_KEYS = frozenset({"agent_timeline"})


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


def _write_all_csvs(out_path, results, *, is_checkpoint=False):
    """Write every result CSV (atomic per file).

    ``is_checkpoint=True`` skips final-only artefacts (timeline, derived
    bucket tables, network_snapshot.json) so per-day checkpoints stay cheap
    and resumeable. Returns dict of paths written.
    """
    out_path = Path(out_path)
    out_path.mkdir(parents=True, exist_ok=True)
    written = {}

    for key, columns in _RESULT_CSV_SCHEMAS.items():
        if is_checkpoint and key in _CHECKPOINT_SKIP_KEYS:
            continue
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

    # Bucket-stratified + diagnostic tables are final-only: they collapse
    # the whole run and are cheap to rebuild from the per-day CSVs, so
    # producing them every checkpoint would waste IO.
    if not is_checkpoint:
        derived = {
            "package_index_by_bucket": build_package_index_by_bucket(results),
            "opinion_shares_by_bucket": build_opinion_shares_by_bucket(results),
            "day0_vs_dayN_shifts": build_day0_vs_dayN_shifts(results),
            "calibration": build_calibration_table(results),
            "message_flow": build_message_flow(results),
        }
        for name, df in derived.items():
            if df is None or df.empty:
                continue
            _atomic_write_csv(df, out_path / f"{name}.csv")
            written[name] = out_path / f"{name}.csv"

        snap = results.get("network_snapshot")
        if snap is not None:
            _atomic_write_json(snap, out_path / "network_snapshot.json")
            written["network_snapshot"] = out_path / "network_snapshot.json"

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
    _write_all_csvs(checkpoint_dir, results, is_checkpoint=True)

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
        agent.survey_raw_response = {}
        agent.survey_assembled_context = {}
        agent._daily_summary_steps = {}
        agent._survey_reasoning_steps = {}
        agent._survey_raw_response_steps = {}
        agent._survey_assembled_context_steps = {}

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
            "sim_step": _safe_step(getattr(row, "sim_step", 0)),
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
        key = (int(row.day), _to_policy(row.policy_id))
        agent.daily_summaries[key] = row.summary
        agent._daily_summary_steps[key] = _safe_step(getattr(row, "sim_step", 0))

    # survey_reasoning
    sreas = _read("survey_reasoning")
    for row in sreas.itertuples(index=False):
        agent = by_id.get(str(row.agent_id))
        if agent is None:
            continue
        pid = _to_policy(row.policy_id)
        agent.survey_reasoning.setdefault(pid, []).append(
            (int(row.day), row.reasoning)
        )
        agent._survey_reasoning_steps.setdefault(pid, []).append(
            _safe_step(getattr(row, "sim_step", 0))
        )

    # survey_raw_response (added in v0.5; missing on older checkpoints)
    sraw = _read("survey_raw_response")
    for row in sraw.itertuples(index=False):
        agent = by_id.get(str(row.agent_id))
        if agent is None:
            continue
        pid = _to_policy(row.policy_id)
        agent.survey_raw_response.setdefault(pid, []).append(
            (int(row.day), row.raw_response)
        )
        agent._survey_raw_response_steps.setdefault(pid, []).append(
            _safe_step(getattr(row, "sim_step", 0))
        )

    # survey_assembled_context (added with timeline; missing on older checkpoints)
    sac = _read("survey_assembled_context")
    for row in sac.itertuples(index=False):
        agent = by_id.get(str(row.agent_id))
        if agent is None:
            continue
        pid = _to_policy(row.policy_id)
        agent.survey_assembled_context.setdefault(pid, []).append(
            (int(row.day), row.assembled_context)
        )
        agent._survey_assembled_context_steps.setdefault(pid, []).append(
            _safe_step(getattr(row, "sim_step", 0))
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
            "sim_step": _safe_step(getattr(row, "sim_step", 0)),
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

    # Restore the monotonic sim_step counter so events logged after
    # resume don't collide (or under-count) relative to the pre-checkpoint
    # tail. Scan every loaded source and take the max.
    max_step = 0
    for df in (refl, summ, sreas, sraw, sac, msgs):
        if df is None or df.empty or "sim_step" not in df.columns:
            continue
        try:
            m = int(pd.to_numeric(df["sim_step"], errors="coerce").max() or 0)
        except Exception:  # noqa: BLE001
            m = 0
        if m > max_step:
            max_step = m
    nation._sim_step = max_step

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


# ── Bucket-stratified builders and plotters ─────────────────────

# Canonical order so plots and tables present buckets the same way.
_BUCKET_ORDER = ("A-only", "B-only", "both", "neither")


def _attach_bucket(df, attrs):
    """Left-join a frame's ``agent_id`` to its ``political_exposure`` bucket."""
    if attrs is None or attrs.empty or "political_exposure" not in attrs.columns:
        out = df.copy()
        out["political_exposure"] = None
        return out
    bucket_map = dict(zip(attrs["agent_id"], attrs["political_exposure"]))
    out = df.copy()
    out["political_exposure"] = out["agent_id"].map(bucket_map)
    return out


def _sorted_buckets(values):
    seen = [b for b in _BUCKET_ORDER if b in set(values)]
    # Append any non-canonical bucket label (defensive: should never trigger
    # under stock SIM_CONFIG, but keep the union explicit for diagnostics).
    extras = sorted(set(values) - set(_BUCKET_ORDER) - {None})
    return seen + extras


def build_package_index_by_bucket(results):
    """Mean/std/quantiles of the package index per (day, bucket).

    Source of truth for the Run-14 v2 headline numbers; equivalent to a
    ``groupby(['day','political_exposure'])`` over package_index_trajectories.
    """
    columns = [
        "day", "political_exposure", "n_agents", "mean", "std",
        "q25", "q50", "q75",
    ]
    traj = results.get("package_index_trajectories")
    attrs = results.get("agent_attributes")
    if traj is None or traj.empty or attrs is None or attrs.empty:
        return pd.DataFrame(columns=columns)

    joined = _attach_bucket(traj, attrs)
    grouped = joined.groupby(["day", "political_exposure"], dropna=False)
    out = grouped["package_index"].agg(
        n_agents="count",
        mean="mean",
        std="std",
        q25=lambda s: float(s.quantile(0.25)),
        q50=lambda s: float(s.quantile(0.50)),
        q75=lambda s: float(s.quantile(0.75)),
    ).reset_index().sort_values(["day", "political_exposure"])
    return out[columns]


def build_opinion_shares_by_bucket(results):
    """Support/neutral/against shares per (policy, day, bucket)."""
    columns = [
        "policy_id", "day", "political_exposure", "n_agents",
        "n_support", "n_neutral", "n_against",
        "support_pct", "neutral_pct", "against_pct",
    ]
    traj = results.get("opinion_trajectories")
    attrs = results.get("agent_attributes")
    if traj is None or traj.empty or attrs is None or attrs.empty:
        return pd.DataFrame(columns=columns)

    joined = _attach_bucket(traj, attrs)
    grouped = joined.groupby(["policy_id", "day", "political_exposure"], dropna=False)
    out = grouped.agg(
        n_agents=("agent_id", "count"),
        n_support=("numeric", lambda v: int((v > 0).sum())),
        n_neutral=("numeric", lambda v: int((v == 0).sum())),
        n_against=("numeric", lambda v: int((v < 0).sum())),
    ).reset_index().sort_values(["policy_id", "day", "political_exposure"])
    out["support_pct"] = out["n_support"] / out["n_agents"] * 100.0
    out["neutral_pct"] = out["n_neutral"] / out["n_agents"] * 100.0
    out["against_pct"] = out["n_against"] / out["n_agents"] * 100.0
    return out[columns]


def build_day0_vs_dayN_shifts(results):
    """Per (agent, policy) signed shift from the first to last surveyed day.

    Handles partial / checkpointed runs: per-agent-per-policy, uses
    ``min(day)`` and ``max(day)`` in the actual trajectory rather than
    assuming 0 and N. Rows with only one day surveyed report ``signed_shift=0``.
    """
    columns = [
        "agent_id", "policy_id", "political_exposure",
        "day0", "dayN", "day0_numeric", "dayN_numeric",
        "signed_shift", "abs_shift",
    ]
    traj = results.get("opinion_trajectories")
    attrs = results.get("agent_attributes")
    if traj is None or traj.empty:
        return pd.DataFrame(columns=columns)

    joined = _attach_bucket(traj, attrs)
    # First and last day per (agent, policy)
    grouped = joined.groupby(["agent_id", "policy_id"], dropna=False)
    first = grouped.apply(
        lambda g: g.sort_values("day").iloc[0], include_groups=False
    ).reset_index().rename(columns={"day": "day0", "numeric": "day0_numeric"})
    last = grouped.apply(
        lambda g: g.sort_values("day").iloc[-1], include_groups=False
    ).reset_index().rename(columns={"day": "dayN", "numeric": "dayN_numeric"})

    merged = first[["agent_id", "policy_id", "political_exposure",
                    "day0", "day0_numeric"]].merge(
        last[["agent_id", "policy_id", "dayN", "dayN_numeric"]],
        on=["agent_id", "policy_id"], how="inner",
    )
    merged["signed_shift"] = merged["dayN_numeric"] - merged["day0_numeric"]
    merged["abs_shift"] = merged["signed_shift"].abs()
    return merged[columns].sort_values(["agent_id", "policy_id"])


def build_calibration_table(results):
    """Per (policy, day) calibration of LLM opinion vs ground truth.

    Reports ``n``, Pearson r, Spearman rho, MAE, and mean signed bias.
    Calibration is the standard diagnostic for "is the LLM tracking real
    population structure?" — formerly recomputed per notebook.
    """
    columns = [
        "policy_id", "day", "n",
        "pearson_r", "spearman_rho", "mae", "mean_signed_bias",
    ]
    traj = results.get("opinion_trajectories")
    gt = results.get("ground_truth")
    if traj is None or traj.empty or gt is None or gt.empty:
        return pd.DataFrame(columns=columns)

    gt_map = gt.set_index(["agent_id", "policy_id"])["ground_truth"]
    rows = []
    for (pid, day), grp in traj.groupby(["policy_id", "day"], dropna=False):
        joined = grp.merge(
            gt_map.reset_index(), on=["agent_id", "policy_id"], how="inner",
        )
        if joined.empty:
            continue
        n = len(joined)
        # Spearman requires variance on both sides; guard zero-var slices.
        try:
            pearson = float(joined["numeric"].corr(joined["ground_truth"], method="pearson"))
        except Exception:  # noqa: BLE001
            pearson = float("nan")
        try:
            spearman = float(joined["numeric"].corr(joined["ground_truth"], method="spearman"))
        except Exception:  # noqa: BLE001
            spearman = float("nan")
        mae = float((joined["numeric"] - joined["ground_truth"]).abs().mean())
        bias = float((joined["numeric"] - joined["ground_truth"]).mean())
        rows.append({
            "policy_id": pid, "day": int(day), "n": int(n),
            "pearson_r": pearson, "spearman_rho": spearman,
            "mae": mae, "mean_signed_bias": bias,
        })
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values(["policy_id", "day"])


def build_message_flow(results):
    """Aggregate message counts per (day, phase, sender_side, recipient_bucket).

    The recipient bucket is joined from ``agent_attributes`` so this also
    surfaces "did political-side X actually reach bucket Y" — would have
    flagged the k_peers=0 wasted-LLM case before it shipped.
    """
    columns = [
        "day", "phase", "sender_side", "recipient_bucket",
        "n_messages", "mean_chars",
    ]
    msgs = results.get("messages")
    attrs = results.get("agent_attributes")
    if msgs is None or msgs.empty:
        return pd.DataFrame(columns=columns)

    df = msgs.copy()
    if attrs is not None and not attrs.empty:
        bucket_map = dict(zip(attrs["agent_id"].astype(str), attrs["political_exposure"]))
        df["recipient_bucket"] = df["recipient_id"].astype(str).map(bucket_map)
    else:
        df["recipient_bucket"] = None
    df["_chars"] = df["message_text"].astype(str).str.len()
    grouped = df.groupby(
        ["day", "phase", "sender_side", "recipient_bucket"], dropna=False,
    ).agg(
        n_messages=("message_text", "count"),
        mean_chars=("_chars", "mean"),
    ).reset_index().sort_values(["day", "phase", "sender_side", "recipient_bucket"])
    return grouped[columns]


# ── Timeline (per-agent diagnostic) ─────────────────────────────

def _resolve_timeline_sample_ids(agent_attributes, sample_size=3, explicit_ids=None):
    """Pick which agents get a full per-event timeline.

    Default: one agent from each of the top-``sample_size``-by-size buckets
    (ties broken by sorted agent_id for determinism). If fewer buckets
    than ``sample_size`` exist, fall back to evenly-spaced agent_ids.
    An explicit list of agent_ids always wins.
    """
    if sample_size is None or sample_size <= 0:
        return []
    if explicit_ids is not None:
        return list(explicit_ids)
    if agent_attributes is None or agent_attributes.empty:
        return []

    buckets_by_size = (
        agent_attributes.groupby("political_exposure", dropna=True)
        .size().sort_values(ascending=False)
    )
    chosen = []
    for bucket in buckets_by_size.index:
        if len(chosen) >= sample_size:
            break
        candidates = agent_attributes[
            agent_attributes["political_exposure"] == bucket
        ]["agent_id"].sort_values().tolist()
        if candidates:
            chosen.append(candidates[0])

    if len(chosen) < sample_size:
        # Fall back to evenly-spaced picks from the agent pool, skipping
        # any already chosen so we still hit ``sample_size`` distinct ids.
        all_ids = agent_attributes["agent_id"].sort_values().tolist()
        remaining = [a for a in all_ids if a not in chosen]
        if remaining:
            need = sample_size - len(chosen)
            if need >= len(remaining):
                chosen.extend(remaining)
            else:
                step = max(1, len(remaining) // need)
                chosen.extend(remaining[::step][:need])
    return chosen[:sample_size]


def build_agent_timeline(results, sample_ids):
    """Long-format per-event timeline for the sampled agents.

    Rows are sortable by ``(agent_id, sim_step)`` to reproduce true
    execution order regardless of how the daily phase plan is configured
    (so changing AABC -> ABCA -> AABCA etc. just changes which rows appear,
    not how they sort). Captures: broadcasts received, broadcast/peer
    reflections, peer messages sent, the EXACT assembled survey context,
    debias reasoning, raw survey response, parsed numeric, daily summary.
    """
    columns = _RESULT_CSV_SCHEMAS["agent_timeline"]
    if not sample_ids:
        return pd.DataFrame(columns=columns)

    sample_set = {str(a) for a in sample_ids}
    attrs = results.get("agent_attributes")
    bucket_map = {}
    if attrs is not None and not attrs.empty:
        bucket_map = dict(zip(attrs["agent_id"].astype(str),
                              attrs["political_exposure"]))

    rows = []

    def _emit(agent_id, sim_step, day, phase, event_type, *,
              policy_id="", counterparty_id="", counterparty_role="",
              content="", metadata=None):
        rows.append({
            "agent_id": agent_id,
            "political_exposure": bucket_map.get(str(agent_id)),
            "sim_step": int(sim_step) if sim_step is not None else 0,
            "day": int(day) if day is not None else None,
            "phase": phase,
            "event_type": event_type,
            "policy_id": str(policy_id) if policy_id not in (None, "") else "",
            "counterparty_id": str(counterparty_id) if counterparty_id not in (None, "") else "",
            "counterparty_role": counterparty_role,
            "content": content,
            "metadata_json": json.dumps(metadata or {}),
        })

    msgs = results.get("messages")
    if msgs is not None and not msgs.empty:
        for row in msgs.itertuples(index=False):
            sender_id = getattr(row, "sender_id", None)
            recipient_id = getattr(row, "recipient_id", None)
            mtype = getattr(row, "message_type", "")
            # Broadcasts received by sampled agents
            if str(recipient_id) in sample_set:
                event_type = (
                    "broadcast_received"
                    if mtype == "political_broadcast"
                    else "peer_message_received"
                )
                role = ("political_agent"
                        if mtype == "political_broadcast" else "peer")
                _emit(
                    recipient_id, row.sim_step, row.day, row.phase,
                    event_type,
                    policy_id=row.policy_id or row.package_scope,
                    counterparty_id=sender_id,
                    counterparty_role=role,
                    content=row.message_text,
                    metadata={
                        "sender_side": row.sender_side,
                        "political_message_id": row.political_message_id,
                        "policy_ids_json": row.policy_ids_json,
                    },
                )
            # Peer messages SENT by sampled agents
            if mtype == "peer_message" and str(sender_id) in sample_set:
                _emit(
                    sender_id, row.sim_step, row.day, row.phase,
                    "peer_message_sent",
                    policy_id=row.policy_id or row.package_scope,
                    counterparty_id=recipient_id,
                    counterparty_role="peer",
                    content=row.message_text,
                    metadata={"policy_ids_json": row.policy_ids_json},
                )

    refs = results.get("reflections")
    if refs is not None and not refs.empty:
        for row in refs.itertuples(index=False):
            if str(row.agent_id) not in sample_set:
                continue
            phase = row.phase
            event_type = (
                "peer_reflection" if phase == "C" else "broadcast_reflection"
            )
            _emit(
                row.agent_id, row.sim_step, row.day, phase,
                event_type,
                policy_id=row.policy_id or row.package_scope,
                content=row.text,
                metadata={
                    "messages_received_count": row.messages_received_count,
                    "policy_ids_json": row.policy_ids_json,
                },
            )

    ctx = results.get("survey_assembled_context")
    if ctx is not None and not ctx.empty:
        for row in ctx.itertuples(index=False):
            if str(row.agent_id) not in sample_set:
                continue
            _emit(
                row.agent_id, row.sim_step, row.day, "survey",
                "survey_assembled_context",
                policy_id=row.policy_id,
                content=row.assembled_context,
            )

    sreas = results.get("survey_reasoning")
    if sreas is not None and not sreas.empty:
        for row in sreas.itertuples(index=False):
            if str(row.agent_id) not in sample_set:
                continue
            _emit(
                row.agent_id, row.sim_step, row.day, "survey",
                "survey_reasoning",
                policy_id=row.policy_id,
                content=row.reasoning,
            )

    sraw = results.get("survey_raw_response")
    if sraw is not None and not sraw.empty:
        for row in sraw.itertuples(index=False):
            if str(row.agent_id) not in sample_set:
                continue
            _emit(
                row.agent_id, row.sim_step, row.day, "survey",
                "survey_raw_response",
                policy_id=row.policy_id,
                content=row.raw_response,
            )

    traj = results.get("opinion_trajectories")
    if traj is not None and not traj.empty:
        # Each survey produces a parsed numeric; sort by day to keep
        # consistent ordering. sim_step is not captured for opinion_history
        # writes (kept minimal); inherit from sraw row for the same key
        # when available, otherwise emit with sim_step=0 (still sorts
        # correctly relative to its day-mates via the day fallback).
        sraw_steps = {}
        if sraw is not None and not sraw.empty:
            for row in sraw.itertuples(index=False):
                sraw_steps[(str(row.agent_id), str(row.policy_id), int(row.day))] = row.sim_step
        for row in traj.itertuples(index=False):
            if str(row.agent_id) not in sample_set:
                continue
            step = sraw_steps.get(
                (str(row.agent_id), str(row.policy_id), int(row.day)), 0,
            )
            _emit(
                row.agent_id, step, row.day, "survey",
                "survey_numeric",
                policy_id=row.policy_id,
                content=str(int(row.numeric)),
            )

    summ = results.get("daily_summaries")
    if summ is not None and not summ.empty:
        for row in summ.itertuples(index=False):
            if str(row.agent_id) not in sample_set:
                continue
            _emit(
                row.agent_id, row.sim_step, row.day, "memory",
                "daily_summary",
                policy_id=row.policy_id,
                content=row.summary,
            )

    if not rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(rows, columns=columns)
    return df.sort_values(["agent_id", "sim_step"]).reset_index(drop=True)


# ── Bucket plots ────────────────────────────────────────────────

def plot_package_index_by_bucket(results, output_path=None):
    """2x2-style panel grid: package-index spaghetti+mean per bucket."""
    import matplotlib.pyplot as plt

    by_bucket = build_package_index_by_bucket(results)
    traj = results.get("package_index_trajectories")
    attrs = results.get("agent_attributes")
    if (
        by_bucket.empty or traj is None or traj.empty
        or attrs is None or attrs.empty
    ):
        logging.warning("No bucketed package data to plot.")
        return None

    joined = _attach_bucket(traj, attrs)
    present = _sorted_buckets(joined["political_exposure"].dropna().unique())
    if not present:
        logging.warning("No buckets present for package_index_by_bucket plot.")
        return None

    n = len(present)
    ncols = min(n, 2)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(7 * ncols, 4.5 * nrows), squeeze=False)

    gt_mean = None
    pkg_gt = results.get("package_ground_truth")
    if pkg_gt is not None and not pkg_gt.empty:
        gt_mean = float(pkg_gt["ground_truth"].mean())

    for i, bucket in enumerate(present):
        ax = axes[i // ncols, i % ncols]
        bdf = joined[joined["political_exposure"] == bucket]
        for aid in bdf["agent_id"].unique():
            adata = bdf[bdf["agent_id"] == aid].sort_values("day")
            ax.plot(adata["day"], adata["package_index"],
                    alpha=0.18, color="steelblue", linewidth=0.8)
        mean = bdf.groupby("day")["package_index"].mean()
        ax.plot(mean.index, mean.values, color="black", linewidth=2, label="Mean")
        if gt_mean is not None:
            ax.axhline(gt_mean, color="red", linestyle="--", linewidth=1.2,
                       label=f"GT mean ({gt_mean:+.2f})")
        ax.set_title(f"{bucket} (n={bdf['agent_id'].nunique()})")
        ax.set_xlabel("Day")
        ax.set_ylabel("Package index (-3..+3)")
        ax.set_ylim(-3.5, 3.5)
        ax.legend(loc="best", fontsize=8)

    for j in range(n, nrows * ncols):
        axes[j // ncols, j % ncols].set_visible(False)

    fig.suptitle("Package Index by Political-Exposure Bucket", fontsize=13)
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()
    return fig


def plot_opinion_shares_by_bucket(results, output_path=None):
    """Grid of (policy x bucket) panels: support/neutral/against lines."""
    import matplotlib.pyplot as plt

    share_df = build_opinion_shares_by_bucket(results)
    if share_df.empty:
        logging.warning("No bucketed opinion-share data to plot.")
        return None

    policies = list(share_df["policy_id"].unique())
    buckets = _sorted_buckets(share_df["political_exposure"].dropna().unique())
    if not policies or not buckets:
        logging.warning("Insufficient (policy x bucket) cells to plot.")
        return None

    policy_names = _policy_short_names()
    nrows, ncols = len(policies), len(buckets)
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(4 * ncols, 3.2 * nrows), squeeze=False,
    )

    for i, pid in enumerate(policies):
        for j, bucket in enumerate(buckets):
            ax = axes[i, j]
            cell = share_df[
                (share_df["policy_id"] == pid)
                & (share_df["political_exposure"] == bucket)
            ].sort_values("day")
            if cell.empty:
                ax.set_visible(False)
                continue
            ax.plot(cell["day"], cell["support_pct"], color="forestgreen",
                    marker="o", label="Support")
            ax.plot(cell["day"], cell["neutral_pct"], color="dimgray",
                    marker="o", label="Neutral")
            ax.plot(cell["day"], cell["against_pct"], color="firebrick",
                    marker="o", label="Against")
            ax.set_ylim(0, 100)
            if i == 0:
                ax.set_title(bucket)
            if j == 0:
                ax.set_ylabel(policy_names.get(pid, str(pid))[:25], fontsize=9)
            if i == nrows - 1:
                ax.set_xlabel("Day")
            if i == 0 and j == ncols - 1:
                ax.legend(fontsize=7, loc="best")

    fig.suptitle("Opinion Shares by (Policy x Bucket)", fontsize=13)
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()
    return fig


def plot_gap_widening(results, output_path=None):
    """Bold package-index (A_mean - B_mean) line, thin per-policy traces."""
    import matplotlib.pyplot as plt

    by_bucket = build_package_index_by_bucket(results)
    opinion_by_bucket = build_opinion_shares_by_bucket(results)
    if by_bucket.empty:
        logging.warning("No bucketed package data for gap plot.")
        return None

    has_a = (by_bucket["political_exposure"] == "A-only").any()
    has_b = (by_bucket["political_exposure"] == "B-only").any()
    if not (has_a and has_b):
        logging.warning(
            "gap_widening needs both A-only and B-only buckets; skipping."
        )
        return None

    pivot = by_bucket.pivot_table(
        index="day", columns="political_exposure", values="mean",
    )
    gap_pkg = (pivot.get("A-only") - pivot.get("B-only")).sort_index()

    fig, ax = plt.subplots(figsize=(8, 5))

    # Per-policy gap traces (thin grey)
    if not opinion_by_bucket.empty:
        # Use the mean numeric per (policy, day, bucket) computed by
        # re-grouping the original opinion_trajectories; the share frame
        # already collapses to share counts so we recompute means here.
        traj = results.get("opinion_trajectories")
        attrs = results.get("agent_attributes")
        if traj is not None and not traj.empty and attrs is not None:
            joined = _attach_bucket(traj, attrs)
            per_pol = (
                joined.groupby(["policy_id", "day", "political_exposure"])
                ["numeric"].mean().reset_index()
            )
            for pid in per_pol["policy_id"].unique():
                sub = per_pol[per_pol["policy_id"] == pid].pivot_table(
                    index="day", columns="political_exposure", values="numeric",
                )
                if "A-only" in sub.columns and "B-only" in sub.columns:
                    g = (sub["A-only"] - sub["B-only"]).sort_index()
                    ax.plot(g.index, g.values, color="grey",
                            alpha=0.45, linewidth=1.0)

    ax.plot(gap_pkg.index, gap_pkg.values,
            color="black", linewidth=2.5, marker="o",
            label="Package index gap (A_mean - B_mean)")
    ax.axhline(0, color="darkgrey", linestyle=":", linewidth=0.8)
    ax.set_xlabel("Day")
    ax.set_ylabel("A-only mean minus B-only mean")
    ax.set_title("Persuasion-Signal Gap-Widening")
    ax.legend(loc="best", fontsize=9)
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()
    return fig


def plot_network_graph(results, output_path=None):
    """Render the peer graph from network_snapshot, coloured by bucket."""
    import matplotlib.pyplot as plt

    snap = results.get("network_snapshot")
    if not snap or not snap.get("nodes"):
        logging.warning("No network snapshot to plot.")
        return None

    try:
        import networkx as nx  # local import: optional for tests that skip plots
    except ImportError:  # pragma: no cover
        logging.warning("networkx not available for network plot.")
        return None

    G = nx.Graph()
    color_map = {
        "A-only": "forestgreen", "B-only": "firebrick",
        "both": "goldenrod", "neither": "lightgrey",
    }
    node_colors = []
    sizes = []
    for node in snap["nodes"]:
        G.add_node(node["id"])
        node_colors.append(color_map.get(node["bucket"], "lightblue"))
        sizes.append(40 + 18 * int(node["degree"]))
    for u, v in snap["edges"]:
        G.add_edge(u, v)

    pos = nx.spring_layout(G, seed=42)
    fig, ax = plt.subplots(figsize=(9, 7))
    nx.draw_networkx_edges(G, pos, alpha=0.25, width=0.6, ax=ax)
    nx.draw_networkx_nodes(
        G, pos, node_color=node_colors, node_size=sizes,
        edgecolors="black", linewidths=0.4, ax=ax,
    )
    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=c, markersize=8, label=b)
        for b, c in color_map.items()
    ]
    ax.legend(handles=legend_handles, loc="best", fontsize=8)
    ax.set_title("Peer Network (nodes coloured by political_exposure)")
    ax.set_axis_off()
    plt.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logging.info(f"Plot saved to {output_path}")
    else:
        plt.show()
    return fig


def plot_calibration_by_policy(results, output_path=None):
    """Per-policy scatter of last-day LLM opinion vs ground truth + diagonal."""
    import matplotlib.pyplot as plt

    traj = results.get("opinion_trajectories")
    gt = results.get("ground_truth")
    if traj is None or traj.empty or gt is None or gt.empty:
        logging.warning("No data for calibration plot.")
        return None

    policies = list(traj["policy_id"].unique())
    if not policies:
        return None
    last_day = int(traj["day"].max())
    last = traj[traj["day"] == last_day]

    ncols = min(len(policies), 3)
    nrows = (len(policies) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 4 * nrows), squeeze=False)
    policy_names = _policy_short_names()

    for i, pid in enumerate(policies):
        ax = axes[i // ncols, i % ncols]
        merged = last[last["policy_id"] == pid].merge(
            gt[gt["policy_id"] == pid], on=["agent_id", "policy_id"], how="inner",
        )
        if merged.empty:
            ax.set_visible(False)
            continue
        try:
            rho = float(merged["numeric"].corr(merged["ground_truth"], method="spearman"))
        except Exception:  # noqa: BLE001
            rho = float("nan")
        ax.scatter(merged["ground_truth"], merged["numeric"], alpha=0.6)
        ax.plot([-3, 3], [-3, 3], color="grey", linestyle="--", linewidth=0.8)
        ax.set_xlim(-3.5, 3.5)
        ax.set_ylim(-3.5, 3.5)
        ax.set_xlabel("Ground truth")
        ax.set_ylabel(f"LLM opinion (day {last_day})")
        ax.set_title(f"{policy_names.get(pid, str(pid))[:30]} (rho={rho:+.2f})")

    for j in range(len(policies), nrows * ncols):
        axes[j // ncols, j % ncols].set_visible(False)

    fig.suptitle("Calibration: LLM Opinion vs Ground Truth (last day)", fontsize=13)
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

    bucket_path = out_path / "package_index_by_bucket.png"
    if plot_package_index_by_bucket(results, output_path=bucket_path) is not None:
        plot_paths["package_index_by_bucket"] = bucket_path

    osbucket_path = out_path / "opinion_shares_by_bucket.png"
    if plot_opinion_shares_by_bucket(results, output_path=osbucket_path) is not None:
        plot_paths["opinion_shares_by_bucket"] = osbucket_path

    gap_path = out_path / "gap_widening.png"
    if plot_gap_widening(results, output_path=gap_path) is not None:
        plot_paths["gap_widening"] = gap_path

    network_path = out_path / "network_graph.png"
    if plot_network_graph(results, output_path=network_path) is not None:
        plot_paths["network_graph"] = network_path

    calib_path = out_path / "calibration_by_policy.png"
    if plot_calibration_by_policy(results, output_path=calib_path) is not None:
        plot_paths["calibration_by_policy"] = calib_path

    return plot_paths
