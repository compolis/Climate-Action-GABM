#!/usr/bin/env python3
"""Generate the Tier-3 network presentation figures (trajectory panel + gap-over-time).

Mirrors the plotting cells added to notebooks/41. Headless (Agg) -> saves PNGs.
Run: .venv/bin/python sandbox/ajay_sandbox/tier3_network_figures.py
"""
from pathlib import Path
import re
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
EXP = REPO / "data/output/experiments"
FIG_DIR = REPO / "data" / "output" / "tier3_network_analysis"
FIG_DIR.mkdir(parents=True, exist_ok=True)

PATS = [
    (re.compile(r"run_(\d+)_tier1_(baseline|green_dom|reform_dom)_s42$"), "sbm"),
    (re.compile(r"run_(\d+)_tier3_(ba)_(baseline|greendom|reformdom)_s42$"), "ba"),
    (re.compile(r"run_(\d+)_tier3_(ws)_(baseline|greendom|reformdom)_s42$"), "ws"),
]
NORM = {"baseline": "baseline", "greendom": "green_dom", "reformdom": "reform_dom",
        "green_dom": "green_dom", "reform_dom": "reform_dom"}
TOPO_ORDER = ["sbm", "ba", "ws"]
TOPO_LABEL = {"sbm": "Stochastic-block (Tier-1)", "ba": "Barab\u00e1si\u2013Albert", "ws": "Watts\u2013Strogatz"}
COND_LABEL = {"baseline": "Baseline", "green_dom": "Green-dominant", "reform_dom": "Reform-dominant"}
COND_COLOR = {"baseline": "#636363", "green_dom": "#2ca25f", "reform_dom": "#8856a7"}
COND_SEQ = ["baseline", "green_dom", "reform_dom"]

runs = []
for d in sorted(EXP.iterdir()):
    if not d.is_dir():
        continue
    for pat, topo in PATS:
        m = pat.match(d.name)
        if not m:
            continue
        sub = sorted([p for p in d.iterdir() if p.is_dir()])
        if sub:
            runs.append({"topology": topo, "condition": NORM[m.groups()[-1]], "path": sub[-1]})
        break
runs = pd.DataFrame(runs)
assert len(runs) == 9, len(runs)

def _mean_ci(vals):
    vals = np.asarray(vals, float); n = len(vals); m = vals.mean()
    if n < 2:
        return m, m, m
    h = vals.std(ddof=1) / np.sqrt(n) * stats.t.ppf(0.975, n - 1)
    return m, m - h, m + h

rows = []
for _, rr in runs.iterrows():
    pkg = pd.read_csv(rr["path"] / "package_index_trajectories.csv")
    for day, grp in pkg.groupby("day"):
        m, lo, hi = _mean_ci(grp["package_index"])
        rows.append({"topology": rr["topology"], "condition": rr["condition"],
                     "day": int(day), "mean": m, "lo": lo, "hi": hi})
TRAJ = pd.DataFrame(rows)
DAYS = sorted(TRAJ["day"].unique())
GT_START = TRAJ[TRAJ.day == 0]["mean"].mean()
print("days:", DAYS, "| GT_START:", round(GT_START, 3))

# ── Figure 1: trajectory panel ──────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(13.8, 4.5), sharey=True)
for ax, topo in zip(axes, TOPO_ORDER):
    for c in COND_SEQ:
        s = TRAJ[(TRAJ.topology == topo) & (TRAJ.condition == c)].sort_values("day")
        ax.plot(s["day"], s["mean"], "-o", color=COND_COLOR[c], lw=2, ms=4, label=COND_LABEL[c])
        ax.fill_between(s["day"], s["lo"], s["hi"], color=COND_COLOR[c], alpha=0.15)
    ax.axhline(GT_START, color="#111111", ls="--", lw=1.2)
    ax.set_title(TOPO_LABEL[topo]); ax.set_xlabel("Simulated day"); ax.grid(True, alpha=0.25)
axes[0].set_ylabel("Average package index\n(\u22123 against \u2026 +3 in favour)")
axes[0].legend(frameon=False, fontsize=9, loc="upper left")
fig.suptitle("Pro-climate support over time, by condition \u00d7 peer-network topology (seed 42)",
             fontweight="bold", y=1.02)
fig.tight_layout()
fig.savefig(FIG_DIR / "fig2_trajectories_by_topology.png", bbox_inches="tight")
print("saved fig2_trajectories_by_topology.png")

# ── Figure 2: gap over time ─────────────────────────────────────────────────
TOPO_C = {"sbm": "#e6550d", "ba": "#3182bd", "ws": "#31a354"}
fig, ax = plt.subplots(figsize=(7.8, 4.8))
for topo in TOPO_ORDER:
    g = TRAJ[(TRAJ.topology == topo) & (TRAJ.condition == "green_dom")].set_index("day")["mean"]
    r = TRAJ[(TRAJ.topology == topo) & (TRAJ.condition == "reform_dom")].set_index("day")["mean"]
    gap = (g - r).reindex(DAYS)
    ax.plot(DAYS, gap.values, "-o", color=TOPO_C[topo], lw=2.4, ms=6, label=TOPO_LABEL[topo])
    print(f"  {topo}: gap day{DAYS[-1]} = {gap.values[-1]:+.3f}")
ax.axhline(0, color="k", lw=1)
ax.set_xlabel("Simulated day")
ax.set_ylabel("Green-dominant \u2212 Reform-dominant\n(package-index gap)")
ax.set_title("The reach-asymmetry gap emerges and widens over time\n(all three topologies, seed 42)")
ax.legend(frameon=False, fontsize=10, title="Peer network")
fig.tight_layout()
fig.savefig(FIG_DIR / "fig3_gap_over_time.png", bbox_inches="tight")
print("saved fig3_gap_over_time.png")
