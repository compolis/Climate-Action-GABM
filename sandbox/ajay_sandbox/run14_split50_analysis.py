#!/usr/bin/env python3
"""Analyse R14: split-50 persuasion responsiveness on Qwen3-8B.

Three runs:
  * R14_split50_5day            (anchor=GT, targets 50/50/0/0, 5 days)
  * R14_neither_5day            (anchor=GT, targets 0/0/0/100, 5 days — matched baseline)
  * R14_split50_5day_anchor_llm (anchor=LLM, targets 50/50/0/0, 4 days completed)

Key questions:
  1. Does the A-only cohort move UP and B-only cohort move DOWN
     relative to the matched-horizon neither baseline? (persuasion test)
  2. Does the LLM-anchored split50 produce wider spread than the GT-anchored
     one? (anchor-freezing test)
  3. Reflection / reasoning quality across runs.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "data" / "output" / "experiments"

# Outdir layouts differ: split50 + neither have a timestamped subfolder;
# anchor_llm has its CSVs in checkpoints/ (run never completed final save).
RUNS = {
    "split50":     EXP / "run_6202348_R14_split50_5day"            / "20260619_192129",
    "neither":     EXP / "run_6203838_R14_neither_5day"            / "20260619_184539",
    "anchor_llm":  EXP / "run_6204291_R14_split50_5day_anchor_llm" / "checkpoints",
}

POLICY_KEYWORDS = re.compile(
    r"\b(renewable|fossil|oil|gas|petrol|car|electric|EV|insulation|"
    r"insulate|home|cold|warm|tax|carbon|emissions|climate|compensation|"
    r"loss|damage|developing|finance|polluter|subsidy|subsidies|grid|"
    r"solar|wind|nuclear|coal|housing|heat)\b",
    re.IGNORECASE,
)


def load_run(path, name):
    config_path = path / "config.json"
    if not config_path.exists():
        # anchor_llm: pull config out of checkpoint_meta.json
        meta = json.loads((path / "checkpoint_meta.json").read_text())
        config = meta["config"]
        config["_last_completed_day"] = int(meta["last_completed_day"])
    else:
        config = json.loads(config_path.read_text())
        config["_last_completed_day"] = None
    return {
        "name":        name,
        "path":        path,
        "config":      config,
        "opinions":    pd.read_csv(path / "opinion_trajectories.csv"),
        "package":     pd.read_csv(path / "package_index_trajectories.csv"),
        "gt":          pd.read_csv(path / "ground_truth.csv"),
        "pkg_gt":      pd.read_csv(path / "package_ground_truth.csv"),
        "reflections": pd.read_csv(path / "reflections.csv"),
        "reasoning":   pd.read_csv(path / "survey_reasoning.csv"),
        "messages":    pd.read_csv(path / "messages.csv"),
        "summaries":   pd.read_csv(path / "daily_summaries.csv"),
    }


def section(title, ch="="):
    print(f"\n{ch * len(title)}\n{title}\n{ch * len(title)}")


def trajectory(data):
    return data["package"].groupby("day")["package_index"].agg(["mean", "std", "count"]).round(3)


def per_agent_shift(data):
    pkg = data["package"]
    pivot = pkg.pivot_table(index="agent_id", columns="day",
                            values="package_index", aggfunc="first")
    last = pivot.columns.max()
    return pivot[last] - pivot[0]


def accuracy(data):
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
                     "mae": round(mae, 3), "rho": round(rho, 3), "n": len(merged)})
    return pd.DataFrame(rows)


def audience_table(data):
    msg = data["messages"]
    bc = msg[msg["message_type"] == "political_broadcast"]
    rows = []
    for day in sorted(bc["day"].unique()):
        for side in ("agent_a", "agent_b"):
            rows.append({
                "day": day, "sender": side,
                "n_recipients": bc[(bc["day"] == day) & (bc["sender_id"] == side)]["recipient_id"].nunique(),
            })
    if not rows:
        return pd.DataFrame(columns=["agent_a", "agent_b"])
    return pd.DataFrame(rows).pivot(index="day", columns="sender", values="n_recipients")


def message_volume(data):
    msg = data["messages"]
    return msg.groupby(["day", "message_type"]).size().unstack(fill_value=0)


def reflection_quality(data):
    r = data["reflections"].copy()
    r["wc"] = r["text"].fillna("").apply(lambda s: len(s.split()))
    r["kw"] = r["text"].fillna("").apply(lambda s: bool(POLICY_KEYWORDS.search(s)))
    return {
        "n": len(r),
        "agents": r["agent_id"].nunique(),
        "median_words": int(r["wc"].median()) if len(r) else 0,
        "p10_words": int(r["wc"].quantile(0.10)) if len(r) else 0,
        "p90_words": int(r["wc"].quantile(0.90)) if len(r) else 0,
        "pct_kw": round(100 * r["kw"].mean(), 1) if len(r) else 0.0,
        "pct_empty": round(100 * (r["wc"] == 0).mean(), 1) if len(r) else 0.0,
    }


def reasoning_quality(data):
    r = data["reasoning"].copy()
    r["wc"] = r["reasoning"].fillna("").apply(lambda s: len(s.split()))
    r["kw"] = r["reasoning"].fillna("").apply(lambda s: bool(POLICY_KEYWORDS.search(s)))
    return {
        "n": len(r),
        "agents": r["agent_id"].nunique(),
        "days": r["day"].nunique(),
        "median_words": int(r["wc"].median()),
        "p10_words": int(r["wc"].quantile(0.10)),
        "p90_words": int(r["wc"].quantile(0.90)),
        "pct_kw": round(100 * r["kw"].mean(), 1),
        "pct_empty": round(100 * (r["wc"] == 0).mean(), 1),
    }


def bucket_from_messages(data):
    """Infer per-agent exposure bucket from messages.csv broadcasts."""
    msg = data["messages"]
    bc = msg[msg["message_type"] == "political_broadcast"]
    rec_a = set(bc[bc["sender_id"] == "agent_a"]["recipient_id"].unique())
    rec_b = set(bc[bc["sender_id"] == "agent_b"]["recipient_id"].unique())
    all_agents = set(data["package"]["agent_id"].unique())

    bucket_of = {}
    for aid in all_agents:
        a, b = aid in rec_a, aid in rec_b
        if a and b:
            bucket_of[aid] = "both"
        elif a:
            bucket_of[aid] = "A-only"
        elif b:
            bucket_of[aid] = "B-only"
        else:
            bucket_of[aid] = "neither"
    return bucket_of


def conditional_shift(data, last_day=None):
    """Bias / shift / accuracy per exposure bucket, at a chosen end-day."""
    pkg = data["package"].copy()
    if last_day is None:
        last_day = pkg["day"].max()

    bucket_of = bucket_from_messages(data)
    pkg["bucket"] = pkg["agent_id"].map(bucket_of)
    gt = data["pkg_gt"].set_index("agent_id")["ground_truth"]

    rows = []
    for bk, sub in pkg.groupby("bucket"):
        d0 = sub[sub["day"] == 0].set_index("agent_id")["package_index"]
        dN = sub[sub["day"] == last_day].set_index("agent_id")["package_index"]
        merged = pd.concat(
            [dN.rename("llm"), gt.rename("gt"), d0.rename("d0")],
            axis=1,
        ).dropna()
        if not len(merged):
            continue
        rows.append({
            "bucket": bk,
            "n": len(merged),
            "mean_d0": round(merged["d0"].mean(), 3),
            "mean_dN": round(merged["llm"].mean(), 3),
            "mean_shift": round((merged["llm"] - merged["d0"]).mean(), 3),
            "std_shift": round((merged["llm"] - merged["d0"]).std(), 3),
            "bias_vs_gt": round((merged["llm"] - merged["gt"]).mean(), 3),
            "mae_vs_gt":  round((merged["llm"] - merged["gt"]).abs().mean(), 3),
        })
    return pd.DataFrame(rows).sort_values("bucket")


def per_day_bucket_means(data):
    """Mean package_index per (day, bucket) — for plotting trajectory by bucket."""
    bucket_of = bucket_from_messages(data)
    pkg = data["package"].copy()
    pkg["bucket"] = pkg["agent_id"].map(bucket_of)
    return pkg.groupby(["day", "bucket"])["package_index"].mean().unstack().round(3)


def sample_passages(data, n=3, last_day=None):
    pkg = data["package"]
    if last_day is None:
        last_day = pkg["day"].max()
    day0 = pkg[pkg["day"] == 0].set_index("agent_id")["package_index"]
    s = day0.sort_values()
    picks = [
        ("opposer (low Day-0)",   s.index[0]),
        ("neutral (median)",      s.index[len(s) // 2]),
        ("supporter (high Day-0)", s.index[-1]),
    ]
    out = []
    refl = data["reflections"]
    rs = data["reasoning"]
    bucket_of = bucket_from_messages(data)
    for label, aid in picks:
        rt = refl[refl["agent_id"] == aid]["text"]
        st = rs[(rs["agent_id"] == aid) & (rs["day"] == 0)]["reasoning"]
        end_st = rs[(rs["agent_id"] == aid) & (rs["day"] == last_day)]["reasoning"]
        dN_row = pkg[(pkg["agent_id"] == aid) & (pkg["day"] == last_day)]
        out.append({
            "label": label,
            "agent_id": aid,
            "bucket": bucket_of.get(aid, "?"),
            "day0": float(day0[aid]),
            "dN": float(dN_row["package_index"].iloc[0]) if len(dN_row) else float("nan"),
            "gt": float(data["pkg_gt"].set_index("agent_id")["ground_truth"].get(aid, np.nan)),
            "refl": (rt.iloc[0] if len(rt) else "")[:700],
            "reason_d0": (st.iloc[0] if len(st) else "")[:600],
            "reason_dN": (end_st.iloc[0] if len(end_st) else "")[:600],
        })
    return out


def main():
    runs = {n: load_run(p, n) for n, p in RUNS.items()}

    # ── A. Headline trajectory per run ─────────────────────────────
    section("A — Daily mean package_index (all agents)")
    for n, d in runs.items():
        last = d["config"]["_last_completed_day"]
        suffix = f" [LIVE THROUGH DAY {last}]" if last is not None else ""
        print(f"\n{n}{suffix}:")
        print(trajectory(d).to_string())

    # ── A2. Per-agent net shift ─────────────────────────────────────
    section("A2 — Net per-agent shift (Day_last − Day_0)")
    for n, d in runs.items():
        delta = per_agent_shift(d).dropna()
        print(f"  {n:12s} n={len(delta):3d}  mean={delta.mean():+.3f}  "
              f"median={delta.median():+.3f}  std={delta.std():.3f}  "
              f"|Δ|≥0.5: {int((delta.abs() >= 0.5).sum())}/{len(delta)}  "
              f"|Δ|≥1.0: {int((delta.abs() >= 1.0).sum())}/{len(delta)}")

    # ── B. Bucket trajectory (the headline test) ──────────────────
    section("B — Daily mean by exposure bucket (the persuasion test)")
    for n, d in runs.items():
        print(f"\n{n}:")
        print(per_day_bucket_means(d).to_string())

    # ── C. End-day bucket summary + matched-baseline subtraction ──
    section("C — End-day bucket summary (mean_d0, mean_dN, shift, bias)")
    cond_tables = {}
    for n, d in runs.items():
        last = d["package"]["day"].max()
        ct = conditional_shift(d, last_day=last)
        cond_tables[n] = ct
        print(f"\n{n} (last day = {last}):")
        print(ct.to_string(index=False))

    # Matched persuasion subtraction at Day 5
    section("C2 — Persuasion = split50.bucket.Δ − neither.cohort.Δ (Day 5)")
    s_ct = cond_tables["split50"].set_index("bucket")
    n_ct = cond_tables["neither"].set_index("bucket")
    baseline_shift = float(n_ct.loc["neither", "mean_shift"])
    print(f"  Neither-baseline cohort shift (Day 0 → Day 5): {baseline_shift:+.3f}")
    for bk in ("A-only", "B-only"):
        if bk in s_ct.index:
            persuasion = float(s_ct.loc[bk, "mean_shift"]) - baseline_shift
            print(f"  {bk:8s} persuasion = {s_ct.loc[bk, 'mean_shift']:+.3f} - "
                  f"{baseline_shift:+.3f} = {persuasion:+.3f}  "
                  f"(n={int(s_ct.loc[bk, 'n'])})")

    # ── D. Accuracy vs ground truth ────────────────────────────────
    section("D — Accuracy vs YouGov ground truth (per day)")
    for n, d in runs.items():
        print(f"\n{n}:")
        print(accuracy(d).to_string(index=False))

    # ── E. Anchor comparison: GT vs LLM, at Day 0 only ─────────────
    section("E — Day 0 anchor comparison: GT-anchored vs LLM-anchored")
    rows = []
    for n in ("split50", "anchor_llm"):
        d = runs[n]
        d0 = d["package"][d["package"]["day"] == 0].set_index("agent_id")["package_index"]
        gt = d["pkg_gt"].set_index("agent_id")["ground_truth"]
        merged = pd.concat([d0.rename("llm"), gt.rename("gt")], axis=1).dropna()
        rows.append({
            "run": n,
            "anchor": d["config"]["day0_anchor"],
            "mean_d0":   round(d0.mean(), 3),
            "std_d0":    round(d0.std(),  3),
            "min_d0":    round(d0.min(),  3),
            "max_d0":    round(d0.max(),  3),
            "bias_vs_gt": round((merged["llm"] - merged["gt"]).mean(), 3),
            "mae_vs_gt":  round((merged["llm"] - merged["gt"]).abs().mean(), 3),
            "rho_vs_gt":  round(merged["llm"].corr(merged["gt"]), 3),
        })
    print(pd.DataFrame(rows).to_string(index=False))

    # ── F. Anchor comparison: end-of-run spread per bucket ─────────
    section("F — End-of-run bucket means: GT-anchored vs LLM-anchored")
    print("  (compare split50 Day 5 vs anchor_llm Day 4 — different horizons)")
    for n in ("split50", "anchor_llm"):
        d = runs[n]
        last = d["package"]["day"].max()
        bm = per_day_bucket_means(d).loc[last]
        print(f"  {n:12s} Day {last}: " +
              "  ".join(f"{k}={v:+.3f}" for k, v in bm.items()))

    # Apples-to-apples: also compare split50 at Day 4 vs anchor_llm Day 4
    section("F2 — Matched horizon: both at Day 4")
    for n in ("split50", "anchor_llm"):
        d = runs[n]
        if 4 in d["package"]["day"].unique():
            bm = per_day_bucket_means(d).loc[4]
            print(f"  {n:12s} Day 4: " +
                  "  ".join(f"{k}={v:+.3f}" for k, v in bm.items()))

    # ── G. Broadcast audience landing ──────────────────────────────
    section("G — Broadcast reach landed per day")
    for n, d in runs.items():
        print(f"\n{n} (reach_a={d['config']['reach_a']}, reach_b={d['config']['reach_b']}, "
              f"targets={d['config']['political_exposure_targets']}):")
        at = audience_table(d)
        if at.empty:
            print("  (no broadcasts — targets force neither)")
        else:
            print(at.to_string())

    # ── H. Per-day message volume (confirm peers=0) ───────────────
    section("H — Per-day message volume (confirm k_peers=0 → zero peer rows)")
    for n, d in runs.items():
        print(f"\n{n}:")
        print(message_volume(d).to_string())

    # ── I. Reflection + reasoning quality ─────────────────────────
    section("I — Reflection quality")
    for n, d in runs.items():
        print(f"  {n:12s} {reflection_quality(d)}")

    section("J — Survey-reasoning quality")
    for n, d in runs.items():
        print(f"  {n:12s} {reasoning_quality(d)}")

    # ── K. Sample passages, split50 only (the persuasion story) ───
    section("K — Sample passages from split50 (stratified by Day-0)")
    for p in sample_passages(runs["split50"]):
        print(f"\n[{p['label']}]  agent={p['agent_id']}  bucket={p['bucket']}  "
              f"Day0={p['day0']:+.2f}  Day5={p['dN']:+.2f}  GT={p['gt']:+.2f}")
        print(f"  Day-0 reasoning:")
        print("    " + p['reason_d0'].replace("\n", "\n    "))
        print(f"  Day-5 reasoning:")
        print("    " + p['reason_dN'].replace("\n", "\n    "))
        print(f"  First reflection:")
        print("    " + p['refl'].replace("\n", "\n    "))

    # ── L. Sample passages, anchor_llm (does free Day-0 unlock movement?) ─
    section("L — Sample passages from anchor_llm (free Day-0)")
    for p in sample_passages(runs["anchor_llm"]):
        print(f"\n[{p['label']}]  agent={p['agent_id']}  bucket={p['bucket']}  "
              f"Day0={p['day0']:+.2f}  Day4={p['dN']:+.2f}  GT={p['gt']:+.2f}")
        print(f"  Day-0 reasoning:")
        print("    " + p['reason_d0'].replace("\n", "\n    "))
        print(f"  Day-4 reasoning:")
        print("    " + p['reason_dN'].replace("\n", "\n    "))


if __name__ == "__main__":
    main()
