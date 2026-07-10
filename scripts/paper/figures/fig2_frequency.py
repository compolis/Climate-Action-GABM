#!/usr/bin/env python3
"""Fig 2 - Frequency dose-response for the draft-45 paper.
Effect (Delta P) vs frequency advantage (2:1, 3:1) for three audiences:
whole population, those who hear both sides (direct/contested), and the
no-broadcast group (spillover via peers only). Within-person difference
(pro-climate-louder - sceptic-louder), 95% CI. Neutral labels only.
"""
from pathlib import Path
import glob
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib as mpl
import matplotlib.pyplot as plt

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
    chunks = []
    for s in seeds:
        a, b = endpoints(find_run(tok1, s)), endpoints(find_run(tok2, s))
        if bucket:
            a, b = a[a.bucket == bucket], b[b.bucket == bucket]
        m = a[["end"]].join(b[["end"]], lsuffix="_1", rsuffix="_2", how="inner").dropna()
        chunks.append((m["end_1"] - m["end_2"]).to_numpy())
    alld = np.concatenate(chunks)
    mean = float(alld.mean())
    h = float(alld.std(ddof=1) / np.sqrt(len(alld)) * stats.t.ppf(0.975, len(alld) - 1))
    return {"mean": mean, "lo": mean - h, "hi": mean + h}


G2, R2 = "d45_freq_green2v1", "d45_freq_reform1v2"
G3, R3 = "d45_freq_green3v1", "d45_freq_reform1v3"
whole = [pooled_diff(G2, R2), pooled_diff(G3, R3)]
both = [pooled_diff(G2, R2, "both"), pooled_diff(G3, R3, "both")]
spill = [pooled_diff(G2, R2, "neither"), pooled_diff(G3, R3, "neither")]
assert np.isclose(whole[0]["mean"], 0.158, atol=0.01)
assert np.isclose(whole[1]["mean"], 0.277, atol=0.01)
assert np.isclose(both[0]["mean"], 0.146, atol=0.01)
assert np.isclose(both[1]["mean"], 0.338, atol=0.01)
print("AUDIT PASSED")

mpl.rcParams.update({
    "font.size": 9, "axes.labelsize": 9.5, "xtick.labelsize": 9, "ytick.labelsize": 8.5,
    "legend.fontsize": 8, "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 150, "savefig.bbox": "tight", "pdf.fonttype": 42, "ps.fonttype": 42,
})
C_WHOLE = "#2ca02c"; C_BOTH = "#166534"; C_SPILL = "#8fbf9f"
x = np.array([0.0, 1.0])


def series(ax, dat, xs, color, marker, ls, label):
    y = [d["mean"] for d in dat]
    lo = [d["mean"] - d["lo"] for d in dat]; hi = [d["hi"] - d["mean"] for d in dat]
    ax.plot(xs, y, ls, color=color, lw=1.5, zorder=2)
    ax.errorbar(xs, y, yerr=[lo, hi], fmt=marker, color=color, ecolor=color,
                elinewidth=1.5, capsize=3, ms=7, mfc=color, mec=color, mew=1.4,
                zorder=3, label=label)
    # annotate only the right-hand (3:1) endpoint, to the right of the marker
    ax.annotate(f"{y[1]:+.2f}", (xs[1], y[1]), xytext=(9, 0), textcoords="offset points",
                ha="left", va="center", fontsize=8, color=color, weight="bold")


fig, ax = plt.subplots(figsize=(5.0, 3.4), constrained_layout=True)
series(ax, both, x - 0.04, C_BOTH, "s", "-", "Hear both sides (~60%, direct)")
series(ax, whole, x, C_WHOLE, "o", "-", "Whole population")
series(ax, spill, x + 0.04, C_SPILL, "^", "--", "No broadcast (~30%, spillover)")
ax.axhline(0, color="0.5", lw=1, ls="--", zorder=1)
ax.set_xticks(x); ax.set_xticklabels(["2 : 1", "3 : 1"])
ax.set_xlim(-0.55, 1.75)
ax.set_ylim(-0.05, 0.44)
ax.set_xlabel("Broadcast frequency advantage (pro-climate : sceptic)")
ax.set_ylabel(r"$\Delta P$  (package-index points, $-3$ to $+3$)")
ax.legend(loc="upper left", frameon=False, handletextpad=0.4, labelspacing=0.3)
for ext in ("pdf", "png"):
    fig.savefig(FIGDIR / f"fig2_frequency.{ext}")
print("saved fig2")
