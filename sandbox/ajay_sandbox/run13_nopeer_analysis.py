#!/usr/bin/env python3
"""Analyse Run 13: reach-asymmetry sweep with PEERS OFF + 5/5/50/40 exposure.

Same dimensions as run12_asymmetry_analysis.py, plus a side-by-side
comparison vs the Run 12 (peers-on) sweep.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "data" / "output" / "experiments"

# Run 13 (peers off, 5/5/50/40 targets)
RUNS_R13 = {
    "S_nopeer":   EXP / "run_6045935_S_symmetric_nopeer"        / "20260617_010957",
    "C1_nopeer":  EXP / "run_6046803_C1_reform_dominant_nopeer" / "20260617_005519",
    "C3_nopeer":  EXP / "run_6046804_C3_green_dominant_nopeer"  / "20260617_005418",
}
# Run 12 (peers on, default 11/11/33/45 targets) — for side-by-side
RUNS_R12 = {
    "S_peer":   EXP / "run_5985256_S_symmetric"         / "20260616_001620",
    "C1_peer":  EXP / "run_5993181_C1_reform_dominant"  / "20260616_043552",
    "C3_peer":  EXP / "run_5993232_C3_green_dominant"   / "20260616_043647",
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
        "path":          path,
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


def conditional_accuracy(data):
    """Bias / MAE / Δ Day7−Day0 split by which broadcasts each agent was exposed
    to. Uses messages.csv to infer per-agent receipt set (any agent who is in
    political_broadcast recipient_id for sender X is 'received X')."""
    msg = data["messages"]
    bc = msg[msg["message_type"] == "political_broadcast"]
    rec_a = set(bc[bc["sender_id"] == "agent_a"]["recipient_id"].unique())
    rec_b = set(bc[bc["sender_id"] == "agent_b"]["recipient_id"].unique())

    def bucket(aid):
        a, b = aid in rec_a, aid in rec_b
        if a and b: return "both"
        if a: return "A-only"
        if b: return "B-only"
        return "neither"

    pkg = data["package"].copy()
    pkg["bucket"] = pkg["agent_id"].apply(bucket)
    gt = data["pkg_gt"].set_index("agent_id")["ground_truth"]
    last_day = pkg["day"].max()

    rows = []
    for bk, sub in pkg.groupby("bucket"):
        d0 = sub[sub["day"] == 0].set_index("agent_id")["package_index"]
        dN = sub[sub["day"] == last_day].set_index("agent_id")["package_index"]
        merged = pd.concat([dN.rename("llm"), gt.rename("gt"), d0.rename("d0")], axis=1).dropna()
        if not len(merged):
            continue
        rows.append({
            "bucket": bk,
            "n": len(merged),
            "mean_d0": round(merged["d0"].mean(), 3),
            "mean_dN": round(merged["llm"].mean(), 3),
            "mean_shift": round((merged["llm"] - merged["d0"]).mean(), 3),
            "bias_vs_gt": round((merged["llm"] - merged["gt"]).mean(), 3),
        })
    return pd.DataFrame(rows).sort_values("bucket")


def sample_passages(data, n=3):
    pkg = data["package"]
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
    last_day = pkg["day"].max()
    for label, aid in picks:
        rt = refl[refl["agent_id"] == aid]["text"]
        st = rs[(rs["agent_id"] == aid) & (rs["day"] == 0)]["reasoning"]
        end_st = rs[(rs["agent_id"] == aid) & (rs["day"] == last_day)]["reasoning"]
        out.append({
            "label": label,
            "agent_id": aid,
            "day0": float(day0[aid]),
            "dN": float(pkg[(pkg["agent_id"] == aid) & (pkg["day"] == last_day)]["package_index"].iloc[0]),
            "gt": float(data["pkg_gt"].set_index("agent_id")["ground_truth"].get(aid, np.nan)),
            "refl": (rt.iloc[0] if len(rt) else "")[:700],
            "reason_d0": (st.iloc[0] if len(st) else "")[:600],
            "reason_dN": (end_st.iloc[0] if len(end_st) else "")[:600],
        })
    return out


def main():
    r13 = {n: load_run(p) for n, p in RUNS_R13.items()}
    r12 = {n: load_run(p) for n, p in RUNS_R12.items()}

    section("A — Daily mean package index, peers-off (Run 13)")
    for n, d in r13.items():
        print(f"\n{n}:")
        print(trajectory(d).to_string())

    section("A2 — Net shift Day7 − Day0 across agents")
    for n, d in r13.items():
        delta = per_agent_shift(d)
        print(f"  {n:14s} mean={delta.mean():+.3f}  median={delta.median():+.3f}  "
              f"std={delta.std():.3f}  |Δ|≥0.5: {int((delta.abs() >= 0.5).sum())}/{len(delta)}  "
              f"|Δ|≥1.0: {int((delta.abs() >= 1.0).sum())}/{len(delta)}")

    section("B — Accuracy vs YouGov package ground truth (Run 13)")
    for n, d in r13.items():
        print(f"\n{n}:")
        print(accuracy(d).to_string(index=False))

    section("C — Broadcast reach landed (Run 13)")
    for n, d in r13.items():
        print(f"\n{n} (reach_a={d['config']['reach_a']}, reach_b={d['config']['reach_b']}):")
        print(audience_table(d).to_string())

    section("D — Per-day message volume (Run 13; confirm peers=0)")
    for n, d in r13.items():
        print(f"\n{n}:")
        print(message_volume(d).to_string())

    section("E — Reflection quality (Run 13)")
    for n, d in r13.items():
        print(f"  {n:14s} {reflection_quality(d)}")

    section("F — Survey-reasoning quality (Run 13)")
    for n, d in r13.items():
        print(f"  {n:14s} {reasoning_quality(d)}")

    section("G — Conditional shift by exposure bucket (the key asymmetry test)")
    for n, d in r13.items():
        print(f"\n{n}:")
        print(conditional_accuracy(d).to_string(index=False))

    section("H — Run 12 vs Run 13: aggregate trajectory comparison")
    rows = []
    for label, runs in (("peer", r12), ("nopeer", r13)):
        for cond in ("S", "C1", "C3"):
            key = f"{cond}_{label}"
            t = trajectory(runs[key])
            rows.append({
                "run": key,
                "day0": t.loc[0, "mean"],
                "day1": t.loc[1, "mean"],
                "day7": t.loc[7, "mean"],
                "max_day": float(t["mean"].max()),
                "min_day": float(t["mean"].min()),
                "spread": float(t["mean"].max() - t["mean"].min()),
            })
    print(pd.DataFrame(rows).to_string(index=False))

    section("I — Run 12 vs Run 13: accuracy & shift (Day 7)")
    rows = []
    for label, runs in (("peer", r12), ("nopeer", r13)):
        for cond in ("S", "C1", "C3"):
            d = runs[f"{cond}_{label}"]
            a = accuracy(d).set_index("day").loc[7]
            delta = per_agent_shift(d)
            rows.append({
                "run": f"{cond}_{label}",
                "bias_d7": a["bias"], "mae_d7": a["mae"], "rho_d7": a["rho"],
                "mean_delta": round(delta.mean(), 3),
                "median_delta": round(delta.median(), 3),
                "std_delta": round(delta.std(), 3),
            })
    print(pd.DataFrame(rows).to_string(index=False))

    section("J — Sample passages from S_nopeer (stratified by Day-0)")
    for p in sample_passages(r13["S_nopeer"]):
        print(f"\n[{p['label']}]  agent={p['agent_id']}  "
              f"Day0={p['day0']:+.2f}  Day7={p['dN']:+.2f}  GT={p['gt']:+.2f}")
        print(f"  Day-0 reasoning (Policy 1):")
        print("    " + p['reason_d0'].replace("\n", "\n    "))
        print(f"  Day-7 reasoning (Policy 1):")
        print("    " + p['reason_dN'].replace("\n", "\n    "))
        print(f"  First reflection:")
        print("    " + p['refl'].replace("\n", "\n    "))


if __name__ == "__main__":
    main()
