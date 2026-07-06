#!/usr/bin/env python3
"""
Tier-3 litmus analysis — Llama-3.1-8B baseline (run_6475093, reach 1.0/1.0, seed 42).

Self-contained, off the main pipeline. Judges the model on the three axes that
decide whether it is a usable "difference engine":

  1. BIAS (absolute levels)  — does it inflate/deflate vs YouGov ground truth?
  2. RANK FIDELITY (Spearman)— does it keep agents in the right order? (the
                               single condition the DiD framing depends on)
  3. STABILITY               — are day-to-day opinion shifts sane, or wild swings?
  4. INSTRUCTION-FOLLOWING   — do Step-2 survey outputs parse to a clean A-G?
  5. REASONING               — eyeball a few Step-1 rationales.

Only pandas + numpy (no scipy/matplotlib) so it runs in a bare env.
Spearman via pandas .corr(method="spearman").
"""
from pathlib import Path
import re
import numpy as np
import pandas as pd

RUN = Path(__file__).resolve().parents[2] / (
    "data/output/experiments/run_6475093_tier3_llama8b_baseline_s42/20260705_111236"
)

def load(name):
    return pd.read_csv(RUN / name)

def section(t):
    print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)

# ── load ────────────────────────────────────────────────────────────────
pkg   = load("package_index_trajectories.csv")   # agent_id, day, package_index
pkg_gt= load("package_ground_truth.csv")          # agent_id, ground_truth
calib = load("calibration.csv")                    # per policy/day pearson/spearman/mae/signed
shifts= load("day0_vs_dayN_shifts.csv")            # per agent/policy day0->dayN
opin  = load("opinion_trajectories.csv")           # agent_id, day, policy_id, numeric
raw   = load("survey_raw_response.csv")            # agent_id, ..., raw_response
reason= load("survey_reasoning.csv")               # agent_id, ..., reasoning

gt = pkg_gt.set_index("agent_id")["ground_truth"]
days = sorted(pkg["day"].unique())
d0, dN = days[0], days[-1]

# ── 1. BIAS: package index vs ground truth ─────────────────────────────
section("1. BIAS — pro/anti-climate drift vs YouGov ground truth (package index)")
gt_mean = gt.mean()
print(f"Ground-truth mean package index      : {gt_mean:+.3f}")
per_day = pkg.groupby("day")["package_index"].mean()
for d in days:
    dev = per_day[d] - gt_mean
    print(f"  day {d}: mean index {per_day[d]:+.3f}   (vs GT {dev:+.3f})")
print(f"\nDay0 -> Day{dN} mean drift            : {per_day[dN]-per_day[d0]:+.3f}")
print(f"Net bias at Day{dN} (index - GT)       : {per_day[dN]-gt_mean:+.3f}")
print("  (Qwen's failure mode was a LARGE POSITIVE bias; sign+size here is the story.)")

# ── 2. RANK FIDELITY: Spearman(agent index vs GT) ──────────────────────
section("2. RANK FIDELITY — Spearman rho(agent package index vs ground truth)")
print("  Needs to stay HIGH (~0.8+) for the difference-engine framing to hold.")
for d in days:
    sub = pkg[pkg["day"] == d].set_index("agent_id")["package_index"]
    j = pd.concat([sub, gt], axis=1, join="inner").dropna()
    rho = j.iloc[:, 0].corr(j.iloc[:, 1], method="spearman")
    print(f"  day {d}: rho = {rho:.3f}   (n={len(j)})")

# per-policy spearman from the shipped calibration.csv (day N only)
section("2b. Per-policy Spearman & signed bias at final day (from calibration.csv)")
last = calib[calib["day"] == calib["day"].max()]
print(last.to_string(index=False,
      columns=["policy_id", "spearman_rho", "mae", "mean_signed_bias"]))
print(f"\n  mean per-policy spearman @ day{int(calib['day'].max())}: "
      f"{last['spearman_rho'].mean():.3f}")
print(f"  mean per-policy signed bias           : {last['mean_signed_bias'].mean():+.3f}")

# ── 3. STABILITY: per-agent shift distribution ─────────────────────────
section("3. STABILITY — per-(agent,policy) Day0->DayN signed shift distribution")
s = shifts["signed_shift"]
print(f"  n = {len(s)}   mean {s.mean():+.3f}   sd {s.std():.3f}")
print(f"  |shift|>=3 (wild swing): {(shifts['abs_shift']>=3).mean()*100:4.1f}%   "
      f"|shift|>=5: {(shifts['abs_shift']>=5).mean()*100:4.1f}%   "
      f"|shift|==0 (sticky): {(shifts['abs_shift']==0).mean()*100:4.1f}%")
print("  signed-shift histogram:")
print(s.value_counts().sort_index().to_string())

# ── 4. INSTRUCTION-FOLLOWING: Step-2 parse cleanliness ─────────────────
section("4. INSTRUCTION-FOLLOWING — do Step-2 raw survey outputs parse to A-G?")
VALID = set("ABCDEFG")
def clean_letter(txt):
    t = str(txt).strip()
    return bool(t) and t[0].upper() in VALID and (len(t) == 1 or t[1] in ".,;:) \n\r\t-")
raw["ok"] = raw["raw_response"].map(clean_letter)
raw["verbose"] = raw["raw_response"].map(lambda x: len(str(x).strip()) > 3)
print(f"  rows                         : {len(raw)}")
print(f"  clean leading A-G            : {raw['ok'].mean()*100:5.1f}%")
print(f"  verbose (>3 chars) responses : {raw['verbose'].mean()*100:5.1f}%")
bad = raw[~raw["ok"]]
print(f"  NON-clean rows               : {len(bad)}")
for t in bad["raw_response"].head(5):
    print("     !!", repr(str(t)[:100]))

# ── 5. REASONING: sample a few Step-1 rationales ───────────────────────
section("5. REASONING — sample Step-1 rationales (coherence / in-character?)")
for _, r in reason.sample(min(4, len(reason)), random_state=1).iterrows():
    txt = str(r["reasoning"]).replace("\n", " ")
    print(f"  [agent {r['agent_id']} {r['policy_id']} day {r['day']}]")
    print(f"    {txt[:280]}")
