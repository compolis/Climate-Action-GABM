#!/usr/bin/env python3
"""Analyse Run 12: reach-asymmetry HPC sweep (S / C1 / C3).

For each of the three runs, compute:

A) Headline trajectory: daily mean package index, Δ(Day7 − Day0).
B) Per-agent shift distribution (Day7 − Day0): mean, std, % movers.
C) Accuracy vs YouGov ground truth: aggregate bias, MAE, ρ on Day 0 and Day 7.
D) Reach effect: agent_a / agent_b broadcast recipient counts per day
   (from messages.csv) — confirms reach trims landed.
E) Reflection quality: count, length (tokens ~ word-count), unique-agent
   coverage, fraction mentioning policy-domain keywords.
F) Survey-reasoning quality: count, length, sample passages.
G) Persona diversity: vote / region / age distribution in the sampled cohort.
H) Peer-vs-broadcast message volume per day (peer-domination check).
I) Sample reflections and reasonings for spot-check.

Reads only the three pinned result dirs. Prints a single Markdown-friendly
report to stdout.
"""
import json
import re
import sys
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "data" / "output" / "experiments"

RUNS = {
    "S_symmetric":     EXP / "run_5985256_S_symmetric"       / "20260616_001620",
    "C1_reform_dom":   EXP / "run_5993181_C1_reform_dominant"/ "20260616_043552",
    "C3_green_dom":    EXP / "run_5993232_C3_green_dominant" / "20260616_043647",
}

POLICY_KEYWORDS = re.compile(
    r"\b(renewable|fossil|oil|gas|petrol|car|electric|EV|insulation|"
    r"insulate|home|cold|warm|tax|carbon|emissions|climate|compensation|"
    r"loss|damage|developing|finance|polluter|subsidy|subsidies|grid|"
    r"solar|wind|nuclear|coal|housing|heat)\b",
    re.IGNORECASE,
)


def load_run(path):
    return {
        "config":        json.loads((path / "config.json").read_text()),
        "opinions":      pd.read_csv(path / "opinion_trajectories.csv"),
        "package":       pd.read_csv(path / "package_index_trajectories.csv"),
        "gt":            pd.read_csv(path / "ground_truth.csv"),
        "pkg_gt":        pd.read_csv(path / "package_ground_truth.csv"),
        "reflections":   pd.read_csv(path / "reflections.csv"),
        "reasoning":     pd.read_csv(path / "survey_reasoning.csv"),
        "messages":      pd.read_csv(path / "messages.csv"),
        "summaries":     pd.read_csv(path / "daily_summaries.csv"),
    }


def section(title, char="="):
    bar = char * len(title)
    print(f"\n{bar}\n{title}\n{bar}")


def trajectory_summary(name, data):
    pkg = data["package"]
    daily = pkg.groupby("day")["package_index"].agg(["mean", "std", "count"]).round(3)
    return name, daily


def per_agent_shift(data):
    pkg = data["package"]
    pivot = pkg.pivot_table(index="agent_id", columns="day",
                            values="package_index", aggfunc="first")
    last_day = pivot.columns.max()
    delta = pivot[last_day] - pivot[0]
    return delta


def accuracy(data):
    """Aggregate bias / MAE / Pearson ρ between LLM and YouGov GT on each day."""
    pkg = data["package"]
    gt = data["pkg_gt"].set_index("agent_id")["ground_truth"]
    rows = []
    for day in sorted(pkg["day"].unique()):
        sub = pkg[pkg["day"] == day].set_index("agent_id")["package_index"]
        merged = pd.concat([sub.rename("llm"), gt.rename("gt")], axis=1).dropna()
        bias = float((merged["llm"] - merged["gt"]).mean())
        mae = float((merged["llm"] - merged["gt"]).abs().mean())
        rho = float(merged["llm"].corr(merged["gt"]))
        rows.append({"day": day, "bias": round(bias, 3),
                     "mae": round(mae, 3), "rho": round(rho, 3),
                     "n": len(merged)})
    return pd.DataFrame(rows)


