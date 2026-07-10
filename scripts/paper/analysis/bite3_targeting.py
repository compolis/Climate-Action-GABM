#!/usr/bin/env python3
"""Bite 3 (Targeting) analysis for the draft-45 paper.

BA network (m=5, hubs). ALL arms are reform-dominant: green throttled to
reach_a=0.25 (reaches 16 of 65), reform at full reach_b=1.0, targeting_b=random
always. Single broadcast each per day (phases [P-A,P-B,C], alternating order).
Lever = WHICH 16 agents the throttled green side targets:
  random       green's 16 chosen uniformly
  persuadable  green keeps smallest |ground truth| (most persuadable)   kept|GT|0.31 vs dropped1.74
  degree       green keeps highest-degree hubs                          kept-deg0.20 vs dropped0.065
(x3 seeds 42/43/44)

NOT a green-vs-reform flip. Contrast = BETWEEN targeting modes at identical
throttled reach: does smart green targeting recover more pro-climate ground than
random? Green is the pro-climate side, so a POSITIVE (mode - random) endpoint
difference = that targeting mode spent the same reach budget better.
Metric contract: paired within-person endpoint difference on the -3..+3 package
index, pooled over 3 seeds (pair within seed). Companion = support/oppose shares.

Run: .venv/bin/python sandbox/ajay_sandbox/bite3_targeting.py
"""
from pathlib import Path
import re
import numpy as np
import pandas as pd
from scipy import stats

EXP = Path(__file__).resolve().parents[3] / "data/output/asymmetry_tests"
PAT = re.compile(r"run_(\d+)_d45_tgt_(random|persuadable|degree)_s(\d+)$")


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
assert len(runs) == 9, f"expected 9, got {len(runs)}"

frames = []
for _, r in runs.iterrows():
    f = load_pkg(r["path"])
    f["condition"] = r["condition"]
    f["seed"] = r["seed"]
    frames.append(f)
S = pd.concat(frames, ignore_index=True)


def paired_diff(cmode, cref, bucket=None):
    diffs = []
    per_seed = {}
    for seed in sorted(S.seed.unique()):
        sub = S[S.seed == seed]
        if bucket:
            sub = sub[sub.bucket == bucket]
        a = sub[sub.condition == cmode][["agent_id", "end", "gt"]].rename(columns={"end": "em"})
        b = sub[sub.condition == cref][["agent_id", "end"]].rename(columns={"end": "er"})
        m = a.merge(b, on="agent_id")
        d = (m["em"] - m["er"]).to_numpy()
        diffs.append(pd.DataFrame({"d": d, "gt": m["gt"].to_numpy(), "seed": seed}))
        per_seed[seed] = float(np.mean(d))
    D = pd.concat(diffs, ignore_index=True)
    mean, lo, hi = mean_ci(D["d"])
    t, p = stats.ttest_1samp(D["d"], 0.0)
    return {"n": len(D), "diff": mean, "lo": lo, "hi": hi, "p": p, "per_seed": per_seed}


def shares(cond):
    sub = S[S.condition == cond]
    return (sub["end"] > 0).mean() * 100, (sub["end"] == 0).mean() * 100, (sub["end"] < 0).mean() * 100


print("\n" + "=" * 78)
print("PRIMARY: within-person endpoint difference (targeting mode - random), pooled n=300")
print("  positive => smart green targeting recovers MORE pro-climate ground than random")
print("  (all arms reform-dominant: green throttled to 25% reach on BA hubs)")
print("=" * 78)
for label, cmode in [("persuadable", "persuadable"), ("degree", "degree")]:
    r = paired_diff(cmode, "random")
    ps = "  ".join(f"s{k}={v:+.3f}" for k, v in r["per_seed"].items())
    signs = {np.sign(v) for v in r["per_seed"].values()}
    same = "SAME SIGN" if len(signs) == 1 else "MIXED SIGN"
    print(f"\n{label} - random   (n={r['n']})")
    print(f"  diff = {r['diff']:+.3f} points  95% CI [{r['lo']:+.3f}, {r['hi']:+.3f}]  p={r['p']:.2e}")
    print(f"  per-seed: {ps}   [{same}]")

# direct persuadable vs degree
r = paired_diff("persuadable", "degree")
print(f"\npersuadable - degree   diff = {r['diff']:+.3f}  95% CI [{r['lo']:+.3f}, {r['hi']:+.3f}]  p={r['p']:.2e}  (n={r['n']})")

print("\n" + "=" * 78)
print('AMONG THE MAJORITY WHO HEAR BOTH SIDES (the "both" bucket)')
print("=" * 78)
for label, cmode in [("persuadable", "persuadable"), ("degree", "degree")]:
    r = paired_diff(cmode, "random", bucket="both")
    print(f"{label} - random   diff = {r['diff']:+.3f}  95% CI [{r['lo']:+.3f}, {r['hi']:+.3f}]  p={r['p']:.2e}  (n={r['n']})")

print("\n" + "=" * 78)
print("PER-CONDITION endpoint mean, support/oppose shares, validation (pooled 3 seeds)")
print("  higher end_mean => green clawed back more pro-climate ground")
print("=" * 78)
print(f"{'condition':12s} {'end_mean':>9s} {'support%':>9s} {'oppose%':>8s} {'rho(end,gt)':>12s} {'bias':>7s}")
for cond in ["persuadable", "degree", "random"]:
    sub = S[S.condition == cond]
    sup, neu, opp = shares(cond)
    rho = stats.spearmanr(sub["end"], sub["gt"]).correlation
    bias = sub["end"].mean() - sub["gt"].mean()
    print(f"{cond:12s} {sub['end'].mean():>+9.3f} {sup:>8.1f} {opp:>8.1f} {rho:>12.3f} {bias:>+7.3f}")

gt_mean = S.groupby("seed")["gt"].apply(lambda s: s.iloc[:100].mean()).mean()
print(f"\nDay-0 ground-truth mean (pooled): {gt_mean:+.3f}")
