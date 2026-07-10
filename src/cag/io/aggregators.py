"""
Result aggregators for Climate-Action-GABM.

Pure DataFrame transforms over the dict returned by ``_collect_results``.
Extracted from ``cag.abm.sim`` in the 2026-06-22 refactor. All names are
re-exported from ``cag.abm.sim`` for backwards compatibility.
"""

__version__ = "0.9.0"

import json

import numpy as np
import pandas as pd


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


# ── Bucket-stratified builders ──────────────────────────────────

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


def build_bucket_summary(results):
    """One row per (run, bucket) end-of-run summary -- the cross-run seed.

    Columns: run_label, political_exposure, n_agents, day0_gt_mean, end_mean,
    drift, mae, rank_rho, reached_a, reached_b. A final ``TOTAL`` row pools
    all agents. Deliberately one-row-per-run-per-bucket so many run dirs
    concatenate straight into the dose-response / targeting figures.
    """
    columns = [
        "run_label", "political_exposure", "n_agents", "day0_gt_mean",
        "end_mean", "drift", "mae", "rank_rho", "reached_a", "reached_b",
    ]
    traj = results.get("package_index_trajectories")
    gt = results.get("package_ground_truth")
    attrs = results.get("agent_attributes")
    if (traj is None or traj.empty or gt is None or gt.empty
            or attrs is None or attrs.empty):
        return pd.DataFrame(columns=columns)

    cfg = results.get("config") or {}
    run_label = str(cfg.get("run_label") or "") if isinstance(cfg, dict) else ""

    end_day = int(traj["day"].max())
    end = traj[traj["day"] == end_day][["agent_id", "package_index"]]
    merged = end.merge(gt[["agent_id", "ground_truth"]], on="agent_id", how="inner")
    bucket_map = dict(zip(attrs["agent_id"], attrs["political_exposure"]))
    merged["political_exposure"] = merged["agent_id"].map(bucket_map)
    ra_map = dict(zip(attrs["agent_id"], attrs.get("reached_by_a", pd.Series(dtype=bool))))
    rb_map = dict(zip(attrs["agent_id"], attrs.get("reached_by_b", pd.Series(dtype=bool))))

    def _summarise(sub, label):
        n = len(sub)
        if n == 0:
            return None
        gt_vals = sub["ground_truth"].astype(float)
        end_vals = sub["package_index"].astype(float)
        if n >= 2 and gt_vals.nunique() > 1 and end_vals.nunique() > 1:
            rho = float(end_vals.corr(gt_vals, method="spearman"))
        else:
            rho = float("nan")
        return {
            "run_label": run_label,
            "political_exposure": label,
            "n_agents": n,
            "day0_gt_mean": float(gt_vals.mean()),
            "end_mean": float(end_vals.mean()),
            "drift": float(end_vals.mean() - gt_vals.mean()),
            "mae": float((end_vals - gt_vals).abs().mean()),
            "rank_rho": rho,
            "reached_a": int(sum(bool(ra_map.get(a, False)) for a in sub["agent_id"])),
            "reached_b": int(sum(bool(rb_map.get(a, False)) for a in sub["agent_id"])),
        }

    rows = []
    for bucket in _sorted_buckets(merged["political_exposure"].dropna().unique()):
        r = _summarise(merged[merged["political_exposure"] == bucket], bucket)
        if r is not None:
            rows.append(r)
    total = _summarise(merged, "TOTAL")
    if total is not None:
        rows.append(total)
    return pd.DataFrame(rows, columns=columns)


def build_targeting_diagnostics(results):
    """Per-side reach-targeting diagnostic: did targeting select who we meant?

    For each political side, compares the reached audience against the
    side's structural-audience members who were NOT reached, on mean
    |ground-truth package index| (persuadable targeting keeps the smaller
    |GT|; a random/full-reach side shows an empty dropped set). One row per
    side; empty when there is no reach data.
    """
    columns = [
        "side", "targeting_mode", "reach", "n_audience", "n_reached",
        "n_dropped", "reached_mean_absgt", "dropped_mean_absgt",
    ]
    attrs = results.get("agent_attributes")
    gt = results.get("package_ground_truth")
    if attrs is None or attrs.empty or gt is None or gt.empty:
        return pd.DataFrame(columns=columns)
    cfg = results.get("config") or {}
    if not isinstance(cfg, dict):
        cfg = {}

    absgt = dict(zip(gt["agent_id"], gt["ground_truth"].astype(float).abs()))

    def _mean_abs(sub):
        vals = [absgt[a] for a in sub["agent_id"] if a in absgt]
        return float(sum(vals) / len(vals)) if vals else float("nan")

    rows = []
    for side, reached_col, audience, mode_key, reach_key in (
        ("A", "reached_by_a", {"A-only", "both"}, "reach_targeting_a", "reach_a"),
        ("B", "reached_by_b", {"B-only", "both"}, "reach_targeting_b", "reach_b"),
    ):
        if reached_col not in attrs.columns:
            continue
        aud = attrs[attrs["political_exposure"].isin(audience)]
        if aud.empty:
            continue
        reached = aud[aud[reached_col].astype(bool)]
        dropped = aud[~aud[reached_col].astype(bool)]
        rows.append({
            "side": side,
            "targeting_mode": str(cfg.get(mode_key, "random")),
            "reach": float(cfg.get(reach_key, 1.0)),
            "n_audience": len(aud),
            "n_reached": len(reached),
            "n_dropped": len(dropped),
            "reached_mean_absgt": _mean_abs(reached),
            "dropped_mean_absgt": _mean_abs(dropped),
        })
    return pd.DataFrame(rows, columns=columns)


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
    # Late import: _RESULT_CSV_SCHEMAS lives in cag.io.results. Top-level
    # would create an import-time cycle (results imports the builders in
    # this module at top level).
    from cag.io.results import _RESULT_CSV_SCHEMAS

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
