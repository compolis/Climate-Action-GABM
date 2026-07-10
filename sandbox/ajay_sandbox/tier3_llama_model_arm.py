#!/usr/bin/env python3
"""
Tier-3 MODEL-REPLICATION ARM — Llama-3.1-8B, all three conditions (seed 42).

The network arm of Tier 3 is closed (NB 41: topology-robust + seed-replicated).
This is the *model* arm: does the reach-asymmetry DiD reproduce on a different
model family? We reuse the `tier1` shape (N=100, 5-day P-A/P-B/C, package mode,
SBM, seed 42) — the ONLY thing that changed vs the Qwen3-14B Tier-1 headline is
the model, so this is a clean cross-model replication.

Central tension: Llama is a WORSE difference engine than Qwen (baseline analysis:
rank rho collapses 1.0 -> 0.46 after the Day-0 anchor expires, bias DEFLATES
-0.55, ~6% wild swings). BUT the headline is a within-agent PAIRED DiD
(shift_green - shift_reform on the same 100 agents), so Llama's common-mode
level/rank noise can cancel. Question: does the *contrast* survive even though
the simulator doesn't?

Method is transcribed verbatim from the network arm harness
(sandbox/ajay_sandbox/tier3_network_validate.py) so the two arms are identical:
paired DiD, 95% CI (t), paired-t p, Cohen dz, both-bucket TOT, rank fidelity,
bias-invariance slope, plus instruction-following / stability / reasoning checks.

Single seed => read direction + within-seed significance, NOT a cross-draw
effect-size claim (same footing as the network PILOT).

Run:  .venv/bin/python sandbox/ajay_sandbox/tier3_llama_model_arm.py
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "data/output/experiments"
FIGDIR = ROOT / "data/output/tier3_llama_analysis"
FIGDIR.mkdir(parents=True, exist_ok=True)

RUNS = {
    "baseline":   "run_6475093_tier3_llama8b_baseline_s42",
    "green_dom":  "run_6479341_tier3_llama8b_greendom_s42",
    "reform_dom": "run_6479390_tier3_llama8b_reformdom_s42",
}
CONDS = ["baseline", "green_dom", "reform_dom"]
LABELS = {"baseline": "Baseline (1.0/1.0)",
          "green_dom": "Green-dominant", "reform_dom": "Reform-dominant"}
COLORS = {"baseline": "#555555", "green_dom": "#2ca02c", "reform_dom": "#d62728"}


def section(t):
    print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)


def run_dir(name):
    """Return the (latest) timestamped output subfolder for a run."""
    base = EXP / name
    subs = sorted([p for p in base.iterdir() if p.is_dir() and p.name[0].isdigit()])
    if not subs:
        raise FileNotFoundError(f"no timestamped subfolder under {base}")
    return subs[-1]


def load_pkg(path):
    """Per-agent start/end package index, ground truth, exposure bucket."""
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


# ── load everything ───────────────────────────────────────────────────────
paths = {c: run_dir(RUNS[c]) for c in CONDS}
frames = []
for c in CONDS:
    f = load_pkg(paths[c])
    f["condition"] = c
    frames.append(f)
S = pd.concat(frames, ignore_index=True)
days_all = sorted(pd.read_csv(paths["baseline"] / "package_index_trajectories.csv")["day"].unique())
d0, dN = days_all[0], days_all[-1]

print("Tier-3 MODEL ARM — Llama-3.1-8B (seed 42)")
for c in CONDS:
    print(f"  {c:11s} -> {paths[c].relative_to(EXP)}  (n={ (S.condition==c).sum() })")


def mean_ci(d):
    d = np.asarray(d, float)
    m = d.mean()
    se = d.std(ddof=1) / np.sqrt(len(d))
    h = se * stats.t.ppf(0.975, len(d) - 1)
    return m, m - h, m + h


def did(c1, c2, bucket=None):
    sub = S if bucket is None else S[S.bucket == bucket]
    a = sub[sub.condition == c1][["agent_id", "shift", "gt"]].rename(columns={"shift": "s1"})
    b = sub[sub.condition == c2][["agent_id", "shift"]].rename(columns={"shift": "s2"})
    m = a.merge(b, on="agent_id")
    d = (m["s1"] - m["s2"]).to_numpy()
    mean, lo, hi = mean_ci(d)
    t, p = stats.ttest_rel(m["s1"], m["s2"])
    dz = d.mean() / d.std(ddof=1)
    slope = np.polyfit(m["gt"], d, 1)[0]
    return {"n": len(d), "DiD": mean, "lo": lo, "hi": hi, "p": p, "dz": dz, "slope_gt": slope}


# ── 1. HEADLINE DiD ───────────────────────────────────────────────────────
section("1. HEADLINE DiD (green_dom - reform_dom), paired per agent — seed 42")
print("  Pass = POSITIVE + significant, matching the Qwen Tier-1 sign.")
r = did("green_dom", "reform_dom")
print(f"  DiD = {r['DiD']:+.3f}   95% CI [{r['lo']:+.3f}, {r['hi']:+.3f}]   "
      f"p = {r['p']:.4g}   Cohen dz = {r['dz']:+.2f}   n = {r['n']}")
print(f"  bias-invariance slope (DiD ~ GT) = {r['slope_gt']:+.3f}")
# component halves vs baseline
gvb = did("green_dom", "baseline")
rvb = did("reform_dom", "baseline")
print(f"\n  half A  green_dom - baseline  = {gvb['DiD']:+.3f}  CI[{gvb['lo']:+.3f},{gvb['hi']:+.3f}]  p={gvb['p']:.4g}")
print(f"  half B  reform_dom - baseline = {rvb['DiD']:+.3f}  CI[{rvb['lo']:+.3f},{rvb['hi']:+.3f}]  p={rvb['p']:.4g}")
print("  (expect half A > 0 push up, half B < 0 push down.)")

# ── 2. both-bucket TOT DiD ─────────────────────────────────────────────────
section("2. TOT DiD on the contested audience (bucket == 'both')")
print("  Cleanest persuasion signal; least dependent on network spillover.")
print("  Bucket sizes (baseline):")
print(S[S.condition == "baseline"]["bucket"].value_counts().to_string())
rb = did("green_dom", "reform_dom", bucket="both")
print(f"\n  both-bucket DiD = {rb['DiD']:+.3f}   CI [{rb['lo']:+.3f}, {rb['hi']:+.3f}]   "
      f"p = {rb['p']:.4g}   n = {rb['n']}")

# ── 3. rank fidelity + signed bias ─────────────────────────────────────────
section("3. RANK FIDELITY (Spearman end vs GT) + signed bias, per condition")
print("  Expected WEAK/DEFLATING — documents Llama as a poor difference engine")
print("  whose common-mode error the paired DiD is designed to cancel.")
for c in CONDS:
    sub = S[S.condition == c]
    rho = stats.spearmanr(sub["end"], sub["gt"]).correlation
    rho0 = stats.spearmanr(sub["start"], sub["gt"]).correlation
    bias = sub["end"].mean() - sub["gt"].mean()
    print(f"  {c:11s}  rho(day0)={rho0:.3f}  rho(end)={rho:.3f}  end_bias={bias:+.3f}")

# per-policy spearman/bias from shipped calibration.csv (final day) — baseline
section("3b. Per-policy Spearman & signed bias, final day (baseline calibration.csv)")
calib = pd.read_csv(paths["baseline"] / "calibration.csv")
last = calib[calib["day"] == calib["day"].max()]
cols = [c for c in ["policy_id", "spearman_rho", "mae", "mean_signed_bias"] if c in last.columns]
print(last.to_string(index=False, columns=cols))
if "spearman_rho" in last:
    print(f"\n  mean per-policy spearman @ day{int(calib['day'].max())}: {last['spearman_rho'].mean():.3f}")

# ── 4. instruction-following + stability ───────────────────────────────────
section("4. INSTRUCTION-FOLLOWING (Step-2 A-G parse) + STABILITY (per-agent shifts)")
VALID = set("ABCDEFG")


def clean_letter(txt):
    t = str(txt).strip()
    return bool(t) and t[0].upper() in VALID and (len(t) == 1 or t[1] in ".,;:) \n\r\t-")


for c in CONDS:
    raw = pd.read_csv(paths[c] / "survey_raw_response.csv")
    ok = raw["raw_response"].map(clean_letter).mean() * 100
    sh = pd.read_csv(paths[c] / "day0_vs_dayN_shifts.csv")
    col = "abs_shift" if "abs_shift" in sh else None
    wild5 = (sh[col] >= 5).mean() * 100 if col else float("nan")
    wild3 = (sh[col] >= 3).mean() * 100 if col else float("nan")
    sticky = (sh[col] == 0).mean() * 100 if col else float("nan")
    print(f"  {c:11s}  clean A-G {ok:5.1f}%   |shift|>=5 {wild5:4.1f}%   "
          f">=3 {wild3:4.1f}%   ==0 {sticky:4.1f}%")

# ── 5. reasoning eyeball (baseline + green_dom) ────────────────────────────
section("5. REASONING — sample Step-1 rationales (coherence / in-character?)")
for c in ["green_dom", "reform_dom"]:
    reason = pd.read_csv(paths[c] / "survey_reasoning.csv")
    print(f"\n  --- {c} ---")
    for _, rr in reason.sample(min(2, len(reason)), random_state=1).iterrows():
        txt = str(rr["reasoning"]).replace("\n", " ")
        print(f"  [agent {rr['agent_id']} {rr.get('policy_id','?')} day {rr.get('day','?')}]")
        print(f"    {txt[:260]}")

# ── network diagnostics (should match Qwen SBM: same seed+shape) ───────────
section("6. NETWORK DIAGNOSTICS (baseline SBM — should mirror Qwen Tier-1)")
diag = json.loads((paths["baseline"] / "network_diagnostics.json").read_text())
print(f"  mean_degree = {diag.get('mean_degree')}   max_degree = {diag.get('max_degree')}   "
      f"assort_expo = {diag.get('assortativity_political_exposure')}   "
      f"clustering = {diag.get('average_clustering')}   diameter = {diag.get('diameter')}")

# ══════════════════════════════════════════════════════════════════════════
# FIGURE — trajectories + gap-over-time, three conditions
# ══════════════════════════════════════════════════════════════════════════
section("FIGURE — building tier3_llama_model_arm.png")


def daily_mean_ci(path):
    pkg = pd.read_csv(path / "package_index_trajectories.csv")
    g = pkg.groupby("day")["package_index"]
    out = []
    for d, vals in g:
        m, lo, hi = mean_ci(vals.to_numpy())
        out.append((d, m, lo, hi))
    return pd.DataFrame(out, columns=["day", "mean", "lo", "hi"])


traj = {c: daily_mean_ci(paths[c]) for c in CONDS}
gt_mean = S[S.condition == "baseline"].drop_duplicates("agent_id")["gt"].mean()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

# Panel 1: mean package index trajectory per condition, with GT anchor
for c in CONDS:
    t = traj[c]
    ax1.plot(t["day"], t["mean"], "-o", color=COLORS[c], label=LABELS[c], lw=2, ms=5)
    ax1.fill_between(t["day"], t["lo"], t["hi"], color=COLORS[c], alpha=0.12)
ax1.axhline(gt_mean, ls="--", color="black", lw=1, label=f"YouGov GT mean ({gt_mean:+.2f})")
ax1.set_xlabel("Day")
ax1.set_ylabel("Mean package index")
ax1.set_title("Llama-3.1-8B — mean opinion trajectory by condition (seed 42)")
ax1.legend(fontsize=8, loc="best")
ax1.grid(alpha=0.3)

# Panel 2: green - reform gap over time (per-agent paired mean shift-to-date)
def paired_gap_by_day(bucket=None):
    pg = {c: pd.read_csv(paths[c] / "package_index_trajectories.csv") for c in ["green_dom", "reform_dom"]}
    if bucket is not None:
        keep = set(S[(S.condition == "baseline") & (S.bucket == bucket)]["agent_id"])
        pg = {k: v[v.agent_id.isin(keep)] for k, v in pg.items()}
    base = {c: pg[c][pg[c].day == d0].set_index("agent_id")["package_index"] for c in pg}
    rows = []
    for d in days_all:
        g_sh = pg["green_dom"][pg["green_dom"].day == d].set_index("agent_id")["package_index"] - base["green_dom"]
        r_sh = pg["reform_dom"][pg["reform_dom"].day == d].set_index("agent_id")["package_index"] - base["reform_dom"]
        j = pd.concat([g_sh, r_sh], axis=1, join="inner").dropna()
        diff = (j.iloc[:, 0] - j.iloc[:, 1]).to_numpy()
        m, lo, hi = mean_ci(diff) if len(diff) > 1 else (diff.mean(), np.nan, np.nan)
        rows.append((d, m, lo, hi))
    return pd.DataFrame(rows, columns=["day", "gap", "lo", "hi"])


gap_all = paired_gap_by_day(None)
gap_both = paired_gap_by_day("both")
ax2.axhline(0, color="black", lw=0.8)
ax2.plot(gap_all["day"], gap_all["gap"], "-o", color="#1f77b4", lw=2, ms=5, label="All agents (n=%d)" % r["n"])
ax2.fill_between(gap_all["day"], gap_all["lo"], gap_all["hi"], color="#1f77b4", alpha=0.15)
ax2.plot(gap_both["day"], gap_both["gap"], "-s", color="#ff7f0e", lw=2, ms=5, label="'both' bucket (n=%d)" % rb["n"])
ax2.fill_between(gap_both["day"], gap_both["lo"], gap_both["hi"], color="#ff7f0e", alpha=0.15)
ax2.set_xlabel("Day")
ax2.set_ylabel("Green-dom − Reform-dom (paired shift-to-date)")
ax2.set_title("Reach-asymmetry DiD over time")
ax2.legend(fontsize=8, loc="best")
ax2.grid(alpha=0.3)

fig.suptitle("Tier-3 model-replication arm — Llama-3.1-8B (seed 42, tier1 shape)", fontsize=12, y=1.02)
fig.tight_layout()
out = FIGDIR / "tier3_llama_model_arm.png"
fig.savefig(out, dpi=130, bbox_inches="tight")
print(f"  saved {out.relative_to(ROOT)}")

# ── VERDICT ────────────────────────────────────────────────────────────────
section("VERDICT")
sign_ok = r["DiD"] > 0
sig_ok = r["p"] < 0.05
print(f"  Headline DiD {r['DiD']:+.3f} (p={r['p']:.4g}) — "
      f"{'POSITIVE' if sign_ok else 'NON-POSITIVE'}, "
      f"{'significant' if sig_ok else 'NOT significant'}.")
if sign_ok and sig_ok:
    print("  => MODEL ARM PASSES: reach-asymmetry reproduces on Llama, correctly signed,")
    print("     DESPITE Llama being a poor difference engine (rho~0.46) — the paired DiD")
    print("     cancels the common-mode level/rank noise. Effect is not a Qwen artefact.")
else:
    print("  => MODEL ARM DOES NOT CLEANLY REPLICATE — scope the headline claim to Qwen;")
    print("     Llama's difference-engine failure (rho~0.46, deflation) is the likely cause.")
print("  Caveat: single seed => direction + within-seed significance only (network-pilot footing).")
