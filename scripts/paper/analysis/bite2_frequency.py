#!/usr/bin/env python3
"""Bite 2 (Frequency asymmetry) analysis for the draft-45 paper.

SBM, full reach (reach_a=reach_b=1.0). Lever = broadcast COUNT per side.
Conditions (x3 seeds 42/43/44):
  green2v1  P-A twice, P-B once   (Green louder 2:1)
  green3v1  P-A x3,   P-B once    (Green louder 3:1)
  reform1v2 P-B twice, P-A once   (Reform louder 2:1)
  reform1v3 P-B x3,   P-A once    (Reform louder 3:1)

No symmetric 1:1 baseline in-folder -> primary contrast is matched-ratio,
green-louder minus reform-louder, paired within seed:
  2:1 ratio: green2v1 - reform1v2
  3:1 ratio: green3v1 - reform1v3

Metric contract (locked 2026-07-09): primary outcome = mean package index on
-3..+3; effect = within-person difference in FINAL opinion (scale points, 95% CI)
pooled over 3 seeds (pair within seed, never cross-seed). Companion = support/
oppose shares. Validation = Spearman rho + signed bias. Reliability = same sign
in every seed. DiD reduces to a paired endpoint difference because Day 0 is
pinned to ground truth in every condition.

Run: .venv/bin/python sandbox/ajay_sandbox/bite2_frequency.py
"""
from pathlib import Path
import re
import numpy as np
import pandas as pd
from scipy import stats

EXP = Path(__file__).resolve().parents[3] / "data/output/asymmetry_tests"

PAT = re.compile(r"run_(\d+)_d45_freq_(green2v1|green3v1|reform1v2|reform1v3)_s(\d+)$")


def discover():
    rows = []
    for d in sorted(EXP.iterdir()):
        if not d.is_dir():
            continue
        m = PAT.match(d.name)
        if not m:
            continue
        sub = sorted([p for p in d.iterdir() if p.is_dir()])
        if not sub:
            continue
        rows.append({"jobid": m.group(1), "condition": m.group(2),
                     "seed": int(m.group(3)), "path": sub[-1]})
    return pd.DataFrame(rows)


def load_pkg(path):
    pkg = pd.read_csv(path / "package_index_trajectories.csv")
    gt = pd.read_csv(path / "package_ground_truth.csv").set_index("agent_id")["ground_truth"]
    attr = pd.read_csv(path / "agent_attributes.csv").set_index("agent_id")["political_exposure"]
    days = sorted(pkg["day"].unique())
    d0, dN = days[0], days[-1]
    start = pkg[pkg.day == d0].set_index("agent_id")["package_index"]
    end = pkg[pkg.day == dN].set_index("agent_id")["package_index"]
    df = pd.DataFrame({"start": start, "end": end, "gt": gt, "bucket": attr}).dropna()
    df["shift"] = df["end"] - df["start"]
    return df.reset_index()


def mean_ci(d):
    d = np.asarray(d, dtype=float)
    m = d.mean()
    se = d.std(ddof=1) / np.sqrt(len(d))
    h = se * stats.t.ppf(0.975, len(d) - 1)
    return m, m - h, m + h


runs = discover()
print("Discovered runs:")
print(runs[["condition", "seed", "jobid"]].sort_values(["condition", "seed"]).to_string(index=False))
assert len(runs) == 12, f"expected 12, got {len(runs)}"

frames = []
for _, r in runs.iterrows():
    f = load_pkg(r["path"])
    f["condition"] = r["condition"]
    f["seed"] = r["seed"]
    frames.append(f)
S = pd.concat(frames, ignore_index=True)


