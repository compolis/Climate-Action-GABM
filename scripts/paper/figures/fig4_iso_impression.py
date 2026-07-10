#!/usr/bin/env python3
"""Fig 4 - Iso-impression (breadth vs depth) for the draft-45 paper.
Both arms pro-climate-dominant with MATCHED total impressions: breadth (reach
0.5 x 2 broadcasts) vs depth (reach 0.25 x 4 broadcasts). Contrast = breadth -
depth. Delta P > 0 => breadth (reach) beats depth (frequency) at equal
impressions. 95% CI, per-seed dots. Whole population + hear-both-sides.
Asserted against docs/result_report.md. Neutral labels only.
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


whole = pooled_diff("d45_iso_depth2", "d45_iso_depth4")
both = pooled_diff("d45_iso_depth2", "d45_iso_depth4", "both")
assert np.isclose(whole["mean"], 0.120, atol=0.01)
assert np.isclose(both["mean"], 0.203, atol=0.01)
print("AUDIT PASSED")

mpl.rcParams.update({
    "font.size": 9, "axes.labelsize": 9.5, "xtick.labelsize": 8.5, "ytick.labelsize": 9,
    "legend.fontsize": 8, "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 150, "savefig.bbox": "tight", "pdf.fonttype": 42, "ps.fonttype": 42,
})
C_MAIN = "#3b6ea5"

rows = [("Whole population", whole), ("Hear both sides\n(~60%)", both)]
ys = [1, 0]
fig, ax = plt.subplots(figsize=(5.6, 2.7), constrained_layout=True)
ax.axvspan(0, 0.42, color="#3b6ea5", alpha=0.05, zorder=0)
for y, (lab, r) in zip(ys, rows):
    ax.errorbar(r["mean"], y, xerr=[[r["mean"] - r["lo"]], [r["hi"] - r["mean"]]],
                fmt="o", color=C_MAIN, ecolor=C_MAIN, elinewidth=1.8, capsize=3, ms=7, zorder=3)
    ax.scatter(r["per_seed"], [y - 0.16] * 3, s=10, color=C_MAIN, alpha=0.45, zorder=2)
    ax.annotate(f"{r['mean']:+.2f}", (r["hi"], y), xytext=(6, 0),
                textcoords="offset points", va="center", ha="left", fontsize=8,
                color=C_MAIN, weight="bold")
ax.axvline(0, color="0.4", lw=1.2, ls="--", zorder=1)
ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows])
ax.set_ylim(-0.5, 1.5)
ax.set_xlim(-0.06, 0.42)
ax.set_xlabel(r"$\Delta P$: breadth (reach) $-$ depth (frequency)  (points)")
ax.annotate("breadth wins \u2192", (0.30, 1.35), fontsize=8, color=C_MAIN, ha="center", style="italic")
for ext in ("pdf", "png"):
    fig.savefig(FIGDIR / f"fig4_iso_impression.{ext}")
print("saved fig4")
