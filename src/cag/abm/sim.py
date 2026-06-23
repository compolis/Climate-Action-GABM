"""
Simulation runner for Climate-Action-GABM.
"""
import json
import logging
from pathlib import Path

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


# ── Network helpers (extracted to cag.abm.network_repair) ───────
from cag.abm.network_repair import (  # noqa: E402,F401
    _adjust_network_params_for_small_n,
    _auto_connect_components,
    _log_network_summary,
    _resolve_network_params,
    _safe_network_diagnostics,
    _safe_network_snapshot,
)


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


# ── Results collection (extracted to cag.io.results) ────────────


# ── Output (extracted to cag.io.results) ────────────────────────


# ── Checkpointing (extracted to cag.io.checkpoint) ──────────────
from cag.io.checkpoint import (  # noqa: E402,F401
    CHECKPOINT_SCHEMA_VERSION,
    _RESUME_HARD_KEYS,
    _RESUME_SOFT_KEYS,
    _config_hash,
    _load_checkpoint,
    _load_checkpoint_meta,
    _validate_resume_config,
    _write_checkpoint,
)


# ── Results + output re-exports (extracted to cag.io.results) ───
from cag.io.results import (  # noqa: E402,F401
    _CHECKPOINT_SKIP_KEYS,
    _RESULT_CSV_SCHEMAS,
    _atomic_write_csv,
    _atomic_write_json,
    _collect_results,
    _enum_value,
    _safe_step,
    _serialise_config,
    _write_all_csvs,
    collect_agent_attributes,
    collect_ground_truth,
    collect_package_ground_truth,
    save_results,
)


# ── Aggregator re-exports (extracted to cag.io.aggregators) ─────
from cag.io.aggregators import (  # noqa: E402,F401
    _BUCKET_ORDER,
    _attach_bucket,
    _resolve_timeline_sample_ids,
    _sorted_buckets,
    build_agent_timeline,
    build_calibration_table,
    build_day0_vs_dayN_shifts,
    build_message_flow,
    build_opinion_shares,
    build_opinion_shares_by_bucket,
    build_package_index_by_bucket,
    build_package_index_shares,
)


# ── Plot re-exports (extracted to cag.io.plots) ─────────────────
from cag.io.plots import (  # noqa: E402,F401
    _policy_short_names,
    plot_calibration_by_policy,
    plot_gap_widening,
    plot_network_graph,
    plot_opinion_shares,
    plot_opinion_shares_by_bucket,
    plot_opinion_trajectories,
    plot_package_index_by_bucket,
    plot_package_index_shares,
    plot_package_index_trajectories,
    save_result_plots,
)


__all__ = [
    # Public API (notebooks, scripts)
    "SIM_CONFIG",
    "VALID_DAY0_ANCHORS",
    "make_phases",
    "run_simulation",
    "save_results",
    "save_result_plots",
    "collect_agent_attributes",
    "collect_ground_truth",
    "collect_package_ground_truth",
    # Aggregators
    "build_agent_timeline",
    "build_calibration_table",
    "build_day0_vs_dayN_shifts",
    "build_message_flow",
    "build_opinion_shares",
    "build_opinion_shares_by_bucket",
    "build_package_index_by_bucket",
    "build_package_index_shares",
    # Plots
    "plot_calibration_by_policy",
    "plot_gap_widening",
    "plot_network_graph",
    "plot_opinion_shares",
    "plot_opinion_shares_by_bucket",
    "plot_opinion_trajectories",
    "plot_package_index_by_bucket",
    "plot_package_index_shares",
    "plot_package_index_trajectories",
    # Checkpoint
    "CHECKPOINT_SCHEMA_VERSION",
    # Private names imported by tests/conftest
    "_BUCKET_ORDER",
    "_CHECKPOINT_SKIP_KEYS",
    "_PHASE_SUGAR_KEYS",
    "_RESULT_CSV_SCHEMAS",
    "_RESUME_HARD_KEYS",
    "_RESUME_SOFT_KEYS",
    "_adjust_network_params_for_small_n",
    "_atomic_write_csv",
    "_atomic_write_json",
    "_attach_bucket",
    "_auto_connect_components",
    "_collect_results",
    "_config_hash",
    "_enum_value",
    "_get_package_policies",
    "_is_package_mode",
    "_load_checkpoint",
    "_load_checkpoint_meta",
    "_log_experiment_config",
    "_log_network_summary",
    "_log_package_index",
    "_policy_short_names",
    "_resolve_day_phases",
    "_resolve_network_params",
    "_resolve_runtime",
    "_resolve_timeline_sample_ids",
    "_run_baseline_surveys",
    "_run_day0",
    "_run_one_day",
    "_safe_network_diagnostics",
    "_safe_network_snapshot",
    "_safe_step",
    "_serialise_config",
    "_sorted_buckets",
    "_validate_resume_config",
    "_write_all_csvs",
    "_write_checkpoint",
]