def reach_check(data):
    msg = data["messages"]
    bc = msg[msg["message_type"] == "political_broadcast"]
    rows = []
    for day in sorted(bc["day"].unique()):
        for side in ("agent_a", "agent_b"):
            n_rec = bc[(bc["day"] == day) & (bc["sender_id"] == side)]["recipient_id"].nunique()
            rows.append({"day": day, "sender": side, "n_recipients": n_rec})
    return pd.DataFrame(rows)


def message_volume(data):
    msg = data["messages"]
    volume = msg.groupby(["day", "message_type"]).size().unstack(fill_value=0)
    return volume


def reflection_quality(data):
    refl = data["reflections"]
    refl["word_count"] = refl["text"].fillna("").apply(lambda s: len(s.split()))
    refl["mentions_policy"] = refl["text"].fillna("").apply(
        lambda s: bool(POLICY_KEYWORDS.search(s))
    )
    summary = {
        "n_reflections": len(refl),
        "n_agents_with_reflections": refl["agent_id"].nunique(),
        "mean_words": round(refl["word_count"].mean(), 1),
        "median_words": int(refl["word_count"].median()),
        "p10_words": int(refl["word_count"].quantile(0.10)),
        "p90_words": int(refl["word_count"].quantile(0.90)),
        "min_words": int(refl["word_count"].min()),
        "max_words": int(refl["word_count"].max()),
        "pct_mention_policy_kw": round(100 * refl["mentions_policy"].mean(), 1),
        "pct_empty": round(100 * (refl["word_count"] == 0).mean(), 1),
    }
    return summary, refl


def reasoning_quality(data):
    rs = data["reasoning"]
    rs["word_count"] = rs["reasoning"].fillna("").apply(lambda s: len(s.split()))
    rs["mentions_policy"] = rs["reasoning"].fillna("").apply(
        lambda s: bool(POLICY_KEYWORDS.search(s))
    )
    summary = {
        "n_reasonings": len(rs),
        "n_agents": rs["agent_id"].nunique(),
        "n_days": rs["day"].nunique(),
        "mean_words": round(rs["word_count"].mean(), 1),
        "median_words": int(rs["word_count"].median()),
        "p10_words": int(rs["word_count"].quantile(0.10)),
        "p90_words": int(rs["word_count"].quantile(0.90)),
        "pct_mention_policy_kw": round(100 * rs["mentions_policy"].mean(), 1),
        "pct_empty": round(100 * (rs["word_count"] == 0).mean(), 1),
    }
    return summary


def diversity_check(data):
    """Demographic spread from each agent's first-row reasoning is unavailable,
    but the ground-truth file gives us agent IDs. To show diversity of
    *opinion*, summarise the Day-0 package-index distribution across agents.
    """
    pkg = data["package"]
    day0 = pkg[pkg["day"] == 0]["package_index"]
    return {
        "n_agents": len(day0),
        "mean": round(day0.mean(), 3),
        "std": round(day0.std(), 3),
        "min": round(day0.min(), 3),
        "p25": round(day0.quantile(0.25), 3),
        "median": round(day0.median(), 3),
        "p75": round(day0.quantile(0.75), 3),
        "max": round(day0.max(), 3),
        "n_strong_support_ge_2": int((day0 >= 2.0).sum()),
        "n_support_pos": int((day0 > 0).sum()),
        "n_neutral_zero": int((day0 == 0).sum()),
        "n_oppose_neg": int((day0 < 0).sum()),
        "n_strong_oppose_le_neg2": int((day0 <= -2.0).sum()),
    }


