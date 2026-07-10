#!/usr/bin/env python3
"""Fig E1 - fit-for-purpose evaluation (Tier P) for the draft-45 paper.
Two panels, recomputed from the nine Tier-P Day-0 runs (run_6457850..6457858,
NB 36/37; Qwen3-14B, no-anchor 'llm_survey', 3 arms x 3 seeds):
  A) Persona signal / rank fidelity: mean Spearman rho (model Day-0 opinion vs
     real YouGov opinion) by arm - real (own persona) vs shuffled (stranger's)
     vs neutral (no persona). Only the real arm recovers the agent's own opinion.
  B) Residual signed bias by policy (real arm): where the model still reads too
     pro-climate on the -3..+3 scale.
Asserted against docs/result_report.md. Neutral labels only.
"""
from pathlib import Path
import glob
import json
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[3]
EXP = REPO / "data/output/experiments"
FIGDIR = REPO / "paper/figures"; FIGDIR.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(REPO / "src"))
try:
    from cag.io.plots import _policy_short_names
    PNAMES = _policy_short_names()
except Exception as e:
    print("name-map import failed:", e); PNAMES = {}

RUN_IDS = [f"run_{i}" for i in range(6457850, 6457859)]


def _sub(r): return sorted([p for p in Path(r).iterdir() if p.is_dir()])[-1]


rows = []
for rid in RUN_IDS:
    rd = EXP / rid
    d = _sub(rd)
    cfg = json.loads((d / "config.json").read_text())
    arm = cfg.get("persona_mode"); seed = cfg.get("random_seed")
    cal = pd.read_csv(d / "calibration.csv")
    cal = cal[cal.day == 0].copy()
    cal["arm"] = arm; cal["seed"] = seed
    rows.append(cal)
C = pd.concat(rows, ignore_index=True)
arms_present = sorted(C.arm.unique())
print("arms:", arms_present, "| rows:", len(C))

# Panel A: mean Spearman rho by arm (pooled over 6 policies x 3 seeds)
rho_by_arm = C.groupby("arm")["spearman_rho"].agg(["mean", "std"])
print(rho_by_arm.round(3).to_string())
real_rho = float(rho_by_arm.loc["real", "mean"])
assert real_rho > 0.40, real_rho
if "neutral" in rho_by_arm.index:
    assert abs(rho_by_arm.loc["neutral", "mean"]) < 0.12, rho_by_arm.loc["neutral", "mean"]
if "shuffled" in rho_by_arm.index:
    assert abs(rho_by_arm.loc["shuffled", "mean"]) < 0.20, rho_by_arm.loc["shuffled", "mean"]

# Panel B: signed bias by policy, real arm (mean over seeds)
real = C[C.arm == "real"]
bias = real.groupby("policy_id")["mean_signed_bias"].mean().sort_values()
pkg_mean_bias = float(real.groupby("seed")["mean_signed_bias"].mean().mean())
print("real per-policy mean signed bias:\n", bias.round(3).to_string())
print("real mean (across policies) bias:", round(pkg_mean_bias, 3))
assert 0.45 < pkg_mean_bias < 0.80, pkg_mean_bias
print("AUDIT PASSED")

mpl.rcParams.update({
    "font.size": 9, "axes.labelsize": 9.5, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "axes.titlesize": 10, "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 150, "savefig.bbox": "tight", "pdf.fonttype": 42, "ps.fonttype": 42,
})

ARM_LABEL = {"real": "Own\npersona", "shuffled": "Stranger's\npersona", "neutral": "No\npersona"}
ARM_ORDER = [a for a in ["real", "shuffled", "neutral"] if a in rho_by_arm.index]
C_REAL = "#2ca02c"; C_GREY = "#b0b0b0"

fig, (axA, axB) = plt.subplots(1, 2, figsize=(7.6, 3.3), constrained_layout=True,
                               gridspec_kw={"width_ratios": [1, 1.35]})

# Panel A
xs = np.arange(len(ARM_ORDER))
vals = [rho_by_arm.loc[a, "mean"] for a in ARM_ORDER]
cols = [C_REAL if a == "real" else C_GREY for a in ARM_ORDER]
axA.bar(xs, vals, color=cols, width=0.62, zorder=3)
axA.axhline(0, color="0.5", lw=0.9)
for xi, v in zip(xs, vals):
    ytxt = v if v >= 0 else 0.0  # keep negative-bar labels above the zero line, clear of x-ticks
    axA.annotate(f"{v:+.2f}", (xi, ytxt), xytext=(0, 4), textcoords="offset points",
                 ha="center", va="bottom", fontsize=8, weight="bold")
axA.set_xticks(xs); axA.set_xticklabels([ARM_LABEL.get(a, a) for a in ARM_ORDER])
axA.set_ylim(-0.16, 0.75)
axA.set_ylabel(r"Spearman $\rho$ (model vs real opinion)")
axA.set_title("A  Persona signal")

# Panel B
pol = list(bias.index)
labels = [PNAMES.get(p, str(p)) for p in pol]
yb = np.arange(len(pol))
vb = bias.values
axB.barh(yb, vb, color=[("#4c72b0" if v >= 0 else "#c44e52") for v in vb], zorder=3)
axB.axvline(0, color="0.5", lw=0.9)
for yi, v in zip(yb, vb):
    axB.annotate(f"{v:+.2f}", (v, yi), xytext=(4 if v >= 0 else -4, 0),
                 textcoords="offset points", va="center",
                 ha="left" if v >= 0 else "right", fontsize=7.5)
axB.set_yticks(yb); axB.set_yticklabels(labels)
axB.set_xlim(-0.4, 1.9)
axB.set_xlabel(r"Signed bias (points, model $-$ real)")
axB.set_title("B  Residual bias by policy (own persona)")

for ext in ("pdf", "png"):
    fig.savefig(FIGDIR / f"figE1_evaluation.{ext}")
print("saved figE1")
