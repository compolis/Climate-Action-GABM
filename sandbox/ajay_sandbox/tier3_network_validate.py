#!/usr/bin/env python3
"""Validation harness for the Tier-3 network-topology notebook logic.

Proves the discovery + DiD + fidelity code against the 9 seed-42 runs before
it is transcribed into notebooks/41. Run with: .venv/bin/python <this file>
"""
from pathlib import Path
import re, json
import numpy as np
import pandas as pd
from scipy import stats

EXP = Path(__file__).resolve().parents[2] / "data/output/experiments"

# topology, condition regex over BOTH the tier1 SBM ref and the tier3 net runs.
PATScmb = [
    (re.compile(r"run_(\d+)_tier1_(baseline|green_dom|reform_dom)_s42$"), "sbm"),
    (re.compile(r"run_(\d+)_tier3_(ba)_(baseline|greendom|reformdom)_s42$"), "ba"),
    (re.compile(r"run_(\d+)_tier3_(ws)_(baseline|greendom|reformdom)_s42$"), "ws"),
]
NORM = {"baseline": "baseline", "greendom": "green_dom", "reformdom": "reform_dom",
        "green_dom": "green_dom", "reform_dom": "reform_dom"}

def discover():
    rows = []
    for d in sorted(EXP.iterdir()):
        if not d.is_dir():
            continue
        for pat, topo in PATScmb:
            m = pat.match(d.name)
            if not m:
                continue
            cond = NORM[m.groups()[-1]]
            sub = sorted([p for p in d.iterdir() if p.is_dir()])
            if not sub:
                continue
            rows.append({"topology": topo, "condition": cond,
                         "jobid": m.group(1), "path": sub[-1]})
            break
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

runs = discover()
print("Discovered runs:\n", runs[["topology", "condition", "jobid"]].to_string(index=False))
assert len(runs) == 9, f"expected 9 runs, got {len(runs)}"

frames = []
for _, r in runs.iterrows():
    f = load_pkg(r["path"])
    f["topology"] = r["topology"]; f["condition"] = r["condition"]
    frames.append(f)
S = pd.concat(frames, ignore_index=True)

def mean_ci(d):
    d = np.asarray(d); m = d.mean(); se = d.std(ddof=1) / np.sqrt(len(d))
    h = se * stats.t.ppf(0.975, len(d) - 1)
    return m, m - h, m + h

def did(topo, c1, c2, bucket=None):
    sub = S[S.topology == topo]
    if bucket:
        sub = sub[sub.bucket == bucket]
    a = sub[sub.condition == c1][["agent_id", "shift", "gt"]].rename(columns={"shift": "s1"})
    b = sub[sub.condition == c2][["agent_id", "shift"]].rename(columns={"shift": "s2"})
    m = a.merge(b, on="agent_id")
    d = (m["s1"] - m["s2"]).to_numpy()
    mean, lo, hi = mean_ci(d)
    t, p = stats.ttest_rel(m["s1"], m["s2"])
    dz = d.mean() / d.std(ddof=1)
    return {"topology": topo, "n": len(d), "DiD": mean, "lo": lo, "hi": hi,
            "p": p, "d": dz, "slope_gt": np.polyfit(m["gt"], d, 1)[0]}

print("\n== HEADLINE DiD (green_dom - reform_dom) per topology ==")
for topo in ["sbm", "ba", "ws"]:
    r = did(topo, "green_dom", "reform_dom")
    print(f"  {topo.upper():4s} DiD={r['DiD']:+.3f} CI[{r['lo']:+.3f},{r['hi']:+.3f}] "
          f"p={r['p']:.4f} d={r['d']:+.2f} n={r['n']}  slope(DiD~gt)={r['slope_gt']:+.3f}")

print("\n== both-bucket TOT DiD (green_dom - reform_dom) ==")
for topo in ["sbm", "ba", "ws"]:
    r = did(topo, "green_dom", "reform_dom", bucket="both")
    print(f"  {topo.upper():4s} DiD={r['DiD']:+.3f} CI[{r['lo']:+.3f},{r['hi']:+.3f}] "
          f"p={r['p']:.4f} n={r['n']}")

print("\n== rank fidelity + signed bias (end vs gt) ==")
for topo in ["sbm", "ba", "ws"]:
    for cond in ["baseline", "green_dom", "reform_dom"]:
        sub = S[(S.topology == topo) & (S.condition == cond)]
        rho = stats.spearmanr(sub["end"], sub["gt"]).correlation
        bias = sub["end"].mean() - sub["gt"].mean()
        print(f"  {topo.upper():4s} {cond:11s} rho={rho:.3f}  bias={bias:+.3f}")

print("\n== network diagnostics (baseline graph per topology) ==")
for topo in ["sbm", "ba", "ws"]:
    p = runs[(runs.topology == topo) & (runs.condition == "baseline")].iloc[0]["path"]
    diag = json.loads((p / "network_diagnostics.json").read_text())
    print(f"  {topo.upper():4s} mean_deg={diag.get('mean_degree'):.2f} "
          f"max_deg={diag.get('max_degree')} "
          f"assort_expo={diag.get('assortativity_political_exposure'):+.3f} "
          f"clustering={diag.get('average_clustering'):.3f} "
          f"diameter={diag.get('diameter')}")