def sample_passages(data, n=3, seed=42):
    """Pick a few reflections and reasonings to eyeball quality.

    Stratified: one strong supporter, one neutral, one opposer (by Day-0
    package index)."""
    pkg = data["package"]
    day0 = pkg[pkg["day"] == 0].set_index("agent_id")["package_index"]
    sorted_agents = day0.sort_values()
    picks = []
    if len(sorted_agents) >= 3:
        picks = [
            ("opposer (low Day-0)",  sorted_agents.index[0]),
            ("neutral (median)",     sorted_agents.index[len(sorted_agents) // 2]),
            ("supporter (high Day-0)", sorted_agents.index[-1]),
        ]
    out = []
    refl = data["reflections"]
    rs = data["reasoning"]
    for label, aid in picks:
        # one reflection from this agent (day 1 preferred)
        r_rows = refl[refl["agent_id"] == aid]
        r_text = r_rows["text"].iloc[0] if len(r_rows) else "(none)"
        # one reasoning (day 0, policy 1 preferred)
        rs_rows = rs[(rs["agent_id"] == aid) & (rs["day"] == 0)]
        rs_text = rs_rows["reasoning"].iloc[0] if len(rs_rows) else "(none)"
        gt_val = float(data["pkg_gt"].set_index("agent_id")["ground_truth"].get(aid, np.nan))
        out.append({
            "label": label,
            "agent_id": aid,
            "day0_pkg": float(day0[aid]),
            "gt_pkg": gt_val,
            "reflection_snippet": (r_text or "")[:600],
            "reasoning_snippet": (rs_text or "")[:600],
        })
    return out


def main():
    runs = {name: load_run(path) for name, path in RUNS.items()}

    # ── A: trajectory ─────────────────────────────────
    section("A — Headline package-index trajectory (mean across agents)")
    summaries = {}
    for name, d in runs.items():
        _, daily = trajectory_summary(name, d)
        summaries[name] = daily
        print(f"\n{name}:")
        print(daily.to_string())
    # combined Δ
    print("\nNet shift Day7 − Day0 (mean / median / std across agents):")
    for name, d in runs.items():
        delta = per_agent_shift(d)
        print(f"  {name:18s} mean={delta.mean():+.3f}  median={delta.median():+.3f}  "
              f"std={delta.std():.3f}  |Δ|≥0.5: {int((delta.abs() >= 0.5).sum())}/{len(delta)}  "
              f"|Δ|≥1.0: {int((delta.abs() >= 1.0).sum())}/{len(delta)}")

    # ── B: accuracy vs ground truth ───────────────────
    section("B — Accuracy vs YouGov package ground truth (per day)")
    for name, d in runs.items():
        acc = accuracy(d)
        print(f"\n{name}:")
        print(acc.to_string(index=False))

    # ── C: reach check ────────────────────────────────
    section("C — Broadcast reach landed correctly (unique recipients per day per agent)")
    for name, d in runs.items():
        rc = reach_check(d)
        wide = rc.pivot(index="day", columns="sender", values="n_recipients")
        print(f"\n{name} (config reach_a={d['config']['reach_a']}, reach_b={d['config']['reach_b']}):")
        print(wide.to_string())

    # ── D: peer-vs-broadcast volume ──────────────────
    section("D — Daily message volume (peer messaging vs broadcasts)")
    for name, d in runs.items():
        vol = message_volume(d)
        print(f"\n{name}:")
        print(vol.to_string())
        total = vol.sum().to_dict()
        if "peer_message" in total and "political_broadcast" in total:
            ratio = total["peer_message"] / max(total["political_broadcast"], 1)
            print(f"  totals: {total}  peer/broadcast = {ratio:.2f}")

    # ── E: reflection quality ────────────────────────
    section("E — Reflection quality (length, coverage, on-topic keywords)")
    for name, d in runs.items():
        s, _ = reflection_quality(d)
        print(f"\n{name}: {s}")

    # ── F: reasoning quality ─────────────────────────
    section("F — Survey-reasoning quality")
    for name, d in runs.items():
        s = reasoning_quality(d)
        print(f"\n{name}: {s}")

    # ── G: opinion diversity (Day 0) ─────────────────
    section("G — Day-0 opinion diversity (package index across agents)")
    for name, d in runs.items():
        s = diversity_check(d)
        print(f"\n{name}: {s}")

    # ── H: representative sample passages ────────────
    section("H — Sample reflections / reasonings (stratified by Day-0 view)")
    # only do this for the symmetric run — others are essentially identical
    # because of the shared seed
    name = "S_symmetric"
    d = runs[name]
    picks = sample_passages(d)
    for p in picks:
        print(f"\n[{p['label']}]  agent_id={p['agent_id']}  "
              f"Day0_pkg={p['day0_pkg']:+.2f}  GT_pkg={p['gt_pkg']:+.2f}")
        print(f"  REASONING (Day 0, Policy 1):")
        print("    " + p["reasoning_snippet"].replace("\n", "\n    "))
        print(f"  REFLECTION (first):")
        print("    " + p["reflection_snippet"].replace("\n", "\n    "))


if __name__ == "__main__":
    main()
