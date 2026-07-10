#!/usr/bin/env python3
"""Fig 1 - the resource ladder (headline) for the draft-45 paper.
Grouped forest plot: VOLUME levers (reach, frequency) vs ALLOCATION levers
(targeting, iso-impression). Point = pooled within-person difference in the
final package index P (points, -3..+3), 95% CI, per-seed dots. Values ASSERTED
against docs/result_report.md. Neutral labels only (no party names).
Contrast sign convention: (pro-climate-dominant) - (climate-sceptic-dominant).
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
ASYM = REPO / "data/output/asymmetry_tests"
EXP = REPO / "data/output/experiments"
FIGDIR = REPO / "paper/figures"; FIGDIR.mkdir(parents=True, exist_ok=True)


def _sub(r): return sorted([p for p in Path(r).iterdir() if p.is_dir()])[-1]


def endpoints(run_dir):
    d = _sub(run_dir)
    pkg = pd.read_csv(d / "package_index_trajectories.csv")
    attr = pd.read_csv(d / "agent_attributes.csv").set_index("agent_id")["political_exposure"]
    dN = sorted(pkg["day"].unique())[-1]
    end = pkg[pkg.day == dN].set_index("agent_id")["package_index"]
    return pd.DataFrame({"end": end, "bucket": attr}).dropna()


def find_run(base, token, seed):
    hits = glob.glob(str(Path(base) / f"run_*_{token}_s{seed}"))
    assert len(hits) == 1, f"{token} s{seed}: {hits}"
    return hits[0]


def pooled_diff(base, tok1, tok2, seeds=(42, 43, 44)):
    chunks, per_seed = [], []
    for s in seeds:
        a, b = endpoints(find_run(base, tok1, s)), endpoints(find_run(base, tok2, s))
        m = a[["end"]].join(b[["end"]], lsuffix="_1", rsuffix="_2", how="inner").dropna()
        d = (m["end_1"] - m["end_2"]).to_numpy()
        chunks.append(d); per_seed.append(float(d.mean()))
    alld = np.concatenate(chunks)
    mean = float(alld.mean())
    h = float(alld.std(ddof=1) / np.sqrt(len(alld)) * stats.t.ppf(0.975, len(alld) - 1))
    _, p = stats.ttest_1samp(alld, 0.0)
    return {"mean": mean, "lo": mean - h, "hi": mean + h, "p": float(p), "per_seed": per_seed}


# token pairs are on-disk run-folder identifiers (data artefacts), not paper prose
reach = pooled_diff(EXP, "tier1_green_dom", "tier1_reform_dom")
freq21 = pooled_diff(ASYM, "d45_freq_green2v1", "d45_freq_reform1v2")
freq31 = pooled_diff(ASYM, "d45_freq_green3v1", "d45_freq_reform1v3")
tgt_p = pooled_diff(ASYM, "d45_tgt_persuadable", "d45_tgt_random")
tgt_d = pooled_diff(ASYM, "d45_tgt_degree", "d45_tgt_random")
iso = pooled_diff(ASYM, "d45_iso_depth2", "d45_iso_depth4")
assert np.isclose(freq21["mean"], 0.158, atol=0.01)
assert np.isclose(freq31["mean"], 0.277, atol=0.01)
assert np.isclose(tgt_p["mean"], 0.044, atol=0.01)
assert np.isclose(tgt_d["mean"], 0.027, atol=0.01)
assert np.isclose(iso["mean"], 0.120, atol=0.01)
assert 0.38 < reach["mean"] < 0.47
print("AUDIT PASSED")

mpl.rcParams.update({
    "font.size": 9, "axes.labelsize": 9.5, "xtick.labelsize": 8.5, "ytick.labelsize": 9,
    "legend.fontsize": 8, "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 150, "savefig.bbox": "tight", "pdf.fonttype": 42, "ps.fonttype": 42,
})
C_VOL = "#2ca02c"
C_ALL = "#3b6ea5"

items = [
    ("Reach", reach, "vol", True, False),
    ("Frequency 2:1", freq21, "vol", False, False),
    ("Frequency 3:1", freq31, "vol", False, False),
    ("Targeting: persuadable", tgt_p, "all", False, True),
    ("Targeting: degree", tgt_d, "all", False, True),
    ("Breadth vs depth", iso, "all", False, False),
]
ys = list(range(len(items)))[::-1]

fig, ax = plt.subplots(figsize=(5.8, 3.2), constrained_layout=True)
for y, (label, r, grp, ph, ns) in zip(ys, items):
    c = C_VOL if grp == "vol" else C_ALL
    ax.errorbar(r["mean"], y, xerr=[[r["mean"] - r["lo"]], [r["hi"] - r["mean"]]],
                fmt="o", color=c, ecolor=c, elinewidth=1.8, capsize=3,
                ms=6.5, mfc=("white" if ph else c), mec=c, mew=1.5, zorder=3)
    ax.scatter(r["per_seed"], [y + 0.17] * len(r["per_seed"]), s=9, color=c, alpha=0.45, zorder=2)
    txt = f"{r['mean']:+.2f}" + ("  n.s." if ns else "")
    ax.annotate(txt, (r["hi"], y), xytext=(5, 0), textcoords="offset points",
                va="center", ha="left", fontsize=8, color=c)

ax.axvline(0, color="0.5", lw=1, ls="--", zorder=1)
ax.axhline(2.5, color="0.9", lw=0.8, zorder=0)
ax.set_yticks(ys)
ax.set_yticklabels([it[0] for it in items])
ax.set_ylim(-0.6, len(items) - 0.15)
ax.set_xlim(-0.2, 0.78)
ax.set_xlabel(r"$\Delta P$  (package-index points, $-3$ to $+3$ scale)")

ax.text(-0.185, 4, "VOLUME", fontsize=7.5, weight="bold", color=C_VOL, alpha=0.75,
        rotation=90, va="center", ha="center")
ax.text(-0.185, 1, "ALLOCATION", fontsize=7.5, weight="bold", color=C_ALL, alpha=0.75,
        rotation=90, va="center", ha="center")

legend = [
    Line2D([0], [0], marker="o", color="w", mfc=C_VOL, mec=C_VOL, ms=6.5, label="Volume lever"),
    Line2D([0], [0], marker="o", color="w", mfc=C_ALL, mec=C_ALL, ms=6.5, label="Allocation lever"),
    Line2D([0], [0], marker="o", color="w", mfc="white", mec="0.35", ms=6.5, mew=1.4,
           label="Placeholder (Tier-1)"),
]
ax.legend(handles=legend, loc="lower right", frameon=False, handletextpad=0.3, labelspacing=0.3)
for ext in ("pdf", "png"):
    fig.savefig(FIGDIR / f"fig1_resource_ladder.{ext}")
print("saved fig1")
