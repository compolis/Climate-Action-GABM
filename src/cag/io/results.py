"""
Result collection and CSV/JSON output for Climate-Action-GABM.

Owns the canonical CSV schemas (``_RESULT_CSV_SCHEMAS``), the in-memory
results dict builder (``_collect_results``), ground-truth and agent-attribute
collectors, atomic file writers, and the public ``save_results`` entry
point. Extracted from ``cag.abm.sim`` in the 2026-06-22 refactor; all names
are re-exported from ``cag.abm.sim`` for backwards compatibility.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from cag.abm.attributes.opinion import (
    ALL_CLIMATE_POLICIES,
    ClimatePolicyID,
    PACKAGE_SCOPE,
    PRO_CLIMATE_INDEX_COLUMN,
    SURVEY_COLUMN_MAP,
    compute_package_index,
)
from cag.io.aggregators import (
    _resolve_timeline_sample_ids,
    build_agent_timeline,
    build_bucket_summary,
    build_calibration_table,
    build_day0_vs_dayN_shifts,
    build_message_flow,
    build_opinion_shares,
    build_opinion_shares_by_bucket,
    build_package_index_by_bucket,
    build_package_index_shares,
    build_targeting_diagnostics,
)


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
        "ukge2019_vote_id", "brexit_vote_id",
        "reached_by_a", "reached_by_b", "persona_text",
    ],
    # Tier-P persona-ablation audit trail: which agent's persona each agent
    # actually carried this run (itself for "real", another agent for
    # "shuffled", the sentinel "NEUTRAL" for "neutral").
    "persona_map": ["agent_id", "source_agent_id", "persona_mode"],
    "agent_timeline": [
        "agent_id", "political_exposure", "sim_step", "day", "phase",
        "event_type", "policy_id", "counterparty_id", "counterparty_role",
        "content", "metadata_json",
    ],
    # Full-prompt audit trail for the sampled agents: every persona-facing
    # LLM call's exact (system_prompt, user_prompt, response). Joins to
    # agent_timeline by (agent_id, day, policy_id); ordered per agent by
    # prompt_seq. Sampled-only + final-only (see _CHECKPOINT_SKIP_KEYS).
    "agent_prompts": [
        "agent_id", "prompt_seq", "day", "phase", "stage", "policy_id",
        "system_prompt", "user_prompt", "response",
    ],
}

# Keys that are written only on the final save_results() call, never by
# per-day checkpoints. Diagnostic artefacts the simulation does NOT need
# to resume from (and which can be expensive to recompute every day).
_CHECKPOINT_SKIP_KEYS = frozenset({"agent_timeline", "persona_map", "agent_prompts"})


def _collect_results(nation, config):
    """Build DataFrames from agent state after simulation."""
    # Late import: these helpers live in cag.abm.sim. Importing them at
    # module top would create an import-time cycle because sim.py re-exports
    # this module's public surface at its EOF.
    from cag.abm.sim import (
        _get_package_policies,
        _is_package_mode,
        _safe_network_diagnostics,
        _safe_network_snapshot,
    )

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
    persona_map_raw = getattr(nation, "persona_map", None) or {}
    persona_mode = config.get("persona_mode", "real")
    persona_map_rows = [
        {
            "agent_id": agent_id,
            "source_agent_id": source_agent_id,
            "persona_mode": persona_mode,
        }
        for agent_id, source_agent_id in persona_map_raw.items()
    ]
    sample_ids = getattr(nation, "_prompt_capture_ids", None)
    if not sample_ids:
        sample_ids = _resolve_timeline_sample_ids(
            agent_attributes_df,
            sample_size=config.get("timeline_sample_size", 3),
            explicit_ids=config.get("timeline_sample_agent_ids"),
        )
    _sac_sample_set = set(sample_ids)

    prompt_rows = []
    for agent in nation.agents_active.values():
        for entry in getattr(agent, "prompt_log", None) or []:
            prompt_rows.append(entry)

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
        # survey_assembled_context is the heaviest per-agent artefact (the full
        # system prompt per survey call). Only the sampled agents' rows are ever
        # consumed (by agent_timeline), so gate the CSV to that sample - the
        # same set as agent_prompts / the timeline.
        "survey_assembled_context": pd.DataFrame(
            [r for r in survey_assembled_context_rows
             if r["agent_id"] in _sac_sample_set],
            columns=_RESULT_CSV_SCHEMAS["survey_assembled_context"],
        ),
        "daily_summaries": pd.DataFrame(
            daily_summary_rows,
            columns=_RESULT_CSV_SCHEMAS["daily_summaries"],
        ),
        "ground_truth": ground_truth_df,
        "package_ground_truth": package_ground_truth_df,
        "agent_attributes": agent_attributes_df,
        "persona_map": pd.DataFrame(
            persona_map_rows,
            columns=_RESULT_CSV_SCHEMAS["persona_map"],
        ),
        "config": config,
        "network_diagnostics": _safe_network_diagnostics(nation, config),
        "network_snapshot": _safe_network_snapshot(nation),
        "agent_prompts": pd.DataFrame(
            prompt_rows, columns=_RESULT_CSV_SCHEMAS["agent_prompts"],
        ),
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
    reached_a = set()
    reached_b = set()
    if getattr(nation, "political_agent_a", None) is not None:
        reached_a = {c.id for c in nation.political_agent_a.connected_citizens}
    if getattr(nation, "political_agent_b", None) is not None:
        reached_b = {c.id for c in nation.political_agent_b.connected_citizens}
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
            "reached_by_a": agent.id in reached_a,
            "reached_by_b": agent.id in reached_b,
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
            "bucket_summary": build_bucket_summary(results),
            "targeting_diagnostics": build_targeting_diagnostics(results),
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


def _serialise_config(config):
    """Make config JSON-safe by converting enums to strings.

    Also injects ``memory_resolved`` — the fully-expanded, validated memory
    / prompt-assembly config derived from the raw ``memory`` spec — so the
    saved ``config.json`` records the exact section toggles, verbatim
    window, and per-stage overrides the run used (the raw ``memory`` value
    may be just a preset name or a partial override dict).
    """
    from cag.abm.config.memory import resolve_memory_config

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
    out["memory_resolved"] = resolve_memory_config(config.get("memory"))
    return out
