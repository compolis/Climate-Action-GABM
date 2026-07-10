#!/usr/bin/env python3
"""Fig 3 - Targeting (the null) for the draft-45 paper.
All arms climate-sceptic-dominant (pro-climate side throttled to 25% reach on a
BA hub network). Contrast = targeting mode - random: does aiming the throttled
pro-climate broadcast at the persuadable / the well-connected beat aiming at
random? Delta P relative to random, 95% CI, per-seed dots. Whole population +
hear-both-sides. Asserted against docs/result_report.md. Neutral labels only.
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
FIGDIR = REPO / "paper/figures"; FIGDIR.mkdir(parents=True, exist_ok=True)


def _sub(r): return sorted([p for p in Path(r).iterdir() if p.is_dir()])[-1]


def endpoints(run_dir):
    d = _sub(run_dir)
    pkg = pd.read_csv(d / "package_index_trajectories.csv")
    attr = pd.read_csv(d / "agent_attributes.csv").set_index("agent_id")["political_exposure"]
    dN = sorted(pkg["day"].unique())[-1]
    end = pkg[pkg.day == dN].set_index("agent_id")["package_index"]
    return pd.DataFrame({"end": end, "bucket": attr}).dropna()


def find_run(token, seed):
    hits = glob.glob(str(ASYM / f"run_*_{token}_s{seed}"))
    assert len(hits) == 1, f"{token} s{seed}: {hits}"
    return hits[0]


def pooled_diff(tok1, tok2, bucket=None, seeds=(42, 43, 44)):
    chunks, per_seed = [], []
    for s in seeds:
        a, b = endpoints(find_run(tok1, s)), endpoints(find_run(tok2, s))
        if bucket:
            a, b = a[a.bucket == bucket], b[b.bucket == bucket]
        m = a[["end"]].join(b[["end"]], lsuffix="_1", rsuffix="_2", how="inner").dropna()
        d = (m["end_1"] - m["end_2"]).to_numpy()
        chunks.append(d); per_seed.append(float(d.mean()))
    alld = np.concatenate(chunks)
    mean = float(alld.mean())
    h = float(alld.std(ddof=1) / np.sqrt(len(alld)) * stats.t.ppf(0.975, len(alld) - 1))
    return {"mean": mean, "lo": mean - h, "hi": mean + h, "per_seed": per_seed}


pw = pooled_diff("d45_tgt_persuadable", "d45_tgt_random")
dw = pooled_diff("d45_tgt_degree", "d45_tgt_random")
pb = pooled_diff("d45_tgt_persuadable", "d45_tgt_random", "both")
db = pooled_diff("d45_tgt_degree", "d45_tgt_random", "both")
assert np.isclose(pw["mean"], 0.044, atol=0.01)
assert np.isclose(dw["mean"], 0.027, atol=0.01)
print("AUDIT PASSED")

mpl.rcParams.update({
    "font.size": 9, "axes.labelsize": 9.5, "xtick.labelsize": 8.5, "ytick.labelsize": 9,
    "legend.fontsize": 8, "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 150, "savefig.bbox": "tight", "pdf.fonttype": 42, "ps.fonttype": 42,
})
C_MAIN = "#3b6ea5"; C_SUB = "#a9c3dc"

rows = [("Persuadable \u2212 random", pw, pb), ("Degree \u2212 random", dw, db)]
ys = [1, 0]
fig, ax = plt.subplots(figsize=(5.1, 2.9), constrained_layout=True)
for y, (lab, w, b) in zip(ys, rows):
    ax.errorbar(b["mean"], y + 0.2, xerr=[[b["mean"] - b["lo"]], [b["hi"] - b["mean"]]],
                fmt="s", color=C_SUB, ecolor=C_SUB, elinewidth=1.4, capsize=3, ms=5, zorder=3)
    ax.errorbar(w["mean"], y, xerr=[[w["mean"] - w["lo"]], [w["hi"] - w["mean"]]],
                fmt="o", color=C_MAIN, ecolor=C_MAIN, elinewidth=1.8, capsize=3, ms=6.5, zorder=3)
    ax.scatter(w["per_seed"], [y - 0.18] * 3, s=10, color=C_MAIN, alpha=0.45, zorder=2)
    ax.annotate(f"{w['mean']:+.2f}  n.s.", (w["hi"], y), xytext=(6, 0),
                textcoords="offset points", va="center", ha="left", fontsize=8, color=C_MAIN)
ax.axvline(0, color="0.4", lw=1.2, ls="--", zorder=1)
ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows])
ax.set_ylim(-0.55, 1.75)
ax.set_xlim(-0.17, 0.28)
ax.set_xlabel(r"$\Delta P$ relative to random targeting (package-index points)")
ax.annotate("0 = no better than\nrandom targeting", (0, 1.62), xytext=(4, 0),
            textcoords="offset points", va="center", ha="left", fontsize=7.5, color="0.4")
leg = [Line2D([0], [0], marker="o", color="w", mfc=C_MAIN, mec=C_MAIN, ms=6.5, label="Whole population"),
       Line2D([0], [0], marker="s", color="w", mfc=C_SUB, mec=C_SUB, ms=6, label="Hear both sides (~60%)")]
ax.legend(handles=leg, loc="lower right", frameon=False, handletextpad=0.3, labelspacing=0.3)
for ext in ("pdf", "png"):
    fig.savefig(FIGDIR / f"fig3_targeting.{ext}")
print("saved fig3")
