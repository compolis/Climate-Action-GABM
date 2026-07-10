#!/usr/bin/env python3
"""Fig 5 - Reach dose-response (PLACEHOLDER) for the draft-45 paper.
The draft-45 reach ladder (18 runs) is still queued; this is a Tier-1 stand-in
with a single asymmetry magnitude (throttle to 25%). Delta P vs the symmetric
baseline: sceptic-dominant (<0), symmetric (=0), pro-climate-dominant (>0).
Watermarked PLACEHOLDER. Neutral labels only.
"""
from pathlib import Path
import glob
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib as mpl
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[3]
EXP = REPO / "data/output/experiments"
FIGDIR = REPO / "paper/figures"; FIGDIR.mkdir(parents=True, exist_ok=True)


def _sub(r): return sorted([p for p in Path(r).iterdir() if p.is_dir()])[-1]


def endpoints(run_dir):
    d = _sub(run_dir)
    pkg = pd.read_csv(d / "package_index_trajectories.csv")
    dN = sorted(pkg["day"].unique())[-1]
    return pkg[pkg.day == dN].set_index("agent_id")["package_index"]


def find_run(token, seed):
    hits = glob.glob(str(EXP / f"run_*_{token}_s{seed}"))
    assert len(hits) == 1, f"{token} s{seed}: {hits}"
    return hits[0]


def pooled_diff(tok1, tok2, seeds=(42, 43, 44)):
    chunks, per_seed = [], []
    for s in seeds:
        a, b = endpoints(find_run(tok1, s)), endpoints(find_run(tok2, s))
        m = pd.concat({"a": a, "b": b}, axis=1).dropna()
        d = (m["a"] - m["b"]).to_numpy()
        chunks.append(d); per_seed.append(float(d.mean()))
    alld = np.concatenate(chunks)
    mean = float(alld.mean())
    h = float(alld.std(ddof=1) / np.sqrt(len(alld)) * stats.t.ppf(0.975, len(alld) - 1))
    return {"mean": mean, "lo": mean - h, "hi": mean + h, "per_seed": per_seed}


pro = pooled_diff("tier1_green_dom", "tier1_baseline")     # pro-climate-dominant vs symmetric
scep = pooled_diff("tier1_reform_dom", "tier1_baseline")   # sceptic-dominant vs symmetric
assert 0.38 < (pro["mean"] - scep["mean"]) < 0.47, (pro["mean"], scep["mean"])
print(f"AUDIT PASSED  pro-sym {pro['mean']:+.3f}  scep-sym {scep['mean']:+.3f}  gap {pro['mean']-scep['mean']:+.3f}")

mpl.rcParams.update({
    "font.size": 9, "axes.labelsize": 9.5, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 150, "savefig.bbox": "tight", "pdf.fonttype": 42, "ps.fonttype": 42,
})
C = "#2ca02c"
pts = [scep, {"mean": 0.0, "lo": 0.0, "hi": 0.0, "per_seed": [0, 0, 0]}, pro]
x = np.array([0, 1, 2])
y = [p["mean"] for p in pts]
lo = [p["mean"] - p["lo"] for p in pts]; hi = [p["hi"] - p["mean"] for p in pts]

fig, ax = plt.subplots(figsize=(5.2, 3.2), constrained_layout=True)
ax.plot(x, y, "-", color=C, lw=1.6, zorder=2)
ax.errorbar(x, y, yerr=[lo, hi], fmt="o", color=C, ecolor=C, elinewidth=1.6,
            capsize=3, ms=7, zorder=3)
for xi, p in zip(x, pts):
    ax.scatter([xi + 0.06] * 3, p["per_seed"], s=9, color=C, alpha=0.4, zorder=2)
    if xi != 1:
        ax.annotate(f"{p['mean']:+.2f}", (xi, p["mean"]), xytext=(0, 10 if xi == 2 else -12),
                    textcoords="offset points", ha="center", fontsize=8, color=C, weight="bold")
ax.axhline(0, color="0.5", lw=1, ls="--", zorder=1)
ax.set_xticks(x)
ax.set_xticklabels(["Sceptic-\ndominant", "Symmetric", "Pro-climate-\ndominant"])
ax.set_xlim(-0.5, 2.6)
ax.set_xlabel(r"Reach configuration ($p_A$ vs $p_B$; under-resourced side throttled to 25%)")
ax.set_ylabel(r"$\Delta P$ vs symmetric  (package-index points)")
# PLACEHOLDER watermark
fig.text(0.5, 0.5, "PLACEHOLDER\nTier-1 stand-in\nfull reach ladder pending",
         fontsize=22, color="0.6", alpha=0.20, ha="center", va="center",
         rotation=25, weight="bold")
for ext in ("pdf", "png"):
    fig.savefig(FIGDIR / f"fig5_reach_placeholder.{ext}")
print("saved fig5")
