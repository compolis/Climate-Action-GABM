#!/usr/bin/env python3
"""Fig E2 - Tier 3 replication (network topologies + model arm).
DiD = (pro-climate-dominant) - (climate-sceptic-dominant) endpoint difference on
the package index. Network arm: Qwen3-14B on SBM / Barabasi-Albert / Watts-
Strogatz, pooled 3 seeds. Model arm: Llama-3.1-8B on SBM, single seed.
Asserted against docs/result_report.md. Neutral labels only.
"""
from pathlib import Path
import glob
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

REPO = Path(__file__).resolve().parents[3]
EXP = REPO / "data/output/experiments"
FIGDIR = REPO / "paper/figures"; FIGDIR.mkdir(parents=True, exist_ok=True)


def _sub(r): return sorted([p for p in Path(r).iterdir() if p.is_dir()])[-1]


def endpoints(run_dir):
    d = _sub(run_dir)
    pkg = pd.read_csv(d / "package_index_trajectories.csv")
    dN = sorted(pkg["day"].unique())[-1]
    return pkg[pkg.day == dN].set_index("agent_id")["package_index"]


def find(pattern):
    hits = glob.glob(str(EXP / pattern))
    assert len(hits) == 1, f"{pattern}: {hits}"
    return hits[0]


def pooled_diff(pat_pro, pat_scep, seeds):
    chunks, per_seed = [], []
    for s in seeds:
        a = endpoints(find(pat_pro.format(s=s)))
        b = endpoints(find(pat_scep.format(s=s)))
        m = pd.concat({"a": a, "b": b}, axis=1).dropna()
        d = (m["a"] - m["b"]).to_numpy()
        chunks.append(d); per_seed.append(float(d.mean()))
    alld = np.concatenate(chunks)
    mean = float(alld.mean())
    h = float(alld.std(ddof=1) / np.sqrt(len(alld)) * stats.t.ppf(0.975, len(alld) - 1))
    return {"mean": mean, "lo": mean - h, "hi": mean + h, "per_seed": per_seed}


S3 = (42, 43, 44)
sbm = pooled_diff("run_*_tier1_green_dom_s{s}", "run_*_tier1_reform_dom_s{s}", S3)
ba = pooled_diff("run_*_tier3_ba_greendom_s{s}", "run_*_tier3_ba_reformdom_s{s}", S3)
ws = pooled_diff("run_*_tier3_ws_greendom_s{s}", "run_*_tier3_ws_reformdom_s{s}", S3)
llama = pooled_diff("run_6479341*", "run_6479390*", (42,))

assert 0.38 < sbm["mean"] < 0.47, sbm["mean"]
assert 0.28 < ba["mean"] < 0.40, ba["mean"]
assert 0.30 < ws["mean"] < 0.42, ws["mean"]
assert 1.30 < llama["mean"] < 1.65, llama["mean"]
print("AUDIT PASSED")
for nm, r in [("SBM", sbm), ("BA", ba), ("WS", ws), ("Llama", llama)]:
    print(f"  {nm:6s} {r['mean']:+.3f} [{r['lo']:+.3f},{r['hi']:+.3f}]")

mpl.rcParams.update({
    "font.size": 9, "axes.labelsize": 9.5, "xtick.labelsize": 8.5, "ytick.labelsize": 9,
    "legend.fontsize": 8, "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 150, "savefig.bbox": "tight", "pdf.fonttype": 42, "ps.fonttype": 42,
})
C_NET = "#8452a0"; C_MOD = "#b5651d"

items = [
    ("SBM  (Qwen3-14B)", sbm, "net", False),
    ("Barab\u00e1si\u2013Albert  (Qwen3-14B)", ba, "net", False),
    ("Watts\u2013Strogatz  (Qwen3-14B)", ws, "net", False),
    ("Llama-3.1-8B  (SBM, 1 seed)", llama, "mod", True),
]
ys = list(range(len(items)))[::-1]
fig, ax = plt.subplots(figsize=(6.3, 3.1), constrained_layout=True)
for y, (lab, r, grp, single) in zip(ys, items):
    c = C_NET if grp == "net" else C_MOD
    ax.errorbar(r["mean"], y, xerr=[[r["mean"] - r["lo"]], [r["hi"] - r["mean"]]],
                fmt="o", color=c, ecolor=c, elinewidth=1.8, capsize=3, ms=7,
                mfc=("white" if single else c), mec=c, mew=1.6, zorder=3)
    ax.scatter(r["per_seed"], [y + 0.17] * len(r["per_seed"]), s=10, color=c, alpha=0.45, zorder=2)
    ax.annotate(f"{r['mean']:+.2f}", (r["hi"], y), xytext=(6, 0), textcoords="offset points",
                va="center", ha="left", fontsize=8, color=c, weight="bold")
ax.axvline(0, color="0.5", lw=1, ls="--", zorder=1)
ax.axhline(0.5, color="0.9", lw=0.8, zorder=0)
ax.set_yticks(ys); ax.set_yticklabels([it[0] for it in items])
ax.set_ylim(-0.6, len(items) - 0.15)
ax.set_xlim(-0.1, 1.9)
ax.set_xlabel(r"$\Delta P$: pro-climate-dominant $-$ sceptic-dominant  (points)")
ax.text(-0.06, 3, "SOCIAL GRAPH", rotation=90, va="center", ha="center", fontsize=7.5, weight="bold", color=C_NET, alpha=0.75)
ax.text(-0.06, 0, "MODEL", rotation=90, va="center", ha="center", fontsize=7.5, weight="bold", color=C_MOD, alpha=0.75)
ax.legend(handles=[Line2D([0], [0], marker="o", color="w", mfc="white", mec="0.35", ms=7, mew=1.5,
          label="single seed (direction only)")], loc="lower right", frameon=False)
for ext in ("pdf", "png"):
    fig.savefig(FIGDIR / f"figE2_replication.{ext}")
print("saved figE2")
