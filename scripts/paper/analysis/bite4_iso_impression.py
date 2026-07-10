#!/usr/bin/env python3
"""Bite 4 (Iso-impression) analysis for the draft-45 paper.

SBM (p_intra=0.15/p_inter=0.05). BOTH arms green-dominant with MATCHED total
green impressions (reach x broadcasts = 1.0 relative), reform at full reach_b=1.0
single broadcast. The lever = how the SAME impression budget is spent:
  depth2  broad+shallow: reach_a=0.5, P-A x2/day (32 agents x 2)  phases [P-A,P-B,P-A,C]
  depth4  narrow+deep:   reach_a=0.25, P-A x4/day (16 agents x 4) phases [P-A,P-B,P-A,P-A,P-A,C]
(x3 seeds 42/43/44)

Contrast = depth2 - depth4, paired per agent within seed, pooled n=300.
  ~0        => breadth = depth: total impressions is the sufficient statistic
              (reach and frequency ARE interchangeable at equal impressions)
  > 0       => broad+shallow (more reach) beats narrow+deep => BREADTH wins
              (reach is the more efficient way to spend impressions; fits Bites 1-2)
  < 0       => narrow+deep (more frequency) beats broad+shallow => DEPTH wins
Because Day 0 is pinned to ground truth in every condition, this is a within-person
endpoint difference on the -3..+3 package index.

Run: .venv/bin/python sandbox/ajay_sandbox/bite4_iso_impression.py
"""
from pathlib import Path
import re
import numpy as np
import pandas as pd
from scipy import stats

EXP = Path(__file__).resolve().parents[3] / "data/output/asymmetry_tests"
PAT = re.compile(r"run_(\d+)_d45_iso_(depth2|depth4)_s(\d+)$")


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
assert len(runs) == 6, f"expected 6, got {len(runs)}"

frames = []
for _, r in runs.iterrows():
    f = load_pkg(r["path"])
    f["condition"] = r["condition"]
    f["seed"] = r["seed"]
    frames.append(f)
S = pd.concat(frames, ignore_index=True)


def paired_diff(c1, c2, bucket=None):
    diffs = []
    per_seed = {}
    for seed in sorted(S.seed.unique()):
        sub = S[S.seed == seed]
        if bucket:
            sub = sub[sub.bucket == bucket]
        a = sub[sub.condition == c1][["agent_id", "end", "gt"]].rename(columns={"end": "e1"})
        b = sub[sub.condition == c2][["agent_id", "end"]].rename(columns={"end": "e2"})
        m = a.merge(b, on="agent_id")
        d = (m["e1"] - m["e2"]).to_numpy()
        diffs.append(pd.DataFrame({"d": d, "gt": m["gt"].to_numpy(), "seed": seed}))
        per_seed[seed] = float(np.mean(d))
    D = pd.concat(diffs, ignore_index=True)
    mean, lo, hi = mean_ci(D["d"])
    t, p = stats.ttest_1samp(D["d"], 0.0)
    dz = D["d"].mean() / D["d"].std(ddof=1)
    return {"n": len(D), "diff": mean, "lo": lo, "hi": hi, "p": p, "dz": dz, "per_seed": per_seed}


def shares(cond):
    sub = S[S.condition == cond]
    return (sub["end"] > 0).mean() * 100, (sub["end"] == 0).mean() * 100, (sub["end"] < 0).mean() * 100


print("\n" + "=" * 78)
print("PRIMARY: within-person endpoint difference depth2 - depth4 (matched impressions), n=300")
print("  ~0 => reach & frequency interchangeable; >0 => breadth(reach) beats depth(freq)")
print("=" * 78)
r = paired_diff("depth2", "depth4")
ps = "  ".join(f"s{k}={v:+.3f}" for k, v in r["per_seed"].items())
signs = {np.sign(v) for v in r["per_seed"].values()}
same = "SAME SIGN" if len(signs) == 1 else "MIXED SIGN"
print(f"\ndepth2 - depth4   (n={r['n']})")
print(f"  diff = {r['diff']:+.3f} points  95% CI [{r['lo']:+.3f}, {r['hi']:+.3f}]  p={r['p']:.2e}  dz={r['dz']:+.2f}")
print(f"  per-seed: {ps}   [{same}]")

rb = paired_diff("depth2", "depth4", bucket="both")
print(f"\namong the majority who hear both sides (both bucket, n={rb['n']}):")
print(f"  depth2 - depth4 = {rb['diff']:+.3f}  95% CI [{rb['lo']:+.3f}, {rb['hi']:+.3f}]  p={rb['p']:.2e}")

print("\n" + "=" * 78)
print("PER-CONDITION endpoint mean, support/oppose shares, validation (pooled 3 seeds)")
print("=" * 78)
print(f"{'condition':9s} {'end_mean':>9s} {'support%':>9s} {'oppose%':>8s} {'rho(end,gt)':>12s} {'bias':>7s}")
for cond in ["depth2", "depth4"]:
    sub = S[S.condition == cond]
    sup, neu, opp = shares(cond)
    rho = stats.spearmanr(sub["end"], sub["gt"]).correlation
    bias = sub["end"].mean() - sub["gt"].mean()
    label = {"depth2": "depth2 (reach .5 x2)", "depth4": "depth4 (reach .25 x4)"}[cond]
    print(f"{label:22s} end={sub['end'].mean():>+7.3f}  sup={sup:>5.1f}  opp={opp:>5.1f}  rho={rho:>.3f}  bias={bias:>+.3f}")

gt_mean = S.groupby("seed")["gt"].apply(lambda s: s.iloc[:100].mean()).mean()
print(f"\nDay-0 ground-truth mean (pooled): {gt_mean:+.3f}")