def paired_diff(cg, cr, bucket=None):
    """Within-person endpoint difference cg - cr, pooled over seeds (paired within seed)."""
    diffs = []
    per_seed = {}
    for seed in sorted(S.seed.unique()):
        sub = S[S.seed == seed]
        if bucket:
            sub = sub[sub.bucket == bucket]
        a = sub[sub.condition == cg][["agent_id", "end", "gt"]].rename(columns={"end": "eg"})
        b = sub[sub.condition == cr][["agent_id", "end"]].rename(columns={"end": "er"})
        m = a.merge(b, on="agent_id")
        d = (m["eg"] - m["er"]).to_numpy()
        diffs.append(pd.DataFrame({"d": d, "gt": m["gt"].to_numpy(), "seed": seed}))
        per_seed[seed] = float(np.mean(d))
    D = pd.concat(diffs, ignore_index=True)
    mean, lo, hi = mean_ci(D["d"])
    t, p = stats.ttest_1samp(D["d"], 0.0)
    slope = np.polyfit(D["gt"], D["d"], 1)[0]
    return {"n": len(D), "diff": mean, "lo": lo, "hi": hi, "p": p,
            "per_seed": per_seed, "slope_gt": slope}


def shares(cond):
    sub = S[S.condition == cond]
    sup = (sub["end"] > 0).mean() * 100
    opp = (sub["end"] < 0).mean() * 100
    neu = (sub["end"] == 0).mean() * 100
    return sup, neu, opp


print("\n" + "=" * 78)
print("PRIMARY: within-person difference in FINAL package index (green-louder - reform-louder)")
print("  positive => Green's extra broadcasts move opinion more pro-climate than Reform's")
print("=" * 78)
for label, cg, cr in [("2:1 ratio", "green2v1", "reform1v2"),
                       ("3:1 ratio", "green3v1", "reform1v3")]:
    r = paired_diff(cg, cr)
    ps = "  ".join(f"s{k}={v:+.3f}" for k, v in r["per_seed"].items())
    signs = {np.sign(v) for v in r["per_seed"].values()}
    same = "SAME SIGN" if len(signs) == 1 else "MIXED SIGN"
    print(f"\n{label}: {cg} - {cr}   (n={r['n']} pooled over 3 seeds)")
    print(f"  diff = {r['diff']:+.3f} points  95% CI [{r['lo']:+.3f}, {r['hi']:+.3f}]  p={r['p']:.2e}")
    print(f"  per-seed: {ps}   [{same}]")
    print(f"  slope(diff ~ ground truth) = {r['slope_gt']:+.3f}  (~0 => effect uniform across spectrum)")

print("\n" + "=" * 78)
print('AMONG THE MAJORITY WHO HEAR BOTH SIDES (the ~60% "both" bucket)')
print("=" * 78)
for label, cg, cr in [("2:1 ratio", "green2v1", "reform1v2"),
                       ("3:1 ratio", "green3v1", "reform1v3")]:
    r = paired_diff(cg, cr, bucket="both")
    print(f"{label}: {cg} - {cr}   diff = {r['diff']:+.3f}  95% CI [{r['lo']:+.3f}, {r['hi']:+.3f}]  p={r['p']:.2e}  (n={r['n']})")

print("\n" + "=" * 78)
print("PER-CONDITION endpoint mean, support/oppose shares, and validation (pooled 3 seeds)")
print("=" * 78)
print(f"{'condition':11s} {'end_mean':>9s} {'support%':>9s} {'oppose%':>8s} {'rho(end,gt)':>12s} {'bias':>7s}")
for cond in ["green3v1", "green2v1", "reform1v2", "reform1v3"]:
    sub = S[S.condition == cond]
    end_mean = sub["end"].mean()
    sup, neu, opp = shares(cond)
    rho = stats.spearmanr(sub["end"], sub["gt"]).correlation
    bias = sub["end"].mean() - sub["gt"].mean()
    print(f"{cond:11s} {end_mean:>+9.3f} {sup:>8.1f} {opp:>8.1f} {rho:>12.3f} {bias:>+7.3f}")

# Ground-truth anchor (same 100 agents per seed; report pooled)
gt_mean = S.groupby("seed")["gt"].apply(lambda s: s.iloc[:100].mean()).mean()
print(f"\nDay-0 ground-truth mean (pooled): {gt_mean:+.3f}")
