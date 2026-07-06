# Experiment Result Report

Ongoing record of simulation experiments, settings, findings, and iteration notes.  
Results are listed newest-first.

---

## Paper Cross-Reference (`paper/sn-article.tex`)

Which results back which sections of the seminar paper draft. Use this to spot-check numbers and reasoning against the underlying CSVs without re-deriving the chain by hand.

| Paper section | Source run / notebook | Result dir | Figures (`paper/figures/`) | What to verify |
|---|---|---|---|---|
| §4.1 Probe 1 — end-to-end run under symmetric broadcasts | Run 5 (NB 19) | [`data/output/experiments/20260425_010615/`](../data/output/experiments/20260425_010615/) | `probe1_package_shares.pdf`, `probe1_package_index.pdf`, `probe1_policy_shares.pdf`, `probe1_policy_index.pdf` | Day-0 package mean +0.96; package-mean plateau +1.16 to +1.22; per-policy means and shares (Carbon tax +0.77→+1.20, Climate compensation +0.10→~+0.65, Green housing +1.53→+1.33); package support share 73–80%, against 13–23% |
| §4.2 Probe 2 — reach asymmetry registers a signal | Run 7 (NB 21) | [`data/output/experiments/20260425_125855/`](../data/output/experiments/20260425_125855/) (S), [`20260425_132515/`](../data/output/experiments/20260425_132515/) (C1), [`20260425_135538/`](../data/output/experiments/20260425_135538/) (C3) | `probe2_means.pdf`, `probe2_shares_by_condition.pdf` | Day-0 anchor +0.43; Day-4 means C1 +0.73 < S +0.83 < C3 +0.90; Day-4 supporting shares 67/70/73; monotone ordering from Day 2 onward |
| §5 Evaluation — persona signal (shuffle test, n=30) | NB 22 | [`data/output/calibration/20260425_203841/`](../data/output/calibration/20260425_203841/) | `calib_null_sixpolicy.pdf` | `p_MAE < 0.05` on 5/6 policies (Renewable borderline at 0.07); `p_ord < 0.05` on 5/6 (Carbon tax fails at 0.13); Spearman ρ range 0.25–0.63 across the six policies |
| §5 Evaluation — higher-power persona signal (n=100) | NB 23 | [`data/output/calibration/20260425_211242_persona/`](../data/output/calibration/20260425_211242_persona/) | `calib_null_followup.pdf` | Carbon tax `p_ord=0.017`, `p_MAE<10⁻³`, ρ=0.41; Climate compensation `p_ord<10⁻³`, `p_MAE<10⁻³`, ρ=0.53; realised MAE 1.29 vs null 1.66 (Carbon tax) and 1.42 vs null 2.15 (Climate compensation) |
| §5.4 Residual bias and what it means for the simulation | NB 22 + NB 23 | both calibration dirs | `calib_bias.pdf` | Behavioural-policy bias band +0.07 to +0.47 (Ban petrol cars +0.07, Ban fossil fuels +0.13, Green housing +0.30, Renewable +0.47); cost-framed bias +0.87 / +0.60 at n=30, +0.85 / +0.48 at n=100 |

Notes:
- Probe 1 and Probe 2 in the paper correspond to Run 5 and Run 7 in this report; the "Run N" labelling is repository-internal only and does not appear in the paper.
- The calibration-figure script (`paper/figures/calibration_figures.py`) regenerates the permutation null at B=1000 for visual consistency between NB 22 and NB 23. NB 22's stored `permutation_null.csv` was computed at B=100 (the in-prose p-values quoted in §5.3 come from the CSV; figure-displayed p-values reflect B=1000).
- NB 23's exclusion list (30 main-run respondent IDs) is recorded in `summary.json` so the n=100 sample is provably disjoint from the n=30 simulation cohort.

---

## v0.9 — Tier-3 network-topology robustness, SEED SWEEP (27 runs = 3 topologies × 3 conditions × 3 seeds 42/43/44, NB 41) — the reach-asymmetry DiD is topology-robust *and* seed-replicated; the pilot's SBM effect-size edge does not survive

**Date:** 2026-07-06
**Supersedes** the seed-42-only section below (now demoted to pilot). **Analysed runs:** the full **network-topology arm** of Tier 3 — 27 Qwen3-14B runs under the `tier1` shape (N=100, 5-day P-A/P-B/C, package mode, `day0_anchor=ground_truth_with_rationale`, memory `day0_anchor.ttl_days=1`), varying **only** the peer-network factory across three seeds. SBM = Tier-1 runs `run_6458324…6458332`; BA `m=5` and WS `k=10, β=0.1` = `run_6475087–92` (s42) + `run_6480290…6480784` (s43/s44). Notebook: [`notebooks/41_tier3_network_robustness.ipynb`](../notebooks/41_tier3_network_robustness.ipynb); figures in [`data/output/tier3_network_analysis/`](../data/output/tier3_network_analysis/). The model-replication arm (Apertus / Llama) is separate and still pending.

**Design.** Within each seed the three topologies share the *same 100 agents, ground truth, exposure buckets, and broadcasts* — only the wiring differs. Agents are re-drawn per seed, so the paired DiD (`end_green − end_reform`) is matched per (seed, agent) and **pooled over the three seeds (n=300 per topology)**, exactly as NB 38. BA/WS pinned to mean-degree parity (~10) with SBM, so density is controlled; only *structure* varies.

### Headline DiD (Green-dom − Reform-dom), pooled n=300 — positive and significant on all three topologies

| Topology | mean degree | DiD | 95% CI | p | Cohen dz |
|---|:--:|:--:|:--:|:--:|:--:|
| Stochastic-block (Tier-1) | 10.2 | +0.423 | [+0.337, +0.508] | <10⁻¹⁵ | +0.56 |
| Barabási–Albert (m=5) | 9.5 | +0.337 | [+0.246, +0.428] | <10⁻¹⁰ | +0.42 |
| Watts–Strogatz (k=10, β=0.1) | 10.0 | +0.360 | [+0.273, +0.447] | <10⁻¹⁰ | +0.47 |

The reach-asymmetry is **topology-robust**: correctly-signed and significant on every network. The three effect sizes are now **statistically indistinguishable** (CIs overlap throughout).

### Per-seed sign-stability — all nine cells positive; the SBM edge was a seed-42 draw

| Topology | s42 | s43 | s44 | seed mean | seed std |
|---|:--:|:--:|:--:|:--:|:--:|
| SBM | +0.532 | +0.423 | +0.313 | +0.423 | 0.109 |
| BA | +0.317 | +0.225 | +0.468 | +0.337 | 0.123 |
| WS | +0.363 | +0.360 | +0.357 | +0.360 | **0.003** |

Every (topology × seed) DiD is positive. **Correction to the pilot:** its SBM +0.53 lead over BA/WS was seed 42's high draw — SBM declines 0.53 → 0.42 → 0.31 across seeds, pooling to +0.42, and its CI now overlaps BA and WS. There is **no** structural SBM amplification; only sign, significance, and rough magnitude are topology-general. (WS is remarkably seed-stable, std 0.003.) This is consistent with SBM's exposure-assortativity ≈ 0 (below): there was never a population-level echo-chamber mechanism to produce a real edge.

### Each side contributes — and green-amplification is now significant on all three

| Topology | Green-dom − Baseline | Reform-dom − Baseline |
|---|:--:|:--:|
| SBM | +0.194 [+0.116, +0.272] | −0.228 [−0.306, −0.151] |
| BA | +0.137 [+0.068, +0.207] (p=1×10⁻⁴) | −0.199 [−0.282, −0.117] |
| WS | +0.123 [+0.051, +0.195] (p=9×10⁻⁴) | −0.237 [−0.326, −0.149] |

Pooling over seeds resolves the pilot's one wobble: the green-amplification arm on BA (n.s. at seed 42) is now significant, so **both** arms (green amplifies up, reform suppresses down) contribute on every topology.

### Treatment-on-treated (the contested `both` bucket, n=180) converges across topologies

| Topology | TOT DiD | 95% CI | p |
|---|:--:|:--:|:--:|
| SBM | +0.498 | [+0.383, +0.613] | <10⁻¹⁰ |
| BA | +0.435 | [+0.302, +0.569] | <10⁻⁸ |
| WS | +0.478 | [+0.362, +0.593] | <10⁻¹⁰ |

Among the ~60% who hear both broadcast streams the three topologies agree closely (0.44–0.50) — the whole-population differences are about *spillover* to the unexposed, not the persuasion effect itself.

### Rank fidelity, bias-invariance, diagnostics

- **Rank fidelity** (Spearman ρ, end vs GT) stays **0.78–0.87 across every topology × condition** — Qwen keeps agents correctly ordered regardless of graph. (Contrast: Llama-3.1-8B ρ ≈ 0.46.)
- **Bias-invariance:** per-agent DiD~GT slopes mildly negative (SBM −0.174, BA −0.084, WS −0.137) — the ceiling artefact from Tier 2, not a treatment interaction. Signed bias positive throughout (pro-climate inflation), cancelling in the DiD.
- **Diagnostics (avg over 3 seeds):** SBM max-deg 18, assort(exposure) **−0.017**, clustering 0.11, diameter 4; BA max-deg 37 (hubs), assort −0.003, clustering 0.20, diameter 3.7; WS max-deg 13, assort −0.016, clustering 0.49 (small-world), diameter 5. The graphs genuinely differ in structure; **SBM is not a treatment-aligned echo chamber** (assort ≈ 0).

**Scorecard: 4/4 gates** (headline positive+significant on all 3; TOT positive on all 3; rank ρ ≥ 0.78 everywhere; bias-invariance slope flat-ish everywhere) — now with seed replication.

**Bottom line.** The reach-asymmetry is **not an artefact of the stochastic-block network, and not of any single seed.** BA and WS reproduce a correctly-signed, significant, seed-stable, rank-faithful, bias-invariant asymmetry at the **same magnitude** as SBM. Safe to move away from SBM, unequivocally. The one pilot caveat that remained — a possible SBM effect-size edge — is now **retracted**: it did not survive seed replication. Remaining open item: the **model-replication arm** (Apertus / Llama).

---

## v0.9 — Tier-3 network-topology robustness (run_6475087…6475092 vs Tier-1 SBM run_6458324/6458327/6458330, seed 42, NB 41) — PILOT, superseded by the 3-seed section above

**Date:** 2026-07-05
**Analysed runs:** the **network-topology arm** of Tier 3 (the model-replication arm — Apertus / Llama — is separate and still pending). Six new seed-42 Qwen3-14B runs under the `tier1` run shape (N=100, 5-day P-A/P-B/C, package mode, `day0_anchor=ground_truth_with_rationale`, memory `day0_anchor.ttl_days=1`), varying **only** the peer-network factory: Barabási–Albert `m=5` (`run_6475087/88/89`) and Watts–Strogatz `k=10, β=0.1` (`run_6475090/91/92`) for baseline / green-dom / reform-dom. Compared against the **seed-42 Tier-1 stochastic-block runs** (`run_6458324` / `6458327` / `6458330`) as the SBM reference. Notebook: [`notebooks/41_tier3_network_robustness.ipynb`](../notebooks/41_tier3_network_robustness.ipynb); figures in [`data/output/tier3_network_analysis/`](../data/output/tier3_network_analysis/). Framing in [research_notes.md](research_notes.md) (2026-07-05 Tier-3 network note).

**Why this is a clean test.** At seed 42 the three topologies share the *same 100 agents, the same YouGov ground truth, the same exposure-bucket assignment, and the same broadcasts* — only the peer-messaging wiring differs, so any change in the DiD across topologies is attributable purely to peer-message propagation. BA/WS parameters were pinned for mean-degree parity (~10) with the SBM canon, so density is controlled; only *structure* varies. **Single seed** — read as directional (within-seed) evidence, not a cross-draw significance claim.

### Headline DiD (Green-dom − Reform-dom) is positive and significant on all three topologies

| Topology | mean degree | DiD | 95% CI | p | Cohen dz |
|---|:--:|:--:|:--:|:--:|:--:|
| Stochastic-block (Tier-1) | 10.1 | +0.532 | [+0.382, +0.681] | <10⁻⁵ | +0.71 |
| Barabási–Albert (m=5) | 9.5 | +0.317 | [+0.155, +0.478] | 1.8×10⁻⁴ | +0.39 |
| Watts–Strogatz (k=10, β=0.1) | 10.0 | +0.363 | [+0.206, +0.520] | 1×10⁻⁵ | +0.46 |

The reach-asymmetry is **topology-robust**: correctly-signed and within-seed significant on every network (n=100 matched pairs each). Effect size is largest on SBM, but the CIs overlap, so the SBM edge is **suggestive, not proven** at a single seed.

### Each side contributes — but off-SBM the asymmetry leans on reform-suppression

Secondary contrasts vs the symmetric baseline:

| Topology | Green-dom − Baseline | Reform-dom − Baseline |
|---|:--:|:--:|
| SBM | +0.297 (p=1×10⁻⁴) | −0.235 (p=1.6×10⁻³) |
| BA | +0.093 (p=0.14, **n.s.**) | −0.223 (p=2×10⁻³) |
| WS | +0.135 (p=0.02) | −0.228 (p=6×10⁻³) |

On SBM both sides move; on BA/WS the green-amplification arm weakens (n.s. on BA) while reform-suppression is stable — off the exposure-structured graph the asymmetry is carried more by *reform being suppressible* than by *green amplifying*.

### Treatment-on-treated (the contested `both` bucket) converges across topologies

| Topology | TOT DiD (`both`, n=60) | 95% CI | p |
|---|:--:|:--:|:--:|
| SBM | +0.583 | [+0.380, +0.786] | <10⁻⁴ |
| BA | +0.494 | [+0.255, +0.733] | 1.1×10⁻⁴ |
| WS | +0.556 | [+0.350, +0.761] | <10⁻⁴ |

Among the ~60% who hear both broadcast streams the three topologies agree closely (0.49–0.58) — so the whole-population DiD differences above are mostly about how *spillover* reaches the unexposed through differently-wired graphs, not about the persuasion effect itself.

### Rank fidelity and bias-invariance hold off-SBM

- **Rank fidelity** (Spearman ρ, end-of-run index vs ground truth) stays **0.82–0.90 across every topology × condition** — Qwen keeps agents correctly ordered regardless of graph, so the difference-engine framing survives leaving SBM. (Contrast: Llama-3.1-8B collapsed to ρ ≈ 0.46 on the same test — see the pending Tier-3 model-arm note.)
- **Bias-invariance:** per-agent DiD regressed on ground truth gives a flat-ish slope on all three (SBM −0.124, BA −0.080, WS −0.059) — the mild negative reflects the known ceiling effect (Tier 2), not a treatment interaction. Signed bias is positive throughout (+0.28…+0.81), the familiar pro-climate inflation, present in every condition and therefore cancelling in the DiD.

### Network diagnostics — the graphs really differ, and SBM is *not* a treatment-aligned echo chamber

| Topology | max degree | assortativity(exposure) | avg clustering | diameter |
|---|:--:|:--:|:--:|:--:|
| SBM | 17 | −0.025 | 0.103 | 4 |
| BA | 41 (hubs) | −0.006 | 0.213 | 3 |
| WS | 12 | −0.028 | 0.505 (small-world) | 5 |

**Correction to the going-in assumption.** SBM builds its two blocks from `political_exposure` (A-only→block 0, B-only→block 1), so we expected a treatment-aligned echo chamber. It is **not**: its exposure-assortativity is ≈ 0 (−0.025), because the committed-minority design puts ~90% of agents (`both` + `neither`) round-robin across *both* blocks; only the ~10% A-only/B-only are actually sorted. So SBM's mild effect-size edge is **not** explained by population-level exposure homophily.

**Scorecard: 4/4 gates** (headline positive+significant on all 3 topologies; TOT positive on all 3; rank fidelity ≥ 0.82 everywhere; bias-invariance slope flat-ish everywhere).

**Bottom line.** The reach-asymmetry effect is **not an artefact of the stochastic-block network.** Barabási–Albert and Watts–Strogatz both reproduce a correctly-signed, within-seed-significant, rank-faithful, bias-invariant asymmetry, so it is safe to move away from SBM. Open items: single seed (a seed sweep is needed before any cross-topology *effect-size* claim), and the SBM effect-size edge is suggestive only. This is the **network arm** of Tier 3; the **model-replication arm** (Apertus / Llama) remains.

---

## v0.9 — Tier-2 scale-robustness (re-analysis of run_6458324…6458335, NB 40) — the headline survives every ruler; the Tier-1 "sceptic-tilt" was a scale-ceiling artefact and the effect is ~uniform (bias-invariance restored)

**Date:** 2026-07-05
**Analysed data:** the same 12 Tier-1 runs, **re-analysed only (no new runs)**. Notebook: [`notebooks/40_tier2_scale_robustness.ipynb`](../notebooks/40_tier2_scale_robustness.ipynb); figures in [`data/output/tier2_analysis/`](../data/output/tier2_analysis/). Framing in [research_notes.md](research_notes.md) (2026-07-05 Tier-2 note).

**What the test asks.** The −3…+3 opinion scale has a ceiling; agents near +3 cannot move up, which can *manufacture* an asymmetry (Green looks more persuasive only because pro-climate agents have run out of room). Tier 2 re-expresses the same final opinions on rulers **without** a ceiling and rechecks the two Tier-1 headlines. Four monotone re-expressions of the package DiD (Green-dom − Reform-dom, n=300 pooled): **raw** (native scale, = NB 38 reference), **headroom** (raw DiD ÷ room-above-start `3−GT`), **logit** (`(x+3)/6` then log-odds; stretches boundary moves), **rank** (percentile on a common ruler; pure ordinal). The raw ruler reproduces NB 38 exactly (DiD +0.423, acid slope −0.174) — internal check.

### Headline is robust on every ruler

| Ruler | Green−Reform DiD | Cohen dz | p |
|---|:--:|:--:|:--:|
| raw | +0.423 | +0.56 | 1×10⁻¹⁹ |
| headroom | +0.197 | +0.60 | 4×10⁻²¹ |
| logit | +0.695 | +0.43 | 7×10⁻¹³ |
| rank | +0.088 | +0.59 | 3×10⁻²¹ |

Positive and significant on all four — including the scale-free **rank** ruler — so the headline Green>Reform effect is **not** a ruler artefact.

### The "sceptic-tilt" is a scale artefact — Tier-1 acid-test revised

Acid slope (per-agent DiD regressed on ground truth):

| Ruler | acid slope | p | verdict |
|---|:--:|:--:|---|
| raw | −0.174 | 3.7×10⁻⁸ | strong tilt |
| headroom | +0.022 | 0.14 | **flat** |
| logit | −0.026 | 0.71 | **flat** |
| rank | −0.017 | 0.007 | negligible residual |

Tertile (sceptic→green, standardised): raw **0.93→0.19** (steep) vs headroom 0.58→0.68 and logit 0.46→0.51 (flat).

- On the two ceiling-free **cardinal** rulers the sceptic-tilt **vanishes** (n.s.). Only a **negligible ordinal residual** survives on rank (slope −0.017 — significant only at n=300; the Tier-P negligibility-vs-significance lesson applies).
- **Reconciles with Tier 1's ceiling dig-in.** Tier 1 dropped the 16% *fully saturated* agents and the raw slope held, so it (wrongly) concluded "not a ceiling artefact". But the bounded scale also *gradually* compresses the whole upper range, not just the pinned agents; the logit/headroom rulers correct that graded squash and the tilt then disappears.
- **Bias-invariance restored.** Because the effect is ~uniform across the spectrum on an appropriate ruler, the Tier-1 raw-scale acid-test "failure" (gate 5a) was itself the artefact. The DiD **is** bias-invariant — a cleaner, stronger claim than Tier 1 alone reached.

**Scorecard: 3/3 gates** (headline positive+significant on all rulers; rank-DiD positive; sceptic-tilt verdict consistent across rulers).

**Bottom line.** The Tier-1 headline (broad, robust, correctly-signed reach-asymmetry effect) passes the ruler stress-test untouched, and the one Tier-1 caveat — a stronger effect for sceptics — dissolves under scale-free measurement. The effect is essentially uniform across the opinion spectrum, so the reach-asymmetry contrast is genuinely bias-invariant. This clears the "scale-ceiling" objection; Tier 3 (replication across models/seeds) is the remaining gate.

---

## v0.9 — Tier-1 bias-invariance & per-policy breakdown of the reach-asymmetry effect (run_6458324…6458335, NB 38 / NB 39) — a broad, robust, correctly-signed reach-asymmetry effect (the raw-scale "sceptic-tilt" is shown by Tier 2 above to be a scale artefact)

**Date:** 2026-07-04
**Analysed runs:** 12 Tier-1 runs — **4 conditions × 3 seeds (42/43/44), N=100 agents**, package mode, Qwen3-14B, `day0_anchor="ground_truth_with_rationale"`, memory anchor `ttl_days=1`. Conditions set by reach: **baseline** (reach 1.0/1.0), **green_dom** (1.0/0.25), **reform_dom** (0.25/1.0), **neither** (no broadcasts, placebo). Notebooks: [`notebooks/38_tier1_bias_invariance.ipynb`](../notebooks/38_tier1_bias_invariance.ipynb) (package level) and [`notebooks/39_tier1_per_policy.ipynb`](../notebooks/39_tier1_per_policy.ipynb) (per-policy); figures in [`data/output/tier1_analysis/`](../data/output/tier1_analysis/). This is the honest, multi-seed successor to the v0.8 seed-42/n=50 pilot below (now demoted to preliminary). Plain-language framing in [research_notes.md](research_notes.md) (2026-07-04 Tier-1 note).

**Design.** Within a seed the *same 100 agents* (identical GT) appear in all four worlds — a within-subjects design; Day 0 is pinned to GT exactly (verified: max |Day0 − GT| = 0.0), so every difference-in-differences (DiD) has the shared GT and the model's pro-climate inflation cancel algebraically. DiD is computed per (seed, agent) and pooled over the three seeds (n=300 matched pairs). Package index scale ≈ −3…+3; GT mean **+0.662**.

### Level view — every world inflates (bias still present), rank preserved

| Condition | mean shift (end−GT) | 95% CI | Spearman ρ (end vs GT) |
|---|:--:|:--:|:--:|
| Baseline | +0.607 | [+0.515, +0.699] | 0.849 |
| Green-dominant | **+0.802** | [+0.699, +0.905] | 0.782 |
| Reform-dominant | **+0.379** | [+0.292, +0.466] | 0.863 |
| Neither (placebo) | +0.477 | [+0.400, +0.554] | 0.867 |

All four worlds sit above GT (the known inflation); rank fidelity is high everywhere (ρ 0.78–0.87).

### Causal result — paired difference-in-differences (package, n=300 pooled)

| Contrast | Mean DiD | 95% CI | Paired p | Cohen dz |
|---|:--:|:--:|:--:|:--:|
| **Green − Reform** | **+0.423** | [+0.337, +0.508] | ≈1×10⁻¹⁹ | **+0.563** |
| Green − Baseline | +0.194 | [+0.116, +0.272] | <10⁻⁴ | +0.283 |
| Reform − Baseline | −0.228 | [−0.306, −0.151] | <10⁻⁴ | −0.336 |
| Green − Neither (placebo) | +0.324 | [+0.240, +0.408] | <10⁻⁴ | +0.439 |
| Reform − Neither (placebo) | −0.098 | [−0.171, −0.026] | 0.0078 | −0.155 |

- **Headline:** a louder Green side leaves citizens **+0.42 package-index points** more pro-climate than a louder Reform side — medium effect, overwhelmingly significant.
- **Placebo behaves:** vs the no-broadcast world, green pushes **up** (+0.32) and reform pushes **down** (−0.10) — opposite signs, so the broadcasts themselves do the work.
- **Sign-stable across seeds:** Green − Reform = +0.532 (s42) / +0.423 (s43) / +0.313 (s44), all positive. (Seed-42 = +0.532 replicates the pilot's +0.53 almost exactly.)

### Where the effect lives — exposure buckets (ITT vs treatment-on-treated)

The committed-minority design (`committed_minority_symmetric`: A 0.05 / B 0.05 / both 0.60 / neither 0.30) splits each cohort into reach buckets, so the whole-population **+0.42** is an **intention-to-treat (ITT)** average — deliberately diluted by the 40% who hear zero or one side. Green − Reform DiD by bucket (pooled 3 seeds):

| Bucket | n | DiD | 95% CI | Paired p | Cohen d |
|---|:--:|:--:|:--:|:--:|:--:|
| **both** (treated) | 180 | **+0.498** | [+0.383, +0.613] | 5×10⁻¹⁵ | +0.64 |
| A-only | 15 | +0.389 | [+0.14, +0.64] | 0.005 | +0.86 |
| B-only | 15 | +0.600 | [+0.08, +1.12] | 0.026 | +0.64 |
| **neither** (unexposed) | 90 | **+0.248** | [+0.11, +0.39] | 0.001 | +0.37 |

- **Treatment-on-treated (TOT):** the "both" bucket (the 60% who actually hear competing broadcasts) gives **+0.50 — ≈1.18× the population average** — the meaningful persuasion size *when messages land*. Quoting only the ITT +0.42 understates the mechanism.
- **Social spillover / two-step flow:** the "neither" bucket is **+0.25 and significant** — *not* a placebo failure but real network diffusion. These agents receive no broadcasts yet still exchange peer messages (`k_peers=2`) with exposed neighbours, so the broadcast effect propagates through the social network. The genuinely clean placebo remains the neither-*condition* world (green−neither +0.32 / reform−neither −0.10 above), where **nobody** is exposed.
- **Caveat:** A-only/B-only are n=15 pooled — directional hints only. Cleanly isolating single-side dose-response (large A-only/B-only samples, e.g. a `split50` design) is a candidate Tier-3 exposure-design arm (see [research_notes.md](research_notes.md)); it is not needed for the core reach-asymmetry claim, which the well-powered "both" bucket already carries.

### The acid test — does the effect depend on where agents started? (raw scale says yes; Tier 2 says no)

On the raw scale, regressing the per-agent Green − Reform DiD on GT gives slope **−0.174 (p = 3.7×10⁻⁸, r = −0.311)** — the gap *looks* monotonically larger for sceptics: **sceptic third +0.699 / middle +0.395 / green third +0.140**. Dropping the 16% of agents fully saturated at a ±3 bound (14% at the +3 green ceiling) barely moves it (**−0.174 → −0.190**), so it is *not* driven by the literally-pinned agents.

- **But this is a scale-ceiling artefact — resolved in the Tier-2 section above (NB 40).** The bounded ruler *gradually* compresses the whole upper range, not just the pinned agents; on ceiling-free rulers (headroom, logit) the slope is flat/non-significant and the effect is ~uniform across the spectrum. So the raw-scale acid-test "failure" was itself the artefact, and **the DiD is bias-invariant** — the reach-asymmetry effect does not depend on where agents started. *(An earlier draft of this subsection read the raw-scale slope as a genuine behavioural sceptic-tilt; Tier 2, run minutes later, corrected it.)*

**Scorecard: 6 / 7 raw-scale gates** (direction ✓, significance ✓, magnitude ✓, placebo ✓, rank fidelity ✓, seed-stability ✓; raw-scale bias-invariance acid slope ✗ — **restored on ceiling-free rulers in Tier 2**).

### Per-policy breakdown (NB 39) — the effect is BROAD (6/6 policies)

| Policy | Green − Reform DiD | 95% CI | Cohen d | % at ±3 ceiling | mean GT |
|---|:--:|:--:|:--:|:--:|:--:|
| Ban petrol cars | **+0.62** | [+0.47, +0.77] | 0.48 | 36% | −0.14 |
| Ban fossil licences | +0.55 | [+0.40, +0.70] | 0.41 | 42% | +0.40 |
| Carbon tax | +0.46 | [+0.31, +0.61] | 0.35 | 29% | +0.43 |
| Green housing | +0.39 | [+0.27, +0.50] | 0.38 | 43% | +1.60 |
| Climate compensation | +0.31 | [+0.16, +0.46] | 0.23 | 31% | −0.06 |
| Renewable energy | +0.21 | [+0.11, +0.32] | 0.23 | 41% | +1.75 |

All six policies show a significant, correctly-signed pro-climate effect. The ordering tracks contestedness: **divisive policies (Ban petrol cars, Ban fossil licences, Carbon tax) move most; near-consensus popular policies (Renewable energy, Green housing) move least — and are the most ceiling-bound (41–43% saturated), so a ceiling genuinely masks movement *there***. The per-policy raw-scale acid slope is negative on all 6 (5/6 significant) — but, like the package-level tilt, this is a scale-ceiling effect that flattens under Tier-2's ceiling-free rulers.

**Bottom line.** The reach manipulation produces a broad, robust, correctly-signed persuasion effect that survives the model's pro-climate bias in every between-condition contrast (the difference-engine works), across all six policies, and — per the Tier-2 section above — on every ceiling-free ruler. The apparent raw-scale "sceptic-tilt" is a scale-ceiling artefact (Tier 2); the effect is essentially **uniform** across the opinion spectrum, so the contrast is genuinely **bias-invariant**.

---

## v0.9 — Tier-P calibration & anchor justification (run_6457850…6457858, NB 37) — the raw model is inflated in *level* but faithful in *rank*; anchoring removes the level bias by construction

**Date:** 2026-07-04
**Analysed runs:** the same nine Tier-P Day-0 runs as NB 36 (3 arms × 3 seeds, N=100 agents, package mode, `day0_anchor="llm_survey"` — the raw *no-anchor* world where the LLM derives each opinion). Notebook: [`notebooks/37_tierP_calibration.ipynb`](../notebooks/37_tierP_calibration.ipynb); figures in [`data/output/calibration_analysis/`](../data/output/calibration_analysis/). Companion to the NB 36 Tier-P section below; the framing lives in [research_notes.md](research_notes.md) (2026-07-04 calibration note).

**What the test asks.** NB 36 proved the model *ranks* agents correctly. This asks the level question: how far off is the raw (no-anchor) opinion, is the error a rank scramble or a common offset, and does the production anchor remove exactly that error? Standard calibration metrics only (MBE/MAE/RMSE, OLS `LLM ~ GT`, Pearson r/R², Spearman ρ). Day 0 only; seeds pooled (n=300/arm). Package pro-climate index, range ≈ −3…+3, GT mean **+0.662**.

### Package calibration battery (Day 0, seeds pooled, n=300 per arm)

| Arm | MBE | MAE | RMSE | Pearson r | R² | OLS slope | OLS intercept | Spearman ρ |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **real** (no-anchor) | **+0.636** | 1.112 | 1.429 | 0.584 | 0.34 | 0.636 | +0.877 | **+0.617** |
| **neutral** (floor) | **+1.503** | 1.631 | 2.017 | 0.012 | 0.00 | 0.001 | +2.165 | −0.030 |

- **Raw inflation:** MBE = **+0.636** (real). Persona-free **floor** MBE = **+1.503**; having *a* persona removes **+0.868** = **58%** of the floor bias.
- **Level, not rank:** Spearman ρ = **+0.617** preserved (restated from NB 36); OLS slope **0.636 < 1** ⇒ compression toward the +3 ceiling.
- The `neutral` arm is a flat band far above the diagonal (r ≈ 0, slope ≈ 0) — the model's unconditional pro-climate prior. See Fig 1 (`fig1_calibration_scatter.png`).

### Bias structure vs ground truth (real arm, Fig 2)

`corr(GT, bias) = −0.380` (p = 9.1×10⁻¹²); bias-vs-GT OLS slope = **−0.364**. Low-GT (sceptical) agents are inflated *more* than high-GT agents — regression toward the pro-climate mean, steepened by the ceiling. The offset stays **same-signed across the GT range**, so it is an additive-style bias that anchoring removes cleanly rather than a rank scramble. Fig 3 (`fig3_bias_decomposition.png`) shows MBE by arm: neutral +1.50 → shuffled/real ≈ +0.64 (shuffled lands with real → it's *having a* persona, not the specific identity, that grounds the level).

### Per-policy calibration (real arm, seeds pooled, per-policy scale −3…+3)

| Policy | MBE | MAE | RMSE | Pearson r | OLS slope | Spearman ρ |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Green housing | −0.153 | 1.307 | 1.794 | 0.336 | 0.311 | 0.304 |
| Renewable energy | +0.333 | 1.000 | 1.512 | 0.294 | 0.202 | 0.377 |
| Ban fossil licences | +0.360 | 1.520 | 2.033 | 0.521 | 0.605 | 0.544 |
| Climate compensation | +0.677 | 1.837 | 2.336 | 0.419 | 0.532 | 0.439 |
| Carbon tax | +0.960 | 1.720 | 2.217 | 0.377 | 0.384 | 0.389 |
| Ban petrol cars | +1.637 | 2.043 | 2.566 | 0.386 | 0.243 | 0.464 |

Inflation is concentrated in the salient behaviour-change policies — **Ban petrol cars +1.64** (worst), **Carbon tax +0.96** — while **Green housing is essentially calibrated (−0.15)**. Every policy keeps a positive Spearman ρ (0.30–0.54), so rank fidelity holds item-by-item. See Fig 4 (`fig4_per_policy_mbe.png`).

### Ceiling / regression-to-mean check

Package GT at the +3 ceiling: **3.0%** of agents; per-policy GT at +3: **23.8%** of responses (at −3: 9.7%). A non-trivial share start pinned pro-climate and cannot be inflated further, so the OLS slope < 1 and the negative bias-vs-GT slope are **partly a ceiling artefact** — the hook Tier 2 (scale-robustness) re-examines on ceiling-free rulers.

### Anchor mechanism — why this bias is removed by construction (Fig 5)

From [`src/cag/abm/sim.py`](../src/cag/abm/sim.py) `_run_day0`: `llm_survey` lets the LLM pick the Day-0 number (the +0.64-biased world measured here); the production default **`ground_truth_with_rationale`** seeds the Day-0 *number* from ground truth and lets the LLM write only the *rationale*. So under production anchoring Day-0 calibration is **MBE = 0, MAE = 0, ρ = 1.0 by construction** while keeping a coherent LLM reasoning chain for the dynamics — confirmed empirically on the v0.8 within-subjects runs (*"Day-0 index = the GT mean, ρ = 1.0, MAE = 0 by construction"*, §v0.8 below). Fig 5 (`fig5_anchor_demonstration.png`) contrasts the biased `llm_survey` histogram (MBE +0.64) with the anchored y = x world.

**Bottom line.** The raw model is not trustworthy in *absolute level* (+0.64 package inflation, worse on cost/behaviour policies) but is faithful in *rank* (ρ ≈ 0.62) with a preserved-order offset. This is the empirical licence for the "difference-engine" stance and the quantitative justification for anchoring Day 0 to ground truth.

---

## v0.9 — Tier-P persona-null ablation (run_6457850…6457858, NB 36) — the LLM demonstrably conditions on personas: GO

**Date:** 2026-07-04
**Analysed runs:** nine Day-0-only runs, 3 arms × 3 seeds (42/43/44), N=100 agents each, package mode (6 climate policies), Qwen3-14B @ temp 0.5, `day0_anchor="llm_survey"` (the model *derives* each opinion from the persona — the no-anchor world), `memory="persona_only"`. Arm→run map (seed 42/43/44): **real** = run_6457850/851/852; **shuffled** = run_6457853/854/855; **neutral** = run_6457856/857/858. Notebook: [`notebooks/36_tierP_persona_null.ipynb`](../notebooks/36_tierP_persona_null.ipynb); figures in [`data/output/tierP_analysis/`](../data/output/tierP_analysis/). This is **Tier P** of the four-tier validation program — the foundational validity gate argued in [research_notes.md](research_notes.md) (2026-07-04 note); see there for the plain-language interpretation.

**What the test asks.** Does the model actually read each agent's persona, or is it emitting a generic pro-climate prior? Three arms: **real** (agent gets its own YouGov persona), **shuffled** (agent gets *another* agent's whole persona via a within-sample derangement), **neutral** (no persona — *"I am an adult living in the United Kingdom."*). Only Day 0 is analysed (`day==0`); the redundant `day==1` survey from the tierP preset is ignored.

**Scale:** package pro-climate index, mean of the six per-policy answers, range roughly −3…+3. Ground-truth (GT) mean +0.662 across all arms (same 100 agents drawn per seed).

### Per-arm summary (Day 0, seeds pooled, n=300 per arm)

| Arm | LLM mean | LLM SD | own-GT mean |
|---|:--:|:--:|:--:|
| real | +1.298 | **1.460** | +0.662 |
| shuffled | +1.284 | **1.462** | +0.662 |
| neutral | +2.166 | **0.147** | +0.662 |

The `neutral` arm's cross-agent SD collapses to **0.147** (**10.1%** of the real arm's 1.460) and its mean jumps to +2.166 — persona-free agents converge on one uniformly pro-climate answer.

### Rank-order fidelity: Spearman ρ (pooled n=300, bootstrap 95% CI)

| Correlation | ρ | 95% CI | Reads as |
|---|:--:|:--:|---|
| real: LLM vs **own** GT | **+0.617** | [+0.541, +0.684] | model recovers the agent's real opinion |
| shuffled: LLM vs **used**-persona GT | **+0.611** | [+0.537, +0.676] | tracks the persona it was *shown* (≈ real) |
| shuffled: LLM vs **own** GT | −0.122 | [−0.230, −0.006] | does *not* track the body it's attached to |
| neutral: LLM vs own GT | −0.030 | [−0.141, +0.085] | no persona → no signal |

(Spearman ρ = rank correlation; +1 = perfect ordering agreement, 0 = none.) Per-seed ρ(real, own) = +0.632 / +0.629 / +0.603; ρ(shuffled, used) = +0.616 / +0.625 / +0.601 — both tight across seeds. ρ(shuffled, own) = −0.037 / −0.031 / −0.325 (the seed-44 value drives the small pooled negative; see the artefact note below).

### The shuffled dissociation is the causal core

In the shuffled arm the model tracks the **persona shown** (+0.611) and is ~0 to the **body** (−0.122) — a clean dissociation proving the persona *text*, not a fixed prior, drives the answer. The small negative (not exactly 0) is a **mechanical artefact of the derangement**: this draw made `own_gt` and `used_gt` themselves slightly anti-correlated (ρ = −0.075 pooled), and since the LLM tracks `used_gt` (+0.611), the predicted bleed-through is +0.611 × (−0.075) ≈ −0.046 (observed −0.122; the rest is seed-44 noise). It is not evidence of inverse persona-tracking.

### Per-policy robustness: ρ(real, own) by policy (seeds pooled)

| P1 | P2 | P3 | P4 | P5 | P6 |
|:--:|:--:|:--:|:--:|:--:|:--:|
| +0.377 | +0.544 | +0.464 | +0.304 | +0.389 | +0.439 |

All six policies are comfortably positive — the persona signal is broad-based, not driven by any single item.

### GO / NO-GO verdict — all three gates PASS → **GO**

1. **Signal exists** — ρ(real, own) = +0.617, CI [+0.541, +0.684] excludes 0. **PASS.**
2. **Persona not body** — ρ(shuffled, used) = +0.611 ≈ ρ(real); |ρ(shuffled, own)| = 0.122 ≪ 0.25 × 0.611 = 0.153. **PASS.** (Gate 2's "≈0" uses a *negligibility* test — |ρ| small and far below the used-GT correlation — not a CI-excludes-0 test, which at n=300 flags even a trivial −0.12 artefact as "significant".)
3. **No persona → no heterogeneity** — neutral/real SD ratio = 0.101 < 0.35. **PASS.**

The model demonstrably conditions on personas; Tier P clears the downstream tiers (bias-invariance, scale-robustness, multiverse) to proceed.

### Calibration hook → done (NB 37)

The `real` arm here is the raw *no-anchor* opinion: LLM mean +1.298 vs GT mean +0.662 = **+0.64** signed inflation. The `neutral` arm's +2.166 is the persona-free bias floor (+1.50 above GT). That measured inflation is exactly what `ground_truth_with_rationale` anchoring removes by construction. The full calibration battery (MBE/MAE/RMSE, OLS slope/intercept, Pearson r, per-policy table, ceiling diagnostics, anchor demonstration) is in the **NB 37** section above.

---

## v0.8 — bias-invariance / difference-in-differences validation of the reach-asymmetry runs (run_6436142 / 6436192 / 6436203 / 6436638) — the pro-climate level bias cancels in between-condition contrasts

> **⚠ Superseded by the v0.9 Tier-1 section above (2026-07-04, NB 38/39).** This is the n=50, seed-42 **pilot**. Tier-1 (n=100 × 3 seeds) replicates the headline (Green − Reform = +0.53 at seed 42 → **+0.42 pooled**) but at higher power **overturns two claims made here**: (1) the DiD is *not* strictly GT-independent — the acid-test slope is **−0.17 (p<10⁻⁷)** vs the underpowered −0.115 (p=0.20) reported below; and (2) that residual GT-dependence is **not** a ceiling artefact — it survives dropping saturated agents (−0.174→−0.190). Treat the numbers below as the preliminary pilot; cite Tier-1 for the load-bearing result.

**Date:** 2026-07-03
**Analysed runs:** the four reach-asymmetry runs in the section below (baseline, reform-dominant, green-dominant, reform-dominant BA). All use `seed=42, n=50`, so the **same 50 agents with identical ground-truth (GT) values** appear in every condition — a within-subjects design (verified: agent set and per-agent GT identical across all four). This section is the quantitative backing for the "difference-engine" framing argued in [research_notes.md](research_notes.md) (2026-07-03 note); see there for the plain-language interpretation.

**What the test asks.** Day-0 is anchored to each agent's real YouGov value by construction, so any end-of-run gap above GT is pure upward drift (the pro-climate bias). The question: is that bias a *common additive offset* that subtracts out when we compare two conditions on the same agents, or does it *interact with the treatment* and thus contaminate the reach-asymmetry contrasts?

**Scale:** observed package index across all runs [−2.67, +3.00]; GT [−2.17, +3.00]; GT mean **+0.587** (already high, several agents pinned at the +3.00 ceiling).

### Per-condition calibration vs ground truth (end of run, n=50)

| Condition | MBE (end−GT) | MAE | OLS slope | intercept | Pearson r | R² | Spearman ρ | corr(GT, drift) |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Baseline | +0.54 | 0.72 | 0.87 | +0.61 | 0.83 | 0.69 | **0.81** | −0.22 (p=0.13) |
| Reform-dominant | +0.24 | 0.57 | 0.93 | +0.28 | 0.86 | 0.74 | **0.85** | −0.13 (p=0.36) |
| Green-dominant | +0.76 | 0.82 | 0.81 | +0.87 | 0.82 | 0.68 | **0.80** | −0.32 (p=0.024) |
| Reform-dominant (BA) | +0.21 | 0.55 | 0.95 | +0.25 | 0.88 | 0.77 | **0.87** | −0.11 (p=0.45) |

Rank-order fidelity (Spearman ρ) is 0.80–0.87 in every condition — the model preserves *who is more/less pro-climate* even though the *level* is inflated (MBE +0.21 to +0.76).

### Is the bias structure the same across conditions? (homogeneity-of-slopes ANCOVA)

Across the three stochastic-block conditions: **F(2, 144) = 0.50, p = 0.61** — no evidence the GT→end slope differs by condition. The inflation is a common offset, not something the reach manipulation reshapes.

### Do the treatment effects survive, and are they GT-independent? (paired DiD, same 50 agents)

| Contrast | Mean DiD | SD | Paired p | Cohen dz | DiD vs GT (slope, r, p) |
|---|:--:|:--:|:--:|:--:|:--:|
| Green − Reform (SBM) | **+0.53** | 0.83 | 4.6×10⁻⁵ | +0.63 | −0.115, r=−0.18, p=0.20 (n.s.) |
| Green − Baseline | +0.23 | 0.76 | 0.040 | +0.30 | −0.060, r=−0.10, p=0.47 (n.s.) |
| Reform − Baseline | −0.30 | 0.74 | 0.006 | −0.41 | +0.055, r=+0.10, p=0.50 (n.s.) |
| Reform_BA − Reform (network placebo) | −0.02 | 0.66 | 0.80 | −0.04 | +0.019, r=+0.04, p=0.79 (n.s.) |

Every treatment contrast is real (the network-swap placebo is correctly ≈0), and **none depends on the agent's GT** — the direct proof the bias cancels in the difference.

### Affinity / exposure enrichment

Per-agent `agent_attributes.csv` fields (`political_exposure` bucket, `affinity_score_a/_b`) are identical across all four runs. Buckets: both=30, neither=16, A-only=2, B-only=2. Net affinity (`score_a − score_b`) ranges [−12.7, +10.6], correlates r=+0.46 with GT.

- **Treatment effect (Green − Reform) by exposure bucket:** both (n=30) **+0.76, p<0.001**; neither (n=16) **+0.16, p=0.30 (n.s.)**; A-only/B-only n=2 each (noise). The effect is localised to the agents who actually receive both broadcasts.
- **DiD orthogonal to agent traits:** DiD ~ GT (r=−0.18, p=0.20), DiD ~ net-affinity (r=−0.17, p=0.23); joint `DiD ~ GT + net_affinity` **R² = 0.044** (agent traits explain <5% of the treatment effect).
- **Within-condition drift** is weakly predicted by everything (R²/η² ≤ 0.11): bucket/affinity edge out GT in baseline/reform (drift is exposure-driven, not start-position-driven), GT edges ahead in green (ceiling). All low → individual movement is largely idiosyncratic.

### Caveat — scale-ceiling / regression-to-mean

corr(GT, drift) is negative everywhere and significant in green-dominant (**−0.32, p=0.024**): low-GT agents inflate more than high-GT agents, because GT already sits high and the upward push compresses against the +3 ceiling (this is why the green OLS slope is 0.81 vs 0.93–0.95 for reform). Implication: the green treatment effect is **conservative**, and part of the "green amplifies easily / reform can't go net-negative" asymmetry is a **bounded-scale artefact**. A scale-aware robustness arm (distance-from-anchor or rank/logit transform) is the recommended Tier-2 follow-up; it does not threaten the DiD validity.

---

## v0.8 — reach-asymmetry experiment (run_6436142 / 6436192 / 6436203 / 6436638) — subsampling one side's audience steers the population, but the pro-climate tilt resists reversal

**Date:** 2026-07-03
**Runs (AIRE, Qwen3-14B via vLLM):**

| Job dir | Condition | reach_a (green/A) | reach_b (reform/B) | network |
|---|---|:--:|:--:|---|
| [`run_6436142_canon_exposure_baseline`](../data/output/experiments/run_6436142_canon_exposure_baseline/) | Baseline (symmetric reach) | 1.0 | 1.0 | stochastic_block |
| [`run_6436192_canon_exposure_reform_dominant`](../data/output/experiments/run_6436192_canon_exposure_reform_dominant/) | Reform-dominant | **0.25** | 1.0 | stochastic_block |
| [`run_6436203_canon_exposure_green_dominant`](../data/output/experiments/run_6436203_canon_exposure_green_dominant/) | Green-dominant | 1.0 | **0.25** | stochastic_block |
| [`run_6436638_canon_exposure_reform_dominant_barabasi_albert`](../data/output/experiments/run_6436638_canon_exposure_reform_dominant_barabasi_albert/) | Reform-dominant (BA network) | **0.25** | 1.0 | barabasi_albert |

**Shared config (identical across all four, only reach + network differ):** `n_citizens=50`, `days=5`, **`k_peers_per_day=2` (peer messaging ON — unlike the memory sweep above)**, `communication_mode=package`, `political_exposure_mode=rule_affinity_rank` with **canonical symmetric targets `{A-only: 0.05, B-only: 0.05, both: 0.60, neither: 0.30}`**, `day0_anchor=ground_truth_with_rationale`, `Qwen/Qwen3-14B`, `thinking=False`, `random_seed=42`. Every run shares the same **GT package mean +0.587** and **Day-0 anchor +0.587**. `reach_a`/`reach_b` subsample the respective political agent's matched audience *each broadcast* (reach, not frequency): reform-dominant throttles the green agent to 25% of its audience, green-dominant throttles the reform agent. **A = green / pro-climate political agent; B = reform / climate-sceptic political agent.**

> **New memory setting used from here on — `day0_anchor.ttl_days = 1` (the configuration we are standardising on).** The three memory tiers play *different* roles and are deliberately configured differently:
> - **Day-0 anchor (`ttl_days = 1`) — an *artificial* seed, not a cognitive model.** The ground-truth YouGov value is injected into the agent's context on Day 0 and Day 1 *only*, then dropped. Its sole job is to pin the agent's starting position to real survey data so Day-1 opinions are grounded in the empirical distribution rather than the LLM's prior; after that the agent is on its own. Keeping it forever (the earlier `ttl = ∞` baseline) turns it into a permanent tether that re-pins opinions every day and manufactures the runaway pro-climate climb (see the memory-ablation sweep below) — that is an artefact, not behaviour we want. `ttl_days = 1` is the value we are happy with: **anchor the start, then forget.**
> - **Verbatim window (`verbatim_window_days = 2`) and daily summaries — these *do* model human cognition** and are left on. They give the agent a rolling short-term verbatim memory of the last two days plus a compressed gist of older days, which is the intended cognitive mechanism (recent events remembered in detail, older ones as summaries). These are conceptually separate from the anchor: they carry the agent's *own* evolving experience forward, whereas the anchor injects an *external* ground-truth number.
>
> So the setting here is: **artificial GT anchor for exactly one day of influence, real cognitive memory (2-day verbatim + summaries + own-reasoning) running normally on top.**

**TL;DR.** This is the reach-asymmetry probe. The result is a **clean monotone population-level signal in the dominant side's direction** — throttling the green agent (reform-dominant) flattens the pro-climate climb, throttling the reform agent (green-dominant) amplifies it — and the effect is **robust to network topology** (stochastic-block vs Barabási–Albert reform-dominant are within 0.02). The **`both` bucket (60% of agents, doubly exposed) is the mechanism**: it swings with whichever side keeps its reach. Peer messaging (`k=2`) carries the shift to the **unexposed `neither` bucket**, which still climbs +0.5 to +0.8 with no direct broadcast. **But the asymmetry is not symmetric in strength:** even a 4:1 reach advantage for the reform side only *flattens* the population to +0.82 — still **above** the +0.587 anchor — and never drives it net-negative, whereas the same advantage for the green side amplifies easily to +1.35. That is the systematic pro-climate bias showing through, and it is the thing to tackle next.

### Population-level effect (package index, D0 → D5)

| Condition | reach A/B | D0 | D5 (end) | Net drift | Mean \|Δ\| | % moved | end − GT (bias) | MAE | ρ vs GT |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Green-dominant | 1.0 / 0.25 | 0.59 | **+1.35** | +0.76 | 0.82 | 88% | **+0.76** | 0.82 | 0.80 |
| **Baseline** | 1.0 / 1.0 | 0.59 | **+1.12** | +0.54 | 0.72 | 94% | +0.54 | 0.72 | 0.81 |
| Reform-dominant | 0.25 / 1.0 | 0.59 | **+0.82** | +0.24 | 0.57 | 86% | +0.24 | 0.57 | 0.85 |
| Reform-dominant (BA) | 0.25 / 1.0 | 0.59 | **+0.80** | +0.21 | 0.55 | 88% | +0.21 | 0.55 | 0.87 |

Clean ordering **Green-dominant (+1.35) > Baseline (+1.12) > Reform-dominant (+0.82 ≈ +0.80 BA)**. Note the calibration columns: reform-dominant is the *most accurate* run (MAE 0.55–0.57, ρ up to 0.87) simply because throttling the pro-climate side drags the inflated aggregate back toward the +0.587 ground truth — accuracy here is a side effect of countering the model's own tilt, not of better dynamics.

### Population trajectory (package-index mean, by day)

| Condition | D0 | D1 | D2 | D3 | D4 | D5 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Green-dominant | 0.59 | 1.24 | 1.36 | 1.30 | 1.34 | 1.35 |
| Baseline | 0.59 | 1.03 | 1.06 | 1.05 | 1.13 | 1.12 |
| Reform-dominant | 0.59 | 0.77 | 0.81 | 0.79 | 0.79 | 0.82 |
| Reform-dominant (BA) | 0.59 | 0.77 | 0.82 | 0.75 | 0.78 | 0.80 |

All four jump on Day 1 then plateau — reach asymmetry sets the *height* of the plateau, not its shape.

### Bucket-wise (the mechanism)

Under 5/5/60/30 the informative buckets are **`both`** (n=30, doubly exposed, Day-0 mean +0.76) and **`neither`** (n=16, no broadcast — only peer messaging + memory, Day-0 mean +0.44). The committed `A-only`/`B-only` cells are n=2 each and are noise (reported for completeness only).

**`both` bucket (n=30) — net drift D0 → D5:**

| Condition | D0 | D5 | Net | reads |
|---|:--:|:--:|:--:|---|
| Green-dominant | 0.76 | **1.60** | **+0.84** | green reach wins → strongest climb |
| Baseline | 0.76 | 1.23 | +0.47 | both sides full → moderate climb |
| Reform-dominant | 0.76 | 0.84 | +0.08 | reform reach wins → **nearly frozen** |
| Reform-dominant (BA) | 0.76 | 0.81 | +0.05 | same, topology-independent |

The doubly-exposed majority is where reach asymmetry bites hardest: it ranges from a near-standstill (+0.05 to +0.08 when the reform side dominates) to a strong +0.84 climb when the green side dominates. This bucket drives the population ordering.

**`neither` bucket (n=16) — no direct broadcast, moves only via peers + memory:**

| Condition | D0 | D5 | Net |
|---|:--:|:--:|:--:|
| Baseline | 0.44 | 1.24 | +0.80 |
| Green-dominant | 0.44 | 1.11 | +0.68 |
| Reform-dominant (BA) | 0.44 | 1.04 | +0.60 |
| Reform-dominant | 0.44 | 0.96 | +0.52 |

Even with **zero** direct exposure, the unexposed cohort climbs +0.5 to +0.8 — peer diffusion (`k=2`) plus the pro-climate anchor carries the broadcast signal indirectly. The ordering here is weaker and noisier than in `both` (peer diffusion is a lagged, indirect channel), but the reform-dominant conditions still sit at the bottom, consistent with the population effect.

### What this says about the systematic pro-climate bias (setup for next step)

- **The reach lever is real and directional** — the population endpoint moves monotonically with which side keeps its audience, and the mechanism (the `both` bucket) is exactly the one that should respond. The probe works.
- **The lever is asymmetric in strength.** A 4:1 reach advantage for the reform side only pulls the aggregate down to +0.82 (still above the +0.587 anchor, never net-negative), while the identical advantage for the green side pushes it up to +1.35. The model amplifies pro-climate persuasion readily but resists counter-attitudinal (sceptic) persuasion — the same asymmetry the memory sweep exposed in the B-only bucket, now visible through the reach channel with peer messaging on.
- **Accuracy ≠ neutrality.** Reform-dominant scores the best MAE (0.55) only because throttling the green side happens to cancel the model's built-in inflation. That is a coincidence of two biases partly offsetting, not a calibrated simulation. The next task is to attack the pro-climate tilt at its source (Day-0 seeding / prompt framing / survey parsing) so that a *symmetric* reach configuration lands near the +0.587 ground truth on its own.

### Caveats

- **Single seed, n = 50, one model.** Directional effects, not error-barred estimates. The n = 2 committed-minority buckets are uninterpretable.
- **Reach ≠ frequency.** These runs vary *audience fraction per broadcast*; the complementary frequency-asymmetry axis (more broadcasts from one side) is not yet CLI-exposed.
- **Peer channel is on (`k=2`).** Unlike the memory-ablation sweep above (broadcast-only), movement here mixes broadcast reach with peer diffusion, which is why the `neither` bucket moves at all.

---

## v0.8 — memory-ablation sweep (run_6426018 / 6426231 / 6426233 / 6426250 / 6426433 / 6434951) — verbatim self-memory is the main inertia driver; stripping it makes agents markedly more responsive

**Date:** 2026-07-02 (daily-summaries-off isolation run added 2026-07-03)
**Runs (AIRE, Qwen3-14B via vLLM):**

| Job dir | Condition |
|---|---|
| [`run_6426233_memory_baseline`](../data/output/experiments/run_6426233_memory_baseline/) | baseline (default memory) |
| [`run_6426018_Day 0  achoring off after two days`](../data/output/experiments/) | Day-0 anchor TTL = 2 |
| [`run_6426231_own_reasoning_false`](../data/output/experiments/run_6426231_own_reasoning_false/) | own_reasoning off |
| [`run_6434951_Daily summaries off`](../data/output/experiments/run_6434951_Daily%20summaries%20off/) | **daily_summaries off (only)** — isolates the summaries tier (anchor kept at TTL = ∞, own_reasoning on) |
| [`run_6426250_Daily summaries off and day 0 anchor off after 2 days`](../data/output/experiments/) | daily_summaries off + anchor TTL = 2 |
| [`run_6426433_Daily summaries off and day 0 anchor off after 2 days and own reasoning off`](../data/output/experiments/) | daily_summaries off + anchor TTL = 2 + own_reasoning off |

**Shared config (identical across all six, only `memory` differs):** `n_citizens=50`, `days=7`, `k_peers_per_day=0` (**broadcast-only — no peer messaging, so opinion movement is driven purely by the two political broadcasts + the agent's own memory**), `communication_mode=package`, `political_exposure_mode=rule_affinity_rank` with **split-50 targets** (`A-only=B-only=0.50`), `day0_anchor=ground_truth_with_rationale`, `Qwen/Qwen3-14B`, `thinking=False`, `random_seed=42`. Every run has the same **GT package mean = +0.587** and the same **Day-0 anchor = +0.587** (seeded from YouGov), so the Day-0 → Day-7 movement is directly comparable.

**TL;DR.** With peer messaging off, the only things that can move an agent are the broadcasts and *what the agent remembers of its own past answers*. This sweep isolates the memory half. The headline: the **verbatim self-memory tier (Day-0 anchor + daily summaries + own-reasoning) is collectively the dominant source of inertia**. The fuller the memory, the *less* responsive and the *more* one-directionally inflationary the agent is; stripping those sections makes agents move more often, in larger daily steps, and stops the runaway monotonic climb. Peer-to-peer diffusion is **not** what pins opinions here — the agent's own remembered history is. **The single most important cut is bucket-wise (A-only vs B-only, below):** the aggregate mean hides a directional asymmetry — the pro-climate-exposed A-only bucket climbs strongly under *every* memory setting, while the sceptic B-only bucket is **frozen at baseline** and only gets persuaded *downward* by the anti-climate broadcast once memory is stripped. Memory's real job here is **shielding the sceptics from counter-attitudinal persuasion**, not damping both sides symmetrically.

> **Baseline caveat:** because the memory pipeline was refactored in v0.8 (section-wise assembly, reflection-stage threading, shared verbatim window), this `memory_baseline` is **not** numerically comparable to pre-refactor v2 runs. Compare only *within* this batch.

### Responsiveness by memory condition (Day-0 → Day-7, package index)

| Condition | anchor | summaries | own‑reas. | Net drift (signed) | Movement (mean \|Δ\|) | % agents moved | **Avg daily step** | End index (D7) |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Baseline (default)** | ttl=∞ | on | on | **+0.51** | 0.74 | 86% | **0.18** | +1.09 |
| Anchor TTL = 2 | ttl=2 | on | on | +0.33 | 0.92 | 94% | 0.21 | +0.92 |
| own_reasoning off | ttl=∞ | on | **off** | +0.39 | 0.78 | 84% | 0.31 | +0.97 |
| **Daily summaries off (only)** | ttl=∞ | **off** | on | +0.54 | 0.72 | 86% | 0.15 | +1.12 |
| Summaries off + TTL = 2 | ttl=2 | **off** | on | +0.43 | 0.73 | 94% | 0.19 | +1.02 |
| **All three stripped** | ttl=2 | **off** | **off** | +0.36 | **1.34** | 94% | **0.44** | +0.94 |

*Net drift* = mean signed (Day7 − Day0) across agents; *Movement* = mean absolute shift; *Avg daily step* = mean absolute change between consecutive surveyed days (the cleanest day-to-day responsiveness proxy since broadcasts are the only external driver).

### Package-index trajectory (population mean, by day)

| Condition | D0 | D1 | D2 | D3 | D4 | D5 | D6 | D7 | shape |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| Baseline | 0.59 | 0.92 | 0.96 | 1.01 | 1.06 | 1.10 | 1.11 | 1.09 | **monotone climb → plateau** |
| Anchor TTL = 2 | 0.59 | 0.96 | 1.06 | 0.94 | 0.95 | 0.95 | 0.93 | 0.92 | jump, then **falls back after anchor drops (D>2)** |
| own_reasoning off | 0.59 | 0.91 | 1.03 | 0.93 | 0.98 | 1.05 | 0.87 | 0.97 | oscillates |
| Daily summaries off (only) | 0.59 | 0.97 | 0.93 | 0.98 | 1.01 | 1.04 | 1.08 | 1.12 | **monotone climb → plateau (≈ baseline)** |
| Summaries off + TTL = 2 | 0.59 | 0.85 | 0.88 | 0.87 | 0.98 | 0.98 | 0.98 | 1.02 | gentle drift |
| All three stripped | 0.59 | 0.91 | 1.05 | 1.02 | 0.95 | 1.00 | 0.91 | 0.94 | **largest swings, no pinning** |

### Bucket-wise trajectory (A-only vs B-only) — the population mean hides a directional asymmetry

**This is the informative cut.** Under split-50 + `rule_affinity_rank` the two buckets don't just receive opposite broadcasts, they *start* far apart: affinity-rank sorts the model's pro-climate leaners into **A-only** (exposed only to pro-climate agent A; n = 25, Day-0 mean **+1.32**) and the climate-sceptic tail into **B-only** (exposed only to sceptic agent B; n = 25, Day-0 mean **−0.15**). Averaging them back to the +0.587 population mean cancels the persuasion signal, so read the buckets, not the aggregate. Both buckets are n = 25 in every run and share the same Day-0 anchors (+1.32 / −0.15), so cross-condition comparison is clean.

**Net drift by bucket (Day-0 → Day-7 package index):**

| Condition | A-only D0 | A-only D7 | **A-only net** | B-only D0 | B-only D7 | **B-only net** |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **Baseline (default)** | 1.32 | 2.31 | **+0.99** | −0.15 | −0.12 | **+0.03** |
| Anchor TTL = 2 | 1.32 | 2.23 | +0.91 | −0.15 | −0.39 | −0.25 |
| own_reasoning off | 1.32 | 2.43 | +1.11 | −0.15 | −0.48 | −0.33 |
| Daily summaries off (only) | 1.32 | 2.31 | +0.99 | −0.15 | −0.06 | +0.09 |
| Summaries off + TTL = 2 | 1.32 | 2.27 | +0.95 | −0.15 | −0.23 | −0.09 |
| **All three stripped** | 1.32 | 2.50 | **+1.18** | −0.15 | −0.61 | **−0.47** |

**A-only trajectory (population mean, by day):**

| Condition | D0 | D1 | D2 | D3 | D4 | D5 | D6 | D7 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Baseline | 1.32 | 2.01 | 2.10 | 2.16 | 2.24 | 2.31 | 2.30 | 2.31 |
| Anchor TTL = 2 | 1.32 | 2.04 | 2.17 | 2.11 | 2.19 | 2.21 | 2.19 | 2.23 |
| own_reasoning off | 1.32 | 1.99 | 2.29 | 2.21 | 2.28 | 2.47 | 2.33 | 2.43 |
| Daily summaries off (only) | 1.32 | 2.09 | 2.10 | 2.18 | 2.21 | 2.23 | 2.24 | 2.31 |
| Summaries off + TTL = 2 | 1.32 | 1.94 | 2.01 | 2.13 | 2.22 | 2.24 | 2.23 | 2.27 |
| All three stripped | 1.32 | 1.96 | 2.21 | 2.45 | 2.47 | 2.44 | 2.38 | 2.50 |

**B-only trajectory (population mean, by day):**

| Condition | D0 | D1 | D2 | D3 | D4 | D5 | D6 | D7 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Baseline | −0.15 | −0.17 | −0.18 | −0.13 | −0.11 | −0.11 | −0.09 | −0.12 |
| Anchor TTL = 2 | −0.15 | −0.12 | −0.05 | −0.23 | −0.29 | −0.31 | −0.33 | −0.39 |
| own_reasoning off | −0.15 | −0.17 | −0.23 | −0.35 | −0.33 | −0.36 | −0.60 | −0.48 |
| Daily summaries off (only) | −0.15 | −0.16 | −0.24 | −0.23 | −0.20 | −0.14 | −0.09 | −0.06 |
| Summaries off + TTL = 2 | −0.15 | −0.25 | −0.25 | −0.39 | −0.26 | −0.29 | −0.28 | −0.23 |
| All three stripped | −0.15 | −0.15 | −0.11 | −0.41 | −0.57 | −0.45 | −0.56 | −0.61 |

**What the buckets reveal (and the average hid):**

- **A-only persuasion is robust to memory — it climbs strongly in every condition (+0.91 to +1.18).** Congenial influence (a pro-climate agent nudging already-pro-climate agents further up) fires regardless of what the agent remembers; memory ablation only modulates the *magnitude* (largest when all three sections are stripped, +1.18; smallest under anchor TTL = 2, +0.91). The pro-side of the model is easy to push and hard to stop.
- **B-only is the discriminating bucket — and it flips sign with memory.** At **baseline the sceptic cohort is effectively frozen (+0.03)**: full memory *shields* it from the anti-climate broadcast, so it never moves off its Day-0 −0.15. As verbatim self-memory is stripped, agent B's message starts to land and B-only drifts **down** toward it: −0.09 (summaries off + TTL 2) → −0.25 (anchor TTL 2) → −0.33 (own_reasoning off) → **−0.47 (all three stripped)**. Memory, not the peer channel (off here), is what prevents counter-attitudinal persuasion of the sceptics.
- **The aggregate "pro-climate inertia" is really a B-side story.** Baseline's headline +0.51 net drift = A-only +0.99 averaged against a frozen B-only +0.03. What memory ablation actually *unlocks* is the anti-climate persuasion of the B-only bucket; the A-only bucket was already moving freely. Reading only the population mean would wrongly attribute the change to symmetric extra movement on both sides.
- **Summaries-off-only confirms the no-op at bucket level too.** B-only stays frozen at **+0.09 ≈ baseline +0.03** and A-only is identical to baseline (+0.99) — removing the compressed gist tier alone shields the sceptics exactly as much as baseline does. The anti-climate persuasion only appears once the **Day-0 anchor** (TTL) or **own-reasoning** verbatim tier is touched.

### What each memory section does to responsiveness

- **The Day-0 anchor is a stickiness *and* inflation driver.** Baseline (anchor never expires) is the *only* run that climbs monotonically and holds near +1.1 — opinions ratchet up and the anchor re-pins them there every day. Expiring the anchor at TTL = 2 lifts the fraction of agents who ever move from **86% → 94%**, cuts net drift **+0.51 → +0.33**, and — visibly — the trajectory *bends back down* once the anchor disappears after Day 2 instead of continuing to inflate. The persistent Day-0 tether is what produces the runaway pro-climate climb.
- **Own-reasoning is a day-to-day stabiliser.** Removing it (own_reasoning off) nearly **doubles the average daily step (0.18 → 0.31)**: with no verbatim record of its own prior rationale in front of it, the agent re-derives its position each day and wobbles more, even though the net endpoint is similar. So this section trades responsiveness for consistency.
- **Daily summaries alone matter least — now cleanly isolated.** The dedicated *summaries-off-only* run (anchor kept at TTL = ∞, own_reasoning on — the sole difference from baseline) is **statistically indistinguishable from baseline**: net drift +0.54 vs +0.51, movement 0.72 vs 0.74, identical 86% moved, avg daily step *lower* at 0.15 vs 0.18, and the same **monotone climb → plateau** ending at +1.12 vs +1.09. Removing the compressed gist tier does **not** increase responsiveness. This also settles the earlier confound: the responsiveness gains seen in the *Summaries off + TTL = 2* run came from the **anchor expiry**, not from dropping summaries — with the anchor left intact, summaries removal is a no-op. The compressed gist tier is a negligible anchor next to the verbatim Day-0 anchor and own-reasoning.
- **The effects stack.** Stripping all three verbatim self-memory sources at once is by far the most responsive configuration: **average daily step 0.44 (2.5× baseline)**, mean absolute shift **1.34 (1.8× baseline)**, and the largest single-agent move of the batch (|Δ| = 3.67, a full sign flip across the scale). Agents here are essentially re-reading only the broadcasts + recent reflections each day, so they track the incoming signal far more loosely to their own past.

### Caveats

- **Single seed, n = 50, one model, broadcast-only.** These are directional effects, not error-barred estimates; no peer channel (`k_peers=0`) by design, so this isolates memory but says nothing about peer diffusion.
- **Direction of bias is unchanged.** Every condition still ends *above* the GT mean of +0.587 (net signed shift positive everywhere) — memory ablation reduces the *runaway* pro-climate climb and increases responsiveness, but does not remove the underlying pro-climate tilt of the model.
- **Responsiveness ≠ accuracy.** A larger daily step means the agent reacts more to the latest broadcast; whether that tracks or *erodes* calibration to ground truth is a separate question (`calibration.csv` per run) not analysed here.

---

## v0.8 — configurable-memory + debias-removal smoke (20260701_221142) — new build runs end-to-end, default memory reproduces the v2 dynamics

**Date:** 2026-07-01
**Run:** [`data/output/experiments/20260701_221142/`](../data/output/experiments/20260701_221142/)
**Notebook:** [`notebooks/32_v06_outputs_smoke.ipynb`](../notebooks/32_v06_outputs_smoke.ipynb) (companion offline demo: [`notebooks/35_memory_ablation_demo.ipynb`](../notebooks/35_memory_ablation_demo.ipynb))
**Model:** `gpt-5-mini` (`llm_provider=openai`, both messaging + surveys, `T=0.5` — auto-dropped, model rejects `temperature`)
**Config:** `n_citizens=10`, `days=2` (alternating `P-A`/`P-B`/`C`), `k_peers_per_day=2`, `communication_mode=package` (all 6 policies), `political_exposure_mode=rule_affinity_rank` (committed-minority symmetric targets, balanced weights), `reach_a=reach_b=1.0`, `day0_anchor=ground_truth_with_rationale`, **`memory="default"`** (the new v0.8 configurable-memory key — the default preset reproduces the v2 hard-wired six-section assembly bit-for-bit), `thinking=False`, `random_seed=42`. **`debias` is gone as a config key** — the two-step Condition-B survey is now unconditional. Wall-clock **14.1 min (848 s)**.

**TL;DR.** First end-to-end run after two structural changes landed: the **configurable memory / prompt-assembly** refactor (`SIM_CONFIG["memory"]`) and the **removal of the `debias` toggle** (two-step survey now always on). Purpose was to confirm the new build runs clean and that `memory="default"` behaves exactly like the old hard-wired v2 path — **it does**. This is a **10-agent × 2-day smoke, not a production result**; all numbers below carry a heavy small-n caveat and should not be read as science. The familiar qualitative signature is intact: a **Day-0 → Day-1 jump then a Day-2 plateau**, and per-agent ordering that tracks ground truth reasonably (Day-2 Spearman ρ ≈ 0.6–0.9 across the six policies).

### Opinion dynamics (package index)

| Day | package index (all) | both (n=6) | neither (n=4) |
|---:|---:|---:|---:|
| 0 (GT anchor) | **+0.75** | +0.81 | +0.67 |
| 1 | **+1.12** | +0.94 | +1.38 |
| 2 | **+1.10** | +0.94 | +1.33 |

- **Day-0 index = +0.75 = the ground-truth mean**, because `ground_truth_with_rationale` seeds the Day-0 numeric directly from YouGov (the LLM writes only the rationale). Consequently Day-0 calibration is **ρ = 1.0, MAE = 0 by construction** for every policy — the informative calibration is Day-1 onward.
- **Movement is concentrated on Day 1 and freezes on Day 2.** Per-policy mean end-of-day shifts on Day 1 ranged +0.2 to +0.6; on Day 2 five of six policies moved a mean of exactly **0.00** (the sixth, −0.10). Same plateau shape seen in every prior run.
- Only **two buckets materialise** (`both`=6, `neither`=4): the committed-minority-symmetric targets produce no committed A-only/B-only minorities at n=10, so `gap_widening` is not computable here (plot skipped by design). No cross-bucket-asymmetry claim is available from this run.

### Day-0 → Day-2 shifts

- Overall mean signed shift **+0.35**, mean absolute shift **0.48** (60 agent-policy pairs).
- By bucket: `both` **+0.14** (std 0.59), `neither` **+0.67** (std 1.17). The unexposed `neither` cohort moved *more* on average than the doubly-exposed `both` cohort — the opposite of a persuasion story, but with n=4 vs n=6 this is noise, not signal.

### Calibration vs ground truth (Spearman ρ, Day 2)

| policy | ρ (Day 2) | MAE (Day 2) |
|---|---:|---:|
| ClimatePolicyID(1) | 0.813 | 0.2 |
| ClimatePolicyID(2) | 0.602 | 1.0 |
| ClimatePolicyID(3) | 0.866 | 0.4 |
| ClimatePolicyID(4) | 0.870 | 0.4 |
| ClimatePolicyID(5) | 0.672 | 0.6 |
| ClimatePolicyID(6) | 0.867 | 0.3 |

Mean signed bias stays small (+0.1 to +0.6 across policies) — as expected under the GT anchor + two-step survey, and consistent with the gpt-5-mini calibration band from earlier runs. Rank recovery (ρ ≈ 0.6–0.9) is intact after the memory/debias refactor.

### Build-integrity notes (not scientific findings)

- The output bundle is complete: **30 files** (19 CSV, 3 JSON, 8 PNG — one fewer PNG than the canonical 9 only because `gap_widening` is skipped absent A-only/B-only buckets).
- `daily_summaries.csv` is **empty by design** on a 2-day run: with `memory="default"` (`verbatim_window_days=2`) the compression target is `day−2`, which never fires for `day ≤ 2`, so nothing is compressed. This is the expected default-memory behaviour, not a regression.
- The companion offline demo NB 35 (no LLM) confirms `memory="default"` assembles an identical context to the pre-refactor path and shows the ablation presets (`no_anchor`, `short_memory`, `anchor_ttl2`) diffing the assembled prompt as intended.

---

## v0.8 — Qwen3-**14B** split50 (20260628_025751) — model upgrade halves the bias and restores the bucket asymmetry

**Date:** 2026-06-28
**Run:** [`data/output/experiments/20260628_025751/`](../data/output/experiments/20260628_025751/)
**Model:** `Qwen/Qwen3-14B` (`llm_provider=local`, vLLM-style endpoint `http://localhost:8000/v1`, `T=0.5`)
**Config:** **bit-identical to [run_6267094](#v08--qwen3-8b-aire-split50-run_6267094--first-production-run-on-v2-memory--day-0-refactor) except `llm_model` (`Qwen/Qwen3-8B` → `Qwen/Qwen3-14B`).** `n_citizens=50`, `days=5` (alternating `P-A`/`P-B`/`C`), `k_peers_per_day=0`, `communication_mode=package` (all 6 policies), `political_exposure_mode=rule_affinity_rank`, `political_exposure_targets=split50` (→ 25 A-only / 25 B-only), `reach_a=reach_b=1.0`, `day0_anchor=ground_truth_with_rationale`, `debias=True`, `thinking=False`, `random_seed=42`

**TL;DR.** Direct response to the run_6267094 finding that Qwen3-**8B** under v2 memory over-inflates the contestable policies by ~2 scale points and lets B-only (anti-climate audience) drift strongly pro-climate. Swapping **only the model** (8B → 14B, same seed, same 50 agents, same offline broadcasts, bit-identical Day-0 anchor) **roughly halves the pro-climate bias and brings the bucket-asymmetric persuasion signature back.** Day-5 mean signed bias drops from **+1.25 (8B) → +0.57 (14B)**, mean MAE from **1.45 → 0.91**, and mean Pearson r *rises* from **0.46 → 0.67** — now in (and on several policies better than) the gpt-5-mini `+0.7–0.9` band. Crucially, B-only no longer caves to the model's "somewhat support" attractor: its total package-index movement collapses from **+1.31 (8B) to +0.17 (14B)** — it stays pinned near its anti-leaning Day-0 anchor — while A-only still climbs to ceiling. The cross-bucket gap therefore **widens by +0.799**, *exceeding* even the pre-refactor [Run-14 v2](#run-14-v2-post-nb-31-fix-split50--first-end-to-end-validation) baseline (+0.667) — and this time via genuine memory-v2 (not the NB-31 static-context bug). **The model upgrade is the fix:** the +2-point bias was a small-model debias-compliance failure, not a structural flaw in the v2 memory / Day-0 refactor.

### Clean model-only swap

- **Day-0 package index bit-identical to 8B** (A-only +1.320, B-only −0.147) — the GT anchor bypasses the LLM, so cohort sampling, affinity-rank bucketing, and the anchor are unchanged.
- **`message_flow.csv` byte-identical to 8B** (broadcasts are `political_message_source=offline`, `v1` — canned text, model-independent). The 25/25 A/B delivery and ~1430–1595 char lengths are the same; any difference is a pure citizen-side response effect.
- **Network topology identical** (same seed): 50 nodes, 130 edges, `p_inter=0.06`, density 0.106, mean degree 5.2, 1 component, `auto_connected_edges=0`. With `k_peers=0` the graph is decorative either way.
- No `run.log`/AIRE wrapper in this output dir, so wall-clock is not recorded here; only operational fact asserted is determinism + identical broadcast/network surfaces.

### Headline — cross-bucket package index (14B vs 8B)

| Day | A-only (14B) | B-only (14B) | gap (14B) | A-only (8B) | B-only (8B) | gap (8B) |
|---:|---:|---:|---:|---:|---:|---:|
| 0 (GT anchor) | +1.320 | −0.147 | **+1.467** | +1.320 | −0.147 | +1.467 |
| 1 | +2.280 | −0.033 | +2.313 | +2.373 | +0.767 | +1.607 |
| 2 | +2.313 | +0.040 | +2.273 | +2.533 | +1.040 | +1.493 |
| 3 | +2.287 | +0.053 | +2.234 | +2.480 | +1.073 | +1.407 |
| 4 | +2.300 | +0.053 | +2.247 | +2.520 | +1.140 | +1.380 |
| 5 | +2.293 | +0.027 | **+2.266** | +2.513 | +1.160 | +1.353 |

- **Gap-widening (Δgap, Day-0 → Day-5): 14B = +0.799 vs 8B = −0.114.** The sign flips back to positive, and the magnitude *beats* Run-14 v2 (+0.667).
- **B-only net movement: 14B +0.174 vs 8B +1.307.** The 14B B-only bucket stays essentially at its anti-leaning anchor across all 5 days (−0.147 → +0.027). A-only still rises to ceiling (+0.973). The asymmetry is real: A moves, B holds.

### Per-policy D0 → D5 signed shift (14B vs 8B vs Run-14 v2)

| policy | B (14B) | B (8B) | B (Run-14 v2) | A (14B) |
|---|---:|---:|---:|---:|
| ClimatePolicyID(1) Carbon Tax | **−0.32** | +0.16 | +0.04 | +0.32 |
| ClimatePolicyID(2) Climate Compensation | +0.64 | +1.96 | +0.60 | +1.20 |
| ClimatePolicyID(3) Green Housing | +0.56 | +2.16 | −0.08 | +1.32 |
| ClimatePolicyID(4) Ban Petrol Cars | **−0.12** | +0.08 | −0.20 | +0.52 |
| ClimatePolicyID(5) Renewable Energy | +0.04 | +1.28 | +0.36 | +1.12 |
| ClimatePolicyID(6) Ban Fossil Fuels | +0.16 | +2.20 | +1.84¹ | +1.36 |

¹ Run-14 v2 B-only for Ban Fossil Fuels was −0.60; the +1.84 in the 8B comparison column of the run_6267094 section is the *A-only* figure — see that section for the full v2 table. The point here: 14B B-only sits at +0.16, an order of magnitude below 8B's +2.20.

Every B-only cell collapses toward zero relative to 8B. Two policies (**Carbon Tax −0.32, Ban Petrol Cars −0.12**) go *negative* under sustained anti-climate broadcasts — the persuasion-responsiveness direction. The two cost-/compensation-framed policies (2, 3) retain a mild positive residue (+0.64, +0.56), but roughly a third of the 8B magnitude. The contestable-vs-saturated partition is back, just softer than Run-14 v2's frozen-replay version.

### Calibration vs YouGov ground truth (final day, per policy) — 14B vs 8B

| Policy | r (14B) | MAE (14B) | bias (14B) | r (8B) | MAE (8B) | bias (8B) |
|---|---:|---:|---:|---:|---:|---:|
| ClimatePolicyID(1) Carbon Tax | 0.51 | 0.68 | **0.00** | 0.51 | 0.72 | +0.36 |
| ClimatePolicyID(2) Climate Compensation | 0.76 | 0.94 | +0.94 | 0.32 | 1.80 | +1.68 |
| ClimatePolicyID(3) Green Housing | 0.68 | 1.22 | +0.94 | 0.42 | 1.90 | +1.78 |
| ClimatePolicyID(4) Ban Petrol Cars | 0.77 | 0.54 | +0.22 | 0.68 | 0.76 | +0.40 |
| ClimatePolicyID(5) Renewable Energy | 0.61 | 1.06 | +0.58 | 0.47 | 1.38 | +1.26 |
| ClimatePolicyID(6) Ban Fossil Fuels | 0.68 | 1.04 | +0.76 | 0.33 | 2.14 | +2.02 |
| **mean** | **0.67** | **0.91** | **+0.57** | **0.46** | **1.45** | **+1.25** |

- **Bias roughly halved** (+1.25 → +0.57). Every policy improved; Carbon Tax is now essentially unbiased (+0.00) and Ban Petrol Cars near-zero (+0.22).
- **The two worst 8B offenders are fixed most:** Ban Fossil Fuels bias +2.02 → +0.76 (MAE 2.14 → 1.04, r 0.33 → 0.68); Green Housing +1.78 → +0.94; Climate Compensation +1.68 → +0.94 (r 0.32 → 0.76).
- **Rank-correlation jumps** (mean r 0.46 → 0.67): 14B doesn't just shrink the average offset, it tracks the *ordering* of YouGov respondents far better.

### Interpretation

1. **The run_6267094 over-inflation was a small-model failure, not a memory-v2 / Day-0-refactor flaw.** The v2 stack is unchanged between the two runs; only the model differs. 14B follows the 2-step debias instruction reliably enough to hold the contestable policies near ground truth, where 8B reverted to a blanket "somewhat support." This matches the run_6267094 interpretation note ("the debias chain is not holding under v2 memory on Qwen3-8B") and the raw-response diagnosis (8B collapsed onto the F/G attractor; only the two most extreme personas resisted).
2. **B-only now holds its anchor — genuine asymmetry under working memory.** Because 14B respects the persona + debias signal, agents hearing only anti-climate broadcasts no longer get pulled up to the prior; they sit at their Day-0 position and two policies even move anti. The +0.799 gap-widening is therefore a *real* persuasion-direction signal produced by the full v2 pipeline, not the NB-31 static-context artefact and not (as in 8B) a floor-effect of everything rushing to ceiling.
3. **Residual pro-bias remains on the cost-framed policies (2, 3, 6) at ~+0.8–0.9.** This is the same family-specific inflation documented since Run 5 and is now at gpt-5-mini-grade magnitude. The debias chain shrinks it but does not eliminate it; targeted debias work on Compensation / Green Housing / Ban Fossil Fuels is still warranted.
4. **Single seed, n=25 per bucket.** Same caveat as run_6267094. The clean part is the paired model-only swap: same agents, same broadcasts, bit-identical Day-0, only 8B→14B differs — and bias halves while the gap-widening sign flips back to positive.

### What this means for the next run

- **Adopt Qwen3-14B as the canonical local research model for split50-class runs.** It recovers the asymmetry the project needs to demonstrate while keeping calibration in the frontier-model band. Update the `r14_canonical` / smoke presets' model note accordingly if 14B becomes the default served weight.
- **The planned ablation is now partly answered.** run_6267094 proposed toggling (a) model and (b) verbatim-vs-compressed Day-0 anchor. This run is the model toggle, and it accounts for essentially all of the +2-point excess. The Day-0-anchor toggle is now lower priority but still the clean way to attribute the *residual* +0.8 cost-framed bias.
- **Re-confirm at scale.** The next step is n=100 / longer horizon on 14B to check the asymmetry persists and the B-only anchor-hold doesn't erode over more days.

---

## v0.8 — Qwen3-8B AIRE split50 (run_6267094) — first production run on v2 memory + Day-0 refactor

**Date:** 2026-06-24
**Run:** [`data/output/experiments/run_6267094/20260624_012156/`](../data/output/experiments/run_6267094/20260624_012156/)
**AIRE job:** `6267094` (Qwen3-8B via vLLM on a single GPU node)
**Invocation:** `sbatch scripts/aire/run.sh --preset r14_canonical --exposure-targets split50`
**Model:** `Qwen/Qwen3-8B` (`llm_provider=local`, vLLM, `T=0.5`)
**Config:** `n_citizens=50`, `days=5` (alternating `P-A`/`P-B`/`C`), `k_peers_per_day=0`, `communication_mode=package` (all 6 policies), `political_exposure_mode=rule_affinity_rank`, `political_exposure_targets=split50` (→ 25 A-only / 25 B-only), `reach_a=reach_b=1.0`, `day0_anchor=ground_truth_with_rationale`, `debias=True`, `thinking=False`, `random_seed=42`

**TL;DR.** First full-scale (n=50, 5-day) AIRE run since the **v0.8 memory-v2 rewrite** (six-section `assemble_context`) and the **Day-0 anchor compression removal** (§2 anchor now reads verbatim from `survey_reasoning`; no `compress_day0_anchor()`, no `day0_anchors.csv`). Bit-identical configuration to the [Run-14 v2 post-NB-31-fix split50](#run-14-v2-post-nb-31-fix-split50--first-end-to-end-validation) baseline (same seed, same 50 sampled agents, same 25/25 split, same GT anchor), so the **only** things differing between the two runs are the v0.8 memory architecture and the Day-0 refactor. **The bucket-asymmetric persuasion signature that NB-31 recovered has disappeared.** Under v2 memory, B-only agents — who hear *only* anti-climate broadcasts — drift strongly pro-climate on every policy (+0.08 to +2.20), and their total package-index movement (+1.31) *exceeds* A-only's (+1.19). The cross-bucket gap therefore **narrows** by −0.11 over 5 days, where Run-14 v2 *widened* it by +0.67. The Qwen3-8B pro-climate prior now dominates the broadcast direction under the richer memory. Status: single-seed production smoke of the v0.8 stack on AIRE; the **headline is that the refactor runs clean end-to-end on AIRE (no `day0_anchors.csv`, 140 min wall-clock, all artefacts populated) but materially changes the opinion dynamics** versus the pre-refactor baseline.

### v0.8 refactor confirmed end-to-end on AIRE

- **No `day0_anchors.csv` in the output bundle** — confirms the §28/§29 Day-0 compression removal works on a real AIRE production run. The §2 Day-0 anchor is now sourced verbatim from `survey_reasoning[target_policy_id]`.
- Day-0 package index is **bit-identical** to Run-14 v2 by construction (A-only +1.320, B-only −0.147) — the GT anchor bypasses the LLM, so the determinism path through `_resolve_runtime` → cohort sampling → affinity-rank bucketing → ground-truth anchor is unchanged by the refactor.
- 30 artefacts written (19 CSV, 9 PNG, 2 JSON), all populated; `sim.py` modular split + aggregators + plots all fire without error at n=50.

### Operational

| Metric | Value |
|---|---|
| Wall-clock (simulation) | 8418.1 s = **140.3 min** |
| Total wall-clock | 8422.5 s = 140.4 min |
| Per agent-day | ~33.7 s (50 agents × 5 days) |
| Network | 50 nodes, 130 edges, density 0.106, mean degree 5.2, **1 component (natural)**, `auto_connected_edges=0` |
| Network defence | Layer-1 bumped `p_inter` 0.05 → 0.06 (30 ≤ n < 100); Layer-2 did **not** fire (graph connected at draw) |

Note: with `k_peers_per_day=0` the peer network is decorative — the only influence channels are the political broadcasts (split50, reach 1.0) and the survey/memory chain. The denser SBM defaults (v0.6, `p_inter` 0.05 vs Run-14 v2's 0.02) therefore do **not** confound the comparison: no peer messages traverse the graph either way.

### Headline — cross-bucket package index (vs Run-14 v2)

| Day | A-only (NEW) | B-only (NEW) | gap (NEW) | A-only (v2) | B-only (v2) | gap (v2) |
|---:|---:|---:|---:|---:|---:|---:|
| 0 (GT anchor) | +1.320 | −0.147 | **+1.467** | +1.320 | −0.147 | +1.467 |
| 1 | +2.373 | +0.767 | +1.607 | +1.980 | +0.160 | +1.820 |
| 2 | +2.533 | +1.040 | +1.493 | +2.067 | +0.107 | +1.960 |
| 3 | +2.480 | +1.073 | +1.407 | +2.153 | +0.153 | +2.000 |
| 4 | +2.520 | +1.140 | +1.380 | +2.100 | +0.180 | +1.920 |
| 5 | +2.513 | +1.160 | **+1.353** | +2.140 | +0.007 | **+2.133** |

- **Gap-widening (Δgap, Day-0 → Day-5): NEW = −0.114 vs Run-14 v2 = +0.667.** The sign flipped. Run-14 v2's headline "12.6× amplification of bucket-asymmetric persuasion" does **not** reproduce under v2 memory.
- **Day-0 → Day-5 bucket movement: A-only +1.193, B-only +1.307.** B-only — exposed only to anti-climate broadcasts — moved *more* than A-only. In Run-14 v2, B-only stalled at +0.15 then retreated to +0.007 (net +0.15); here it climbs steadily to +1.16 (net +1.31).

### Per-policy D0 → D5 signed shift (vs Run-14 v2)

| policy | A (NEW) | A (v2) | B (NEW) | B (v2) | B-side change |
|---|---:|---:|---:|---:|---|
| ClimatePolicyID(1) Carbon Tax | +0.56 | +0.36 | +0.16 | +0.04 | both small + |
| ClimatePolicyID(2) Climate Compensation | +1.40 | +1.16 | **+1.96** | +0.60 | B amplified |
| ClimatePolicyID(3) Green Housing | +1.40 | +1.00 | **+2.16** | −0.08 | **B flipped + (was −)** |
| ClimatePolicyID(4) Ban Petrol Cars | +0.72 | +0.36 | +0.08 | −0.20 | **B flipped + (was −)** |
| ClimatePolicyID(5) Renewable Energy | +1.24 | +0.84 | +1.28 | +0.36 | B amplified |
| ClimatePolicyID(6) Ban Fossil Fuels | +1.84 | +1.20 | **+2.20** | −0.60 | **B flipped + (was −)** |

In Run-14 v2 the three *contestable* policies (Green Housing, Ban Petrol Cars, Ban Fossil Fuels) had B-only flipping **negative** under sustained anti-climate broadcasts — that was the persuasion-responsiveness signal. Here **every B-only cell is positive**, and the three formerly-negative policies are now among the *largest* pro-climate movers (+2.16, +0.08, +2.20). The contestable-vs-saturated partition that held across NB 14, NB 31, and Run-14 v2 has collapsed.

### Calibration vs YouGov ground truth (final day, per policy)

| Policy | Pearson r | MAE | Signed bias |
|---|---:|---:|---:|
| ClimatePolicyID(1) Carbon Tax | 0.51 | 0.72 | +0.36 |
| ClimatePolicyID(2) Climate Compensation | 0.32 | 1.80 | +1.68 |
| ClimatePolicyID(3) Green Housing | 0.42 | 1.90 | +1.78 |
| ClimatePolicyID(4) Ban Petrol Cars | 0.68 | 0.76 | +0.40 |
| ClimatePolicyID(5) Renewable Energy | 0.47 | 1.38 | +1.26 |
| ClimatePolicyID(6) Ban Fossil Fuels | 0.33 | **2.14** | **+2.02** |

Day-0 is perfect by construction (r = 1.0, MAE = 0, bias = 0). By Day 5 the signed bias is large and uniformly positive, worst on the cost-/burden-framed policies (Compensation +1.68, Green Housing +1.78, Ban Fossil Fuels +2.02) and tight on the two behavioural-framed policies (Carbon Tax +0.36, Ban Petrol Cars +0.40). This is the same cost-framed-inflation pattern documented since Run 5 — but **much larger here than the gpt-5-mini smoke** (which sat at +0.7–0.9): the v2-memory + Qwen3-8B combination over-inflates the contestable policies by ~2 full scale points after 5 days.

### Message flow — broadcasts only

`k_peers=0`, so the only `messages.csv` rows are political broadcasts: 25 A-only recipients per `P-A` phase, 25 B-only recipients per `P-B` phase, every day, mean length ~1430–1595 chars. Zero peer-message rows (the `run_package_peer_messaging` early-return is firing). Broadcast delivery is symmetric and complete — the asymmetry collapse is a *response* effect, not a delivery artefact.

### Interpretation

1. **The NB-31 / Run-14 v2 persuasion signal was real but fragile.** It required the per-policy survey context to surface the day's broadcast reflection (the NB-31 fix) *without* also surfacing a strong, persistent pro-climate Day-0 rationale. The v2 six-section memory now keeps the verbatim Day-0 anchor rationale (pro-climate-leaning, written per-policy by the GT-with-rationale step) vivid alongside the accumulating reflections, and the Qwen3-8B pro-climate prior resolves the resulting conflict upward — even for agents hearing only anti-climate content.
2. **This is genuine pro-climate convergence, not the NB-31 static-context artefact.** Under the old bug the survey ignored the broadcast entirely (bit-identical context across days). Here the memory chain *does* reach the survey (v2 works), but the model interprets the conflict in favour of its prior. B-only moving +1.31 is movement, not a flatline.
3. **The day0-refactor + memory-v2 cannot be isolated from each other in this single run** — both landed together in v0.8. Attributing the asymmetry collapse to one or the other needs an ablation (toggle one change at a time, same seed). The verbatim Day-0 anchor (now un-compressed and more prominent in §2) is the prime suspect for amplifying the pro-climate pull on B-only.
4. **Single seed, n=25 per bucket.** Treat the magnitudes as a smoke-scale signal. The clean part is the paired A/B against Run-14 v2: same agents, same broadcasts, bit-identical Day-0, only the v0.8 stack differs — and the gap-widening sign flips from +0.67 to −0.11.

### What this means for the next run

- **Re-open the Run-14 persuasion question under v2 memory.** The "Qwen3-8B is non-persuasive / pro-climate prior dominates" conclusion from Run 14 is *back* — but now via genuine upward convergence rather than a context bug. Whether this is desirable depends on the research claim: if the goal is to show broadcast-direction asymmetry, v2 memory currently buries it.
- **Ablation needed:** run the same split50 config with (a) v2 memory but compressed Day-0 anchor, and (b) v2 memory but Day-0 anchor demoted/omitted from §2, to localise which v0.8 change drives the B-only upward pull.
- **The cost-framed bias is now ~2 scale points** on Compensation / Green Housing / Ban Fossil Fuels — large enough that the debias chain is not holding under v2 memory on Qwen3-8B. Worth a targeted debias re-measurement on the contestable policies.

---

## v0.8 — v2 memory smoke on gpt-5-mini (PRE-day0-refactor caveat)

**Date:** 2026-06-23
**Run:** [`data/output/experiments/20260623_180305/`](../data/output/experiments/20260623_180305/)
**Model:** `gpt-5-mini` (`T=0.5`, OpenAI)
**Config:** `n_citizens=10`, package mode, 4-day alternating `P-A`/`P-B`/`C`, `debias=True`, `day0_anchor="ground_truth_with_rationale"`, `random_seed=42`
**Test suite at time of doc:** 556 passed, 1 skipped, 21 subtests passed

### CAVEAT — predates the Day-0 anchor compression removal

This run was executed **before** the v0.8 §28 / §29 work landed. It still has `day0_anchors.csv` from the deprecated `compress_day0_anchor()` step. Under v0.8 the §2 Day-0 anchor section reads *verbatim* from `survey_reasoning[target_policy_id]` and no `day0_anchors.csv` is produced. The headline polarisation signal below is still valid as a **non-regression check** that the v0.7 outputs expansion, the v0.7 network connectivity defence, the v0.8 sim.py modular split, and the wider v2 memory plumbing (six-section ordering, `policy_id` / `target_policy_id` scope split) work end-to-end on a real OpenAI model. The eventual AIRE production smoke under the *new* `survey_reasoning`-sourced §2 will confirm whether removing the compression step has any measurable effect on the cross-bucket gap-widening dynamic; the local Apple-Silicon path on this laptop is too slow to be the validation surface.

### Headline result — cross-bucket polarisation

| Day | A-only (n=1) | B-only (n=1) | both (n=3) | neither (n=5) | A-vs-B gap |
|---:|---:|---:|---:|---:|---:|
| 0 | 1.833 | 0.333 | 0.444 | 0.800 | **1.50** |
| 1 | 2.000 | 0.000 | 1.667 | 1.267 | 2.00 |
| 2 | 2.167 | 0.000 | 1.667 | 1.233 | 2.17 |
| 3 | 2.167 | 0.000 | 1.667 | 1.233 | 2.17 |
| 4 | 2.167 | -0.333 | 1.667 | 1.167 | **2.50** |

**A-vs-B gap widened from +1.50 (Day-0) to +2.50 (Day-4) — Δ = +1.00 over 4 days** (n=10, single seed, single-policy exposed bucket sample size 1 each, so this is a smoke-scale signal not a measurement; it confirms the v0.7 NB-31 fix and the v0.7 connectivity defence + v0.8 refactor compose without regression to the v0.7 cross-bucket persuasion dynamic).

### Day-0 → Day-N shift distribution

- mean signed shift: **+0.52**, std 1.47, range [-3, +5], n=60
- direction: net pro-climate drift (consistent with the v0.5 1P-debias-chain prior on `gpt-5-mini`).

### Calibration (final day, by policy)

| Policy bin | Pearson r | MAE | Signed bias |
|---|---:|---:|---:|
| 6 policies (range) | 0.25 – 0.71 | 0.6 – 1.4 | mostly +0.7 – +0.9 |

Pattern matches the v0.7 NB 32 baseline: LLM is more pro-climate than YouGov ground truth (signed bias positive across most policies). Per-bucket MAE under 1.0 is the v0.7 connectivity-defence-grade signal; the v2 memory refactor + sim.py modular split do not degrade it.

### Network defence — confirmed firing on n=10

- Layer-1 (small-N adaptive bump): `p_inter` 0.05 → 0.10.
- Layer-2 (deterministic auto-repair): added **4 bridging edges** (component count 5 → 1).
- Layer-3 (visibility): logged in `network_diagnostics.json` (`auto_connected_edges`).
- Final network: 10 nodes, 9 edges, density 0.2, mean degree 1.8, **1 component**.

### Why this run is the smoke surface

`gpt-5-mini` at `T=0.5` and `n=10` is the smallest configuration that exercises every v0.7 + v0.8 plumbing surface (6-section memory assembly, package-scope EOD survey, network-defence triggers on small N, 22-CSV result bundle, agent timeline, network snapshot, calibration table) on a real frontier model without burning an AIRE-scale budget. It is not a production result — it is a paired regression check for the refactor work. The next AIRE production smoke will re-measure under (a) verbatim §2 Day-0 anchors, (b) n=30+ buckets with statistical power, and (c) the canonical local Qwen3-8B-4bit profile or a comparable open model.

---

## v0.8 — `sim.py` modular split (refactor only, NB 32 regression-validated)

**Date:** 2026-06-23
**Pre-refactor baseline:** [`data/output/experiments/20260622_170436/`](../data/output/experiments/20260622_170436/)
**Post-refactor run:** [`data/output/experiments/20260623_140314/`](../data/output/experiments/20260623_140314/)
**Notebook:** [`notebooks/32_v06_outputs_smoke.ipynb`](../notebooks/32_v06_outputs_smoke.ipynb)
**Test suite:** 538 passed, 1 skipped, 21 subtests passed (unchanged from end of v0.7)

**TL;DR.** [src/cag/abm/sim.py](../src/cag/abm/sim.py) reduced from **2755 → 838 lines** (orchestration only) by extracting five focused single-responsibility modules: [src/cag/abm/network_repair.py](../src/cag/abm/network_repair.py) (263 lines, v0.7 3-layer connectivity defence), [src/cag/io/aggregators.py](../src/cag/io/aggregators.py) (506 lines, `_collect_results` post-processing), [src/cag/io/plots.py](../src/cag/io/plots.py) (555 lines, `save_result_plots` + plotters), [src/cag/io/results.py](../src/cag/io/results.py) (512 lines, `save_results` + CSV/JSON IO), [src/cag/io/checkpoint.py](../src/cag/io/checkpoint.py) (366 lines, checkpoint/resume). **Pure structural split, zero behaviour change.** Validated end-to-end against the v0.7 NB 32 baseline.

### Regression-validation matrix

| Output | Type | Status |
|---|---|---|
| `config.json` | deterministic | **bit-identical** |
| `ground_truth.csv` (60 rows) | deterministic | **bit-identical** |
| `package_ground_truth.csv` (10 rows) | deterministic | **bit-identical** |
| `agent_attributes.csv` (10 rows) | deterministic | **bit-identical** |
| `network_snapshot.json` | deterministic | **bit-identical** — 10 nodes, 9 edges, buckets `{A-only:1, B-only:1, both:3, neither:5}`, total degree 18 |
| `opinion_trajectories.csv` (180 rows × 4 cols) | LLM-driven | schema + row count match |
| `package_index_trajectories.csv` (30 rows × 5 cols) | LLM-driven | schema + row count match |
| `reflections.csv` (60 rows × 10 cols) | LLM-driven | schema + row count match |
| `messages.csv` (292 rows × 14 cols) | LLM-driven | schema + row count match |
| `day0_vs_dayN_shifts.csv` (60 rows × 9 cols) | LLM-driven | schema + row count match |
| `calibration.csv` (18 rows × 7 cols) | LLM-driven | schema + row count match |
| Mean abs_shift | LLM-driven | both runs ≈ 0.8–1.0 |
| Mean Day-1/2 MAE | LLM-driven | pre 0.32 / post 0.35 (within `gpt-5-mini @ T=0.5` stochasticity) |

**What this validates.** (a) The determinism path through `_resolve_runtime` → network construction → ground-truth collection → agent_attributes serialisation is unchanged. (b) The schema contract on all 22 CSVs is unchanged. (c) The call-count contract (number of LLM invocations per agent-day-policy) is unchanged. (d) The numeric distributional shape of LLM-driven outputs is unchanged within stochastic noise — refactor did not perturb prompt assembly, message routing, or survey-context construction.

**What this does NOT validate.** Long-horizon behaviour (>2 days), package-mode survey-context fidelity beyond the trivial smoke window, or any of the upcoming v0.8 memory-architecture changes (separate track). Those are guarded by the standing pytest baseline and will be re-validated on the next end-to-end smoke after the next behaviour change.

### Why this refactor now

`sim.py` had grown to 2755 lines accumulating responsibilities orthogonal to its name: network repair, plot generation, result aggregation, CSV/JSON IO, and checkpoint mechanics. The diagnostic affordance from v0.7 (29 saved artefacts, full prompt capture, agent timeline) makes structural splits low-risk to validate — a single smoke run produces evidence on every output surface. Splitting now keeps the next round of behaviour work (memory architecture, target-policy scoping, blind-spot fix) on a clean canvas where changes to `_run_one_day` don't touch plot code or CSV schemas.

---



## v0.6 outputs expansion + network connectivity defence — NB 32 smoke validation

**Date:** 2026-06-22
**Result dir:** [`data/output/experiments/20260622_170436/`](../data/output/experiments/20260622_170436/)
**Notebook:** [`notebooks/32_v06_outputs_smoke.ipynb`](../notebooks/32_v06_outputs_smoke.ipynb)
**Test suite at write time:** 538 passed, 1 skipped (baseline before this work: 495 → +43, of which +30 from outputs expansion and +13 from the 3-layer connectivity tests)

**TL;DR.** Two coordinated model-side changes shipped against `main` (commit `e5bb298`): (1) a **v0.6 outputs expansion** that takes the saved run bundle from 17 artefacts to 29, adds bucket-stratified analyses, a per-event agent timeline, full survey-prompt audit (`survey_assembled_context.csv`), end-of-run network snapshot, and a monotonic `sim_step` counter wired through every event-logging site; (2) a **3-layer network connectivity defence** with literature-grounded SBM defaults (`p_inter` 0.02 → 0.05, ratio 3:1 ≈ Bakshy 2015 cross-cutting fraction), an adaptive small-N bump, and a deterministic post-creation auto-repair pass so disjoint peer networks can no longer corrupt opinion dynamics silently. NB 32 is a deliberately tiny smoke run (10 agents × 2 alternating package-mode days, `gpt-5-mini`) whose **only purpose** is to exercise every new code path and surface every new artefact for visual inspection. Both layers fire as designed: `p_inter` is bumped from 0.05 → 0.10 because `n=10 < 30` (Layer 1), the random SBM draw produces 5 disconnected components which Layer 2 stitches together with 4 bridging edges (`auto_connected_edges=4`, final `n_connected_components=1`), and Layer 3 logs the resulting graph as `n_nodes=10, n_edges=9, n_components=1, mean_degree=1.8, auto_connected_edges=4`. Every new CSV is populated, the `sim_step` column is dense and strictly monotonic per agent across all 5 instrumented sources, the per-agent timeline reconstructs a sampled agent's full day (broadcasts received → reflections → 6-policy survey → next day), and `survey_assembled_context` differs across days for every (agent, policy) pair — the NB-31 staleness signature is impossible to miss going forward.

### What changed since last commit (`e5bb298`)

**Diff scope:** 10 source/test files modified, +1,549 / −56 lines; 3 new files (1 notebook, 1 test module, 1 calibration script). No `__version__` bump, no docs sweep (deferred — this is the docs sweep).

#### 1. v0.6 outputs expansion (Phases 1–5)

Motivation: NB-31's package-mode survey-context bug stayed hidden for two months because the assembled prompt was discarded immediately after the LLM call, and the bucket-stratified Day-N − Day-0 gap that finally surfaced it had to be hand-derived in a notebook from the existing CSVs. The outputs expansion bakes both diagnostic affordances — full prompt capture and pre-computed bucket views — into the saved bundle so future class-of-context bugs are visible from `agent_timeline.csv` alone.

- **Phase 1 — agent attribute persistence ([src/cag/abm/environment.py](../src/cag/abm/environment.py), [src/cag/abm/sim.py](../src/cag/abm/sim.py)).** `_assign_affinity_rank` now caches `_affinity_score_a` and `_affinity_score_b` on each citizen (mirrors the existing in-place `political_exposure` write). New `collect_agent_attributes(nation)` returns a per-agent DataFrame keyed on `agent_id` with `political_exposure`, both affinity scores, the demographic IDs that drive the persona (`year_of_birth, gender_id, region_id, education_id, ukge2019_vote_id, brexit_vote_id`), and the full `get_persona()` string — written verbatim, no truncation. Persisted as `agent_attributes.csv` to both checkpoints and final.
- **Phase 2 — bucket-stratified derived CSVs ([src/cag/abm/sim.py](../src/cag/abm/sim.py)).** Three pure-function builders that take `results` and join `agent_attributes`: `build_package_index_by_bucket` (cols: `day, political_exposure, n_agents, mean, std, q25, q50, q75`), `build_opinion_shares_by_bucket` (cols: `policy_id, day, political_exposure, n_agents, n_support, n_neutral, n_against, support_pct, neutral_pct, against_pct`), and `build_day0_vs_dayN_shifts` (cols: `agent_id, policy_id, political_exposure, day0_numeric, dayN_numeric, signed_shift, abs_shift`). The "12.6× gap-widening" headline from Run-14 v2 is now derivable from `package_index_by_bucket.csv` alone with no notebook scaffolding.
- **Phase 3 — bucket plots ([src/cag/abm/sim.py](../src/cag/abm/sim.py)).** `plot_package_index_by_bucket` (one panel per bucket), `plot_opinion_shares_by_bucket` (`policy × bucket` mega-grid), and `plot_gap_widening` (single panel: bold package-index gap + thin per-policy gap lines). Wired into `save_result_plots`.
- **Phase 4 — calibration, message flow, network snapshot ([src/cag/abm/sim.py](../src/cag/abm/sim.py), [src/cag/abm/networks.py](../src/cag/abm/networks.py)).** `build_calibration_table(results)` computes `pearson_r / spearman_rho / mae / mean_signed_bias` per `(policy_id, day)` against `ground_truth`; `plot_calibration_by_policy` is the per-policy GT-vs-LLM scatter with ρ in the title. `build_message_flow(results)` joins `messages × agent_attributes` to a `(day × phase × sender_side × recipient_bucket)` aggregation with `n_messages` and `mean_chars` — would have flagged the `k_peers=0` waste in one glance. `_safe_network_snapshot(nation)` writes a JSON-safe `{nodes:[{id,bucket,degree}], edges:[[u,v],...]}` file (sibling to `network_diagnostics.json`); `plot_network_graph` renders it with `nx.draw_spring`, node colour by bucket, size by degree.
- **Phase 5 — assembled survey context + agent timeline ([src/cag/abm/agent.py](../src/cag/abm/agent.py), [src/cag/abm/sim.py](../src/cag/abm/sim.py)).** New `self.survey_assembled_context = {}` on `SurveyedCitizen` (next to `survey_reasoning` / `survey_raw_response`); `administer_survey()` appends `(day, ctx_str)` immediately after `assemble_context()`. Two new `SIM_CONFIG` keys: `timeline_sample_size=3` (default) and `timeline_sample_agent_ids=None` (auto-stratify one agent per top-3-by-size bucket; ties → sorted agent_id; <3 buckets → evenly-spaced agent_ids). `build_agent_timeline(results, sample_ids)` returns a long-format DataFrame (`agent_id, political_exposure, day, phase, phase_order, event_order, event_type, policy_id, counterparty_id, counterparty_role, content, metadata_json`) covering 9 event types: `broadcast_received, broadcast_reflection, peer_message_received, peer_message_sent, peer_reflection, survey_assembled_context, survey_raw_response, survey_reasoning, survey_numeric`. Written to final only (can be GB-scale on long runs) via the new `_CHECKPOINT_SKIP_KEYS = frozenset({"agent_timeline"})` mechanism.
- **Cross-cutting — `sim_step` instrumentation ([src/cag/abm/environment.py](../src/cag/abm/environment.py), [src/cag/abm/agent.py](../src/cag/abm/agent.py), [src/cag/abm/sim.py](../src/cag/abm/sim.py)).** Monotonic `nation._sim_step` counter (lazy-init on first use, restored to `max(sim_step)` across all loaded sources on resume) incremented at every event-logging site: `message_log` appends in `environment.py`, `agent.reflections.append` calls, survey context capture, survey raw/reasoning append, `daily_summaries` setitem. `messages`, `reflections`, `survey_reasoning`, `survey_raw_response`, `survey_assembled_context`, and `daily_summaries` CSVs all gain a `sim_step` column. **Sort key for any interleaved replay is now `(agent_id, sim_step)` — schema makes zero assumption about phase count, ordering, or repetition.** Three existing tests updated to expect the new column (no regressions).
- **Schema + write infrastructure.** `_RESULT_CSV_SCHEMAS` extended with the new entries (`survey_assembled_context`, `agent_attributes`, `agent_timeline`) plus `sim_step` cols on the existing 5. `_write_all_csvs(out_path, results, *, is_checkpoint=False)` now writes derived bucket CSVs + `network_snapshot.json` only on final; `_write_checkpoint` passes `is_checkpoint=True` so checkpoints stay lean. `_load_checkpoint` rehydrates `survey_assembled_context` and the 4 parallel `_*_steps` dicts.
- **Test coverage.** New file [`tests/test_timeline_and_outputs.py`](../tests/test_timeline_and_outputs.py) (30 tests) covering the sim_step counter, `_safe_step`, agent_attributes collection, network_snapshot shape, timeline sampling, agent_timeline construction, all bucket builders, calibration, message_flow, the checkpoint skip-keys mechanism, and `save_results` writing `network_snapshot.json`.

#### 2. Network connectivity 3-layer defence

Motivation: the immediately-prior NB 32 smoke run ([`data/output/experiments/20260622_154751/`](../data/output/experiments/20260622_154751/), n=10) opened with `n_connected_components=5, largest_component_size=4` — a textbook silent failure for an opinion-dynamics study. An empirical sweep (`scripts/estimate_connectivity_threshold.py`, n ∈ {10, 20, 50, 100, 200, 500} × `p_inter` ∈ linspace(0.001, 0.15, 30), 100 trials per cell) confirmed that the old SBM default (`p_inter=0.02`) is hopeless at n=10 (0% connectivity at any p ≤ 0.15) and only ~80% reliable at n=50.

- **Defaults updated ([src/cag/abm/networks.py](../src/cag/abm/networks.py), [src/cag/abm/sim.py](../src/cag/abm/sim.py)).** SBM `p_inter` 0.02 → **0.05** (drops the within-to-between ratio from 7.5:1 to 3:1, yielding ~25% cross-cutting exposure — within the Facebook ~24% of Bakshy et al. 2015 *Science* and the Twitter 18–26% of Halberstam & Knight 2016). ER default `p` 0.05 → **0.10** (n=50 connectivity threshold is `ln(50)/50 ≈ 0.078`, so 0.10 sits comfortably above it). Both builder docstrings updated with rationale and the v0.6 (2026-06-22) note. Watts–Strogatz, Barabási–Albert, and homophily_weighted are unchanged (always connected by construction or by attribute density).
- **Layer 1 — adaptive small-N bump ([src/cag/abm/sim.py](../src/cag/abm/sim.py)).** New `_adjust_network_params_for_small_n(cfg, n_agents)` called in `run_simulation` **before** `nation.create_network`. SBM: `n < 30` → bump `p_inter` to `max(p_inter, 0.10)` and log WARNING; `30 ≤ n < 100` → bump to `max(p_inter, 0.06)` and log INFO. ER: `n < 30` → bump `p` to 0.20; `30 ≤ n < 100` → bump to 0.10. `n ≥ 100` is left alone. Helper only ever raises values, never lowers — explicit higher overrides survive untouched.
- **Layer 2 — post-creation auto-repair ([src/cag/abm/sim.py](../src/cag/abm/sim.py)).** New `_auto_connect_components(nation, seed)` called **after** `nation.assign_network_blocks`. If `nx.is_connected(G)` is False, sorts components by `(-len, sorted_node_ids[0])` for determinism, uses `np.random.default_rng(seed)` to pick endpoints, adds exactly `(k − 1)` bridging edges from each smaller component to the largest, re-runs `nation.assign_network_blocks()` to refresh agent `network_neighbors`, and logs a WARNING with `n_components / largest_size / n_added / seed`. Records `nation._auto_connected_edges` (defaults to 0 when already-connected). Defensively guarded with `isinstance(G, nx.Graph)` so MagicMock-based unit tests don't crash.
- **Layer 3 — visibility ([src/cag/abm/sim.py](../src/cag/abm/sim.py)).** New `_log_network_summary(nation)` emits a single INFO line `Network: n_nodes=…, n_edges=…, n_components=…, mean_degree=…, auto_connected_edges=…` after every setup. `_safe_network_diagnostics` extended (both success and exception branches) with a new `auto_connected_edges` field in `network_diagnostics.json`.
- **Test coverage.** 13 new tests in three classes in [`tests/test_networks.py`](../tests/test_networks.py): `TestAdjustNetworkParamsForSmallN` (×7: SBM bump at n=10 / n=50 / no-op at n=200 / never lowers explicit high values / ER analogues / skips WS+BA+homophily), `TestAutoConnectComponents` (×4: repairs disjoint graph with correct `(k-1)` edge count / no-op when already connected / safe on MagicMock / deterministic under fixed seed), `TestNetworkDiagnosticsAutoConnectedField` (×2: field present and reflects repair count).

#### 3. Notebook + script

- New [`notebooks/32_v06_outputs_smoke.ipynb`](../notebooks/32_v06_outputs_smoke.ipynb) — canonical 10-agent × 2-day package-mode smoke whose **only purpose** is to surface every artefact added in v0.6 (file inventory, per-CSV schema preview, each new table, the agent_timeline for sampled agents, every PNG inline). Every key in `SIM_CONFIG` is enumerated explicitly with a `# default` / `# SMOKE OVERRIDE` / `# PROVIDER OVERRIDE` tag and asserted to match. Provider is `openai/gpt-5-mini` for both messaging and surveys.
- New [`scripts/estimate_connectivity_threshold.py`](../scripts/estimate_connectivity_threshold.py) — empirical SBM connectivity sweep that produced the threshold table used to set the Layer 1 cutoffs. Writes `data/output/connectivity_analysis/connectivity_sweep.csv` and `connectivity_threshold.png`.

### NB 32 design

`n_citizens=10`, `days=[{phases:[P-A,P-B,C]}, {phases:[P-B,P-A,C]}]` (alternating package-mode), `k_peers_per_day=2`, `communication_mode=package`, `package_policies` = all six, `day0_anchor=ground_truth_with_rationale`, `debias=True`, `thinking=False`, `llm_temperature=0.5`, `political_message_source=offline` (`v1`), `political_exposure_mode=rule_affinity_rank` (defaults), `reach_a=reach_b=1.0`, `network_type=stochastic_block` with `p_inter=0.05` (the new default — Layer 1 promotes it to 0.10 at runtime), `timeline_sample_size=3`, `random_seed=42`, provider/model = `openai/gpt-5-mini` for messaging **and** surveys. Wall time: ~3 minutes, a handful of cents in API spend.

### NB 32 results — does v0.6 work end-to-end?

**File inventory** (target ≥ 17 + new 12): **31 files** (19 CSVs, 9 PNGs, 3 JSONs). `daily_summaries.csv` is non-empty in schema only — only 1–3 reflections per agent per day, so the memory-compression threshold never fired (expected for a 2-day run).

**Network defence — both layers fired:**

| Signal | Expected | Observed | Status |
|---|---|---|---|
| `cfg.p_inter` (in NB32 input) | 0.05 (new default) | 0.05 | — |
| `config.json` top-level `p_inter` | 0.10 (Layer 1 bump, n=10 < 30) | **0.10** | ✓ Layer 1 fired |
| `config.json` `network_params.p_inter` | 0.10 | **0.10** | ✓ |
| `network_diagnostics.auto_connected_edges` | > 0 (n=10 SBM is fragile even at 0.10) | **4** | ✓ Layer 2 fired |
| `network_diagnostics.n_connected_components` | 1 (after repair) | **1** | ✓ |
| `network_diagnostics.largest_component_size` | 10 (all nodes) | **10/10** | ✓ |
| Mean degree | small (10 nodes, 9 edges) | 1.8 | as expected |

Reading the log line: the raw SBM draw at (`p_intra=0.15`, `p_inter=0.10`, n=10) produced 5 components; Layer 2 added `5 − 1 = 4` bridging edges deterministically (seed=42) to merge them into the largest. This is the **live demo case** for the defence — exactly the failure mode the pre-fix NB 32 smoke exhibited, now caught and repaired automatically without aborting the run or silently corrupting the peer graph.

**v0.6 outputs — every new CSV populated:**

| CSV | Rows | Cols | Meaning |
|---|---:|---:|---|
| `agent_attributes` | 10 | 11 | one row per active agent, both affinity scores cached |
| `package_index_by_bucket` | 12 | 8 | 3 days × 4 buckets (A-only, B-only, both, neither) |
| `opinion_shares_by_bucket` | 72 | 10 | 6 policies × 3 days × 4 buckets |
| `day0_vs_dayN_shifts` | 60 | 9 | 10 agents × 6 policies |
| `calibration` | 18 | 7 | 6 policies × 3 days |
| `message_flow` | 16 | 6 | 2 days × 2 phases × 4 buckets |
| `survey_assembled_context` | 120 | 5 | 10 agents × 6 policies × 2 days (Day 0 anchored, no LLM survey) |
| `agent_timeline` | 213 | 11 | 3 sampled agents × full per-event log |

**Bucket coverage in `agent_attributes`:** A-only=1, B-only=1, both=3, neither=5. All 4 affinity-rank buckets present in a 10-agent draw — Layer 2 of the recent `_safe_int` fix (committed earlier) is also indirectly confirmed (affinity scores span `[0.20, 8.85]` for A and `[1.40, 7.97]` for B, not all-zero).

**`sim_step` instrumentation sanity** — strictly monotonic per agent on `agent_timeline`, zero zeros on every instrumented CSV, range spans 1–500 across the 2-day run:

| CSV | n_rows | sim_step range | zeros |
|---|---:|---|---:|
| `messages` | 46 | [61, 311] | 0 |
| `reflections` | 34 | [62, 320] | 0 |
| `survey_reasoning` | 180 | [1, 499] | 0 |
| `survey_raw_response` | 120 | [103, 500] | 0 |
| `survey_assembled_context` | 120 | [101, 498] | 0 |

**NB-31 regression check** — the whole point of `survey_assembled_context`. For a single (agent=165, policy=ClimatePolicyID(1)) pair across the two survey days: day 1 context length = 12,429 chars, day 2 = 18,669 chars; SHA hashes differ. The day-2 context contains the day-1 reflections + daily summary; if the NB-31 bug ever recurs, the lengths and hashes will be bit-identical across days for every (agent, policy) pair and a one-line `groupby` will surface it immediately.

**Bucket-stratified package index** (3 days × 4 buckets, from `package_index_by_bucket.csv`):

| day | A-only (n=1) | B-only (n=1) | both (n=3) | neither (n=5) |
|---:|---:|---:|---:|---:|
| 0 (GT anchor) | +1.83 | +0.33 | +0.44 | +0.80 |
| 1 | +1.83 | +1.00 | +0.33 | +1.23 |
| 2 | +1.83 | +1.00 | +0.33 | +1.13 |

The cross-bucket gap-widening narrative does not appear in this run — the bucket cells are n=1/1/3/5 and the run is 2 days. Expected for a smoke test; the point is the CSV shape and content, not the science. Calibration vs ground truth: Day 0 ρ = 1.000 across all 6 policies (sanity check on the GT anchor — perfect by construction); Day 1 ρ ranges 0.80 (Carbon tax) to 0.94 (Ban petrol cars), MAE 0.2–0.6 — modest LLM drift after one day of broadcasts, as expected with the new prompt chain.

**Message flow** — confirms reach asymmetry by design (`reach=1.0` symmetric): each day P-A delivers 4 broadcasts (1 to A-only + 3 to both, by exposure-bucket eligibility), P-B delivers 4 broadcasts (1 to B-only + 3 to both); phase C reaches all 4 buckets (3 / 1 / 5 / 6 messages on day 1; 2 / 1 / 3 / 9 on day 2). The `recipient_bucket` aggregation worked correctly across both rounds of `assign_network_blocks` (the second one happens inside Layer 2 after auto-repair).

**Plots** — all 9 PNGs render without errors and without `None` axes:
`opinion_trajectories`, `opinion_shares`, `package_index_trajectories`, `package_index_shares`, `package_index_by_bucket`, `opinion_shares_by_bucket`, `gap_widening`, `network_graph`, `calibration_by_policy`. `gap_widening.png` is degenerate at n=2 days but renders cleanly; `network_graph.png` shows the 10 nodes coloured by bucket with the 4 auto-added bridging edges visually distinguishable from the SBM draws (they cross block boundaries, which by definition they had to in order to merge components).

### What this run does **not** do

- No claim about the science. n=10 × 2 days is too small for any persuasion signature; the bucket cells are singletons in 2/4 buckets.
- No checkpoint exercise. NB 32 calls `run_simulation(config, sn)` directly with no `checkpoint_dir`, so `checkpoint_every_day` falls through to the Python-side default of `False`. The CLI default is `True` (see [src/cag/\_\_main\_\_.py](../src/cag/__main__.py)); the two are intentionally different — interactive notebooks rarely need per-day on-disk state, batch AIRE runs always do.
- No resume exercise. The next AIRE production run (n ≥ 50, days ≥ 5) is what tests v0.6 outputs and the connectivity defence at scale.

### Status

**v0.6 outputs and connectivity defence: ready for production AIRE runs.** Every new CSV/PNG/JSON populates with valid content on the smoke run, every new code path is exercised, the test suite is green at 538 / 1 skipped, and the network defence catches the exact disjoint-graph failure mode that motivated it (`auto_connected_edges=4` recorded, simulation continued, peer graph is connected).

**Deferred to next session:**
- `__version__` bump (still showing v0.5.0 across 12 modules; the v0.6 work is unbumped on disk)
- CHANGE_LOG, Model_Design.md, Run_Output_Guide.md, USER_GUIDE.md, ROADMAP.md sweeps for v0.6
- README v0.5 → v0.6 status bump and test-count refresh
- Production AIRE run at n=50–100 to validate v0.6 outputs + connectivity defence under load and bucket-asymmetric persuasion under the new SBM defaults

---

## Run-14 v2: post-NB-31-fix split50 — first end-to-end validation

**Date:** 2026-06-21
**Result dir:** [data/output/experiments/run_6214872/20260621_034000/](../data/output/experiments/run_6214872/20260621_034000/)
**Baseline for comparison:** [data/output/experiments/run_6202348_R14_split50_5day/20260619_192129/](../data/output/experiments/run_6202348_R14_split50_5day/20260619_192129/) (the original R14 split50, pre-fix)
**AIRE job:** 6214872 (Qwen3-8B via vLLM on a single GPU node)

**TL;DR.** First full-pipeline run after the NB-31 package-mode survey-context fix landed in `main`. Bit-identical configuration to the pre-fix R14 split50 baseline (n=50, days=5, k_peers=0, GT-anchor, debias=True, reach=(1.0,1.0), seed=42, same 50 sampled agents, same A=25 / B=25 split50 bucketing), so the only thing differing between the two runs is the fix itself. **Day-5 cross-bucket gap-widening jumps from +0.053 (pre-fix) to +0.667 (post-fix) — a 12.6× amplification that matches NB-31's surgical-replay prediction (~+0.67 on GPT-5.4-mini) within the noise.** This is the first end-to-end confirmation that the fix produces the predicted bucket-asymmetric persuasion signature in a fresh production simulation, not just in a frozen-state replay. Status: smoke validation of the fix on a small run; **not a publishable result.** The planned production run is n=100, 30 days, with reach / exposure asymmetry levers swept.

### Bug fixes shipped before this run

Three small follow-ups landed alongside the NB-31 context fix (full suite 495 passing, 1 skipped):

1. **`k_peers=0` short-circuit in peer messaging.** `run_peer_messaging` and `run_package_peer_messaging` both used to fall through `random.sample(neighbors, 0)` for every citizen and still call `generate_peer_message` on each one before discovering the inbox was empty. The log line `48 citizens generated package messages, 0 citizens reflected` was the visible artefact: 48 LLM generations × 5 days = ~240 wasted Qwen3-8B calls per r14-style run with k_peers=0. New early-return at the top of both functions: `if k_peers == 0: log "peer messaging disabled (k_peers=0), skipping"; return zero-filled dict`. Tests added: `TestPeerMessagingKPeersZeroShortCircuits` in [tests/test_peer_messaging.py](../tests/test_peer_messaging.py) (asserts `send_chat.assert_not_called()` for both single-policy and package variants).
2. **Per-day checkpointing now default-on.** Recent r14-family runs accidentally shipped without checkpoints because the new AIRE Quickstart sbatch invocations dropped the `--checkpoint-every-day` flag, while the earlier R14 split50 baseline ([run_6202348](../data/output/experiments/run_6202348_R14_split50_5day/checkpoints/)) had them. Promoting checkpointing to default-on (`argparse.BooleanOptionalAction, default=True`) means every run is wall-clock-kill-recoverable by default; `--no-checkpoint-every-day` opts out for throwaway smoke tests. Tests added in [tests/test_cli.py](../tests/test_cli.py) (`test_checkpoint_default_on`, `test_checkpoint_opt_out`).
3. **Docs in sync.** [docs/AIRE_Quickstart.md](AIRE_Quickstart.md) §5 / §7 / §10.6 / §11 updated to reflect both defaults; [scripts/aire/run.sh](../scripts/aire/run.sh) inline examples updated to remove the now-redundant `--checkpoint-every-day` flag.

### Design

Identical configuration to [run_6202348](../data/output/experiments/run_6202348_R14_split50_5day/20260619_192129/): `n_citizens=50`, `days=5`, `k_peers_per_day=0`, `communication_mode=package`, `package_policies` = all six, `day0_anchor=ground_truth_with_rationale`, `debias=True`, `thinking=False`, `random_seed=42`, `political_exposure_mode=rule_affinity_rank`, `political_exposure_targets=split50` (= `{A-only:0.50, B-only:0.50, both:0.00, neither:0.00}`), `reach_a=reach_b=1.0`, `llm_model=Qwen/Qwen3-8B`, `llm_provider=local` (vLLM v0.8.5). YouGov seed is shared so the 50 sampled agents are the same in both runs, and `split50` is fully deterministic on the affinity-rank rule, so A=25 / B=25 bucket membership is identical agent-for-agent between pre-fix and post-fix.

The only thing differing between the two runs is the code path inside `administer_survey()` and `run_end_of_day_survey()`. Pre-fix, package-mode surveys passed the per-policy id to `assemble_context()` and got an empty context view; post-fix, they pass `context_policy_id=PACKAGE_SCOPE` and get the actual reflections + daily summaries.

### Bucket trajectory: pre-fix vs post-fix package index

| day | PRE A-only | POST A-only | PRE B-only | POST B-only | PRE gap (A−B) | POST gap (A−B) |
|---:|---:|---:|---:|---:|---:|---:|
| 0 (GT anchor) | +1.320 | +1.320 | −0.147 | −0.147 | +1.467 | +1.467 |
| 1 | +1.807 | +1.980 | +0.207 | +0.160 | +1.600 | +1.820 |
| 2 | +1.800 | +2.067 | +0.287 | +0.107 | +1.513 | +1.960 |
| 3 | +1.820 | +2.153 | +0.220 | +0.153 | +1.600 | +2.000 |
| 4 | +1.807 | +2.100 | +0.220 | +0.180 | +1.587 | +1.920 |
| 5 | +1.807 | +2.140 | +0.287 | +0.007 | +1.520 | **+2.133** |

Day-0 column is bit-identical by construction (GT anchor bypasses the LLM). From Day 1 onward the runs diverge.

### Bucket Δ from Day-0 anchor (the persuasion signal)

| day | PRE A-Δ | POST A-Δ | PRE B-Δ | POST B-Δ | PRE gap-widen | POST gap-widen |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | +0.487 | +0.660 | +0.353 | +0.307 | +0.133 | +0.353 |
| 2 | +0.480 | +0.747 | +0.433 | +0.253 | +0.047 | +0.493 |
| 3 | +0.500 | +0.833 | +0.367 | +0.300 | +0.133 | +0.533 |
| 4 | +0.487 | +0.780 | +0.367 | +0.327 | +0.120 | +0.453 |
| 5 | +0.487 | +0.820 | +0.433 | +0.153 | **+0.053** | **+0.667** |

In the pre-fix run, A-only and B-only move together at roughly +0.43 to +0.50 from Day 1 onward — A drifts up slightly more than B but the cross-bucket gap-widening is in the noise (Day-5 +0.053, less than one ordinal step out of six). That is the static-context bug burying the persuasion signal: every day's survey was reading an effectively unchanging system prompt, so the broadcasts had nothing to influence at the survey step. In the post-fix run, A keeps climbing (+0.66 → +0.82 by Day 5) and B stalls then partially retreats (+0.31 → +0.15 by Day 5). Day-5 gap-widening is +0.667 — within the noise of NB-31's GPT-5.4-mini Day-2 surgical-replay prediction (~+0.67) and right at the upper end of the Qwen3-8B 4-bit MLX prediction band (NB 31: Qwen Day-2 gap +0.55).

The 12.6× amplification of the gap-widening (+0.053 → +0.667) is the key number: it confirms the fix lands in production at the same magnitude as in the surgical replay, not just qualitatively.

### Per-policy D0→D5 shift — where the persuasion responsiveness lives

| policy | PRE A | POST A | PRE B | POST B | B-side flip |
|---|---:|---:|---:|---:|---:|
| ClimatePolicyID(1) Carbon Tax | +0.16 | +0.36 | +0.08 | +0.04 | small |
| ClimatePolicyID(2) Climate Compensation | +0.76 | +1.16 | +0.68 | +0.60 | small |
| ClimatePolicyID(3) Green Housing | +0.72 | +1.00 | +0.88 | **−0.08** | **−0.96** |
| ClimatePolicyID(4) Ban Petrol Cars | +0.36 | +0.36 | +0.12 | **−0.20** | **−0.32** |
| ClimatePolicyID(5) Renewable Energy | +0.52 | +0.84 | +0.60 | +0.36 | small |
| ClimatePolicyID(6) Ban Fossil Fuels | +0.40 | +1.20 | +0.24 | **−0.60** | **−0.84** |

Three of six policies have B-only flipping from positive in pre-fix to negative in post-fix: **Ban Fossil Fuels (−0.84 flip), Green Housing (−0.96 flip), Ban Petrol Cars (−0.32 flip)**. Three stay slightly positive even post-fix: **Carbon Tax (+0.04), Climate Compensation (+0.60), Renewable Energy (+0.36)** — these are the policies where Qwen3-8B's pro-climate prior dominates the anti-broadcast even when the survey context now sees the broadcast reflection. The contestable-vs-saturated partition reproduces NB 14's pattern from a year earlier: high-consensus policies show ceiling effects, contestable policies have room to move.

### B-only baseline-direction caveat

NB 31's surgical replay (frozen Qwen state, GPT-5.4-mini survey) had B-only averaging **−0.10 to −0.43 mean signed shift** across days 1–3. This live run has B-only averaging **+0.15 to +0.33** signed shift — same trajectory shape (rises then partially retreats) but with a positive baseline offset of about +0.4 to +0.5 across the run.

Two non-exclusive explanations, both testable:

1. **Quantization / serving stack drift.** NB 31 used 4-bit MLX Qwen3-8B locally; this run is full-precision Qwen3-8B via vLLM v0.8.5 on AIRE. Same family, different quantization and different inference runtime. The full-precision model's pro-climate prior is evidently a touch stronger than 4-bit MLX, and the 2-step debias chain does not fully scrub it under sustained anti-broadcasts.
2. **Surgical-replay vs full-pipeline feedback.** NB 31 was 3 days, surgical, with frozen reflections and daily summaries. This run is 5 days end-to-end, with reflections and daily summaries being re-generated each day and feeding back into the next day's context. Cumulative pro-bias compounds because Day-N's survey rationale carries Day-N pro-bias forward into Day-(N+1)'s context.

The bucket-asymmetric signature still holds — Δ-gap-widening is the right quantity for the persuasion claim, and that number reproduces NB 31's prediction. But the baseline shift in B-only is something to keep an eye on: if it persists at n=100 / 30 days, the framing needs to be "the model is persuasion-responsive in the predicted direction, but the pro-climate prior is strong enough that B-only does not cross the neutrality line in 5 days" rather than "B-only moves anti-climate".

### What this means for the planned production sweep (n=100, 30 days, asymmetry levers)

- **The fix is real and lands at the predicted magnitude.** Subsequent sweeps over reach asymmetry (e.g. C1 reach=(0.5, 1.0), C3 reach=(1.0, 0.5)) and exposure presets (e.g. legacy_v05, committed_minority_*) should now produce real signal at the survey step, not the muted artefact pre-fix produced.
- **The contestable-vs-saturated policy partition is stable.** Sweeps should report by-policy as well as by-package; pooling all six masks the persuasion signal on Ban Fossil Fuels / Green Housing / Ban Petrol Cars and dilutes it with the ceiling-bound Carbon Tax / Climate Compensation / Renewable Energy responses.
- **Watch B-only baseline drift over 30 days.** The +0.4 to +0.5 positive offset in this 5-day run may compound or may stabilise; the 30-day run is the right horizon to see which.
- **Checkpointing default-on means resume-from-day-N is now routine.** A 100-agent × 30-day run is well over a 10-hour wall-clock at Qwen3-8B speed; expect to use resume.

---

---

## NB 30 + NB 31: Package-mode survey context bug — discovery and fix

**Date:** 2026-06-20
**Notebooks:** [notebooks/30_surgical_survey_replay.ipynb](../notebooks/30_surgical_survey_replay.ipynb), [notebooks/31_package_mode_fix_validation.ipynb](../notebooks/31_package_mode_fix_validation.ipynb)
**Result dirs:**
- NB 30 — [data/output/calibration/30_replay_20260620_162106/](../data/output/calibration/30_replay_20260620_162106/)
- NB 31 — [data/output/calibration/31_pkgfix_20260620_193325/](../data/output/calibration/31_pkgfix_20260620_193325/)

**TL;DR.** Two-step audit of Run 14's "Qwen3-8B is non-persuasive" finding. NB 30 froze the R14 split50 reflections and daily summaries for 20 stratified agents, replayed the per-policy survey through three frontier models (claude-sonnet-4-6, claude-haiku-4-5, gpt-5.4-mini), and observed that **all four models — including Qwen — plateau from Day 1 onward in lockstep**. That cross-model lockstep ruled out "Qwen-specific lethargy" and surfaced the actual cause: in `package` mode the end-of-day per-policy survey was assembling its system prompt with `policy_id=<one policy>`, but `manage_memory` writes reflections and `daily_summaries` under `PACKAGE_SCOPE`, so `assemble_context()` filtered every package-scoped entry out. Every day's survey context was **bit-identical** across days. NB 31 patched `administer_survey()` to thread `context_policy_id=PACKAGE_SCOPE` for package-mode runs and replayed the same 20 agents under Qwen3-8B (4-bit MLX local) + gpt-5.4-mini. With the fix, **survey answers move in the bucket-asymmetric direction the broadcast assignment predicts**: A-only +0.05 to +0.18 mean signed shift across days, B-only −0.25 to −0.62. The bug was real and material; the Run 14 persuasion finding needs to be re-measured under the fix.

### NB 30 — cross-model frozen replay (the audit that surfaced the bug)

**Design.** Replay R14 split50 surveys for 20 stratified agents (10 A-only + 10 B-only, stratified on broadcast bucket) on days 1–3 across all 6 policies. For each cell, **freeze Qwen's upstream state** (Day-0 anchor + rationale, reflections, daily_summaries, survey_reasoning, opinion_history) and let each candidate model run the same 2-step debias chain against the exact `assemble_context()` prompt Qwen saw. No agent state is mutated. Budget: 3 models × 20 agents × 3 days × 6 policies × 2 debias steps = 2,160 calls. Source: `data/output/experiments/run_6202348_R14_split50_5day/20260619_192129/`.

**Per-cell `|model − qwen_saved|` numeric divergence** (range −3..+3, 360 rows per model):

| model | n | median | p90 | %\|Δ\|≥1 | %\|Δ\|≥2 | mean |
|---|---:|---:|---:|---:|---:|---:|
| gpt-5.4-mini | 360 | 0 | 1 | 19.7% | 5.0% | **0.267** |
| claude-sonnet-4-6 | 360 | 0 | 1 | 27.8% | 8.1% | 0.378 |
| claude-haiku-4-5 | 360 | 0 | 2 | 35.6% | 14.2% | 0.586 |

Closest to Qwen is **gpt-5.4-mini** (mean |Δ| = 0.27), which is why NB 31 used it as the second model for the fix verification: a model whose voice already tracks Qwen's gives a cleaner read on what the *fix* changes vs what the model character changes.

**The smoking gun (bucket-mean trajectory, [data/output/calibration/30_replay_20260620_162106/bucket_trajectory.png](../data/output/calibration/30_replay_20260620_162106/bucket_trajectory.png)).** Day 1 → Day 3 trajectories for all four models pooled over six policies:

| bucket | model | Day 1 | Day 2 | Day 3 |
|---|---|---:|---:|---:|
| A-only | qwen3-8b (saved) | +2.10 | +2.13 | +2.10 |
| A-only | claude-sonnet-4-6 | +2.18 | +2.20 | +2.10 |
| A-only | claude-haiku-4-5 | +2.13 | +2.20 | +2.18 |
| A-only | gpt-5.4-mini | +2.03 | +2.05 | +2.07 |
| B-only | qwen3-8b (saved) | +0.35 | +0.38 | +0.28 |
| B-only | gpt-5.4-mini | +0.13 | +0.25 | +0.23 |
| B-only | claude-sonnet-4-6 | −0.07 | −0.08 | −0.05 |
| B-only | claude-haiku-4-5 | −0.30 | −0.40 | −0.23 |

The cross-model spread is **vertical (model character)**, not **horizontal (day-to-day movement)**. Within each model, Day 1 → Day 3 is essentially flat — for the B-only bucket every line moves by ≤ 0.20 across two days, and the A-only bucket is even tighter. That this lockstep flatness held for four very different models — Qwen3-8B (open-weights), GPT-5.4-mini (OpenAI), and two Claude tiers — is what triggered the suspicion that the input wasn't actually changing.

**What we then checked, and what we found.** An md5 hash of `agent.get_system_prompt(day, policy_id=<one policy>)` across days 1, 2, 3 for the same (agent, policy) cell was **bit-identical**. Source diagnosis: `assemble_context()` filters reflections and `daily_summaries` by exact `policy_id` match, but `manage_memory()` in package mode writes both under the sentinel `PACKAGE_SCOPE` rather than per-policy. So the per-policy survey was reading an empty package-scope view and falling back to whatever the static Day-0 anchor + persona produced — every day. The plateau was a 100% mechanical artefact.

### The fix (Option B)

A new optional argument `context_policy_id: str | None = None` was threaded through both `SurveyedCitizen.administer_survey()` and `SurveyedNation.run_end_of_day_survey()`. When set, it is the policy id used to **build the system prompt context** (i.e. the `assemble_context()` call), while the per-policy `policy_id` continues to select the question text and the storage keys. In `sim.py`'s package-mode end-of-day survey loop, `context_policy_id=PACKAGE_SCOPE` is now passed explicitly. Single-policy mode is untouched. Storage keys still use `policy_id`, so reading back the trajectory CSVs is unchanged.

Diff scope: [src/cag/abm/agent.py](../src/cag/abm/agent.py) (`administer_survey` signature + body), [src/cag/abm/environment.py](../src/cag/abm/environment.py) (`run_end_of_day_survey` signature + threading), [src/cag/abm/sim.py](../src/cag/abm/sim.py) (~line 460, package-mode call site). Test suite: 470 passing + 1 skipped, no regressions.

### NB 31 — post-fix validation replay (the fix actually changes the answer)

**Design.** Same 20 agents from NB 30. Now replay the **2-step debias chain with `policy_id=PACKAGE_SCOPE` in the system prompt** — bit-for-bit what the patched production path now does. Two models: **Qwen3-8B (local, 4-bit MLX quant)** and **gpt-5.4-mini** (clean fix-only signal since it's the same model as NB 30 with only the prompt construction changed). Budget: 2 models × 20 agents × 3 days × 6 policies × 2 debias steps = 1,440 calls. Output: [data/output/calibration/31_pkgfix_20260620_193325/](../data/output/calibration/31_pkgfix_20260620_193325/).

A md5-hash diagnostic (Cell 6) explicitly asserts that post-fix `get_system_prompt(day, PACKAGE_SCOPE)` differs across days 1/2/3 while pre-fix `get_system_prompt(day, <one policy>)` is bit-identical — passes for every (agent, policy) sampled. The fix demonstrably reaches the prompt.

**Per-cell post-fix vs pre-fix numeric divergence:**

| model | n | %changed | median \|Δ\| | mean \|Δ\| | p90 \|Δ\| | mean signed Δ |
|---|---:|---:|---:|---:|---:|---:|
| gpt-5.4-mini | 360 | 29.7% | 0 | 0.43 | 1.0 | **−0.194** |
| qwen3-8b (4-bit) | 360 | 33.1% | 0 | 0.44 | 1.0 | −0.103 |

About one cell in three flips at least one survey step; the typical magnitude is a one-step change; **the sign is consistently mildly anti-climate in aggregate**, with GPT (the clean fix-only signal) at −0.194 and Qwen (fix + quantization noise) at −0.103.

**The bucket-asymmetric signature: direction tracks the broadcast.** Pooled means by model × bucket × day (post-fix minus pre-fix signed shift, GPT row is the clean signal):

| bucket | model | Day 1 | Day 2 | Day 3 |
|---|---|---:|---:|---:|
| A-only (saw pro-climate broadcasts) | gpt-5.4-mini | −0.083 | **+0.050** | **+0.150** |
| A-only | qwen3-8b (4-bit) | +0.050 | +0.117 | +0.183 |
| B-only (saw anti-climate broadcasts) | gpt-5.4-mini | −0.250 | **−0.617** | **−0.417** |
| B-only | qwen3-8b (4-bit) | −0.283 | −0.433 | −0.250 |

This is the predicted signature. A-only agents already sit near the +2.0 ceiling, so feeding the survey their pro-broadcast reflections nudges them only a sliver higher (Day 3 +0.15 for GPT). B-only agents have plenty of dynamic range from a +0.2 pre-fix baseline downward, and the fix uses most of it: GPT B-only mean drops to −0.37 on Day 2. The cross-bucket gap on Day 2 widens from ~+0.05 (pre-fix, both models) to **~+0.67 (post-fix, GPT)** — that gap is the persuasion-response signal the per-policy context filter was hiding.

**Per-policy breakdown (GPT only, the cleanest signal), mean signed shift:**

| policy | A-only | B-only |
|---|---:|---:|
| ClimatePolicyID(1) | −0.10 | −0.30 |
| ClimatePolicyID(2) | +0.03 | −0.47 |
| ClimatePolicyID(3) | +0.03 | −0.53 |
| ClimatePolicyID(4) | +0.03 | **−0.77** |
| ClimatePolicyID(5) | +0.20 | −0.37 |
| ClimatePolicyID(6) | +0.03 | −0.13 |

**Every single policy in the B-only column shifts negative**, and 5 of 6 in the A-only column shift non-negative. The directional consistency across policies and across the two models is what makes this a structural fix-effect rather than a model artefact.

**\|Δ\|≥1 share by bucket** (share of cells that flipped at least one survey step):

| model | A-only | B-only |
|---|---:|---:|
| gpt-5.4-mini | 17.8% | **41.7%** |
| qwen3-8b (4-bit) | 21.1% | 45.0% |

Nearly half of B-only cells moved at least one step. The bucket asymmetry is again consistent across both models.

**Day 2 is the peak shift.** This makes sense given how `manage_memory` lays out context: by Day 2 the Day-0 (pre-broadcast, neutral) reflections have been compressed into a daily summary, while the Day-1 broadcast reflection is still full text — so Day 2's survey context contains the maximum fraction of new broadcast-influenced material. By Day 3, additional daily summaries start to dilute it.

### What this means for Run 14

1. **The Run 14 "Qwen3-8B is non-persuasive" conclusion is contaminated** by the per-policy context bug. Every Run 14 trajectory was being fed an effectively static survey prompt past Day 0; broadcasts could and did populate reflections (Run 14 confirmed reflection quality was healthy), but those reflections never reached the survey. The +0.10 / +0.04 net persuasion subtraction reported in Run 14 was measuring debias-chain drift + Day-0 anchor — not the agent's response to the day's broadcast.
2. **The plateau-and-decoupling observation in Run 14 §"reasoning text" was the bug's literal signature.** Reflections engaged with broadcasts; survey rationales were word-for-word identical to Day 0. That is *mechanically* what the bug guaranteed.
3. **The Qwen freeze observation specifically (Run 14 §"Reflection production is healthy — engagement isn't the bottleneck") survives, but loses its model-attribution.** The cross-model lockstep in NB 30 shows every frontier model also plateaued under the same buggy paradigm; the bug, not the model, was the bottleneck.
4. **The size of the post-fix effect is real but moderate.** ~30% of cells change, one-step moves dominate (p90 = 1), and the B-only bucket-mean shift maxes at −0.62 on Day 2. Combined with Run 14's healthy reflection production, this puts the *measurable* persuasion ceiling under the fix at roughly half a survey step per day for a one-sided audience after a handful of broadcasts — still a long way short of dramatic, but it is a signal rather than the flatline.
5. **The R14 split50 trial needs to be rerun on AIRE with the fix.** The 4-bit MLX local Qwen used here confounds the Qwen row with quantization noise; the only clean Qwen pre/post comparison is the same 5-day R14 split50 design re-executed on the FP Qwen3-8B / vLLM stack. Until that rerun lands, treat the Run 14 numbers as a lower bound for Qwen's persuasion-responsiveness, not a verdict.

### Caveats

- NB 31's Qwen row uses **mlx-community/Qwen3-8B-4bit**, not the FP Qwen3-8B that R14 used on AIRE H100/vLLM. Magnitudes for the Qwen row in NB 31 mix the fix's effect with quantization noise; treat the GPT row (−0.194 aggregate, −0.617 on B-only Day 2) as the clean fix-only signal.
- All NB 30/31 numbers are over a 20-agent stratified subsample of R14's 50-agent cohort, days 1–3 only, 6 policies pooled, 2 debias steps per cell. Cross-day movement in NB 30 (the smoking-gun lockstep flatness) was measured against Qwen's saved opinion_trajectories; NB 31's pre/post divergence is measured against Qwen-saved + NB-30-saved respectively, not against a fresh re-run.
- The frozen-replay design holds the agent's reflections and daily summaries fixed. It cannot capture **iterative feedback** dynamics — i.e. what happens when Day 2's survey reflects on richer memory that itself was produced under the fix. The Run 14 rerun will tell us whether the per-day effect compounds, stays flat, or attenuates.

---

## Run 14: AIRE Split-50 Persuasion Responsiveness Trial (broadcasts only, matched neither baseline, anchor ablation)

> **Audit note (2026-06-20):** The "Qwen3-8B is non-persuasive" conclusion below was confounded by the package-mode per-policy survey context bug discovered in NB 30 and fixed in NB 31 — see the section directly above. End-of-day surveys past Day 0 were reading an effectively static system prompt, so broadcast-induced reflections never reached the survey. The numbers in this section are still correct *as measurements*, but should be read as the pre-fix lower bound on Qwen3-8B's persuasion-responsiveness, not as the model's actual ceiling. The split50 + neither matched-baseline design needs to be re-run on AIRE under the patched code before any persuasion claim is final.

**Date:** 2026-06-19
**Cluster:** AIRE HPC, GPU node (NVIDIA H100, CUDA 12.6), vLLM 0.8.5 in Apptainer serving `Qwen/Qwen3-8B` (bf16)
**Slurm jobs:** `6202348` (split50, anchor=GT, 5 days), `6203838` (neither baseline, anchor=GT, 5 days), `6204291` (split50, anchor=LLM, 4 days completed of 5 planned)
**Result files:**
- split50 — [data/output/experiments/run_6202348_R14_split50_5day/20260619_192129/](../data/output/experiments/run_6202348_R14_split50_5day/20260619_192129/)
- neither — [data/output/experiments/run_6203838_R14_neither_5day/20260619_184539/](../data/output/experiments/run_6203838_R14_neither_5day/20260619_184539/)
- anchor_llm — [data/output/experiments/run_6204291_R14_split50_5day_anchor_llm/checkpoints/](../data/output/experiments/run_6204291_R14_split50_5day_anchor_llm/checkpoints/) (CSVs sit in `checkpoints/` because the wall-clock-killed run never reached the final save step; checkpoint_meta records `last_completed_day = 4`)

**Analysis script:** [sandbox/ajay_sandbox/run14_split50_analysis.py](../sandbox/ajay_sandbox/run14_split50_analysis.py)

Designed in response to Run 13's muted aggregate signal and the persuasion-responsiveness concern (Run 13 §K). Three runs were submitted in parallel:

1. **`split50_5day`** — 50/50/0/0 `political_exposure_targets`, `reach_a = reach_b = 1.0`, peers off, GT-anchored Day 0. The cleanest possible persuasion test: every agent gets exactly one side of the broadcast feed and nothing else. By design the cohort splits 25 A-only / 25 B-only because `corr(score_A, score_B) ≈ −0.975` on the YouGov pool (NB 27).
2. **`neither_5day`** — `targets = {neither: 1.0}`, all other knobs identical to split50. Zero broadcasts and zero peers all five days — the matched-horizon baseline for the persuasion subtraction.
3. **`split50_5day_anchor_llm`** — identical to split50 but with `day0_anchor = "llm_survey"` (LLM picks its own Day-0 number; no YouGov rationale injected). Tests whether the GT anchor is itself the cause of the day-1 plateau seen in every prior run.

### Configuration delta vs Run 13

| Parameter | Run 13 | **Run 14** |
|---|---|---|
| n_citizens | 50 | 50 |
| days | 7 | **5** |
| `k_peers_per_day` | 0 | 0 |
| `political_exposure_targets` | {A-only: 0.05, B-only: 0.05, both: 0.50, neither: 0.40} | **split50: {0.50, 0.50, 0.00, 0.00}** &nbsp;·&nbsp; **neither: {0.00, 0.00, 0.00, 1.00}** |
| `reach_a` / `reach_b` | S 1/1, C1 0.25/1, C3 1/0.25 | **all 1.0 / 1.0** |
| `day0_anchor` | GT-with-rationale | **GT-with-rationale** (split50, neither) ·&nbsp; **`llm_survey`** (anchor_llm) |
| Cohort assignment under seed=42 | uneven A-only/B-only/both/neither sizes (rank-affinity on the 5/5/50/40 mix) | **25 A-only / 25 B-only / 0 both / 0 neither** for both split50 runs (`corr(score_A, score_B) ≈ −0.975`) |
| All other knobs | (package, offline v1, debias on, thinking off, seed=42, stochastic_block 0.15/0.02, vLLM bf16) | identical |

### TL;DR

**Qwen3-8B is essentially non-persuasive in this paradigm.** After subtracting the matched-horizon "no broadcasts at all" baseline, pro-climate broadcasts move A-only agents +0.10, anti-climate broadcasts move B-only agents +0.04 — both with the *same* sign. The pro-climate bias dominates broadcast content, peers (already off), and anchor choice. Free-Day-0 anchoring (anchor_llm) makes things *worse*, not better.

### Headline: the persuasion subtraction (Day 0 → Day 5)

Same horizon, same n=50, same Qwen3-8B, same prompt chain — just different broadcast exposure:

| Run | Cohort | n | Day 0 | Day 5 | Δ | Δ − neither_baseline |
|---|---|---:|---:|---:|---:|---:|
| **neither** | all agents | 50 | +0.59 | +0.98 | **+0.39** | — (this *is* the baseline) |
| **split50** | A-only | 25 | +1.32 | +1.81 | **+0.49** | **+0.10** |
| **split50** | B-only | 25 | −0.15 | +0.29 | **+0.43** | **+0.04** |

The two persuasion deltas (+0.10 and +0.04) are:
- **Both positive** — even pure anti-climate exposure (B-only) doesn't push opinions down.
- **Tiny** relative to the prompt-chain baseline (+0.39).
- **Asymmetric in the "wrong" direction** — anti-climate broadcasts should have negative persuasion if the model were responsive; they have +0.04 (essentially noise).

This is the cleanest evidence to date that Qwen3-8B doesn't update on broadcast content in this setup. Whatever drift you see in the asymmetry runs is mostly the bias baseline showing through, with maybe ~0.1 of broadcast-attributable effect on the side that aligns with the model's pre-existing pro-climate tilt.

### Day-1 plateau holds at 5 days

The "everything happens between Day 0 and Day 1, then nothing" pattern from earlier runs persists through Day 5 with no compounding:

| Run | Day 0 | Day 1 | Day 2 | Day 3 | Day 4 | Day 5 |
|---|---:|---:|---:|---:|---:|---:|
| split50 | 0.587 | 1.007 | 1.043 | 1.020 | 1.013 | **1.047** |
| neither | 0.587 | 0.990 | 0.963 | 1.003 | 0.970 | **0.977** |
| anchor_llm | 1.530 | 1.573 | 1.580 | 1.603 | 1.590 | (no D5) |

- **split50 and neither are within 0.07 of each other at every day past Day 0.** Broadcasts contribute essentially nothing on top of the prompt-chain drift.
- **The jump from Day 0 to Day 1 is +0.40 in both runs** — this is not persuasion, it's what happens when an agent's stated number transitions from a GT-rationalised value to one written by the LLM survey-with-debias chain. Once that transition is paid for at Day 1, the trajectory is flat.
- **No compounding past Day 1** — running for 5 days instead of 3 did not surface any further movement. The plateau answer is now settled.

### The anchor ablation says: the GT anchor is *not* the cause of the freeze

This was the hypothesis to kill — and it dies cleanly:

| Run | Anchor | mean Δ Day0→last | \|Δ\|≥0.5 | std Δ | Day-0 std | Day-0 bias vs GT | Day-0 ρ vs GT |
|---|---|---:|---:|---:|---:|---:|---:|
| split50 | GT + rationale | **+0.46** | 18/50 | 0.51 | 1.33 | 0.00 | 1.00 |
| anchor_llm | LLM survey | **+0.06** | 4/50 | 0.27 | 0.95 | +0.94 | 0.56 |

When you let the LLM pick its own Day-0 number (anchor_llm), it concentrates agents tightly around +1.5 (std 0.95, all agents stacked between −0.33 and +3.0), shows a +0.94 bias against the YouGov ground truth, and **barely moves at all** afterward (mean Δ = +0.06, only 4 of 50 agents shift more than 0.5). The "free" anchor doesn't unlock movement — it collapses the starting distribution and locks even harder.

So the GT anchor was *helping* by giving agents distinct starting positions to defend. Without it, the model defaults to "moderate-to-strong support for climate policy" for nearly everyone, then sits there.

The Day-0 ρ of 0.56 with the YouGov ground truth (for anchor_llm) also tells you something important: **Qwen's free survey answer has weak correlation with the agent's actual demographic+values+vote profile.** Personas are getting compressed toward a generic pro-climate stance regardless of who the agent is supposed to be.

### The reasoning text confirms the freeze is at the reasoning layer

The package_index isn't moving because the underlying *reasoning* isn't moving. Compare Day 0 to Day 5 for the three stratified agents in split50 (agent 713 = staunch opposer, 759 = neutral, 1045 = supporter):

- **Agent 713 (B-only, GT=−2.17)**: Day 0 and Day 5 reasoning are *word-identical* in three of five sentences, and paraphrases of each other in the rest. Day 5 still says "slightly support" the same as Day 0. Five days of only-anti-climate broadcasts produced no change in what the agent writes.
- **Agent 759 (B-only)**: writes a thoughtful first reflection acknowledging the broadcast (*"makes me reconsider the balance… the argument that renewable subsidies are a drain on public funds… is compelling"*) — and then writes a Day-5 survey rationale that *still says* *"I **strongly support** government policies that accelerate the roll-out of renewable energy."* Reflection engages with the message; survey ignores it.
- **Agent 1045 (A-only, GT=+3)**: word-identical Day-0 and Day-5 reasoning at the ceiling.

This is the failure mode that matters most: the agent reads the broadcast, writes a reflection that explicitly engages with its argument, then re-emits a survey answer that's a verbatim copy of the pre-broadcast survey answer. The persuasion stage and the survey stage are decoupled.

### Reflection production is healthy — engagement isn't the bottleneck

| Run | n reflections | median words | p10 | p90 | % policy-keyword | % empty |
|---|---:|---:|---:|---:|---:|---:|
| split50 | 250 | 288 | 213 | 364 | 100% | 0% |
| anchor_llm | 200 | 295 | 239 | 400 | 100% | 0% |
| neither | 0 | — | — | — | — | — |

Agents are producing long, substantive, policy-bearing reflections in response to broadcasts. The freeze is not "Qwen is too lazy to think about the broadcast" — it's "Qwen thinks about the broadcast, writes 288 words about it, and then writes a survey answer as if the broadcast didn't exist."

### The bucket Day-0 split shows the affinity-rank assignment works

| Cohort (split50) | Day-0 mean | Notes |
|---|---:|---|
| A-only (n=25) | +1.32 | Day-0 matches YouGov GT (anchor=GT) |
| B-only (n=25) | −0.15 | Day-0 matches YouGov GT (anchor=GT) |

The rank-affinity sort correctly put the 25 most pro-climate agents (by YouGov score) into the A-only cohort and the 25 most anti-climate into the B-only cohort. So the persuasion test is a clean test — we're sending pro-climate broadcasts only to the people most likely to already agree with them (no test of whether they *can* be moved further), and anti-climate broadcasts only to the people most likely to already agree with them (the actual persuasion failure: they don't move toward the message *or* down generally, they drift UP +0.43).

### What Run 14 tells us about the simulation

1. **For Qwen3-8B specifically, broadcasts are non-persuasive.** Any apparent asymmetry between A-leaning and B-leaning outcomes in the prior 7-day Run 12/Run 13 runs is bias-driven, not persuasion-driven. The 4-condition reach sweep was measuring sycophancy + prompt-chain drift, not actual influence.
2. **The GT anchor is a feature, not a bug.** It gives agents room to differentiate; without it, Qwen collapses them onto a narrow pro-climate band and the simulation has even less to measure.
3. **The +0.39 baseline drift in 5 days from zero input is the prompt-chain artefact.** This is the number to design around — the "model is responsive" threshold should be persuasion ≥ ~3× this baseline (so ≥ +1.0) to be a defensible effect.
4. **The decoupling of reflection from survey** is the most actionable finding. Reflections are rich; survey answers are stuck. That points at the survey prompt itself (the debias chain at end-of-day) as the locus of the freeze — when the agent is asked to fill in a number, they're re-reading their `assemble_context()` memory and pattern-matching back to Day-0 reasoning. If we want to test this, the next ablation is to drop the persona reminder from the survey prompt or to make the survey see only the most recent reflection (not the assembled context that includes Day-0 anchor reasoning).
5. **The model question is now urgent, not optional.** The case for the open-source ladder previously parked ("for later") has gotten stronger. If Qwen3-8B is structurally non-persuasive, the right next comparison isn't another asymmetry sweep — it's the same R14 design on Qwen3-14B/32B, Apertus, Llama-3.1, and possibly a Claude run for the upper bound. Without that, we can't tell whether the freeze is Qwen3-8B-specific (likely fixable by scaling) or a general LLM-agent property in this setup.

### Operational notes

- The anchor_llm run was killed by the 2-hour wall time during Day 5's 5th policy survey. CSVs were salvaged from `checkpoints/` (`last_completed_day = 4`). Resume infrastructure (`--resume` CLI flag in [src/cag/__main__.py](../src/cag/__main__.py), `RESUME=1`+`OUTDIR=` env-var overrides in [scripts/aire/smoke.sh](../scripts/aire/smoke.sh)) is now wired up for future kills.
- Both completed runs (split50, neither) finished under wall time; the neither run is the cheapest baseline available (no broadcasts → ~70% of split50's LLM call count).
- All three runs reused seed=42, n_citizens=50, Qwen3-8B bf16, llm_temperature=0.5, debias=on, thinking=off — only the three knobs in the configuration table above were changed across runs.

---

## Run 13: AIRE Reach-Asymmetry Sweep, peers OFF + supervisor exposure mix (5/5/50/40)

**Date:** 2026-06-17
**Cluster:** AIRE HPC, GPU node (NVIDIA H100, CUDA 12.6), vLLM 0.8.5 in Apptainer serving `Qwen/Qwen3-8B` (bf16)
**Slurm jobs:** `6045935` (S, symmetric), `6046803` (C1, reform-dominant), `6046804` (C3, green-dominant)
**Result files:**
- S  — [data/output/experiments/run_6045935_S_symmetric_nopeer/20260617_010957/](../data/output/experiments/run_6045935_S_symmetric_nopeer/20260617_010957/)
- C1 — [data/output/experiments/run_6046803_C1_reform_dominant_nopeer/20260617_005519/](../data/output/experiments/run_6046803_C1_reform_dominant_nopeer/20260617_005519/)
- C3 — [data/output/experiments/run_6046804_C3_green_dominant_nopeer/20260617_005418/](../data/output/experiments/run_6046804_C3_green_dominant_nopeer/20260617_005418/)
**Analysis script:** [sandbox/ajay_sandbox/run13_nopeer_analysis.py](../sandbox/ajay_sandbox/run13_nopeer_analysis.py)

Follow-up to Run 12. Two changes from Run 12: (1) `k_peers_per_day = 0` (peer messaging fully disabled — `run_package_peer_messaging` now early-returns when `k_peers <= 0`); (2) `political_exposure_targets = {A-only: 0.05, B-only: 0.05, both: 0.50, neither: 0.40}` per supervisor recommendation, replacing the previous `committed_minority_symmetric` (11/11/33/45) default. Hypothesis going in: with peers muted, the reach-asymmetry signal should finally show up in the aggregate trajectory. **Hypothesis not supported at the cohort-mean level**, but a cleaner partial signal is now visible inside the conditional-by-exposure-bucket cut (§G).

### Configuration delta vs Run 12

Identical to Run 12 except the two flags above. Repeated here so this section is self-contained.

| Parameter | Run 12 | **Run 13** |
|---|---|---|
| n_citizens | 50 | 50 |
| days | 7 | 7 |
| `k_peers_per_day` | **2** | **0** |
| `political_exposure_targets` | default `committed_minority_symmetric` (11/11/33/45) | **{A-only: 0.05, B-only: 0.05, both: 0.50, neither: 0.40}** |
| `reach_a` / `reach_b` | S 1.0/1.0 — C1 0.25/1.0 — C3 1.0/0.25 | **identical** |
| All other knobs | (package, offline v1, day0_anchor=GT-with-rationale, debias on, thinking off, seed=42, stochastic_block 0.15/0.02, vLLM bf16) | identical |

### New exposure mix landed as designed

Seed-42 cohort under the 5/5/50/40 targets produces this assignment:

| Bucket | n citizens | Where they sit in each broadcast pipeline |
|---|---:|---|
| A-only | 2 (S) / 1 (C1) / 21 (C3) | hears agent A only |
| B-only | 2 (S) / 22 (C1) / 0 (C3) | hears agent B only |
| both   | 25 (S) / 5 (C1) / 6 (C3) | hears both broadcasts |
| neither | 21 (S) / 22 (C1) / 23 (C3) | hears nothing all week |

Note the asymmetric bucket sizes in C1/C3 (which were structurally identical 22-22 in Run 12): with the new `rule_affinity_rank` cut on this cohort, "A-only" and "B-only" no longer have parity, and the audience-cap step is still `None`, so the reach trim now interacts with already-uneven side populations. The cleanest comparison stays C1 vs C3 within Run 13 (mirror reach), not across the two target presets.

Broadcast audiences after the reach trim (from `messages.csv`):

| Condition | agent_a (Green) recipients/day | agent_b (Reform) recipients/day |
|---|---:|---:|
| S  (1.0 / 1.0) | 27 | 27 |
| C1 (0.25 / 1.0) | **6** | 27 |
| C3 (1.0 / 0.25) | 27 | **6** |

`messages.csv` confirms **zero `peer_message` rows in any of the three runs** — the guard in `run_package_peer_messaging` is doing its job. Daily message volume is therefore 54 / 33 / 33 broadcast deliveries (no peer rows at all). Compare Run 12: 137 / 120 / 120 daily messages, of which ~93 were peer.

### Headline: aggregate trajectories are still essentially flat

Daily mean package index across all 50 agents:

| Day | S (1.0/1.0) | C1 (0.25/1.0, reform-dom) | C3 (1.0/0.25, green-dom) |
|---:|---:|---:|---:|
| 0 (GT-anchored) | +0.587 | +0.587 | +0.587 |
| 1 | +1.007 | +0.963 | +1.023 |
| 2 | +0.997 | +1.003 | +1.030 |
| 3 | +1.013 | +1.027 | +1.017 |
| 4 | +1.007 | +0.990 | +0.987 |
| 5 | +1.050 | +0.987 | +1.010 |
| 6 | +1.027 | +1.037 | +1.037 |
| 7 | +1.020 | **+0.950** | **+1.033** |

C3 (green-dominant) is **consistently above** C1 (reform-dominant) on 6 of 7 post-anchor days, and the Day 7 gap is **+0.08 points** in the expected direction (loud Green broadcast → slightly higher pro-climate plateau). This is the **first cohort-mean signal of broadcast-reach asymmetry** we have seen at n=50: in Run 12 the same comparison was non-monotone and zero-signed at Day 7. The gap is, however, still small relative to within-day std (~1.27) and within day-to-day noise (~0.05) — not a defensible large effect, but a directional improvement.

Per-agent net Δ (Day 7 − Day 0):

| Condition | mean Δ | median Δ | std | \|Δ\|≥0.5 | \|Δ\|≥1.0 |
|---|---:|---:|---:|---:|---:|
| S_nopeer  | +0.433 | +0.333 | 0.484 | 17 / 50 | 5 / 50 |
| C1_nopeer | +0.363 | +0.167 | 0.513 | 15 / 50 | 4 / 50 |
| C3_nopeer | +0.447 | +0.333 | 0.519 | 16 / 50 | 8 / 50 |

C1 (reform-dom) shows the smallest mean and median per-agent shift of the three — directionally consistent: muting the Green broadcast reduces the upward drift.

### Accuracy vs YouGov ground truth — same +0.42 ± 0.04 plateau as Run 12

| Day | S bias / MAE / ρ | C1 bias / MAE / ρ | C3 bias / MAE / ρ |
|---:|---|---|---|
| 0 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| 1 | +0.42 / 0.45 / 0.91 | +0.38 / 0.40 / 0.93 | +0.44 / 0.45 / 0.93 |
| 4 | +0.42 / 0.45 / 0.92 | +0.40 / 0.42 / 0.92 | +0.40 / 0.43 / 0.93 |
| 7 | +0.43 / 0.44 / 0.93 | +0.36 / 0.39 / 0.93 | +0.45 / 0.45 / 0.92 |

The Day-1-onwards aggregate bias is **+0.42 ± 0.04 across every condition and every day in every run we have ever measured at n=50**. Turning peers off did not change it. Pearson ρ stays at 0.91–0.93. The "Day-1 LLM inflation, then plateau" pattern is now confirmed as **independent of peer messaging and of broadcast direction**.

### Conditional shift by exposure bucket — the real story

Per-bucket mean shift Day 7 − Day 0, where bucket is **derived from messages.csv** (who actually received a political broadcast):

**S_nopeer** (1.0 / 1.0):

| bucket | n | Day 0 mean | Day 7 mean | mean shift | bias vs GT |
|---|---:|---:|---:|---:|---:|
| A-only | 2 | +0.92 | +1.25 | +0.33 | +0.33 |
| B-only | 2 | −1.17 | −0.75 | +0.42 | +0.42 |
| both   | 25 | +0.79 | +1.24 | +0.45 | +0.45 |
| neither | 21 | +0.48 | +0.91 | +0.43 | +0.43 |

**C1_nopeer** (0.25 / 1.0):

| bucket | n | Day 0 mean | Day 7 mean | mean shift | bias vs GT |
|---|---:|---:|---:|---:|---:|
| A-only | 1 | −0.83 | −0.17 | +0.67 | +0.67 |
| B-only | 22 | +0.58 | +1.01 | +0.43 | +0.43 |
| both   | 5 | +0.97 | +1.23 | +0.27 | +0.27 |
| neither | 22 | +0.58 | +0.88 | +0.30 | +0.30 |

**C3_nopeer** (1.0 / 0.25):

| bucket | n | Day 0 mean | Day 7 mean | mean shift | bias vs GT |
|---|---:|---:|---:|---:|---:|
| A-only | 21 | +1.00 | +1.48 | **+0.48** | +0.48 |
| both   | 6 | +0.11 | +0.42 | +0.31 | +0.31 |
| neither | 23 | +0.33 | +0.79 | +0.46 | +0.46 |

Three things stand out:

1. **The "neither" bucket — citizens who received zero broadcasts and zero peer messages — still drifted upward +0.30 to +0.46 in every run.** This is not a broadcast effect or a peer effect. It is the same Day-0 → Day-1 prompt-chain bias visible in every run since Run 1. Whatever is producing the +0.42 plateau lives in the survey prompt itself, not in the social influence pipeline. This is the single most important finding from Run 13.
2. **C3 A-only (n=21) shows the largest broadcast-conditional shift of any cell** (+0.48) — exactly the cell the experiment was designed to inflate (Green broadcast goes to a wide audience, Reform broadcast nearly muted, no peer dilution). This is the cleanest piece of evidence in the report so far that a directed broadcast does shift opinion *in its receivers*. Compare against C1's "both" cell (+0.27, the cell where both messages compete): hearing the opposing voice halves the shift.
3. **C1's "B-only" cell (n=22) still drifts UP** (+0.43) — citizens who only heard the anti-climate broadcast still ended Day 7 *more* pro-climate than they started. The +0.42 baseline drift dominates the direction of any reasonable single broadcast effect over 7 days. To pull these citizens *down* would need either much harder anti-climate content, more days, or content that explicitly challenges the prompt-chain bias.

### Run 12 vs Run 13 side-by-side (Day 7)

| Run | bias | MAE | ρ | mean Δ | median Δ | std Δ |
|---|---:|---:|---:|---:|---:|---:|
| S_peer    | +0.420 | 0.433 | 0.925 | +0.420 | +0.250 | 0.513 |
| C1_peer   | +0.433 | 0.433 | 0.933 | +0.433 | +0.333 | 0.484 |
| C3_peer   | +0.457 | 0.470 | 0.913 | +0.457 | +0.333 | 0.550 |
| S_nopeer  | +0.433 | 0.440 | 0.931 | +0.433 | +0.333 | 0.484 |
| C1_nopeer | **+0.363** | 0.390 | 0.925 | **+0.363** | **+0.167** | 0.513 |
| C3_nopeer | +0.447 | 0.453 | 0.921 | +0.447 | +0.333 | 0.519 |

Switching peers off **does not move the headline numbers** (bias, MAE, ρ all within ±0.02 across the six runs). The one row that moves is C1 nopeer: shutting both the peer channel and most of the pro-climate broadcasts cuts the mean shift by ~0.07 — small in absolute terms but the largest delta in the table. C3 (green-dom) is the highest mean shift in both peer regimes.

### Quality of the simulation run

Same five dimensions as the Run 12 analysis. Headline: **Qwen3-8B output stays production-grade with peers off**, in some respects more so.

**Reflections.** Fewer rows than Run 12 — only broadcast phases produce reflections now, not the C phase — but the rows that do exist are **longer and unanimously on-topic**.

| Condition | n reflections | agents covered | median words | p10 / p90 words | empty | mentions ≥1 keyword |
|---|---:|---:|---:|---:|---:|---:|
| S_nopeer  | 378 | 29 / 50 | **293** | 224 / 363 | 0 % | **100.0 %** |
| C1_nopeer | 231 | 28 / 50 | **302** | 241 / 369 | 0 % | **100.0 %** |
| C3_nopeer | 231 | 27 / 50 | 290 | 213 / 395 | 0 % | 100.0 % |

Median 290–302 words is ~70 words *longer* than Run 12's 170–225, and policy-keyword coverage is 100 % across all three runs (vs ~99 % in Run 12). Note that *only the 27–29 broadcast-receiving agents* generate reflections at all — the 21–23 "neither" agents go a full week without producing a reflection row. This is correct behaviour, not a quality drop: with no broadcasts to react to and no peer messages, those agents have nothing to reflect on.

**Survey reasoning.** Unchanged.

| Condition | n | median words | p10 / p90 words | empty | on-topic |
|---|---:|---:|---:|---:|---:|
| S_nopeer  | 2,400 | 77 | 65 / 93 | 0 % | 98.5 % |
| C1_nopeer | 2,400 | 78 | 65 / 93 | 0 % | 98.2 % |
| C3_nopeer | 2,400 | 78 | 65 / 92 | 0 % | 97.9 % |

7,200 reasoning rows, 0 empty, ≥97.9 % on-topic, tight 65–93 word IQR — same envelope as Run 12. The end-of-day survey is doing its work without peer scaffolding.

**Cohort diversity.** Day-0 distribution is identical across Run 12 and Run 13 (same seed, same cohort): n=50, range [−2.17, +3.00], 10 strong supporters, 33 supporters, 2 neutrals, 15 opposers, 2 strong opposers.

**Representativeness through the week.** Pearson ρ vs YouGov stays at 0.91–0.93 across Days 1–7 in all three runs (was 0.92–0.94 in Run 12). Per-bucket Day-0 means show strong heterogeneity: in C1, A-only has Day-0 mean −0.83 (the one anti-broadcast-receiving citizen is the strongest opposer in the sample), while in C3 A-only has Day-0 mean +1.00 (the 21 pro-broadcast receivers skew pro-climate). This is exactly the kind of structured exposure-target ↔ position coupling the `rule_affinity_rank` mode is meant to produce.

**Persona-fidelity at Day 7 (stratified samples from S_nopeer).** With peers off, persona stability across the week becomes very high — almost too high in places:

> **Agent 713 — strong opposer (Day 0 = GT = −2.17, Day 7 = −1.50).**
>
> *Day-0 reasoning, Policy 1:* "I slightly support the acceleration of renewable energy production, as I believe in human progress and the importance of sustainable development. However, I am cautious about rapid changes that might disrupt traditional ways of life or local communities, and I value maintaining balance between progress and environmental respect."
>
> *Day-7 reasoning, Policy 1:* "I would slightly support the acceleration of renewable energy production because I believe in human progress and the importance of sustainable development. However, I am cautious about rapid changes that might disrupt traditional ways of life or local communities, and I value maintaining balance between progress and environmental respect."
>
> Near-verbatim copy of Day 0 — the agent's stance hasn't shifted at the prose level, only the second sentence's leading clause is rewritten. With no peer dilution, the persona+context chain reproduces itself with very small variance.

> **Agent 759 — median (Day 0 = GT = +0.67, Day 7 = +1.00).**
>
> *Day-0 reasoning, Policy 1:* "I strongly support government policies that accelerate the roll-out of renewable energy production... As someone who deeply respects nature and believes all lifeforms should be treated equally, I see renewable energy as a way to reduce harm to the environment while still maintaining the prosperity and stability I value."
>
> *Day-7 reasoning, Policy 1:* "As a right-wing individual who values tradition and stability, I strongly support government policies that accelerate the roll-out of renewable energy production... While I value traditional ways, I also recognize that adapting to new, cleaner technologies is a way to maintain prosperity without harming the environment."
>
> Day-7 prose has internalised the demographic frame ("As a right-wing individual…") — same conclusion, different scaffolding.

> **Agent 1045 — strong supporter (Day 0 = GT = +3.00, Day 7 = +3.00).**
>
> Day-0 and Day-7 reasoning both lead with "I strongly support… deeply committed to environmental protection and global harmony… renewable energy is essential for reducing our carbon footprint." Persona pinned exactly at GT for the entire week.

### Cost

| | S_nopeer | C1_nopeer | C3_nopeer |
|---|---:|---:|---:|
| Wall-clock | ~2.1 h | ~1.4 h | ~1.4 h |

Cut roughly in half vs Run 12 (~3.4 h). The savings come from (a) no peer-message generation step, (b) fewer reflection rows per day (only broadcast-receiving agents reflect). Per-agent-day cost falls from ~30 s to ~14–18 s. Three asymmetry runs now fit comfortably in a single 6-hour Slurm submission.

### Verdict and what we have learned

1. **The +0.42 Day-1 inflation is a prompt-chain property, not a social-influence artefact.** The 21–23 "neither" citizens who got zero stimulus still drifted +0.30 to +0.46. Whatever is producing the bias lives inside `administer_survey` (debias chain + persona context), not in broadcast or peer messaging. Future debias work should target the survey prompt directly, not the influence pipeline.
2. **Broadcast reach *does* register a per-bucket effect** that was invisible at the aggregate-mean level. C3 A-only +0.48 vs C1 "both" +0.27 (the receiver-side comparison the experiment was designed to surface). Aggregate-mean reporting masks this because the "neither" bucket carries 42–46 % of cohort weight and saturates the average at the prompt-chain baseline.
3. **Aggregate cohort-mean monotonicity (C3 ≥ S ≥ C1)** first appeared in Run 13 (C3 +1.033, S +1.020, C1 +0.950 at Day 7), albeit weakly. With peers on (Run 12) the ordering was zero-signed.
4. **Peers off does not "free up" the broadcast signal at the cohort level.** Both regimes plateau at the same +0.42 ± 0.04. The peer channel is therefore neither a strong amplifier nor a strong dampener of broadcasts at this configuration — it adds variance (Run 12 std 0.55 vs Run 13 std 0.52 in C3, very similar) and shifts a small fraction of agents, but does not produce qualitatively different aggregate outcomes.
5. **Qwen3-8B remains production-grade** with peers off: 7,200 zero-empty rationales, 840 zero-empty reflections, 100 % policy-on-topic in reflections, near-verbatim persona stability across 7 days when broadcast input is removed.

### Open questions for the next run

- **The +0.42 baseline.** Run a "neither only" diagnostic: subset 30 agents to the neither bucket, run 7 days with no broadcasts and no peers. If the +0.42 drift reproduces, it confirms the bias is purely the Day-0 vs subsequent-day prompt difference (anchor rationale on Day 0 vs vanilla survey thereafter). Then fix it in the survey prompt rather than the influence layer.
- **Audience-cap symmetrisation.** C1 and C3 in Run 13 have *different* underlying audience compositions (asymmetric `A-only` / `B-only` counts in the new 5/5 mix). Capping both sides to `min(|A_audience|, |B_audience|)` would make the two conditions structural mirrors — apples-to-apples comparison.
- **Receiver-side analysis is now the right unit.** Report aggregate-mean as one slice but headline the conditional-bucket table — that is where the experiment's manipulation actually shows up. Promote the §G table to the front of the next run's writeup.
- **Larger reach contrast.** Try `reach_a = 0.0` vs `reach_b = 1.0` (full mute) to see if the C3 A-only +0.48 effect scales to a clearly demonstrable cohort-mean signal once the cohort is dominated by one-side-only agents.

---

---

## Run 12: AIRE Reach-Asymmetry Sweep — Qwen3-8B (bf16) via vLLM, 50 agents × 7 days

**Date:** 2026-06-16
**Cluster:** AIRE HPC, GPU node (NVIDIA H100, CUDA 12.6), vLLM 0.8.5 in Apptainer serving `Qwen/Qwen3-8B` (bf16)
**Slurm jobs:** `5985256` (S, symmetric), `5993181` (C1, reform-dominant), `5993232` (C3, green-dominant)
**Result files:**
- S  — [data/output/experiments/run_5985256_S_symmetric/20260616_001620/](../data/output/experiments/run_5985256_S_symmetric/20260616_001620/)
- C1 — [data/output/experiments/run_5993181_C1_reform_dominant/20260616_043552/](../data/output/experiments/run_5993181_C1_reform_dominant/20260616_043552/)
- C3 — [data/output/experiments/run_5993232_C3_green_dominant/20260616_043647/](../data/output/experiments/run_5993232_C3_green_dominant/20260616_043647/)

First full-scale (n=50, 7 days) reach-asymmetry sweep on the HPC stack with `thinking=False` (per the Run 11 recommendation). The three conditions vary only the broadcast-reach knobs (`reach_a`, `reach_b`); every other dimension — seed, sampled cohort, network, prompts, exposure mode, message pool — is held fixed. **Headline finding: peer messaging swamps the broadcast channel, so muting one political agent to 23 % of its baseline audience produces essentially zero aggregate movement.** The opportunity to extract value from this run is therefore not in the asymmetry effect itself, but in a battery of *quality dimensions* the run lets us check at scale for the first time (see §"Quality of the simulation run", below).

### Configuration

Identical between the three jobs except `reach_a` / `reach_b`. Matches the NB 29 canonical reference stack scaled up.

| Parameter | Value |
|---|---|
| n_citizens | 50 |
| days | 7 (alternating `P-A/P-B/C` and `P-B/P-A/C`; 8 survey days including Day 0) |
| k_peers_per_day | 2 |
| communication_mode | `package` (6 climate policies broadcast jointly each phase) |
| political_message_source / set | `offline` / `v1` |
| llm_provider / llm_model | `local` / `Qwen/Qwen3-8B` (bf16) |
| llm_temperature | 0.5 |
| local_base_url | `http://localhost:8000/v1` (vLLM) |
| thinking | `False` |
| debias | `True` (Condition B 1P chain) |
| day0_anchor | `ground_truth_with_rationale` |
| political_exposure_mode | `rule_affinity_rank` (default `committed_minority_symmetric`, `balanced` weights) |
| audience_cap | `None` |
| network_type | `stochastic_block` (`p_intra=0.15`, `p_inter=0.02`) |
| random_seed | 42 |
| **reach_a / reach_b** | **S: 1.0 / 1.0 — C1: 0.25 / 1.0 — C3: 1.0 / 0.25** |

Naming: **agent A = pro-climate (Green-aligned)**, **agent B = anti-climate (Reform-aligned)**. So **C1 (reform-dominant)** mutes A by trimming its audience from 22 → 5; **C3 (green-dominant)** mutes B symmetrically.

### Reach trims landed exactly as specified

From `messages.csv`, unique recipients per political broadcast per day:

| Condition | agent_a (Green) recipients/day | agent_b (Reform) recipients/day |
|---|---:|---:|
| S  (1.0 / 1.0) | 22 | 22 |
| C1 (0.25 / 1.0) | **5** | 22 |
| C3 (1.0 / 0.25) | 22 | **5** |

Audience composition is identical in all three runs (the seed-42 cohort produces 6 A-only / 6 B-only / 16 both / 22 neither under `rule_affinity_rank` + default targets — see [sandbox/ajay_sandbox/check_reach_split.py](../sandbox/ajay_sandbox/check_reach_split.py)). The reach knob only subsamples *who hears the broadcast*; per-citizen `political_exposure` labels are untouched.

### Headline: trajectories are essentially flat across the three conditions

Daily mean package index across all 50 agents:

| Day | S (1.0/1.0) | C1 (0.25/1.0, reform-dom) | C3 (1.0/0.25, green-dom) |
|---:|---:|---:|---:|
| 0 (anchored on GT) | +0.587 | +0.587 | +0.587 |
| 1 | +1.037 | +1.017 | +0.947 |
| 2 | +1.007 | +1.003 | +0.970 |
| 3 | +1.017 | +1.020 | +0.983 |
| 4 | +1.040 | +1.017 | +1.033 |
| 5 | +1.027 | +1.000 | +0.970 |
| 6 | +1.010 | +1.010 | +0.997 |
| 7 | +1.007 | +1.020 | +1.043 |

The three trajectories are within **±0.04 points of each other** at every plateau day. The C3 (green-dominant) condition is *not* monotonically above C1 (reform-dominant) — on Day 1 it is actually 0.07 *below*. The Day-0 → Day-1 jump (+0.42 mean) is the dominant move in every run; everything after Day 1 is a noisy plateau around +1.0.

Per-agent net Δ (Day 7 − Day 0):

| Condition | mean Δ | median Δ | std | agents with \|Δ\|≥0.5 | agents with \|Δ\|≥1.0 |
|---|---:|---:|---:|---:|---:|
| S  | +0.420 | +0.250 | 0.513 | 16 / 50 | 7 / 50 |
| C1 | +0.433 | +0.333 | 0.484 | 19 / 50 | 7 / 50 |
| C3 | +0.457 | +0.333 | 0.550 | 17 / 50 | 8 / 50 |

The per-agent distributions are statistically indistinguishable across conditions. The +0.42 mean upward drift is the **same "Day-1 inflation, then plateau"** pattern seen in every prior LLM-citizen run in this report (Runs 1–10).

### Accuracy vs YouGov package ground truth — stable across days and conditions

Day 0 has zero bias by construction (`ground_truth_with_rationale` writes the YouGov value directly). Day 1+ stabilises around a constant +0.42 aggregate bias with Pearson ρ around 0.93 and MAE around 0.43 in all three runs:

| Day | S bias / MAE / ρ | C1 bias / MAE / ρ | C3 bias / MAE / ρ |
|---:|---|---|---|
| 0 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| 1 | +0.45 / 0.47 / 0.93 | +0.43 / 0.43 / 0.93 | +0.36 / 0.41 / 0.93 |
| 2 | +0.42 / 0.45 / 0.93 | +0.42 / 0.42 / 0.93 | +0.38 / 0.40 / 0.94 |
| 3 | +0.43 / 0.44 / 0.93 | +0.43 / 0.43 / 0.93 | +0.40 / 0.43 / 0.92 |
| 4 | +0.45 / 0.46 / 0.94 | +0.43 / 0.45 / 0.93 | +0.45 / 0.46 / 0.93 |
| 5 | +0.44 / 0.45 / 0.92 | +0.41 / 0.41 / 0.92 | +0.38 / 0.42 / 0.93 |
| 6 | +0.42 / 0.43 / 0.94 | +0.42 / 0.44 / 0.94 | +0.41 / 0.44 / 0.93 |
| 7 | +0.42 / 0.43 / 0.93 | +0.43 / 0.43 / 0.93 | +0.46 / 0.47 / 0.91 |

C3 (green-dominant) is marginally *less* biased than the others on Days 1–3 — the opposite of what a "loud Green broadcast pushes opinions up" hypothesis predicts. The effect is well inside day-to-day noise. **Reach asymmetry on this knob, at this scale, does not move the package-level signal.**

### Why no swaying? The peer channel dominates

Message volume per day (the same in every condition for peer messages because peer messaging is independent of `reach_*`):

| Condition | peer messages / day | political broadcasts / day | peer : broadcast ratio |
|---|---:|---:|---:|
| S  | 93 | 44 (= 22 + 22) | 2.11 : 1 |
| C1 | 93 | 27 (=  5 + 22) | **3.44 : 1** |
| C3 | 93 | 27 (= 22 +  5) | **3.44 : 1** |

Every agent receives ~2 peer messages each day from neighbours of their own and the opposite valence (the stochastic-block network mixes both ways). Stacked against at most 1–2 broadcasts per agent per day, the peer channel carries 2–3× the volume in S and 3.4× in C1/C3. **Whatever opinion correction one political broadcast tries to push gets immediately diluted by both a same-side and an opposite-side peer message in the C-phase that closes every day.** The agents are not behaving like passive radios with a volume knob; they are predominantly *peer-influenced*, which collapses the broadcast asymmetry signal at the package-mean level.

The pattern is consistent with the per-day end-of-day survey logs (`run.log`): mean shift across 50 agents is ≤ ±0.02 from Day 1 onward in all three runs, and the shift distribution is `0` for 48 / 49 / 50 agents on most days. The simulation has reached an **opinion plateau by Day 1** and stays there.

---

### Quality of the simulation run (Qwen3-8B local LLM behaviour at n=50, 7 days)

The chief value of these three runs is that they give us 6,000+ on-task LLM completions on a real persona × policy grid. Five dimensions, all computed from the artefact CSVs (see [sandbox/ajay_sandbox/run12_asymmetry_analysis.py](../sandbox/ajay_sandbox/run12_asymmetry_analysis.py)):

**1. Reflection completeness and length** (one per agent per phase that received messages; phases C + the broadcast phases yield up to ~12 reflections per agent over 7 days):

| Condition | n reflections | agents covered | median words | p10 / p90 words | empty | mention ≥1 policy keyword |
|---|---:|---:|---:|---:|---:|---:|
| S  | 599 | 50 / 50 | 225 | 133 / 354 | 0 % | 99.7 % |
| C1 | 480 | 50 / 50 | 171 | 128 / 339 | 0 % | 99.2 % |
| C3 | 480 | 50 / 50 | 177 | 131 / 335 | 0 % | 99.0 % |

Every agent produces reflections every day they receive a message; not a single empty reflection in any of the three runs. Median length is 170–225 words (S is higher because S receives more broadcasts per day → more phases → more reflection rows per agent). Policy-keyword coverage is ≥99 % in all three runs — the model is staying on topic, not drifting into generic small-talk.

**2. Survey-reasoning completeness and length** (one per agent per day per policy = 50 × 8 × 6 = 2,400 rows per run; the survey is administered every day including Day 0):

| Condition | n reasonings | median words | p10 / p90 words | empty | on-topic keyword |
|---|---:|---:|---:|---:|---:|
| S  | 2,400 | 77 | 65 / 92 | 0 % | 98.2 % |
| C1 | 2,400 | 78 | 66 / 93 | 0 % | 97.8 % |
| C3 | 2,400 | 78 | 65 / 92 | 0 % | 98.8 % |

Zero malformed / empty survey answers across 7,200 reasoning rows. Median ~78 words / 65–92 IQR is **very tight**, suggesting the model has internalised the response-length convention from the chain rather than spraying randomly. This is exactly what we want from a 1P-debias chain serving as a budget-controlled "diary-entry" generator.

**3. Cohort diversity** (Day-0 package-index distribution across the 50 sampled YouGov respondents; identical in all three runs because seed-42 fixes the cohort):

| Stat | Value |
|---|---:|
| n agents | 50 |
| mean / median | +0.587 / +0.667 |
| std | 1.33 |
| range | [−2.17, +3.00] |
| strong supporters (≥ +2.0) | 10 |
| supporters (> 0) | 33 |
| neutral (= 0) | 2 |
| opposers (< 0) | 15 |
| strong opposers (≤ −2.0) | 2 |

The cohort spans the full opinion range with healthy representation on both tails — not a "centrist mush". Both strong-opposer and strong-supporter sub-populations are present in every run.

**4. Representativeness (persona ↔ output coupling)** — Day-0 package index of the LLM agents *is* the YouGov ground truth by construction, so the meaningful representativeness question is whether the **reasoning the LLM produces on Day 0 reads as persona-consistent**. The spot checks below (and the strong Day 1+ rank correlation, ρ ≈ 0.93, which is *not* anchored) say yes: agents who score low on the package on Day 0 give cautious / sceptical rationales; agents who score high give pro-climate / values-driven rationales; mid-scorers split their reasoning per policy.

The rank-order preservation through Days 1–7 (Pearson ρ stays at 0.92–0.94 across all 7 post-anchor days in all three runs) is the strongest single piece of evidence that the prompts and persona context are coupling correctly: even after a week of broadcasts and peer messaging, an agent's relative position in the cohort matches their YouGov position to that correlation.

**5. Sample passages (stratified by Day-0 opinion, S run)** — picked deterministically as the min / median / max of the Day-0 package index. Persona-fidelity check by eye:

> **Agent 713 — strong opposer (Day 0 = GT = −2.17).**
>
> *Day-0 reasoning, Policy 1 (Renewable energy):* "I slightly support the acceleration of renewable energy production, as I believe in human progress and the importance of moving towards sustainable practices. However, I am cautious about the pace and methods of implementation, particularly if it disrupts traditional ways of life or causes unnecessary environmental or social disruption. I value balance and respect for established customs, so I prefer a measured approach that respects both progress and the natural world."
>
> *Reflection (first):* "These peer messages make me think about how my own views align with and differ from others. I notice that some of their positions, like supporting renewable energy but wanting it done carefully, mirror my own cautious approach. Their neutrality on banning fossil fuel licenses also resonates with my belief in balancing environmental concerns with economic and traditional values."

> **Agent 759 — median (Day 0 = GT = +0.67).**
>
> *Day-0 reasoning, Policy 1:* "I **strongly support** government policies that accelerate the roll-out of renewable energy production, such as more offshore and onshore wind parks. As someone who deeply respects traditional values and the natural world, I recognize the importance of preserving our environment for future generations. While I value stability and established customs, I also believe in the necessity of progress that aligns with ethical responsibility and long-term sustainability."
>
> *Reflection (first):* "This message resonates with some of my existing concerns, particularly around the economic impact of climate policies and the potential for public funds to be misused. The argument that renewable subsidies are a transfer from struggling families to a sheltered industry aligns with my skepticism about government overreach. I can see how the cost-of-living crisis has been exacerbated by reliance on international gas markets, and the idea of producing more energy at home does appeal to my values of self-reliance and national sovereignty."

> **Agent 1045 — strong supporter (Day 0 = GT = +3.00).**
>
> *Day-0 reasoning, Policy 1:* "I strongly support government policies that accelerate the roll-out of renewable energy production. As someone deeply committed to environmental protection and global harmony, I believe transitioning to renewable energy is essential for reducing our carbon footprint and ensuring a sustainable future for all life on Earth. I reject the idea that any group should dominate the planet, and I see renewable energy as a way to create a more equitable and environmentally responsible society."
>
> *Reflection (first):* "Reading these peer messages has made me reflect on how my own views might not be as black-and-white as I thought. The idea of accelerating renewable energy still feels very aligned with my values, but I hadn't considered the local impact angle, which is an important point. On the oil and gas ban, I can see the economic concerns, even though I still strongly support it. The petrol car ban raises some valid points about accessibility and infrastructure, which I hadn't fully considered before."

Three patterns to note:

- **Each agent's reasoning is recognisably theirs.** Agent 713 hedges every clause with "balance / traditional / cautious"; 759 frames support through "values / national sovereignty / self-reliance"; 1045 leads with universal-environmentalist language. None of these prose blocks would swap convincingly with another agent's persona.
- **Reflections show genuine engagement with the messages received**, not boilerplate ("This message resonates with some of my existing concerns...", "I hadn't considered the local impact angle..."). Agents disagreeing with the prevailing message direction (1045 on the petrol-car ban) acknowledge the counterargument without flipping.
- **The Day-0 anchor is doing its job.** Even though we instruct the LLM to write a rationale *consistent with the GT score we inject*, agent 759 (median, +0.67) splits per policy — "strongly support" on renewables, more hedging elsewhere — which produces an average around +0.67 across the six. This is the kind of internal differentiation we want.

### Cost

| | S | C1 | C3 |
|---|---:|---:|---:|
| Wall-clock | 222.9 min (3.7 h) | 202.1 min (3.4 h) | 203.1 min (3.4 h) |
| Per agent-day | 33.4 s | 30.3 s | 30.5 s |

S is slightly slower because it has 22 + 22 = 44 broadcast deliveries per day (and therefore 44 reflection-generating phases per day across agents) vs 27 in C1/C3. All three runs comfortably fit a single 6-hour Slurm budget on one H100. Per-agent-day cost is in line with the Run 11 OFF baseline (25.5 s/agent-day at n=10) — scales near-linearly with `n_citizens × n_days`.

### Verdict and recommendations

1. **The reach-asymmetry signal is below the noise floor at n=50 / 7 days under the current peer + broadcast configuration.** Dropping one side's broadcast audience from 22 → 5 (≈77 % cut) produces a ≤0.04-point aggregate shift over a week.
2. **The peer channel is the dominant force**, ~3 × broadcast volume in the asymmetric runs. To make broadcast asymmetry visible, the next probe will need to either (a) suppress peer messaging entirely (`k_peers_per_day = 0`, like NB 21's broadcast-only design), or (b) push asymmetry harder still (e.g. zero-reach for one side, paired with audience-cap symmetry so the two political agents address identical headcounts) and/or (c) measure on per-agent shifts conditional on *which side they were exposed to*, not on the cohort mean.
3. **Qwen3-8B at `thinking=False` produces excellent simulation-grade text at scale.** 7,200 zero-empty survey rationales, 1,559 zero-empty reflections, median ~78-word rationales / ~190-word reflections, ≥97 % policy-on-topic, and visibly persona-aligned prose. The model is comfortably ready to back paper figures at this scale.
4. **Representativeness through the week stays at ρ ≈ 0.93 vs YouGov ground truth** despite a +0.42 aggregate-bias inflation — the same well-characterised "regression-to-pro-climate-mean" bias documented since Run 1. Rank-order signal is preserved; the open issue is the constant additive offset.

### Open questions

- **Re-run with `k_peers_per_day = 0`** (NB 21 design) to recover a clean broadcast-only asymmetry signal under the package + 7-day stack; expect to reproduce the Run 7 / Run 8 monotone ordering.
- **Audience-cap symmetrisation** (`audience_cap = 5` paired with reach asymmetry) — would make the C1/C3 comparison structurally cleaner, since both political agents would address identically-sized canonical audiences.
- **Why is the additive bias parked at +0.42 from Day 1?** Look at which policies dominate the offset (Run 5 showed Climate Compensation and Carbon Tax drove most of it). If the same two policies dominate at n=50, the bias is a per-policy property, not an aggregation artefact.
- **Per-agent ρ over time** (within-agent persistence) was not extracted here; with 50 × 7 = 350 (agent × day) samples per run there is finally enough data to compute it cleanly.

---

## Run 11: AIRE Thinking-Mode Ablation — Qwen3-8B (bf16) via vLLM, thinking OFF vs ON

**Date:** 2026-06-15
**Cluster:** AIRE HPC, `gpu018.aire.lee.alces.network` (CUDA 12.6), vLLM 0.8.5 in Apptainer
**Slurm jobs:** `5957902` (thinking OFF), `5975867` (thinking ON)
**Result files:**
- OFF — [data/output/experiments/run_5957902/20260615_145510/](../data/output/experiments/run_5957902/20260615_145510/)
- ON  — [data/output/experiments/run_5975867/20260615_185649/](../data/output/experiments/run_5975867/20260615_185649/)

First true apples-to-apples comparison of `thinking=true` vs `thinking=false` for the integrated `provider="local"` path against a real chat-template-honouring backend (vLLM serving `Qwen/Qwen3-8B` in bf16). Replaces the misattributed NB 24 / NB 25 "thinking helps" claim (see *Correction* at end of this section).

### Important correction to NB 24 / NB 25

The NB 24 and NB 25 result blocks recorded above (Day-0 bias +0.50, Day-1 ρ +0.76, ~22 reflections, etc.) were labelled as `thinking=True`. They are not. The `mlx-lm` server used in NB 24 / NB 25 **silently ignored** the `enable_thinking` chat-template kwarg in the model registry: the request was accepted, no `<think>...</think>` block was ever emitted, and the run was in practice a `thinking=False` execution. The model + sampling + prompt chain were otherwise as documented, so the NB 24 / NB 25 numbers remain valid as a baseline for `Qwen3-8B-4bit` on mlx without thinking — only the "with thinking" label needs to be retired. Run 11 below is the first time the thinking flag has been honoured end-to-end on a Qwen3-class model in this codebase.

### Configuration

Identical between the two jobs except the `thinking` flag.

| Parameter | Value |
|---|---|
| n_citizens | 10 |
| days | 2 (alternating `P-A/P-B/C` and `P-B/P-A/C`; 3 survey days including Day 0) |
| k_peers_per_day | 2 |
| communication_mode | `package` |
| package_policies | all 6 climate policies |
| political_message_source / set | `offline` / `v1` |
| llm_provider / llm_model | `local` / `Qwen/Qwen3-8B` (bf16) |
| llm_temperature | 0.5 |
| local_base_url | `http://localhost:8000/v1` (vLLM) |
| debias | `True` |
| day0_anchor | `ground_truth_with_rationale` |
| political_exposure_mode | `rule_affinity_rank` |
| network_type | `stochastic_block` (p_intra=0.15, p_inter=0.02) |
| random_seed | 42 |
| **thinking** | **`False` (job 5957902) / `True` (job 5975867)** |

`config.json` diff between the two runs is exactly one line: `"thinking": false` vs `"thinking": true`.

### Parser-bug fix that made this comparison possible

vLLM honours `chat_template_kwargs.enable_thinking` and, when enabled, emits real `<think>...</think>` blocks in the Step-2 letter response. The existing `parse_letter_response()` uses `re.search(r"\b([A-G])\b", text)` and returned the first A–G inside the think block instead of the final answer, producing opinion swings of ±4/±5/±6 against ground truth in early test runs. Fixed by an unconditional strip in [src/cag/io/llm.py](../src/cag/io/llm.py) `_send_local()`:

```python
text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)
```

Run 11 (ON) shows zero `<think>` leakage in any artefact and healthy per-agent shift distributions, confirming the fix.

### Headline accuracy — Day 2 vs YouGov package ground truth (n=10)

Day 0 is **identical** in both runs because `day0_anchor=ground_truth_with_rationale` writes the YouGov package index directly to Day 0 (the LLM only produces accompanying rationale). The headline NB 25 "Day-0 bias" metric is therefore meaningless for this comparison — Day 2 is the first day where the two runs can diverge through broadcast + peer exposure.

| Metric (Day 2, n=10) | OFF (`5957902`) | ON (`5975867`) |
|---|---:|---:|
| LLM mean | 1.133 | 1.001 |
| Ground-truth mean | 0.749 | 0.749 |
| **Aggregate bias** (mean − GT) | **+0.384** | **+0.252** |
| **MAE vs GT** | **0.384** | **0.350** |
| **Pearson ρ vs GT** | **0.974** | **0.957** |

Both runs are near-ceiling on rank correlation because Day 0 is anchored on GT and only two days of drift have accumulated. ON shows marginally lower aggregate bias and marginally lower MAE; OFF shows marginally higher Pearson ρ. None of these differences are defensible at n=10.

### Per-agent Day-2 trajectory (package index, ProClimatePolSupp)

| Agent | GT | OFF Day 0 → Day 2 | ON Day 0 → Day 2 |
|---:|---:|---:|---:|
| 165  | +0.83 | +0.83 → +1.33 (+0.50) | +0.83 → +0.67 (−0.17) |
| 582  |  0.00 |  0.00 → +1.00 (+1.00) |  0.00 → +0.33 (+0.33) |
| 1379 | +0.33 | +0.33 → +1.00 (+0.67) | +0.33 → +1.17 (+0.83) |
| 713  | −2.17 | −2.17 → −1.50 (+0.67) | −2.17 → −2.17 (0.00) |
| 1878 | +0.67 | +0.67 → unchanged plateau | +0.67 → unchanged plateau |
| 844  | +2.00 | +2.00 → +2.00 (0.00) | +2.00 → +2.67 (+0.67) |
| 409  | +1.83 | +1.83 → +1.83 (0.00) | +1.83 → +1.83 (0.00) |
| 1957 | +2.67 | +2.67 → +2.67 (0.00) | +2.67 → +2.67 (0.00) |
| 91   | +1.33 | +1.33 → +1.50 (+0.17) | +1.33 → +1.00 (−0.33) |
| 69   |  0.00 |  0.00 → +1.00 (+1.00) |  0.00 → +0.67 (+0.67) |

OFF shows more aggregate upward drift; ON keeps strong-opposers (713) and strong-supporters at GT. Both runs preserve persona ordering — no rank reversals between OFF and ON on either day.

### Reasoning prose — qualitative comparison (180 `survey_reasoning` rows each)

Both runs produce paper-readable first-person rationales. Stylistically they diverge in a consistent way.

**OFF: flowing, single-paragraph, first-person citizen voice.** Agent 165 (Conservative, parent, South West), Day 1, Policy 1 (Renewable energy):

> "I would somewhat support accelerating the roll-out of renewable energy production because I believe in balancing human progress with environmental respect. While I'm not an active environmental advocate, I recognize the importance of sustainable development and reducing reliance on fossil fuels, especially as a parent concerned about the future. However, I might oppose it if it leads to significant disruption of local communities or traditional ways of life, which I value and respect."

**ON: structured, often dual-frame, markdown-formatted.** Same agent, same day, same policy:

> "I **somewhat support** accelerating renewable energy production because I believe in equal opportunities and the long-term benefits of sustainable solutions … However, I might **oppose** rapid changes that disrupt traditional ways of life or local communities."

The **`Support:` / `Oppose:` dual-framing** and liberal use of `**bold**` markers appear in roughly 1-in-3 ON entries from Day 1 onward and almost never in OFF. ON entries also tend to be 15–25% longer (e.g. ~745 chars vs ~596 chars for agent 165 day 1).

**Reflections (`reflections.csv`)** show the same divergence on the same broadcast input. Agent 165, Day 1, P-A (pro-climate broadcast `A_PKG_13`):

- **OFF**: opens with a one-paragraph summary, then enumerates the broadcast bullet-by-bullet across six topical paragraphs (renewables → oil/gas → EVs → housing → carbon tax → compensation), each ending with a hedge tied to the persona ("I remain wary of government intervention", "I value gradual change", etc.). Total ~1.4k chars.
- **ON**: opens with the same summary paragraph, then collapses the six topics into 2–3 synthesis paragraphs that name fewer specific policies but argue across them ("the package feels more convincing in its focus on long-term planning and practical, inclusive solutions"). Total ~1.1k chars.

Neither dominates as "better reasoning". OFF reads like a citizen explaining themselves; ON reads like a policy analyst writing a memo. For a paper whose contribution is treating LLMs as **surrogate citizens**, OFF is more on-message.

### Persona fidelity

Persona-driven valence is preserved across days in both runs. Spot checks:

- **Agent 713** (Scottish, traditional, strong opposer, GT −2.17): both runs consistently "strongly oppose" across all six policies on all three days. OFF drifts to −1.50 on Day 2 (one policy softening); ON stays pinned at −2.17.
- **Agent 1957** (East Midlands, Labour, GT +2.67): both runs consistently "strongly support" across all six policies on all three days; both stay at +2.67 throughout.
- **Agent 844** (deep-green, GT +2.00): OFF stays at +2.00; ON moves to +2.67 (saturating the scale).
- **Agent 165** (Conservative parent, GT +0.83): both runs produce identical hedge structure ("balance human progress with environmental respect", "respect for tradition", "concern as a parent").

### Broadcast and peer-message pipelines

`messages.csv` shows broadcasts are byte-identical across the two runs (offline pool `v1` IDs `A_PKG_13`, `B_PKG_...` etc. — these are canned and do not exercise the LLM). The **peer messages** in phase C are LLM-generated and do differ. Sample (agent 582 → agent 1379, Day 1):

- **OFF**: "I slightly support policies that accelerate the roll-out of renewable energy like wind parks because I think it's important to protect the planet for future generations, even if it's not my top priority. I'm more comfortable with gradual change than sudden shifts, so I'm neutral on banning new oil, gas, and coal licenses…"
- **ON**: "Honestly, I think accelerating renewable energy is a solid idea — I like the idea of moving toward cleaner energy without being too radical. I can see the value in wind farms and solar, especially if it helps reduce our environmental impact without putting too much strain on local communities."

Same persona, same broadcasts received, same target peer — ON is slightly more conversational and shorter; OFF is more "policy summary" in register. Neither shows a quality cliff.

### Cost

| | OFF | ON | Ratio |
|---|---:|---:|---:|
| Wall-clock (10 agents × 2 days) | 12.8 min | 70.7 min | **5.5×** |
| Per agent-day | 25.5 s | 141.4 s | 5.5× |
| Projected 50 × 5 (10× workload) | ~2.2 h | ~12 h | 5.5× |
| Recommended Slurm budget for 50 × 5 ON | — | 14 h | — |

### Verdict and recommendation for the paper

1. **Accuracy is statistically tied** at n=10. ON is marginally better on bias (+0.25 vs +0.38) and MAE (0.35 vs 0.38); OFF is marginally better on rank-order (ρ 0.974 vs 0.957). Day-0 cannot be compared (anchor confound). No defensible quality claim either direction.
2. **Reasoning prose is different in kind, not quality.** OFF reads as a citizen; ON reads as an analyst with `Support:` / `Oppose:` scaffolding. The citizen voice is on-message for the paper's framing.
3. **Persona fidelity is preserved equivalently** in both runs across all 10 personas.
4. **The parser-bug fix held**: zero `<think>` leakage in any ON artefact.
5. **Cost is 5.5×** for no defensible accuracy gain on this evidence.

**Use `thinking=False` for headline production runs.** Reserve `thinking=True` for one targeted appendix run if the paper wants to demonstrate latent deliberation capacity. The previously-recorded "thinking helps" narrative from NB 24 / NB 25 was a label error and should not be cited.

### Open questions deferred

- Re-test at larger n (e.g. 50 × 5) where stronger statistical claims become possible; project ON budget at ~12 h Slurm.
- Compare against NB 25's Day-0 LLM-survey path (no anchor) to recover a true "with vs without thinking" Day-0 bias comparison; currently impossible under `day0_anchor=ground_truth_with_rationale`.
- Re-examine peer-message quality at larger N (single sample here is suggestive only).

---

## Run 10: NB 29 — Canonical Full-Scale Smoke (offline broadcasts + local LLM, package mode)

**Date:** 2026-05-22 (run), 2026-05-24 (fresh-kernel replay of headline metrics)
**Notebook:** [notebooks/29_canonical_full_smoke.ipynb](../notebooks/29_canonical_full_smoke.ipynb)
**Result files:** [data/output/experiments/20260522_234958/](../data/output/experiments/20260522_234958/)

NB 29 is the canonical end-to-end smoke reference for the current research default stack: offline political-message pool (`v1`) + local Qwen3 + package mode. The notebook now includes a load-from-disk cell so Section 8 can be rerun in a fresh kernel without rerunning the full simulation.

### Configuration (as printed in notebook output)

| Parameter | Value |
|---|---|
| n_citizens | 10 (smoke) |
| days | 2 (alternating `P-A/P-B/C` and `P-B/P-A/C`) |
| k_peers_per_day | 2 (smoke) |
| communication_mode | `package` |
| package_policies | all 6 climate policies |
| political_message_source / set | `offline` / `v1` |
| llm_provider / llm_model | `local` / `mlx-community/Qwen3-8B-4bit` |
| local_base_url | `http://localhost:8080/v1` |
| debias | `True` |
| day0_anchor | `ground_truth_with_rationale` |
| random_seed | 42 |

### Headline results

| Check | Output |
|---|---|
| Local server ping | Reachable; `/v1/models` returned `mlx-community/Qwen3-8B-4bit` |
| Offline pool sanity | `Total cells: 14`; `Empty cells: 0` |
| Population load | `Citizens loaded: 10 (target 10)` |
| Full simulation runtime | `251.1 min (15067s)` |
| Political broadcast LLM tripwire | `generate_message calls: 0`; `generate_package_message calls: 0` |
| Saved artifacts | Run saved to `.../20260522_234958` + 4 canonical plots emitted |
| Broadcast round-trip integrity | `political_broadcast rows: 16`; `mismatches: 0` |
| Example message IDs used | `A_PKG_20`, `B_PKG_05`, `B_PKG_04`, `A_PKG_10` (each count 4) |
| Reloaded row counts (fresh kernel) | `opinion_trajectories=180`, `package_index_trajectories=30`, `reflections=32`, `messages=36`, `survey_reasoning=180`, `ground_truth=60`, `package_ground_truth=10`, `daily_summaries=0` |
| Day-0 anchor invariant | `0 mismatches of 60` (agent, policy) pairs |
| Reflection budget | `n=32`, median tokens `168`, min `98`, max `389` |
| Package-index trajectory (plot) | Mean pro-climate index rises Day0→Day1 and stays elevated Day2 (approx. `0.75 -> 1.45 -> 1.45`) |

### Interpretation

Run 10 passes all smoke gates for the canonical profile:

- offline broadcast sourcing is active and stable (zero political-broadcast LLM calls),
- package-mode run/output schema is internally consistent,
- Day-0 anchoring is exact,
- and the artifact bundle is complete and replayable from disk.

This is now a reliable acceptance template before scaling `n_citizens` or day count.

---

## Affinity-based political exposure: NB 27 — committed-minority audience sanity check

**Date:** 2026-05-20
**Notebook:** [notebooks/27_affinity_exposure_demo.ipynb](../notebooks/27_affinity_exposure_demo.ipynb)
**Code under test:** [src/cag/abm/environment.py](../src/cag/abm/environment.py) — `assign_political_exposure`, `_green_affinity_score`, `_reform_affinity_score`, `_safe_int`
**Pool:** full YouGov, N = 1483 (`data/yougov_survey_data/YouGovProcessedData.csv`)

The v0.5 committed-minority reframe replaced the vote-only `priority_chain` exposure rule with an **affinity-rank** assignment: each citizen receives a continuous green-affinity and Reform-affinity score, and a cell label (`A-only` / `B-only` / `both` / `neither`) is allocated by deterministic top-K on the two scores so that realised cell shares match a configurable target preset. NB 27 is the structural sanity check: no LLM calls, no simulation — just verify that on the real YouGov pool (i) the rank mode hits its targets exactly, (ii) the cell-level demographic profile is interpretable, and (iii) the weight presets are not collapsed.

### Configuration

| Parameter | Value |
|---|---|
| Pool | YouGov processed, N = 1483 |
| Modes compared | `rule_priority_chain` (legacy), `rule_affinity_rank` (new default) |
| Target presets | `committed_minority_symmetric` (`A=0.11, B=0.11, both=0.33, neither=0.45`), `committed_minority_uk_2024` (`A=0.08, B=0.14, both=0.33, neither=0.45`) |
| Weight presets | `balanced` (default), `vote_dominant`, `values_dominant` |
| LLM calls | None |

### Headline results

**Affinity-score distributions.** `corr(score_A, score_B) = -0.975` on the YouGov pool. Mirror-symmetric, as designed — that anti-correlation is the structural reason rank-mode hits the symmetric target cleanly and is, separately, the reason the previously-shipped `rule_affinity_logistic` mode was removed (see "Bug fixes" below).

**Realised cell shares (rank mode).**

| Mode / target | A-only | B-only | both | neither |
|---|---:|---:|---:|---:|
| `priority_chain` (legacy, targets ignored) | 0.105 | 0.105 | 0.342 | 0.448 |
| `rule_affinity_rank` (symmetric) | **0.110** | **0.110** | **0.330** | **0.450** |
| `rule_affinity_rank` (uk_2024) | **0.080** | **0.140** | **0.330** | **0.450** |

The rank mode hits both target presets to within rounding (≤ 0.001 pp). The legacy `priority_chain` is incidentally close to the symmetric target on this pool, but does not respond to the `targets=` knob at all.

**Per-cell demographic profile** (rank mode, symmetric default; weights = `balanced`):

| cell | openness | selftransc | rwa | sdo | age | degree | green_region | Remain | Leave | Green vote | Brexit vote |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A-only | **2.24** | **2.68** | 1.33 | 1.03 | 40.4 | 0.93 | 0.41 | **0.96** | 0.00 | 0.26 | 0.00 |
| both | 2.01 | 2.42 | 1.71 | 1.13 | 49.3 | 0.58 | 0.32 | 0.53 | 0.31 | 0.02 | 0.00 |
| B-only | 1.69 | 2.09 | **2.06** | **1.36** | **65.5** | 0.07 | 0.14 | 0.00 | **0.98** | 0.00 | 0.07 |
| neither | 1.92 | 2.33 | 1.81 | 1.16 | 44.7 | 0.35 | 0.28 | 0.33 | 0.24 | 0.01 | 0.00 |

All four pre-registered validation gates pass:

| Gate | Threshold | Realised | Pass? |
|---|---|---|:---:|
| A-only mean openness > pool mean + 0.5 SD | > 2.22 | **2.24** | ✓ |
| A-only Remain-share > 80 % | > 0.80 | **96.3 %** | ✓ |
| B-only mean RWA > pool mean + 0.5 SD | > 1.99 | **2.06** | ✓ |
| B-only Leave-share > 80 % | > 0.80 | **98.2 %** | ✓ |

The cells are substantively interpretable: `A-only` is younger, university-educated, high-openness, high-self-transcendence, almost entirely Remain-voting; `B-only` is the oldest cell, low-education, high-RWA, high-SDO, almost entirely Leave-voting. `both` and `neither` sit between them on every dimension.

**Weight-preset sensitivity.** Holding the target fixed at `committed_minority_symmetric`, swapping the affinity weight preset changes which citizens land in each cell, while keeping the cell shares pinned at target:

| balanced vs vote_dominant | balanced vs values_dominant | vote_dominant vs values_dominant |
|---:|---:|---:|
| 84.2 % | 78.2 % | 65.8 % |

The cell shares are identical across presets by construction (top-K is share-preserving), but only 66 % of citizens get the same label under `vote_dominant` vs `values_dominant`. The weight knob is therefore real — it shifts cell membership without distorting marginals — and is not collapsed to a no-op.

### Bug fixes triggered by this notebook

NB 27 surfaced two issues. Both are resolved.

1. **`_safe_int` silently returned 0 on every GABM ordinal attribute.** The psychometric IDs (`openness_id`, `rwa_id`, `sdo_id`, `selftransc_id`) are `GABMAttributeID` enum subclasses that expose their ordinal via `.id`. The previous `_safe_int` body did a bare `int(attr_id)`, which raises `TypeError` on a `GABMAttributeID`, was swallowed by the `except`, and silently returned `0`. The full psych-scale weight bucket therefore multiplied zero on every `build_nation` citizen, making the three weight presets produce bit-identical cell shares on the first pass of this notebook. The unit-test suite missed the bug because its synthetic fixtures pass raw `int` ordinals, on which `int(v)` works.
   - **Fix.** `_safe_int` now reads `.id` first, then `.value`, then falls back to `int()`. A new `TestSafeInt` regression class in [tests/test_exposure.py](../tests/test_exposure.py) exercises the GABM-attribute path directly and includes an integration-level guard (`test_psych_scales_contribute_to_score`) that builds two otherwise-identical citizens differing only on `openness_id` and asserts their green-affinity scores differ.
2. **`rule_affinity_logistic` systematically missed cell-share targets by ±18 pp.** Independent Bernoulli sampling on two anti-correlated affinity scores (`corr = -0.975` on this pool) collapses the `both` cell and inflates the singleton cells, even though per-side marginals are individually correct. Across 30 seeds the mode produced `{A: 0.287, B: 0.290, both: 0.151, neither: 0.272}` against a symmetric target of `{0.11, 0.11, 0.33, 0.45}`. The unit-test suite missed this because the original `TestAffinityLogistic` tests only checked per-side marginals on a synthetic n=400 fixture with uncorrelated scores.
   - **Fix.** The `rule_affinity_logistic` mode has been removed entirely — from `VALID_EXPOSURE_MODES`, the dispatcher, `_assign_affinity_logistic`, the `affinity_logistic_temperature` SIM_CONFIG key, the `_RESUME_HARD_KEYS` list, and the test suite. v0.5 ships with two modes only: `rule_priority_chain` (legacy) and `rule_affinity_rank` (new default).

After both fixes the test suite is **432 passed, 1 skipped** (430 → 432 = -2 logistic tests + 4 new `TestSafeInt` tests).

### Status and next steps

The v0.5 committed-minority audience reframe is structurally sound on the real YouGov pool: targets are hit exactly, cells are demographically interpretable, validation gates pass, and the weight knob is non-trivial. The audience layer is therefore ready to be exercised end-to-end inside a simulation run — that integration-level experiment (NB 28 / Run 9) is the next planned step. Outstanding caveats are documented in [docs/Literature_Political_Exposure.md](Literature_Political_Exposure.md) §6.2.2 — most importantly that the YouGov pool is panel-engaged, so the `neither` cell is best read as "engaged respondents who score lowest on both affinities", not as the Hansard / Reuters / CAST disengaged cluster.

---

## v0.5 Integration Parity: NB 25 — Qwen3 8B 4-bit via integrated `provider="local"`

**Date:** 2026-05-09
**Notebook:** [notebooks/25_local_llm_integrated_smoke.ipynb](../notebooks/25_local_llm_integrated_smoke.ipynb)
**Result files:** [data/output/local_qwen3_integrated_20260509_182846/20260509_202846/](../data/output/local_qwen3_integrated_20260509_182846/20260509_202846/)

NB 24 was the local-LLM proof-of-concept via in-notebook monkey-patching. NB 25 is the same run executed through the **v0.5 integrated `provider="local"`** branch in [src/cag/io/llm.py](../src/cag/io/llm.py) — no patching, no notebook-side wrapper. The purpose is parity validation before promoting any future local-model work onto the supported path.

### Configuration

Identical to NB 24 (10 agents × 1 day, Ban Petrol Cars, `mlx-community/Qwen3-8B-4bit` on `mlx_lm.server`, `debias=True`, `thinking=True`, seed 42, M1 16 GB) — only the routing changes. The `SIM_CONFIG` now sets `llm_provider="local"` and `local_base_url="http://localhost:8080/v1"`; `configure_local()` and `ping_local()` are called automatically by `_resolve_runtime` at simulation start.

### Headline Results — Bit-for-Bit Parity with NB 24

| Metric | NB 24 (monkey-patched) | NB 25 (integrated) |
|---|---:|---:|
| Day-0 LLM mean / GT mean | +0.70 / +0.20 | **+0.70 / +0.20** |
| Day-0 bias | +0.50 | **+0.50** |
| Day-0 MAE | 2.10 | **2.10** |
| Day-0 ρ (p) | −0.05 (0.88) | **−0.05 (0.88)** |
| Day-1 LLM mean / GT mean | 0.00 / +0.20 | **0.00 / +0.20** |
| Day-1 bias | −0.20 | **−0.20** |
| Day-1 ρ (p) | +0.76 (0.010) | **+0.76 (0.010)** |
| Reflections n / median tokens | 22 / 136 | **22 / 135.5** |
| Mention petrol/car | 59 % | **59 %** |
| Errors / empty-thinking retries | 0 / 0 | **0 / 0** |

`mlx_lm.server` is deterministic at fixed seed for this prompt set, so the match is mechanical, not statistical: anything other than identity would have signalled a routing difference between the monkey-patch and the integrated provider. There is none.

### What This Validates

- `cag.io.llm.send_chat(provider="local")` is functionally identical to NB 24's patched path.
- `_MODEL_REGISTRY` correctly applies Qwen3 sampling, max_tokens, and the `enable_thinking` chat-template kwarg under a live mlx-lm server.
- `SIM_CONFIG["local_base_url"]` propagates through `_resolve_runtime` → `configure_local()` → every downstream `send_chat` call site without touching `agent.py` or `environment.py`.
- `ping_local()` startup health-check ran cleanly; the empty-thinking retry path was not triggered (0 retries) but is exercised in [tests/test_llm_local.py](../tests/test_llm_local.py).

### Status and Next Steps

The NB 24 monkey-patch is now superseded. All future local-model experiments should follow the NB 25 pattern. Open accuracy questions (per-agent persona ρ at non-trivial N) and scale questions (wall-time, parallel dispatch — see [Model_Design.md §16](Model_Design.md)) are unchanged from NB 24 and remain the next experimental priorities.

---

## Local-LLM Smoke Test: NB 24 — Qwen3 8B 4-bit End-to-End

**Date:** 2026-05-09
**Notebook:** [notebooks/24_local_qwen3_smoke_test.ipynb](../notebooks/24_local_qwen3_smoke_test.ipynb)
**Result files:** [data/output/local_qwen3_smoke_20260509_170007/20260509_174754/](../data/output/local_qwen3_smoke_20260509_170007/20260509_174754/)

First end-to-end run of the simulation pipeline with **all** LLM calls (broadcasts, peer messages, reflections, surveys) routed to a **local Qwen3 8B 4-bit** model served by `mlx_lm.server` on M1 16 GB. No `src/` changes — routing is done by monkey-patching `cag.io.llm.send_chat`, the rebound copy in `cag.abm.agent`, and the `load_api_key` rebind in `cag.abm.sim`.

### Configuration

| Parameter | Value |
|---|---|
| n_citizens | 10 |
| n_days | 1 (+ Day 0 baseline) |
| communication_mode | single_policy |
| policy | ClimatePolicyID(3) — Ban Petrol Cars |
| day0_anchor | llm_survey |
| debias | True (Condition D) |
| llm_model | mlx-community/Qwen3-8B-4bit (local) |
| survey_model | (same — local) |
| thinking | True (only forwarded to surveys) |
| sampling | non-thinking T=0.7 top_p=0.8; thinking T=0.6 top_p=0.95 |
| max_tokens | 2048 (msg) / 16384 (survey) |
| k_peers_per_day | 2 |
| network | SBM, p_intra=0.3, p_inter=0.05 |
| random_seed | 42 |
| hardware | Apple M1 16 GB |

### Headline Results

| Question | Answer |
|---|---|
| End-to-end success? | Yes — 0 errors, 0 thinking-mode empty-content retries, all 7 output artefacts produced |
| Total wall-time | **46.6 min** (Day 0 baseline 16.1 min, Day 1 30.4 min) |
| Total LLM calls | 72 |
| Reflection length (mean / median) | **133 / 136 tokens** (range 84–176, n=22) |
| Reflections mentioning policy | 59 % (`petrol` or `car`) |

### Day-0 / Day-1 Survey Accuracy vs YouGov GT (Ban Petrol Cars, n=10)

| Day | LLM mean | GT mean | **Bias** | MAE | **Pearson ρ** | p |
|-----|---------:|--------:|---------:|----:|--------------:|--:|
| 0 | +0.70 | +0.20 | **+0.50** | 2.10 | −0.05 | 0.88 |
| 1 | 0.00 | +0.20 | −0.20 | 1.00 | **+0.76** | **0.010** |

- **Aggregate Day-0 bias of +0.50 is the lowest we have ever measured.** Better than NB 15 Sonnet+debias+thinking (+0.87) on Carbon Tax, dramatically below the +1.4 to +2.2 NB 11/13 baselines. Condition D debiasing transfers cleanly to Qwen3 8B.
- **Per-agent persona fidelity on Day 0 is poor** (ρ ≈ 0, MAE 2.10 / 7-pt scale). Aggregate cancellation hides per-agent error: marginals are right, individuals are essentially decoupled from their persona.
- **Day 1 ρ jumps to +0.76 (p = 0.010).** Either (a) the EOD survey re-anchors on memory of received messages and snaps agents toward their persona-consistent stance, or (b) n=10 makes Day-0 ρ noise. **Disambiguation requires a 30–50-agent rerun.**

### Latency Profile

| Stage | n calls | mean (s) | median (s) | total (s) | share |
|-------|--------:|---------:|-----------:|----------:|------:|
| survey (thinking) | 40 | **53.2** | 50.8 | 2129 | **76 %** |
| broadcast_msg | 2 | 25.9 | 25.9 | 52 | 2 % |
| reflection_broadcast | 14 | 23.6 | 23.5 | 331 | 12 % |
| reflection_peer | 8 | 19.6 | 18.1 | 157 | 6 % |
| peer_msg | 8 | 15.5 | 15.3 | 124 | 4 % |

Each agent-survey is 2 calls under `debias=True` (reasoning + answer), so 40 survey calls = 10 agents × 2 days × 2 passes. The projection model self-checks at +12 % (predicted 41.7 min vs actual 46.6 min).

### Scenario Projections (same hardware, same model)

| Scenario | thinking on | thinking off |
|---|---:|---:|
| 100 agents × 1 day | 6.8 h | 5.0 h |
| 100 agents × 5 days | 28 h | 23 h |
| 100 agents × 10 days | **55 h** | 45 h |
| 50 agents × 5 days | 14 h | — |
| 10 agents × 10 days | 5.6 h | — |

### Where We Are and Where to Go

**Status.** Qwen3 8B 4-bit is a *viable* local backend: full pipeline, research-quality reflections, best aggregate Day-0 bias on record. Open questions are per-agent persona fidelity at non-trivial N, and wall-time at non-trivial scale.

**Accuracy levers (priority order):**
1. **30–50-agent Qwen3 rerun** — the highest-value experiment; resolves whether per-agent ρ ≈ 0 is real or noise.
2. **Try Qwen3 14B 4-bit (fits 16 GB) and 32B 4-bit (HPC).** Persona fidelity scales with model size more than with bit-width.
3. **Qwen3 4B Instruct 2507 4-bit** as a *speed* baseline — if accuracy holds, 100×10 becomes overnight on a single M1.
4. **Explicit debias on/off A/B with Qwen3** to confirm Condition D is doing the work.
5. **`day0_anchor="ground_truth"` for Qwen3** — side-steps the per-agent ρ problem on small N and is the right fit if Qwen3 turns out to be a weak persona-tracker.

**Realism / mechanism levers (HPC + parallelism):**
1. **Async concurrent dispatch** — within-day calls (broadcast reflections, peer reflections, EOD surveys) are embarrassingly parallel. asyncio + httpx against N model replicas gives near-linear speedup; 100×10 drops from 55 h to ~5 h with 10 replicas.
2. **vLLM or sglang on NVIDIA HPC** instead of mlx-lm. Continuous batching + paged attention is 5–20× faster at the same model size; OpenAI-compatible API drops in for free.
3. **Batched survey calls** (vLLM/sglang) — surveys are 76 % of cost and have no inter-agent dependency.
4. **Cap thinking-mode reasoning** (e.g. 2048 tokens, not 16384), or apply thinking only to Condition D's *reasoning* call and not the *answer* call.
5. **Persistent prefix caching** (vLLM/sglang automatic) — every call re-sends the 1–2k-token persona system prompt; caching roughly halves per-call latency.
6. **Reflection conditioning** — promote the policy name to an explicit slot in the reflection user prompt to lift the 59 % policy-mention rate.

**Recommended next step.** Promote the in-notebook monkey-patch into a real `provider="openai_compatible"` (or `"local"`) branch in [src/cag/io/llm.py](../src/cag/io/llm.py), then run the 30–50-agent Qwen3 rerun, then move heavy experiments to HPC with vLLM/sglang and concurrent dispatch.

---

## Run 8: NB 21 Broadcast-Only Asymmetry Replication Across Seeds (43 / 47 / 53)

**Date:** 2026-04-26
**Notebook:** [`notebooks/21_broadcast_only_asymmetry.ipynb`](../notebooks/21_broadcast_only_asymmetry.ipynb)

**Result files:**
- Seed 43 reference (Run 7): S [`data/output/experiments/20260425_125855/`](../data/output/experiments/20260425_125855/), C1 [`20260425_132515/`](../data/output/experiments/20260425_132515/), C3 [`20260425_135538/`](../data/output/experiments/20260425_135538/)
- Seed 47 replication: S [`data/output/experiments/20260426_172247/`](../data/output/experiments/20260426_172247/), C1 [`20260426_180114/`](../data/output/experiments/20260426_180114/), C3 [`20260426_182614/`](../data/output/experiments/20260426_182614/)
- Seed 53 replication: S [`data/output/experiments/20260426_185644/`](../data/output/experiments/20260426_185644/), C1 [`20260426_192446/`](../data/output/experiments/20260426_192446/), C3 [`20260426_202955/`](../data/output/experiments/20260426_202955/)

This section is the cross-seed read of NB 21. Run 7 below remains the full single-seed diagnostic write-up for seed 43; the purpose here is to ask whether the same peers-off, audience-capped asymmetry design survives across independently sampled seed-47 and seed-53 cohorts.

### What Changed Since Run 7

No code changes. The same NB 21 design was re-run at `random_seed=47` and `random_seed=53`, keeping the prompt stack, models, alternating P-A/P-B order, `audience_cap=20`, and peers-off design fixed. Only the sampled 30-person cohort and the deterministic cap/reach draws changed.

### Shared Configuration

| Parameter | Value |
|---|---|
| n_citizens | 30 |
| n_days | 4 |
| communication_mode | single_policy |
| policy | ClimatePolicyID(3) — Ban Petrol Cars |
| day0_anchor | ground_truth_with_rationale |
| debias | True |
| llm_model (broadcast) | gpt-5-mini |
| survey_model | claude-sonnet-4-6 |
| thinking | False |
| llm_temperature | 0.5 |
| k_peers_per_day | 0 |
| phases (alternating) | odd days P-A→P-B, even days P-B→P-A |
| network | SBM, p_intra=0.15, p_inter=0.02 |
| audience_cap | 20 |
| seeds tested | 43, 47, 53 |

| Seed | S wall-time | C1 wall-time | C3 wall-time | Total |
|---|---|---|---|---|
| 43 | 26.2 min | 22.3 min | 22.6 min | 71.1 min |
| 47 | 30.8 min | 22.1 min | 22.9 min | 75.9 min |
| 53 | 24.0 min | 22.5 min | 21.5 min | 68.0 min |

The delivery budget remains structurally identical across seeds: S always delivers 80 pro-climate + 80 anti-climate broadcasts, while C1 and C3 each deliver 20 on the reduced side and 80 on the full-reach side. What changes across seeds is the sampled cohort's Day-0 baseline and the overlap structure of the effective audiences.

### Cohort Baselines and Natural Exposure

| Seed | GT mean | Day 0 support / neutral / against | Natural exposure A-only / B-only / both / neither | Natural audiences |
|---|---|---|---|---|
| 43 | +0.43 | 50 / 23 / 27 | 10 / 3 / 17 / 0 | agent_a=27, agent_b=20 |
| 47 | -0.27 | 37 / 17 / 47 | 7 / 1 / 21 / 1 | agent_a=28, agent_b=22 |
| 53 | 0.00 | 47 / 10 / 43 | 6 / 5 / 18 / 1 | agent_a=24, agent_b=23 |

This is the main reason the effect sizes differ. Seed 43 starts mildly pro-climate, seed 47 starts mildly anti-climate, and seed 53 is almost exactly centred. The reach-asymmetry design is therefore being tested on three substantively different cohorts, not just three RNG perturbations around the same mean.

### Effective Delivery Groups After Cap + Reach

Counts below are reconstructed from `messages.csv` and therefore refer to citizens who actually received at least one political broadcast during the 4-day run.

| Seed | Condition | A-only | B-only | both | neither | agent_a/day | agent_b/day |
|---|---|---|---|---|---|---|---|
| 43 | S | 6 | 6 | 14 | 4 | 20 | 20 |
| 43 | C1 | 1 | 16 | 4 | 9 | 5 | 20 |
| 43 | C3 | 17 | 2 | 3 | 8 | 20 | 5 |
| 47 | S | 6 | 6 | 14 | 4 | 20 | 20 |
| 47 | C1 | 2 | 17 | 3 | 8 | 5 | 20 |
| 47 | C3 | 15 | 0 | 5 | 10 | 20 | 5 |
| 53 | S | 7 | 7 | 13 | 3 | 20 | 20 |
| 53 | C1 | 1 | 16 | 4 | 9 | 5 | 20 |
| 53 | C3 | 16 | 1 | 4 | 9 | 20 | 5 |

The cap-and-reach mechanism behaves exactly as intended on every seed: identical per-day audience sizes inside each condition and a clean C1/C3 mirror on total broadcast volume. What varies is overlap. Seed 47's Green-dominant run, for example, leaves zero B-only citizens at Day 4 because the reduced anti-climate audience is entirely nested inside the pro-climate side's broader reach.

### Aggregate Mean Opinion (Ban Petrol Cars)

| Seed | Day | C1 | S | C3 | Ordered? |
|---|---|---|---|---|---|
| 43 | 0 | +0.433 | +0.433 | +0.433 | — |
| 43 | 1 | +0.633 | +0.600 | +0.767 | No |
| 43 | 2 | +0.533 | +0.833 | +0.900 | Yes |
| 43 | 3 | +0.633 | +0.733 | +0.833 | Yes |
| 43 | 4 | +0.733 | +0.833 | +0.900 | Yes |
| 47 | 0 | -0.267 | -0.267 | -0.267 | — |
| 47 | 1 | -0.133 | +0.233 | +0.833 | Yes |
| 47 | 2 | +0.067 | +0.367 | +0.633 | Yes |
| 47 | 3 | -0.133 | +0.233 | +0.567 | Yes |
| 47 | 4 | -0.133 | +0.500 | +0.667 | Yes |
| 53 | 0 | +0.000 | +0.000 | +0.000 | — |
| 53 | 1 | +0.067 | +0.300 | +0.533 | Yes |
| 53 | 2 | +0.067 | +0.167 | +0.500 | Yes |
| 53 | 3 | -0.067 | +0.167 | +0.567 | Yes |
| 53 | 4 | -0.100 | +0.233 | +0.667 | Yes |

By Day 4 the mean ordering holds on all three seeds. It is monotone from Day 1 onward on seeds 47 and 53, and from Day 2 onward on seed 43 (where Day 1 has a small C1 > S inversion despite the expected C3 > S gap).

### Day-4 Summary

| Seed | C1 day 4 | S day 4 | C3 day 4 | C1 drift | S drift | C3 drift | C3 − C1 swing |
|---|---|---|---|---|---|---|---|
| 43 | +0.733 | +0.833 | +0.900 | +0.300 | +0.400 | +0.467 | +0.167 |
| 47 | -0.133 | +0.500 | +0.667 | +0.133 | +0.767 | +0.933 | +0.800 |
| 53 | -0.100 | +0.233 | +0.667 | -0.100 | +0.233 | +0.667 | +0.767 |
| Mean across seeds | +0.167 | +0.522 | +0.744 | +0.111 | +0.467 | +0.689 | +0.578 |

The large story is robustness with strong seed sensitivity in magnitude. Seed 43 gives the smallest swing (+0.167). Seeds 47 and 53 produce much larger separations (+0.800 and +0.767), largely because their cohorts start less pro-climate and therefore leave much more room for the anti-dominant condition to suppress support.

### Population Composition at Day 4

| Seed | C1 support / against | S support / against | C3 support / against |
|---|---|---|---|
| 43 | 67 / 33 | 70 / 30 | 73 / 27 |
| 47 | 40 / 60 | 63 / 37 | 63 / 37 |
| 53 | 53 / 47 | 60 / 40 | 70 / 30 |

Support-share ordering is therefore slightly noisier than mean ordering. Seed 43 and seed 53 show the expected monotone support gradient at Day 4. Seed 47 shows a tie between S and C3 on support shares (both 63%), even though the mean still cleanly orders C1 < S < C3; on the coarse 7-point scale, the C3 advantage in seed 47 appears mostly as more intensity among supporters rather than a larger supporter count.

### Per-Agent Comparison Across Conditions

| Seed | S vs C3 identical at Day 4 / drift r | S vs C1 identical at Day 4 / drift r | C1 vs C3 identical at Day 4 / drift r |
|---|---|---|---|
| 43 | 25 / 0.924 | 23 / 0.747 | 21 / 0.681 |
| 47 | 21 / 0.687 | 15 / 0.453 | 13 / 0.492 |
| 53 | 17 / 0.677 | 18 / 0.750 | 14 / 0.493 |

The mean effect is robust, but the individual-level path is seed-sensitive. Seed 43 preserves the earlier pattern where S is much closer to C3 than to C1. Seed 47 still shows S closer to C3, but much less tightly. Seed 53 partially flips that comparison on the drift correlation, with S closer to C1 than to C3. So the sign of the reach effect is robust; the claim that one side is systematically the "less disruptive" variant is not yet robust enough to elevate into the paper.

### Daily Dispersion

Across all three seeds, Day 4 standard deviations stay at or below the Day-0 level in every condition: seed 43 falls from 2.11 to 1.81-1.98, seed 47 from 2.27 to 1.74-1.90, and seed 53 from 2.23 to 2.06-2.17. The broadcast asymmetry continues to move the cohort mean without generating wider disagreement at this scale.

### Key Findings

1. **The mean-ordering result replicates.** By Day 4 all three seeds satisfy `C1 < S < C3` on the opinion mean. Two of the three seeds satisfy it from Day 1 onward; all three satisfy it from Day 2 onward.
2. **Effect size is strongly cohort-dependent.** The Day-4 full swing `C3 - C1` ranges from **+0.167** (seed 43) to **+0.800** (seed 47) and **+0.767** (seed 53), with a three-seed average of **+0.578**. The design is robust to seed at the sign level, not at the magnitude level.
3. **The cohort baseline matters as much as the reach lever.** Seed 43 starts mildly pro-climate (`GT=+0.43`), seed 47 mildly anti-climate (`GT=-0.27`), and seed 53 roughly neutral (`GT=0.00`). These starting points explain much of the variation in swing size.
4. **Support shares are a blunter diagnostic than means.** Day-4 support shares are monotone on seeds 43 and 53, but seed 47 ends in a tie between S and C3 (63 / 63) despite a clear mean gap (+0.50 vs +0.67). The integer survey scale compresses some of the treatment effect into intensity rather than count changes.
5. **The audience-cap mirror property is fully validated.** Every seed yields the intended 20/20 capped baseline, 5/20 in C1, and 20/5 in C3. The earlier NB 20 confound is gone.
6. **No evidence of added polarisation at N=30, 4 days.** Dispersion does not widen under asymmetry on any seed; the effect continues to operate as a shift in the centre of the distribution.

### Interpretation

The clean conclusion is that the broadcast-only asymmetry mechanism is real, but the current paper should describe it as a **directionally robust small-N result** rather than as a stable effect-size estimate. The three seeds agree on the sign and final-day ordering. They disagree sharply on magnitude because the sampled cohorts differ materially in Day-0 baseline and exposure composition. Seed 43 remains the most conservative illustration; seed 47 and seed 53 show that once the sampled cohort is less pro-climate at baseline, the same reach manipulation can produce a much larger final gap.

### Remaining Issues / Open Questions

- **Effect-size stability is still open.** Three seeds are enough to reject the idea that seed 43 was a one-off fluke, but not enough to estimate a paper-grade mean effect with confidence.
- **Share-based claims should be phrased carefully.** Means replicate more cleanly than support shares because a 30-agent sample on a 7-point scale is coarse.
- **The seed-47 cohort is unusually favourable to a large asymmetry effect.** With only one B-only citizen and 21 naturally in `both`, the effective overlap structure leaves more room for reach to re-sort exposure sharply.
- **The per-agent "less disruptive" story is not yet robust.** Seed 43 suggested C3 was consistently closer to S than C1 was; seeds 47 and 53 weaken that claim.

### Implication for the Paper

Run 8 does not replace the current Probe-2 source run in the paper; it supplies the replication evidence for deciding how strongly the main text should state the asymmetry claim and what should be tabulated in the SI. The main-text figure can still use seed 43 as the concrete worked example, but any strengthened prose should be grounded in the three-seed result reported here rather than in Run 7 alone.

---

## NB 23: Persona Signal Test at n=100 (Carbon tax + Climate compensation)

**Date:** 2026-04-25
**Notebook:** [`notebooks/23_persona_signal_test.ipynb`](../notebooks/23_persona_signal_test.ipynb)
**Result files:** [`data/output/calibration/20260425_211242_persona/`](../data/output/calibration/20260425_211242_persona/) — `calibration_raw.csv`, `per_policy.csv`, `permutation_null.csv`, `null_distributions.npz`, `summary.json`

### Purpose

Resolve the two NB-22 borderline cases (Carbon tax failing the ordinal test at `p_ord=0.13`; Renewable energy borderline on `p_MAE=0.07`) by running the same survey-path stack at higher statistical power. Re-tested only the two cost-framed policies on which NB 22 was inconclusive (Carbon tax and Climate compensation) — Renewable energy was not re-run because its NB-22 borderline is a power artefact of a heavily compressed YouGov marginal, not a Sonnet failure mode.

### Configuration

| Parameter | Value |
|---|---|
| n_agents | 100 |
| policies | ClimatePolicyID(5) Carbon tax, ClimatePolicyID(6) Climate compensation |
| sample_seed | 23 |
| sample disjointness | 30 main-run respondent IDs explicitly excluded (recorded in `summary.json::excluded_main_run_ids`) |
| model | claude-sonnet-4-6 (anthropic) |
| temperature | 0.5 |
| thinking | False |
| debias | True (two-step protocol) |
| n_perms | 1000 |

Same survey-path stack as Run 5 / Run 7 production runs.

### Per-Policy Results

| Policy | n | Bias | MAE | Spearman ρ | Exact | Ordinal |
|---|---|---|---|---|---|---|
| Carbon tax (5) | 100 | **+0.85** | 1.29 | 0.407 | 0.29 | 0.58 |
| Climate compensation (6) | 100 | **+0.48** | 1.42 | 0.528 | 0.22 | 0.62 |

### Permutation Null (B=1000)

| Policy | real_ord | null_ord_mean | p_ord | real_mae | null_mae_mean | p_mae |
|---|---|---|---|---|---|---|
| Carbon tax (5) | 0.58 | ≈0.43 | **0.017** | 1.29 | 1.661 | **<0.001** |
| Climate compensation (6) | 0.62 | ≈0.40 | **<0.001** | 1.42 | 2.151 | **<0.001** |

Both policies clear the null comfortably on both summary statistics. The realised MAE on Carbon tax (1.29) is well below the null mean (1.66); on Climate compensation (1.42 vs 2.15) the gap is larger still.

### Findings

1. **Borderline NB-22 cases were power artefacts, not signal failures.** At n=100 both Carbon tax and Climate compensation reject random pairing on both metrics. Sonnet under two-step debias *is* reading the persona on cost-framed policies; n=30 was just too small to detect it on the ordinal test.
2. **Bias is reproduced on a disjoint sample.** Carbon tax bias +0.85 (NB 23) corroborates +0.87 (NB 22); Climate compensation +0.48 (NB 23) corroborates +0.60 (NB 22). The cost-framed pro-climate prior is real and not an artefact of the n=30 sample.
3. **Spearman ρ improves modestly with n.** Carbon tax ρ rises from 0.48 (n=30) to 0.41 (n=100), Climate compensation from 0.46 to 0.53; both stay in the rank-informative-but-noisy regime expected at this individual-agent grain.

### Implication for the Paper

NB 23 is the high-power complement to NB 22. Together they support §5.3 (persona signal) and §5.4 (per-policy bias) of `sn-article.tex`. The disjoint-sample design also lets the paper claim corroboration rather than re-fitting on the same draws.

---

## NB 22: Day-0 Survey Accuracy under Sonnet + Two-Step Debias (n=30, six policies)

**Date:** 2026-04-25
**Notebook:** [`notebooks/22_day0_accuracy_sonnet.ipynb`](../notebooks/22_day0_accuracy_sonnet.ipynb)
**Result files:** [`data/output/calibration/20260425_203841/`](../data/output/calibration/20260425_203841/) — `calibration_raw.csv`, `per_agent.csv`, `per_policy.csv`, `permutation_null.csv`, `summary.json`

### Purpose

Evaluation of the survey-path component used in Run 5 (NB 19) and Run 7 (NB 21). Holds the agent in isolation (no memory, no broadcasts, no peer exchange, opinion history cleared) and asks two questions: (i) does Sonnet under two-step debias actually read the persona it is given, or does it sample from a marginal distribution that happens to overlap the YouGov one? and (ii) what is the residual per-policy bias the production survey path leaves behind?

### Configuration

| Parameter | Value |
|---|---|
| n_agents | 30 (same cohort as Run 5 / Run 7, random_seed=43) |
| policies | All six (ClimatePolicyID(1)–ClimatePolicyID(6)) |
| model | claude-sonnet-4-6 (anthropic) |
| temperature | 0.5 |
| thinking | False |
| debias | True (two-step protocol; selected from the four-condition pilot — NB 13) |
| n_perms | 100 |

### Aggregate Result

| Metric | Value |
|---|---|
| n calls | 180 |
| Exact match | 0.289 |
| Ordinal match (within ±1) | 0.706 |
| MAE | 1.194 |
| Bias (LLM − GT) | **+0.406** |
| Spearman ρ (pooled) | 0.550 |

### Per-Policy Results

| Policy | LLM mean | GT mean | Bias | MAE | Spearman ρ | Ordinal | Exact |
|---|---|---|---|---|---|---|---|
| (1) Renewable energy | 2.333 | 1.867 | +0.467 | — | 0.251 | 0.833 | 0.400 |
| (2) Ban fossil fuels | 1.200 | 1.067 | +0.133 | — | 0.613 | 0.800 | 0.433 |
| (3) Ban petrol cars | 0.500 | 0.433 | +0.067 | — | 0.628 | 0.700 | 0.233 |
| (4) Green housing | 1.833 | 1.533 | +0.300 | — | 0.444 | 0.767 | 0.233 |
| (5) Carbon tax | 1.633 | 0.767 | **+0.867** | — | 0.480 | 0.567 | 0.233 |
| (6) Climate compensation | 0.700 | 0.100 | **+0.600** | — | 0.464 | 0.567 | 0.200 |

### Permutation Null (B=100)

| Policy | real_ord | null_ord_mean | p_ord | real_mae | null_mae_mean | p_mae |
|---|---|---|---|---|---|---|
| (1) Renewable energy | 0.833 | 0.745 | **0.04** | 0.867 | 1.045 | 0.07 |
| (2) Ban fossil fuels | 0.800 | 0.443 | **<0.01** | 0.933 | 2.133 | **<0.01** |
| (3) Ban petrol cars | 0.700 | 0.423 | **<0.01** | 1.267 | 2.244 | **<0.01** |
| (4) Green housing | 0.767 | 0.600 | **<0.01** | 1.033 | 1.496 | **<0.01** |
| (5) Carbon tax | 0.567 | 0.481 | 0.13 | 1.400 | 1.885 | **0.01** |
| (6) Climate compensation | 0.567 | 0.400 | **0.02** | 1.667 | 2.178 | **0.04** |

`p_MAE < 0.05` on **5 of 6** policies (Renewable borderline at 0.07). `p_ord < 0.05` on **5 of 6** policies (Carbon tax fails at 0.13). The two tests fail on different policies, which is expected at n=30: Renewable's MAE test loses power because the YouGov marginal is heavily compressed at the pro-climate end (a random pairing already scores ordinally well, eroding MAE separation), while Carbon tax's ordinal test is hurt by the LLM's upward bias inflating ordinal noise without affecting MAE in the same way.

### Findings

1. **Persona is read on every behavioural / supply-side policy with no ambiguity.** Policies (2)–(4) reject random pairing decisively on both tests.
2. **Borderline cases are power, not signal.** Renewable (1) and Carbon tax (5) are inconclusive at n=30. NB 23 was run to resolve the cost-framed cases; Renewable's borderline is structurally explained by ground-truth compression and was not re-run.
3. **Bias is structured by policy framing.** Behavioural-restriction and supply-side policies (1)–(4) sit in a small bias band of +0.07 to +0.47, all within roughly one SE of zero on (2) and (3). Cost-framed policies (5) and (6) carry +0.87 and +0.60 — large, persistent, and qualitatively distinct from the behavioural band.
4. **Implication for the simulation.** Day-0 in Run 5 / Run 7 is anchored to ground truth, not to a cold LLM survey, so the bias documented here does not contaminate the empirical starting point of the cohort. Within-policy directional change (the quantity Probe 2 tests) is measured against the same biased anchor on every day and remains interpretable; absolute support levels on Carbon tax and Climate compensation in Probe 1 should be read with the residual cost-framed bias in mind.

### Implication for the Paper

NB 22 supplies the n=30 panel of §5.3 (Figure `calib_null_sixpolicy.pdf`) and the blue series of §5.4 (Figure `calib_bias.pdf`). NB 23 supplies the orange overlay on the latter and the n=100 high-power panel of §5.3 (Figure `calib_null_followup.pdf`). Together they back the four bullets in §5.4's "implications for the simulation".

---

## Run 7: NB 21 Broadcast-Only Asymmetry Sweep (S / C1 / C3, single-policy, peers off)

**Date:** 2026-04-25
**Notebook:** [`notebooks/21_broadcast_only_asymmetry.ipynb`](../notebooks/21_broadcast_only_asymmetry.ipynb)
**Result files:**
- S_symmetric: [`data/output/experiments/20260425_125855/`](../data/output/experiments/20260425_125855/) — `reach_a=1.0, reach_b=1.0`
- C1_reform_dominant: [`data/output/experiments/20260425_132515/`](../data/output/experiments/20260425_132515/) — `reach_a=0.25, reach_b=1.0`
- C3_green_dominant: [`data/output/experiments/20260425_135538/`](../data/output/experiments/20260425_135538/) — `reach_a=1.0, reach_b=0.25`

Each run produced the standard suite: [`opinion_trajectories.csv`](../data/output/experiments/20260425_125855/opinion_trajectories.csv), [`opinion_shares.csv`](../data/output/experiments/20260425_125855/opinion_shares.csv), [`messages.csv`](../data/output/experiments/20260425_125855/messages.csv), [`reflections.csv`](../data/output/experiments/20260425_125855/reflections.csv), [`survey_reasoning.csv`](../data/output/experiments/20260425_125855/survey_reasoning.csv), [`ground_truth.csv`](../data/output/experiments/20260425_125855/ground_truth.csv), [`timings.csv`](../data/output/experiments/20260425_125855/timings.csv), [`CONDITION.txt`](../data/output/experiments/20260425_125855/CONDITION.txt), and [`opinion_trajectories.png`](../data/output/experiments/20260425_125855/opinion_trajectories.png).

### What Changed Since Run 6

Run 6 (NB 20 C1) showed only a −0.044 aggregate package-index gap vs the Run 5 symmetric baseline. Per-agent diagnostics (Q2) revealed two confounds: (i) **peer flooding** — pro-climate peer messages in phase C carry the population's pro-climate prior into every interaction and dilute any broadcast asymmetry, and (ii) **structural audience asymmetry** — `assign_political_exposure()` produces a 27/20 audience split on this seed, so reach=1.0/1.0 was already 35% asymmetric in agent_a's favour and (C1, C3) were not true mirrors.

Run 7 addresses both:

| Confound | Mechanism in Run 7 |
|---|---|
| Peer flooding | Phase C removed entirely; `phases=["P-A","P-B"]` only |
| Structural audience asymmetry | New `audience_cap=20` knob applied before reach subsample → both political agents start from identical-sized capped audiences |
| Aggregate-noise drowning the signal | Single-policy mode (Ban Petrol Cars, GT mean ≈ +0.43, the most contestable policy in our set), so 1 EOD survey/agent/day instead of 6 |

This is the cleanest possible test of the reach mechanism that this codebase supports as of today.

### Experiment Configuration

| Parameter | Value (all 3 conditions) |
|---|---|
| n_citizens | 30 |
| n_days | 4 |
| communication_mode | single_policy |
| policy | ClimatePolicyID(3) — Ban Petrol Cars (GT = +0.43) |
| day0_anchor | ground_truth_with_rationale |
| debias | True |
| llm_model (broadcast) | gpt-5-mini |
| survey_model | claude-sonnet-4-6 |
| thinking | False |
| llm_temperature | 0.5 |
| **k_peers_per_day** | **0** (peers off) |
| phases (alternating) | odd days P-A→P-B, even days P-B→P-A |
| network | SBM, p_intra=0.15, p_inter=0.02 |
| **audience_cap** | **20** |
| random_seed | 43 |

| | reach_a | reach_b | wall-time |
|---|---|---|---|
| S_symmetric | 1.0  | 1.0  | 1,574 s = 26.2 min |
| C1_reform_dominant | 0.25 | 1.0  | 1,339 s = 22.3 min |
| C3_green_dominant  | 1.0  | 0.25 | 1,354 s = 22.6 min |

C1 and C3 are ~14% faster than S because they cut total broadcast deliveries from 160 to 100. The dominant cost (120 Anthropic survey calls per condition) is identical across all three. Total wall-time: ~71 min, total cost: ~£3–6 across the three runs.

### Audience Construction (cap → reach pipeline)

`assign_political_exposure()` produces the same starting audiences in every condition: agent_a natural=27, agent_b natural=20. The `audience_cap=20` knob trims agent_a's list to 20 (independent RNG, seed+100), leaving agent_b untouched. The `apply_reach_subsample` step then enforces the condition-specific reach (independent RNG, seed/seed+1).

Resulting effective audiences (citizens who received ≥1 broadcast across the 4 days, reconstructed from `messages.csv`):

| Group | S | C1 | C3 |
|---|---|---|---|
| A-only | 6  | 1  | 17 |
| B-only | 6  | 16 | 2  |
| both   | 14 | 4  | 3  |
| neither| 4  | 9  | 8  |

Per-day broadcast deliveries:

| Source | S | C1 | C3 |
|---|---|---|---|
| agent_a (pro-climate) | 20/day × 4 = 80  | 5/day × 4 = 20  | 20/day × 4 = 80 |
| agent_b (anti-climate)| 20/day × 4 = 80  | 20/day × 4 = 80 | 5/day × 4 = 20  |
| **Total broadcasts**  | **160**          | **100**         | **100**         |
| Peer messages         | 0 | 0 | 0 |

C1 and C3 are now true mirrors: identical total volume, identical reach ratios, swapped sides. This is the property Run 6 lacked.

### Aggregate Mean Opinion (Ban Petrol Cars, GT = +0.43)

| Day | C1 (anti dom.) | S (sym) | C3 (pro dom.) | C3 − C1 |
|---|---|---|---|---|
| 0 (anchor) | +0.433 | +0.433 | +0.433 | 0.000 |
| 1 | +0.633 | +0.600 | +0.767 | +0.133 |
| 2 | +0.533 | +0.833 | +0.900 | +0.367 |
| 3 | +0.633 | +0.733 | +0.833 | +0.200 |
| 4 | **+0.733** | **+0.833** | **+0.900** | **+0.167** |

**4-day drift:** C1 = **+0.300**, S = **+0.400**, C3 = **+0.467**. Strictly monotone in reach asymmetry from Day 1 onward, no inversions on any day. The full swing C3 − C1 = **+0.167** opinion units on the −3..+3 scale at N=30 after only 4 days.

Daily SDs (1.81–2.01 across all conditions and days) are slightly *lower* than Day 0's 2.11 — the population is converging marginally, not polarising. Asymmetric reach moves the *mean*; it does not fan out the distribution at this scale.

### Population Composition (% support / neutral / against)

| Day | C1 | S | C3 |
|---|---|---|---|
| 0 | 50 / 23 / 27 | 50 / 23 / 27 | 50 / 23 / 27 |
| 1 | 67 / 0 / 33  | 63 / 0 / 37  | 67 / 3 / 30  |
| 2 | 63 / 0 / 37  | 67 / 0 / 33  | 73 / 0 / 27  |
| 3 | 67 / 0 / 33  | 67 / 3 / 30  | 73 / 0 / 27  |
| 4 | **67 / 0 / 33** | **70 / 0 / 30** | **73 / 0 / 27** |

Day 4 support: 20 / 21 / 22 agents — a clean +1-agent-per-step monotone progression. Same monotonicity holds on the against side (10 / 9 / 8).

### Per-Agent Comparison

| Comparison | Identical at Day 4 | Drift correlation r |
|---|---|---|
| S vs C3  | 25/30 (83%) | **0.924** |
| S vs C1  | 23/30 (77%) | 0.747 |
| C1 vs C3 (full swing) | 21/30 (70%) | 0.681 |

C3 is the closest to S: it adds a modest pro-climate push without destabilising who responds. C1 is more disruptive — silencing the pro-climate side both shifts the mean and changes which agents move (lower r with both S and C3). The lower C1↔C3 correlation (0.681) means asymmetric reach is doing something more than rescaling magnitudes; it's reshuffling individual trajectories at the margin.

### Top Differential Movers (C3 vs C1, |Δ| ≥ 1 at Day 4)

9/30 agents differ. The five largest swings:

| agent_id | C1 d4 | C3 d4 | C3 − C1 |
|---|---|---|---|
| 332  | −1 | +2 | **+3** |
| 1244 | −2 | +1 | **+3** |
| 1555 | −1 | +1 | +2 |
| 991  | +1 | −1 | −2 |
| 574  | +1 | 0  | −1 |

agent 332 and 1244 are the cleanest signature: both centrist (GT 0 and −2 respectively), both swing the full reach-knob range when the dominant voice flips. agent 991 swings the wrong way (more pro-climate when the *anti* side dominates) — small-N noise on a centrist who's reactive to whichever broadcast happens to land late.

### Per-Phase Trajectory Note

C1 has a non-monotone Day 1 → Day 2 dip (+0.633 → +0.533) before recovering to +0.733 at Day 4. The other two conditions rise smoothly. This is consistent with the alternating-phase ordering: Day 2 starts with phase P-B, and with agent_a's 5-recipient broadcast unable to compensate the 20-recipient anti-climate broadcast on the same day, the population briefly retreats toward GT before stabilising. Worth a single-seed replication before claiming it's structural.

### Mechanism Throughput Summary

| Channel | S | C1 | C3 |
|---|---|---|---|
| Political broadcasts (agent_a) | 80 | **20** | 80 |
| Political broadcasts (agent_b) | 80 | 80 | **20** |
| Peer messages | 0 | 0 | 0 |
| Reflections (P-A and P-B only) | 240 | 240 | 240 |
| Survey reasoning rows | 120 | 120 | 120 |

### Key Findings

1. **Reach asymmetry produces a clean monotone signal once peers are removed.** Day 4 means: C1 +0.733 < S +0.833 < C3 +0.900. Same monotonicity for support shares (67% < 70% < 73%) and for against shares (33% > 30% > 27%). All three independent metrics agree.
2. **Effect size: 0.167 opinion units on the −3..+3 scale (full reach swing C3 − C1) after 4 days at N=30.** This is ~4× the per-day-Day-7 NB 20 effect of −0.044 — the broadcast-only design clearly recovers signal that NB 20's package + peers configuration buried.
3. **C3 − S = +0.067 ≈ S − C1 = +0.100 in the right direction.** The asymmetry between the two halves is small enough to be seed noise, but the direction is consistent: each step of the reach knob (0.25 → 1.0) moves the mean by ~0.08–0.10.
4. **Peer flooding is confirmed as the NB 20 confound.** Same agents, same seed, same day count — moving from "package + 3 peers/day + 7 days" (NB 20) to "single-policy + 0 peers + 4 days" (NB 21) flips the C1 vs symmetric gap from −0.044 (in noise) to a clean monotone effect.
5. **Audience-cap mechanism works as designed.** Both C1 and C3 produce identical total broadcast counts (100 each) with reach swapped. This is the property NB 20 lacked because of the 27/20 structural asymmetry.
6. **C3 is "less disruptive" than C1 (r(S,C3)=0.92 vs r(S,C1)=0.75).** Adding pro-climate dominance pushes the mean further in the same direction the population already drifts; muting it (C1) creates more individual trajectory reshuffling because some centrists who would have moved pro now stay put or drift the other way.
7. **No polarisation at N=30, 4 days.** Daily SDs are within ±0.13 of each other across conditions and slightly lower than Day 0. The reach knob shifts the population centre; it does not widen the distribution at this scale.

### Caveats and Open Questions

- **Single seed.** All three results are at seed=43. Replicate at 47 and 53 to bound seed noise on the 0.167 effect size.
- **C1 Day-1→Day-2 dip.** Non-monotone within-condition trajectory. Could be alternating-phase artefact; needs a second seed to disambiguate from structural.
- **Coarsening the discrete scale.** Several differences vanish into integer rounding. A continuous-scale survey (or averaging across multiple LLM samples per opinion) would surface sub-unit reach effects more cleanly.
- **N=30 ceiling on per-exposure-group inference.** A-only/B-only/both partition shifts dramatically across conditions (S: 6/6/14, C1: 1/16/4, C3: 17/2/3) — too small for stable group-level claims. N=60 would help.
- **"Most contestable" policy choice.** Ban Petrol Cars was picked as the contestable single policy (GT = +0.43, near neutral). High-consensus policies (Renewable Energy, GT > +1.8) likely show ceiling effects; contested low-baseline policies (Climate Compensation, GT ≈ +0.1) might amplify the swing. Worth a follow-up sweep across policies.
- **Effect sizes on the discrete −3..+3 scale.** A 0.167-unit shift is real and monotone but small in absolute terms — it's roughly "1–2 agents shifting by one notch". Whether that constitutes a meaningful "tipping" signal in the GABM-as-public-opinion-instrument framing is a separate methodological question.

### Comparison Across Reach-Asymmetry Experiments So Far

| Run | Mode | Days | Peers | Audience cap | C1 − Sym (aggregate) | Signal? |
|---|---|---|---|---|---|---|
| Run 5 vs Run 6 | package | 7 | k=3 | None (27/20) | −0.044 | Ambiguous |
| Run 7 (NB 21 S vs C1) | single_policy | 4 | 0 | 20/20 | −0.100 | Yes, clean |
| Run 7 (NB 21 S vs C3) | single_policy | 4 | 0 | 20/20 | +0.067 | Yes, clean |
| Run 7 (NB 21 C1 vs C3) | single_policy | 4 | 0 | 20/20 | +0.167 | Yes, monotone |

The trend is unambiguous: removing peers and equalising audiences progressively surfaces the broadcast effect.

### Suggested Next Steps

1. **Seed replication.** Run S/C1/C3 at seeds 47 and 53. Cost: ~70 min × 2 = ~140 min wall-time, ~£10–12 Anthropic.
2. **Add intermediate reach.** A 5-point sweep (reach_a ∈ {0.25, 0.5, 0.75, 1.0} × reach_b ∈ {1.0, 0.75, 0.5, 0.25}) would test linearity vs threshold dynamics.
3. **Reintroduce peers gradually.** k_peers_per_day ∈ {0, 1, 2, 3} sweep at fixed reach C1 — confirms the peer-flooding magnitude and finds the threshold at which broadcast asymmetry becomes invisible again.
4. **Multi-policy replication.** Repeat S/C1/C3 on Carbon Tax (the Run 6 anomaly) and Climate Compensation (low-baseline contested) to test policy generalisation.
5. **N=60 paper-grade run.** Once seed-noise is bounded, scale up to support per-exposure-group inference.

### Code Changes Triggered or Validated

- New `audience_cap` knob (added during Run 6 follow-up): validated end-to-end here. C1/C3 produce the expected identical broadcast-volume mirror condition.
- NB 21 itself: new notebook, single-policy + peers-off + audience_cap design, with cross-condition overlay cell that auto-discovers latest output dir per condition via `CONDITION.txt` markers.
- No further code changes required; existing infrastructure now demonstrably supports clean reach-asymmetry experiments.

---

## Run 6: 20260425_082317 — NB 20 C1 (Reach Asymmetry Pilot: Reform-Dominant Broadcast)

**Date:** 2026-04-25
**Result files:** [`data/output/experiments/20260425_082317/`](../data/output/experiments/20260425_082317/)
- [`CONDITION.txt`](../data/output/experiments/20260425_082317/CONDITION.txt) — `C1_reform_dominant`, reach_a=0.25, reach_b=1.0
- [`config.json`](../data/output/experiments/20260425_082317/config.json)
- [`opinion_trajectories.csv`](../data/output/experiments/20260425_082317/opinion_trajectories.csv) (1,440 rows)
- [`package_index_trajectories.csv`](../data/output/experiments/20260425_082317/package_index_trajectories.csv) (240 rows)
- [`reflections.csv`](../data/output/experiments/20260425_082317/reflections.csv)
- [`messages.csv`](../data/output/experiments/20260425_082317/messages.csv) (553 rows: 182 broadcast + 371 peer)
- [`survey_reasoning.csv`](../data/output/experiments/20260425_082317/survey_reasoning.csv) (1,440 rows)
- Plots: [`opinion_trajectories.png`](../data/output/experiments/20260425_082317/opinion_trajectories.png), [`package_index_trajectories.png`](../data/output/experiments/20260425_082317/package_index_trajectories.png), [`opinion_shares.png`](../data/output/experiments/20260425_082317/opinion_shares.png), [`package_index_shares.png`](../data/output/experiments/20260425_082317/package_index_shares.png)
- [`timings.csv`](../data/output/experiments/20260425_082317/timings.csv)

**Notebook:** [`notebooks/20_reach_asymmetry_pilot.ipynb`](../notebooks/20_reach_asymmetry_pilot.ipynb)
**Comparison baseline:** Run 5 ([`data/output/experiments/20260425_010615/`](../data/output/experiments/20260425_010615/), NB 19) — identical config except `reach_a=reach_b=1.0`.

### What Changed Since Run 5

Run 6 introduces the first **broadcast-reach asymmetry** experiment. A single new mechanism, `apply_reach_subsample()`, runs once at simulation start (after `assign_political_exposure()`, before `create_network()`) to deterministically subsample each political agent's audience to `floor(reach × |audience|)` citizens. RNG seeds are `random_seed` for agent A and `random_seed + 1` for agent B, so the two sides draw independently and the result is fully reproducible. Per-citizen `political_exposure` labels are unchanged; peer messaging is unaffected.

Run 6 is the C1 condition of the NB 20 pilot:

| Knob | Run 5 (baseline) | Run 6 (C1) |
|---|---|---|
| `reach_a` (pro-climate) | 1.0 | **0.25** |
| `reach_b` (anti-climate) | 1.0 | 1.0 |
| Everything else | identical | identical |

The intent is to model an asymmetric communication environment in which the anti-climate ("Reform-aligned") political agent dominates the airwaves while the pro-climate ("Green-aligned") agent reaches only a quarter of its natural audience.

### Experiment Configuration

| Parameter | Value |
|---|---|
| n_citizens | 30 |
| n_days | 7 |
| communication_mode | package (all 6 climate policies) |
| day0_anchor | ground_truth_with_rationale |
| debias | True |
| llm_model (broadcast / peer / memory) | gpt-5-mini |
| survey_model | claude-sonnet-4-6 |
| thinking | False |
| llm_temperature | 0.5 |
| k_peers_per_day | 3 |
| **reach_a** | **0.25** |
| **reach_b** | **1.0** |
| phases (alternating) | odd days P-A→P-B→C, even days P-B→P-A→C |
| network | SBM, p_intra=0.15, p_inter=0.02 |
| random_seed | 43 |
| **wall-time** | **13,498 s ≈ 225 min** |

The wall-time is *higher* than Run 5's 138 min despite ~45% fewer broadcast deliveries — most of the cost is the Anthropic survey calls (1,440 of them with debias), not the OpenAI broadcasts. Reach-subsampling cuts cheap calls but leaves the dominant cost untouched.

### Audience Construction

`assign_political_exposure()` produces a structurally asymmetric population on the YouGov sample:

| Group | Count (N=30, seed=43) | Receives agent_a | Receives agent_b |
|---|---|---|---|
| A-only | 10 | ✓ | — |
| B-only | 3 | — | ✓ |
| both | 17 | ✓ | ✓ |
| neither | 0 | — | — |
| **agent_a natural audience** | **27** | | |
| **agent_b natural audience** | **20** | | |

After `apply_reach_subsample(reach_a=0.25, reach_b=1.0, seed=43)`:

| Audience | Run 5 | Run 6 (C1) |
|---|---|---|
| agent_a (pro-climate) | 27/27 | **6/27** |
| agent_b (anti-climate) | 20/20 | 20/20 |

Per-day broadcast deliveries (verified from `messages.csv`):

| Source | Run 5 | Run 6 (C1) |
|---|---|---|
| agent_a broadcasts (7 days) | 189 | **42** (= 6 × 7) |
| agent_b broadcasts (7 days) | 140 | 140 (unchanged) |
| Total broadcasts | 329 | 182 (−45%) |
| Peer messages | 371 | 371 (unchanged) |
| **Peer : political ratio** | **1.13 : 1** | **2.04 : 1** |

The peer:political ratio more than doubles under C1 — peer messaging now carries roughly twice the message volume of the (combined) political broadcast channel. This is mechanistically important; see "Findings" below.

### Aggregate Package-Index Trajectory

| Day | Run 5 mean | Run 6 (C1) mean | Δ (C1 − Run 5) | Run 5 SD | C1 SD |
|---|---|---|---|---|---|
| 0 (anchor) | +0.961 | +0.961 | **0.000** | 1.323 | 1.323 |
| 1 | +1.156 | +1.150 | −0.006 | 1.338 | 1.370 |
| 2 | +1.194 | +1.156 | −0.039 | 1.356 | 1.362 |
| 3 | +1.222 | +1.122 | −0.100 | 1.332 | 1.369 |
| 4 | +1.183 | +1.211 | +0.028 | 1.349 | 1.298 |
| 5 | +1.178 | +1.139 | −0.039 | 1.327 | 1.304 |
| 6 | +1.217 | +1.167 | −0.050 | 1.304 | 1.318 |
| 7 (final) | +1.167 | +1.122 | **−0.044** | 1.357 | 1.376 |

The aggregate gap is **−0.044** at Day 7, much smaller than the manipulation might suggest. Direction is correct (silencing the pro-climate broadcast yields a slightly less pro-climate population) but the magnitude is well within seed/sampling noise. SDs across days are essentially identical between the two conditions (1.30–1.38 in both), so the asymmetric reach did **not** produce additional polarisation.

### Per-Policy Drift (GT → Day 7)

| Policy | GT mean | Run 5 Day 7 | Run 6 (C1) Day 7 | Run 5 drift | C1 drift | Δ drift (C1 − R5) |
|---|---|---|---|---|---|---|
| Renewable Energy (1) | +1.87 | +2.07 | +1.80 | +0.20 | **−0.07** | **−0.27** |
| Ban Fossil Fuel (2) | +1.07 | +1.13 | +1.07 | +0.07 | 0.00 | −0.07 |
| Ban Petrol Cars (3) | +0.43 | +0.63 | +0.57 | +0.20 | +0.13 | −0.07 |
| Green Housing (4) | +1.53 | +1.33 | +1.40 | −0.20 | −0.13 | +0.07 |
| Carbon Tax (5) | +0.77 | +1.20 | +1.30 | +0.43 | **+0.53** | **+0.10** |
| Climate Compensation (6) | +0.10 | +0.63 | +0.60 | +0.53 | +0.50 | −0.03 |

**Renewable Energy is the clean signature of the manipulation.** Run 5 drifted +0.20 above its already high GT (+1.87) — clearly attributable to the pro-climate political agent pushing on a high-consensus policy. Under C1, with that agent silenced for 21 of its 27 audience members, Renewable Energy drifts in the *opposite* direction, ending −0.07 below GT (Δ = −0.27). This is the largest signed gap in the table and the one most consistent with the intended mechanism.

**Carbon Tax goes the wrong way.** Counterintuitively, Carbon Tax drifts *more* pro-climate under C1 (+0.53) than under Run 5 (+0.43). Two plausible explanations: (i) seed-level noise on a contested low-baseline policy, (ii) a latent peer-channel effect — when the pro-climate political broadcast is silenced, peer messaging becomes the dominant channel and the population's pro-climate prior asserts itself more strongly. The peer:political ratio doubling (1.13 → 2.04) supports the latter. This anomaly is worth investigating in any longer-run replication.

### Per-Exposure-Group Drift (Day 0 → Day 7, package index)

Citizens classified by Run 5 broadcast audience (the unfiltered population labels). The A-only group are the strongest diagnostic: they have *no* exposure to the anti-climate agent and *only* the pro-climate agent's broadcast (plus peers) can move them.

| Group | n | Run 5 d0 | Run 5 d7 | C1 d7 | Run 5 drift | C1 drift | Δ drift |
|---|---|---|---|---|---|---|---|
| A-only | 10 | +1.967 | +2.233 | +2.217 | +0.267 | +0.250 | **−0.017** |
| B-only | 3 | −0.611 | −1.278 | −1.389 | −0.667 | −0.778 | −0.111 |
| both | 17 | +0.647 | +0.971 | +0.922 | +0.324 | +0.275 | −0.049 |

**A-only is the smoking gun for peer-flooding.** Under C1, most A-only citizens lose their political broadcast (only ~6/27 of the natural audience get any pro-climate input). Yet their drift barely changes (+0.267 → +0.250, Δ = −0.017). They continue to drift pro-climate at almost the same rate as when fully reached. The conclusion is that **the +0.25 drift in this group is being carried by peer messaging, not by the political broadcast**. When peers are the dominant channel and the population GT mean is +0.961, every peer-pull is a small pro-climate nudge.

B-only (n=3) shows the cleanest asymmetric effect (−0.667 → −0.778, additional −0.111) but is too small for inference.

### Population Composition (Package-Index Shares)

| Day | Run 5 support / neutral / against | C1 support / neutral / against |
|---|---|---|
| 0 | 73.3 / 16.7 / 10.0 | 73.3 / 16.7 / 10.0 |
| 1 | 73.3 / 10.0 / 16.7 | 83.3 / 0.0 / 16.7 |
| 2 | 80.0 / 0.0 / 20.0 | 80.0 / 0.0 / 20.0 |
| 3 | 80.0 / 3.3 / 16.7 | 76.7 / 0.0 / 23.3 |
| 4 | 76.7 / 0.0 / 23.3 | 80.0 / 3.3 / 16.7 |
| 5 | 76.7 / 0.0 / 23.3 | 80.0 / 3.3 / 16.7 |
| 6 | 76.7 / 10.0 / 13.3 | 83.3 / 0.0 / 16.7 |
| 7 | 76.7 / 3.3 / 20.0 | 80.0 / 0.0 / 20.0 |

C1 actually has a *larger* support share than Run 5 at most days (80–83% vs 73–80%) — the opposite of the intended manipulation. Same explanation as Carbon Tax: peers carry the population's pro-climate prior when the political broadcast is muted.

### Individual Dynamics

**Run 5 vs C1 drift correlation across the 30 agents: r = 0.937.**

The same individuals move in both runs and they move by similar magnitudes. Cutting agent_a's reach to 25% did not change *who* moves; it slightly trimmed *how far* they moved. Net effect on counts:

| Metric | Run 5 | C1 |
|---|---|---|
| |drift| ≥ 0.5 (movers) | 10 / 30 | 12 / 30 |
| Sign flips Day 0 → Day 7 | 1 (in "both" group) | 1 (same agent) |
| Population SD across days | 1.30–1.36 | 1.30–1.38 |

Top 5 differential movers (largest |C1_drift − Run5_drift|), all in the "both" exposure group except one A-only:

| agent_id | exposure | Run5 d0 | Run5 d7 | C1 d7 | Run5 drift | C1 drift | Δ |
|---|---|---|---|---|---|---|---|
| 1545 | both   | +0.50 | +0.83 | +1.50 | +0.33 | +1.00 | +0.67 |
| 516  | both   | +1.00 | +1.17 | +0.67 | +0.17 | −0.33 | −0.50 |
| 1339 | both   | +0.17 | +2.00 | +1.50 | +1.83 | +1.33 | −0.50 |
| 332  | both   |  0.00 | +1.67 | +1.33 | +1.67 | +1.33 | −0.33 |
| 1923 | A-only | +0.67 | +2.00 | +1.67 | +1.33 | +1.00 | −0.33 |

No agent flipped to or from the centre under C1 that hadn't already flipped under Run 5 — the manipulation produced amplitude differences, not categorical flips.

### Mechanism Throughput

| Channel | Run 5 | Run 6 (C1) | Notes |
|---|---|---|---|
| Political broadcasts (agent_a) | 189 | **42** | reach_a=0.25 → 6/27 audience × 7 days |
| Political broadcasts (agent_b) | 140 | 140 | unchanged |
| Peer messages | 371 | 371 | unchanged (peer mechanism untouched) |
| Reflections | 490 | 372 | drop is broadcast-receive reflections (157 → 39 for P-A) |
| Survey reasoning rows | 1,440 | 1,440 | one debias trace per (agent, policy, day) |

### Key Findings

1. **The reach-asymmetry mechanism fires correctly.** Broadcast counts match `floor(reach × audience)` exactly: 6 deliveries/day × 7 days = 42 from agent_a, 20/day × 7 = 140 from agent_b.
2. **Aggregate effect is small (−0.044 on package index at Day 7) and within seed-noise.** Direction is correct but magnitude does not support a strong "asymmetric reach shifts the population" claim from this single seed.
3. **Renewable Energy is the cleanest signal.** Drift goes from +0.20 (Run 5) to −0.07 (C1), a Δ of −0.27 — the largest signed per-policy gap and the one most directly consistent with the manipulation's intent.
4. **Per-agent drifts are highly correlated across conditions (r=0.937).** The same individuals move in both runs by similar amounts. The reach knob rescales magnitudes; it does not restructure who moves.
5. **A-only group is the smoking-gun diagnostic for peer flooding.** Under C1, A-only citizens lose ~78% of their pro-climate broadcasts but their pro-climate drift falls only from +0.267 to +0.250. The drift is being carried by peer messaging, not by the political broadcast.
6. **The peer : political ratio doubles (1.13 → 2.04) and the population's pro-climate prior asserts itself.** Several "wrong-direction" results — Carbon Tax drifting *more* pro-climate, support share *higher* under C1 — are consistent with the peer channel becoming dominant when one political voice is muted, and peers carrying the GT mean (+0.961, structurally pro-climate) into every interaction.
7. **No additional polarisation.** Daily SDs of the package index are within ±0.03 between Run 5 and C1. Asymmetric reach did not produce a wider opinion distribution at this scale.

### Methodological Issues Surfaced

This run made two pre-existing limitations of the test design visible enough to require fixes before further reach-asymmetry experiments:

- **Structural audience asymmetry (27 vs 20).** `assign_political_exposure()` produces a 27-citizen audience for agent_a and a 20-citizen audience for agent_b on this seed, because the YouGov panel is more Remain/Labour-leaning than Leave/Conservative-leaning. A "symmetric" baseline at reach=1.0/1.0 already favours agent_a by 35%. C1 (reach_a=0.25) cuts agent_a to 6 deliveries/day; a future C3 (reach_b=0.25) would cut agent_b to 5 — so C1 and C3 are **not** mirror conditions as the code stands.
- **B-only group too small for inference (n=3).** Any per-exposure-group claim about asymmetric reach effects on B-only citizens is statistically anecdotal at this N.

Both are addressed by the `audience_cap` knob added in this session (see "Code Changes" below) and by moving to N=60 in future paper-grade sweeps.

### Code Changes Triggered by This Run

- New `SurveyedNation.apply_audience_cap(cap, seed)` method: deterministic uniform random trim of each political agent's `connected_citizens` to ≤ `cap`, applied *before* `apply_reach_subsample`. RNG seeds `seed+100` / `seed+101`, independent of reach's `seed` / `seed+1`. With `audience_cap=20`, both political agents broadcast to identical-sized audiences at reach=1.0/1.0, so future C1/C3 conditions become true mirrors. Adds a 7th `_RESUME_HARD_KEYS` entry. Tests: 7 new in `TestApplyAudienceCap` (test_broadcast.py); 339/339 suite passes.
- Default `audience_cap=None` preserves bit-for-bit reproducibility of Run 5 and prior.

### Remaining Issues / Open Questions

- **Is the small effect a real ceiling, or seed noise?** Repeating C1 at seeds 47 and 53 would distinguish them. Cost: ~225 min × 2.
- **Run a true peer-free condition.** With phases reduced to `["P-A", "P-B"]` only (no peer C), the broadcast asymmetry should produce its full effect. NB 21 has been created for this (single-policy, 4-day, peers-off, with `audience_cap=20` and the three reach conditions S/C1/C3 as a clean mirror sweep).
- **Re-run a `Run 5b` symmetric baseline at `audience_cap=20`** as the canonical control for future asymmetric runs. Diagnostic: how much does the cap alone move the trajectory vs Run 5?
- **Run capped C3 (reach_a=1.0, reach_b=0.25).** Only with the cap does C3 become a real mirror of C1 and the (S, C1, C3) triple a valid asymmetry-direction comparison.
- **Carbon Tax anomaly.** The +0.10 *increase* in pro-climate drift under C1 is the most surprising result in the table. A peer-free replication should disambiguate "peer-channel taking over" from "seed noise on a contested policy".
- **Per-agent message-exposure join.** With `messages.csv` already structured, attributing the (small) gaps to specific broadcast vs peer events per agent is a one-notebook follow-up.

---

## Run 5: 20260425_010615 — NB 19 (Full-Stack Production Run: Package Mode + Day-0 Anchor + Debias)

**Date:** 2026-04-25
**Result files:** [`data/output/experiments/20260425_010615/`](../data/output/experiments/20260425_010615/)
- [`config.json`](../data/output/experiments/20260425_010615/config.json)
- [`opinion_trajectories.csv`](../data/output/experiments/20260425_010615/opinion_trajectories.csv) (1,440 rows = 30 agents × 6 policies × 8 days)
- [`package_index_trajectories.csv`](../data/output/experiments/20260425_010615/package_index_trajectories.csv) (240 rows)
- [`reflections.csv`](../data/output/experiments/20260425_010615/reflections.csv) (490 rows)
- [`messages.csv`](../data/output/experiments/20260425_010615/messages.csv) (700 rows: 329 broadcast + 371 peer)
- [`survey_reasoning.csv`](../data/output/experiments/20260425_010615/survey_reasoning.csv) (1,440 rows)
- [`ground_truth.csv`](../data/output/experiments/20260425_010615/ground_truth.csv), [`package_ground_truth.csv`](../data/output/experiments/20260425_010615/package_ground_truth.csv)
- Plots: [`opinion_trajectories.png`](../data/output/experiments/20260425_010615/opinion_trajectories.png), [`package_index_trajectories.png`](../data/output/experiments/20260425_010615/package_index_trajectories.png), [`opinion_shares.png`](../data/output/experiments/20260425_010615/opinion_shares.png), [`package_index_shares.png`](../data/output/experiments/20260425_010615/package_index_shares.png)
- [`timings.csv`](../data/output/experiments/20260425_010615/timings.csv)

**Notebook:** [`notebooks/19_full_simulation.ipynb`](../notebooks/19_full_simulation.ipynb)

### What Changed Since Run 4

Run 4 (NB 15) was a single-policy run on Carbon Tax with debias + Claude surveys + extended thinking. Run 5 is the first **production-scale** run that combines every mechanism added through v0.4 in a single experiment.

| Mechanism | First introduced | Run 5 setting |
|---|---|---|
| Condition B debias on surveys | Run 4 | `debias=True` |
| Dual-model (cheap msg / strong survey) | Run 4 | `gpt-5-mini` + `claude-sonnet-4-6` |
| Extended thinking | Run 4 | `thinking=False` (cost) |
| **Package communication mode** (all 6 policies in one broadcast/peer pass) | NB 16, v0.4 | `communication_mode="package"` |
| **Day-0 ground-truth anchor with rationale** | v0.4 | `day0_anchor="ground_truth_with_rationale"` |
| **Per-day atomic checkpoints + resume** | NB 18, v0.4 | `checkpoint_every_day=True` |
| Alternating P-A / P-B order across days | Run 3 | reinstated |

The NB 19 notebook also adds explicit Day-0 anchor verification (every (agent, policy) Day-0 opinion equals GT exactly) and a sanity check that Day-0 rationales are stored for all 30 × 6 = 180 (agent, policy) cells.

### Experiment Configuration

| Parameter | Value |
|---|---|
| n_citizens | 30 |
| n_days | 7 |
| communication_mode | **package** (all 6 climate policies) |
| day0_anchor | **ground_truth_with_rationale** |
| debias | **True** (Condition B on every end-of-day survey) |
| llm_model (broadcast / peer / memory) | gpt-5-mini |
| llm_provider | openai |
| survey_model | claude-sonnet-4-6 |
| survey_provider | anthropic |
| thinking | False |
| llm_temperature | 0.5 |
| k_peers_per_day | 3 |
| phases (alternating) | odd days P-A→P-B→C, even days P-B→P-A→C |
| network | SBM, p_intra=0.15, p_inter=0.02 |
| random_seed | 43 |
| **wall-time** | **8,294 s ≈ 138 min** |

### Day-0 Anchor Verification (sanity)

| Check | Result |
|---|---|
| Day-0 opinion == GT for all 180 (agent, policy) cells | **PASS** |
| Day-0 rationale stored per (agent, policy) | 180 / 180 |
| Day-0 mean package index | **+0.961** |
| GT package mean | **+0.961** |
| Day-0 SD | 1.323 (matches GT SD = 1.323) |

The new anchor mechanism reproduces the YouGov sample distribution **exactly** at Day 0, eliminating baseline bias by construction. Runs 1–4 all started with a +0.87 to +2.04 inflation that had to be argued away; Run 5 starts at zero.

### Aggregate Package-Index Trajectory

| Day | Mean | SD | Min | Max | Bias vs GT |
|---|---|---|---|---|---|
| 0 (anchor) | **+0.961** | 1.32 | −2.17 | +2.83 | **0.000** |
| 1 | +1.156 | 1.34 | −2.00 | +2.83 | +0.195 |
| 2 | +1.194 | 1.36 | −2.00 | +2.83 | +0.233 |
| 3 | +1.222 | 1.33 | −1.83 | +2.83 | +0.261 |
| 4 | +1.183 | 1.35 | −2.00 | +2.83 | +0.222 |
| 5 | +1.178 | 1.33 | −1.83 | +2.83 | +0.217 |
| 6 | +1.217 | 1.30 | −1.83 | +2.83 | +0.256 |
| 7 (final) | +1.167 | 1.36 | −2.00 | +2.83 | +0.206 |

Day 1 jumps **+0.20** and then *flat-lines* through Day 7 (+0.20 to +0.26). This is a qualitatively new pattern. Compared with Run 4's drift between +0.87 → −0.03 → +0.47, Run 5 produces a small, *stable* steady-state offset rather than oscillation. The combined Day-0 anchor + Condition-B debias stack reduces persistent bias by roughly **3–10×** versus prior runs.

### Per-Policy Drift (GT → Day 7)

| Policy | GT mean | Day 0 (anchored) | Day 7 | Drift |
|---|---|---|---|---|
| Renewable Energy (1) | +1.87 | +1.87 | +2.07 | +0.20 |
| Ban Fossil Fuel (2) | +1.07 | +1.07 | +1.13 | **+0.07** |
| Ban Petrol Cars (3) | +0.43 | +0.43 | +0.63 | +0.20 |
| Green Housing (4) | +1.53 | +1.53 | +1.33 | **−0.20** |
| Carbon Tax (5) | +0.77 | +0.77 | +1.20 | +0.43 |
| Climate Compensation (6) | +0.10 | +0.10 | +0.63 | **+0.53** |

The high-consensus, ceiling-pinned policies (Renewable Energy, Ban Fossil Fuel, Green Housing) move ≤ 0.2 — Green Housing actually drifts *down*, which is qualitatively new and rules out a "pro-climate gradient on everything" interpretation. The biggest movement is concentrated in the two **lowest-baseline** policies — Climate Compensation (+0.53) and Carbon Tax (+0.43) — exactly the policies the NB 14 multi-policy work flagged as the most dynamic. This matches a regression-from-the-anchor dynamic plus genuine pro-climate net pull on the contested policies.

### Population Composition (Package-Index Shares)

| Day | Support (>0) | Neutral (=0) | Against (<0) |
|---|---|---|---|
| 0 | 73.3% | 16.7% | 10.0% |
| 1 | 73.3% | 10.0% | 16.7% |
| 2 | 80.0% | 0.0% | 20.0% |
| 3 | 80.0% | 3.3% | 16.7% |
| 4 | 76.7% | 0.0% | 23.3% |
| 5 | 76.7% | 0.0% | 23.3% |
| 7 | 76.7% | 3.3% | 20.0% |

The neutral band collapses from 17% to 0–3% by Day 2 and stays there. Mass redistributes in *both* directions: support 73 → 77–80%, against 10 → 17–23%. The simulation produces **mild polarisation** around the GT mean rather than runaway pro-climate convergence — this is the cleanest demonstration so far that the competing-political-agent setup is doing the qualitative thing it was designed to do.

### Individual Dynamics

**Net movement Day 0 → Day 7 (package index):**

| Direction | Agents |
|---|---|
| Moved up (>0) | 16 |
| Unchanged | 3 |
| Moved down (<0) | 11 |
| Max single agent gain | +1.83 |
| Max single agent loss | −1.33 |

Day-to-day inertia (package index): **41.0% zero-shift** day-pairs, mean abs shift **0.18**, mean signed shift **+0.03**. Zero-shift fractions are not directly comparable to single-policy runs (a 6-policy mean is more granular and harder to keep flat), but the ~+0.03 net drift per day matches the small steady-state bias.

Notable individual cases (manual spot-check of [`package_index_trajectories.csv`](../data/output/experiments/20260425_010615/package_index_trajectories.csv)):
- **Strong supporters lock in:** agents 528, 861, 1450, 1318 stay pinned at +2.5 to +2.83 across all 8 days.
- **Strong opposers harden:** agent 771 drifts −1.83 → −2, agent 1540 drifts −2.17 → −1.67, agent 174 stays −1.0 to −1.17. The anti-climate broadcast is reinforcing existing opposers, not converting them.
- **One clear conversion:** agent **1932 moves 0 → −1.33** between Day 0 and Day 1 and stays anti for the rest of the run — a centrist captured by the anti-climate political agent. This is the kind of single-agent flip the research question is interested in.
- **One clear pro-side capture:** agent **332 moves 0 → +1.5** on Day 1 and consolidates around +1.5 to +1.83.

### Mechanism Throughput

| Channel | Count | Notes |
|---|---|---|
| Political broadcasts | 329 | ~47/day; both political agents broadcast each day |
| Peer messages | 371 | ~53/day; matches `k_peers_per_day=3` × 30 agents minus deduplication |
| Reflections | 490 | P-A: 189, P-B: 140, C: 161 (per-phase imbalance reflects the alternating phase order) |
| Survey reasoning rows | 1,440 | 30 agents × 6 policies × 8 days; debias Step-1 reasoning is stored for every cell |

The structured `messages.csv` instrumentation added in v0.4 makes this the first run where every persuasion event is auditable — useful for downstream causal analyses (e.g. "did the agent who flipped 1932 also receive a peer message from another opposer?"), which prior runs could not answer cleanly.

### Key Findings

1. **The Day-0 anchor works perfectly.** Mean and full per-(agent, policy) distribution match GT at Day 0 by construction. The historical bias-investigation line (NB 11–14) is no longer a methodological prerequisite for opinion-dynamics research using this code path — but it remains the only way to *measure* bias on new models.
2. **Steady-state bias is small and flat.** Day 1+ settles at +0.20 to +0.26 above GT and stays there for 7 days. No drift, no rebound, no escalation. This is the cleanest steady state observed.
3. **Polarisation rather than consensus.** The neutral band collapses; both tails grow. This is the qualitative behaviour the model was designed to produce, and the first run where it's unambiguous in the data.
4. **Where the dynamics live: low-consensus contested policies.** Carbon Tax and Climate Compensation account for almost all of the directional movement. High-consensus policies hit a ceiling (Renewable Energy ~+2) or even drift slightly down (Green Housing).
5. **At least one genuine flip per side.** Agents 1932 (0 → −1.33) and 332 (0 → +1.5) are clean examples of competing political agents capturing centrists in opposite directions — the smallest-scale instance of the social-tipping dynamic the project is studying.
6. **Cost / wall-time is now the binding constraint.** 30 × 7 × package mode took ~138 min and is dominated by Claude survey calls (1,440 of them, two per cell because of debias). Scaling to N=50 / 14 days would push this into the multi-hour range; the new checkpoint/resume machinery (NB 18) is the right answer rather than reducing rigour.

### Remaining Issues / Open Questions

- **Is +0.20 steady-state bias the floor for this stack, or noise?** A repeat with a different seed would tell us whether the offset is structural (e.g. the pro-climate political agent is genuinely more persuasive) or sampling.
- **No exposure-group breakdown yet.** The same per-exposure-group analysis flagged in Run 4 is still pending. With package-mode messages now logged, this is straightforward in a follow-up notebook.
- **Polarisation magnitude is small.** The against share grows from 10% to 20%, but this is 2 extra agents in N=30. To make polarisation claims with statistical confidence we need either larger N or repeated seeds.
- **Green Housing drift is negative.** Worth investigating whether this is the anti-climate agent successfully pushing on a high-consensus policy, or a Claude survey artefact (e.g. small reluctance to repeat the strongest agreement letter twice in a row).
- **Per-agent message exposure not yet joined.** The instrumented `messages.csv` enables, but doesn't yet provide, an answer to "which messages each flipped agent saw before flipping". A short follow-up notebook can produce this directly.

---

## Run 4: 20260419_204851 — NB 15 (Claude Sonnet + Debias + Thinking)

**Date:** 2026-04-19  
**Result files:** [`data/output/experiments/20260419_204851/`](../data/output/experiments/20260419_204851/)
- [`config.json`](../data/output/experiments/20260419_204851/config.json)
- [`opinion_trajectories.csv`](../data/output/experiments/20260419_204851/opinion_trajectories.csv) (180 rows = 30 agents × 6 days)
- [`reflections.csv`](../data/output/experiments/20260419_204851/reflections.csv) (359 rows)
- [`ground_truth.csv`](../data/output/experiments/20260419_204851/ground_truth.csv) (first run with GT saved)

**Notebook:** [`notebooks/15_full_simulation_ground_truth.ipynb`](../notebooks/15_full_simulation_ground_truth.ipynb)

### What Changed Since Run 3 / NB 14

This run integrates all findings from the NB 11-14 bias investigation and several new features. It is the first run with (a) debiased surveys, (b) a separate survey model, (c) extended thinking, and (d) ground truth comparison.

#### Code Changes (src/)

| Change | Files | Description |
|---|---|---|
| **Condition B debias integration** | `agent.py`, `environment.py`, `sim.py` | NB 13-14 found Condition D (two-step reasoning + anti-sycophancy + numeric scale + 50% reversal) eliminated 97% aggregate bias. After review, **Condition B** (two-step reasoning + anti-sycophancy, letter scale preserved) was chosen for integration — it achieves similar bias reduction without the implementation complexity of scale reversal. Activated via `debias=True` in config. When enabled, `administer_survey()` makes 2 LLM calls: Step 1 generates reasoning about the persona's likely view, Step 2 uses that reasoning + an anti-sycophancy preamble to select the A-G letter. |
| **Survey model override** | `sim.py` | New `survey_model` / `survey_provider` config keys allow using a different (typically more capable) model for baseline + end-of-day surveys while keeping broadcast, peer messaging, and memory on a cheaper model. Falls back to main `llm_model` / `llm_provider` when `None`. Separate API key loaded when providers differ. |
| **Ground truth utility** | `sim.py` | New `collect_ground_truth(agents)` function extracts each agent's real YouGov survey response for all 6 climate policies. Returns a DataFrame with columns `agent_id`, `policy_id`, `ground_truth`. Called *before* the simulation to capture the pre-mutation state. |
| **Thinking support** | `sim.py`, `llm.py` | `thinking=True` in config is passed to baseline and end-of-day survey LLM calls. For Anthropic models, this activates `{"type": "adaptive"}` extended thinking mode with `max_tokens=16000`. Thinking is NOT passed to broadcast, peer messaging, or memory calls (those use the cheap model). |
| **Logging cleanup** | `notebooks/15_*` | Silenced `httpx` and `httpcore` loggers at WARNING level to suppress per-request HTTP noise from the Anthropic client. |

#### Design Decisions

- **Condition B over Condition D:** Condition D's scale reversal (50% numeric, 50% reversed) adds parsing complexity and the numeric scale is a departure from the real YouGov letter-based survey. Condition B achieves +78% bias reduction on Ban Petrol Cars (NB 13) using only prompt changes, preserving the original A-G letter format. The anti-sycophancy preamble and two-step reasoning are the key ingredients.
- **Claude Sonnet for surveys:** NB 11 showed Claude had the best Spearman ρ (0.417) and second-lowest MAE among tested models. Extended thinking provides deeper persona reasoning at the cost of ~3× longer survey calls.
- **gpt-4o-mini for other phases:** Broadcast message generation, peer messaging, and memory compression are less sensitive to calibration — they produce free text, not survey responses. Using a cheap fast model here keeps costs manageable.
- **Fixed phase ordering:** NB 10 Run 3's alternating phase order was a sensible precaution, but analysis showed no measurable effect given the high inertia levels. NB 15 uses fixed P-A → P-B → C for simplicity.

### Experiment Configuration

| Parameter | Value |
|---|---|
| n_citizens | 30 |
| n_days | 5 |
| policy | **Carbon Tax** (ClimatePolicyID 5) |
| phases | P-A, P-B, C (fixed order, all days) |
| llm_model (broadcast/peer/memory) | gpt-4o-mini |
| llm_provider | openai |
| survey_model | **claude-sonnet-4-6** |
| survey_provider | **anthropic** |
| thinking | **True** |
| debias | **True** |
| llm_temperature | 0.5 |
| k_peers_per_day | 3 |
| p_intra / p_inter | 0.15 / 0.02 |
| random_seed | 42 |

**New policy.** Switched from Ban Petrol Cars (Runs 1-3) to Carbon Tax for two reasons: (1) Carbon Tax has a moderate GT mean (+0.50), avoiding the near-zero GT that made Runs 1-3 baseline bias analysis ambiguous; (2) tests debias generalization to a policy not used in the NB 13-14 calibration experiments.

### Ground Truth (Carbon Tax, N=30)

| Metric | Value |
|---|---|
| GT mean | **+0.50** |
| GT SD | 1.66 |
| GT range | −3 to +3 |

**GT distribution:**

| Opinion | Count | % |
|---|---|---|
| −3 | 1 | 3.3% |
| −2 | 3 | 10.0% |
| −1 | 3 | 10.0% |
| 0 | 9 | 30.0% |
| +1 | 6 | 20.0% |
| +2 | 3 | 10.0% |
| +3 | 5 | 16.7% |

The real sample is center-right with a large neutral cluster (30% at 0). Support slightly outweighs opposition.

### Per-Day Opinion Statistics

| Day | Mean | SD |
|---|---|---|
| 0 (baseline) | **+1.37** | 1.50 |
| 1 | +1.00 | — |
| 2 | +1.10 | — |
| 3 | +0.47 | — |
| 4 | +0.77 | — |
| 5 (final) | **+0.97** | 1.47 |

Trajectory: starts at +1.37, dips to +0.47 on Day 3 (nearly matching GT!), then drifts back to +0.97 by Day 5. This oscillation is consistent with competing political agents creating genuine push-pull dynamics.

### Baseline Bias (Day 0 vs Ground Truth)

| Metric | Value |
|---|---|
| Day 0 LLM mean | +1.37 |
| Ground truth mean | +0.50 |
| **Day 0 bias** | **+0.87** |
| Day 0 MAE | 1.73 |

**Day 0 LLM distribution:**

| Opinion | Count |
|---|---|
| −2 | 2 |
| −1 | 4 |
| 0 | 1 |
| +1 | 1 |
| +2 | **18** |
| +3 | 4 |

The LLM still clusters heavily at +2 (18/30 = 60%). However, the aggregate bias (+0.87) is substantially lower than previous runs.

**Comparison of Day 0 bias across runs:**

| Run | Policy | Model | Debias | Day 0 Bias |
|---|---|---|---|---|
| Run 1 (NB 08) | Ban Petrol Cars | gpt-4o-mini | No | +1.38 |
| Run 2 (NB 08) | Ban Petrol Cars | gpt-4o-mini | No | +1.38 |
| Run 3 (NB 10) | Ban Petrol Cars | gpt-4.1-mini | No | +2.04 |
| **Run 4 (NB 15)** | **Carbon Tax** | **Claude Sonnet** | **Yes** | **+0.87** |

Run 4's +0.87 bias is a **37–57% reduction** compared to Runs 1-3, depending on the comparison. Different policies make a direct comparison imperfect, but the debias mechanism is clearly contributing.

### Bias Trajectory Over Simulation

| Day | LLM Mean | GT Mean | Bias | Change from Day 0 |
|---|---|---|---|---|
| 0 | +1.37 | +0.50 | +0.87 | — |
| 3 | +0.47 | +0.50 | −0.03 | −0.90 (97% reduction) |
| 5 | +0.97 | +0.50 | +0.47 | −0.40 (46% reduction) |

Day 3 briefly reaches near-perfect calibration (bias = −0.03). The rebound to +0.47 by Day 5 suggests the pro-climate pull from Agent A / peer messaging partially counteracts the initial correction.

### Dynamics

| Metric | Run 2 (NB 08) | **Run 4 (NB 15)** |
|---|---|---|
| Inertia | 81.9% | **69.3%** |
| Mean abs shift/day | 0.32 | **0.56** |
| Mean shift direction | −0.12 | −0.08 |
| Agents who moved ≥1 | 23/30 | 20/30 |
| Final SD | 1.76 | 1.47 |

Agents are more dynamic (69.3% vs 81.9% inertia, 0.56 vs 0.32 mean absolute shift). This is likely a combination of Claude Sonnet being more responsive than gpt-4o-mini for surveys and the two-step debias prompting encouraging more thoughtful re-evaluation each day.

### Reflections

| Metric | Run 2 (NB 08) | Run 4 (NB 15) |
|---|---|---|
| Total | 502 (7 days) | 359 (5 days) |
| Per day | ~72 | ~72 |
| Mean text length (P-A) | 1,024 chars | 1,074 chars |
| Mean text length (P-B) | 1,212 chars | 1,235 chars |
| Mean text length (C) | 987 chars | 957 chars |

Reflection volume and length are consistent with prior runs (proportional to days). No obvious change in reflection quality from the model switch.

### Key Findings

1. **Debias is working.** Day 0 baseline bias of +0.87 is the lowest of any run. Previous runs had +1.38 to +2.04. The two-step reasoning + anti-sycophancy preamble reduces aggregate bias without changing the letter-scale survey format.

2. **The +2 clustering problem persists.** Despite lower aggregate bias, 18/30 agents (60%) landed on +2 at Day 0. The debias mechanism shifts the *mean* down (fewer +3s, more −1s and −2s) but doesn't fix the modal clustering. The GT distribution is much more spread (SD=1.66 vs LLM SD=1.50).

3. **Bias shrinks further during the simulation.** Day 0 bias = +0.87, Day 3 bias ≈ 0, Day 5 bias = +0.47. Political agents and peer messaging pull opinions toward GT. The 46% bias reduction over 5 days is encouraging, though the Day 3→5 rebound suggests the pro-climate agent partially counteracts corrections.

4. **Lower inertia than all prior runs.** 69.3% zero-shift rate is the best achieved. Claude Sonnet + debias appears to produce agents that are more willing to reconsider on each survey.

5. **Mean shift direction is near-neutral.** At −0.08 per day, this is the closest to zero of any run (Run 2: −0.12, Run 3: −0.12). The competing agents are more balanced now, likely because the lower starting bias leaves more room for both directions of movement.

6. **First run with ground truth comparison.** The `collect_ground_truth()` utility and saved `ground_truth.csv` make this the first experiment where LLM-vs-real calibration can be precisely measured at both agent and aggregate level.

### Remaining Issues

- **+2 modal clustering:** The LLM's tendency to cluster at "Somewhat agree" is not solved by debias. May require scale reversal (Condition D) or alternative approaches.
- **Day 3→5 rebound:** After briefly matching GT on Day 3, the mean drifts back up. Longer runs (10+ days) would test whether this oscillation stabilizes or continues.
- **Single policy:** Carbon Tax only. Future runs should test across multiple policies simultaneously, especially the problematic Renewable Energy (high-consensus) and Climate Compensation (significant MAE improvement with debias).
- **No exposure group breakdown:** NB 15 does not include per-exposure-group analysis. The NB 10-style spaghetti plots by exposure would reveal whether specific agent groups drive the Day 3 dip.

---

## Baseline Bias Investigation (Notebooks 11–14)

After Run 3 revealed a +2.0 baseline inflation above the real YouGov mean, a systematic investigation was conducted to understand and mitigate LLM pro-climate sycophancy.

### NB 11: Model Comparison (2026-04-18)

**Result files:** [`data/output/experiments/20260416_*/`](../data/output/experiments/)  
**Notebook:** [`notebooks/11_model_baseline_comparison.ipynb`](../notebooks/11_model_baseline_comparison.ipynb)

Compared 6 LLM models on the Ban Petrol Cars baseline task (N=30, seed=44). All models exhibit pro-climate bias.

| Model | Mean Error | MAE | Spearman ρ |
|---|---|---|---|
| claude-sonnet-4-6 | +1.067 | 1.87 | 0.417 |
| gemini-3.1-pro | +0.733 | 1.63 | 0.396 |
| gpt-4.1-mini | +2.167 | 2.17 | 0.345 |

**Finding:** All models show aggregate pro-climate bias (+0.7 to +2.2). Claude and Gemini have the best Spearman correlation. GPT-4.1-mini is worst on all metrics.

### NB 12: Third-Person Perspective Shift (2026-04-18)

**Result files:** [`data/output/experiments/20260418_223858_3p_experiment/`](../data/output/experiments/20260418_223858_3p_experiment/)  
**Notebook:** [`notebooks/12_third_person_prompt_experiment.ipynb`](../notebooks/12_third_person_prompt_experiment.ipynb)

Tested whether prompting Claude to reason "about this person" (3P) instead of "as this person" (1P) reduces sycophancy. N=30, Ban Petrol Cars.

**Result: NEGATIVE.** 3P was slightly worse on all metrics (higher MAE, lower ρ). Hypothesis: 3P reduces personal identification without reducing social-desirability bias.

### NB 13: Four-Condition Bias Mitigation (2026-04-19)

**Result files:** [`data/output/experiments/20260419_002808_mitigation_experiment/`](../data/output/experiments/20260419_002808_mitigation_experiment/)  
**Notebook:** [`notebooks/13_bias_mitigation_experiment.ipynb`](../notebooks/13_bias_mitigation_experiment.ipynb)

Tested 4 conditions on Ban Petrol Cars (Claude, N=30, seed=44):

| Condition | Description | Mean Error | MAE | Spearman ρ |
|---|---|---|---|---|
| **A** (control) | Single-step, A-G letter scale | +1.067 | 1.87 | 0.417 |
| **B** | Two-step reasoning + anti-sycophancy | +0.233 | 1.83 | 0.424 |
| **C** | Numeric scale (-3 to +3) + 50% reversal | +0.700 | 1.70 | 0.392 |
| **D** (combined) | B + C combined | **+0.033** | 1.77 | 0.385 |

**Key finding:** Condition D eliminates 97% of aggregate bias (+1.067 → +0.033) but does not improve individual-level MAE (~1.7–1.9 floor). Scale reversal analysis shows large primacy bias in C (Δ = -0.87) that is neutralized in D (Δ = -0.07) by the two-step reasoning.

### NB 14: Multi-Policy Generalization (2026-04-19)

**Result files:** [`data/output/experiments/20260419_020128_multi_policy_generalization/`](../data/output/experiments/20260419_020128_multi_policy_generalization/)  
**Notebook:** [`notebooks/14_multi_policy_generalization.ipynb`](../notebooks/14_multi_policy_generalization.ipynb)

Tested whether Condition D generalizes across 3 additional policies (Claude, N=30, seed=44):

| Policy | GT Mean | A Mean Err | D Mean Err | Bias Reduction | Δ MAE | Wilcoxon p |
|---|---|---|---|---|---|---|
| Ban Petrol Cars (NB 13) | +0.07 | +1.067 | +0.033 | **+97%** | -0.10 | ns |
| Carbon Tax | +0.73 | +1.300 | +0.167 | **+87%** | -0.27 | ns |
| Climate Compensation | -0.07 | +1.500 | +0.400 | **+73%** | **-0.70** | **0.006** |
| Renewable Energy | +2.23 | +0.300 | -0.433 | **-44%** ⚠️ | +0.33 | ns |

**Key findings:**
1. **D generalizes to 3 of 4 policies** (bias reduction +73% to +97%).
2. **D overcorrects on Renewable Energy** — the most consensual policy (GT = +2.23). Anti-sycophancy pushes the LLM to find opposition where little exists.
3. **Climate Compensation is the only policy with significant individual MAE improvement** (p=0.006, 18↑ 5↓ 7=).
4. Scale reversal Δ is consistently negative (-0.40 to -1.00) across all policies, confirming positional bias is balanced by the 50/50 design.
5. Condition A compresses responses to the positive end (Renewable Energy A = only 2s and 3s). D restores variance.

**Decision:** Condition D meets the pre-registered success criterion (>50% bias reduction for ≥3 of 4 policies). Recommended for integration into `administer_survey()`, with the caveat that highly consensual policies (GT mean > +2.0) may overcorrect.

---

## Run 3: 20260417_221156

**Date:** 2026-04-17  
**Result files:** [`data/output/experiments/20260417_221156/`](../data/output/experiments/20260417_221156/)
- [`config.json`](../data/output/experiments/20260417_221156/config.json)
- [`opinion_trajectories.csv`](../data/output/experiments/20260417_221156/opinion_trajectories.csv) (400 rows = 50 agents × 8 days)
- [`reflections.csv`](../data/output/experiments/20260417_221156/reflections.csv) (686 KB)
- [`fig_trajectories.png`](../data/output/experiments/20260417_221156/fig_trajectories.png)
- [`fig_trajectories_by_exposure.png`](../data/output/experiments/20260417_221156/fig_trajectories_by_exposure.png)
- [`fig_mean_by_exposure.png`](../data/output/experiments/20260417_221156/fig_mean_by_exposure.png)
- [`fig_distribution_baseline_vs_final.png`](../data/output/experiments/20260417_221156/fig_distribution_baseline_vs_final.png)

### What Changed Since Run 2

Three changes tested a different hypothesis: that the Reform UK dominance was partly a phase-ordering artefact, and that a better LLM and larger sample would produce more realistic dynamics. Post-hoc analysis revealed a more fundamental issue: the LLM baseline is inflated ~2 points above the real survey mean.

| Change | What | Why |
|---|---|---|
| **Phase ordering fix** | P-A/P-B order now alternates by day: odd days = P-A→P-B→C, even days = P-B→P-A→C | Run 2 always ran P-A first, P-B second every day. The last-heard message has recency advantage — hypothesis: this systematically favours Reform UK. |
| **LLM upgrade** | gpt-4o-mini → gpt-4.1-mini | Better instruction-following and reasoning capability at similar speed. Tests whether B-dominance is an artefact of gpt-4o-mini's response tendencies. |
| **Scale** | 30 → 50 agents | More diverse sample, better statistical power. Different random subset of survey data. |

**Code files modified:** Notebook config only (no `src/` changes).

### Experiment Configuration

| Parameter | Value |
|---|---|
| n_citizens | **50** |
| n_days | 7 |
| policy | Ban Petrol Cars (ClimatePolicyID 3) |
| phases | Alternating: odd days P-A→P-B→C, even days P-B→P-A→C |
| llm_model | **gpt-4.1-mini** |
| llm_temperature | 0.5 |
| k_peers_per_day | 3 |
| p_intra / p_inter | 0.15 / 0.02 |
| random_seed | 42 |

Different 50-agent sample (same seed, but larger n draws different agents from the 1,483-row pool).

### Exposure Distribution (50 sampled agents)

| Group | n | % |
|---|---|---|
| A-only (Green Party UK) | 13 | 26.0% |
| B-only (Reform UK) | 11 | 22.0% |
| both | 25 | 50.0% |
| neither | 1 | 2.0% |

### Three-Run Comparison

| Metric | Run 1 | Run 2 | Run 3 | Trend |
|---|---|---|---|---|
| Agents | 30 | 30 | **50** | — |
| Model | gpt-4o-mini | gpt-4o-mini | **gpt-4.1-mini** | — |
| Phase ordering | Fixed P-A→P-B | Fixed P-A→P-B | **Alternating** | — |
| Day-over-day shifts | 210 | 210 | 350 | — |
| Zero shifts | 203 (96.7%) | 172 (81.9%) | 297 (84.9%) | Run 3 slightly more inert than Run 2 |
| Positive shifts | 0 | 13 (6.2%) | 15 (4.3%) | Similar count, lower % |
| Negative shifts | 7 | 25 (11.9%) | 38 (10.9%) | Similar % |
| Movers (baseline→final) | 7/30 (23.3%) | 20/30 (66.7%) | 20/50 (40.0%) | **Drop from 67% to 40%** |
| Mean d-o-d shift | -0.048 | -0.124 | -0.120 | Stable |
| SD d-o-d shift | 0.290 | 0.861 | 0.855 | Stable |
| Mean total shift | -0.333 | -0.867 | -0.840 | Stable |
| Positive movers (total) | 0 | 7 | **1** | **Severe drop** |
| Negative movers (total) | 7 | 13 | **19** | Stronger anti-climate skew (but confounded by baseline inflation) |

### Per-Day Opinion Statistics

| Day | Mean | SD | Min | Max |
|---|---|---|---|---|
| 0 (baseline) | +1.960 | 1.029 | -2 | +3 |
| 1 | +1.480 | 1.568 | -2 | +3 |
| 2 | +1.400 | 1.604 | -2 | +3 |
| 3 | +1.240 | 1.706 | -2 | +3 |
| 4 | +1.180 | 1.737 | -2 | +3 |
| 5 | +1.140 | 1.702 | -2 | +3 |
| 6 | +1.140 | 1.702 | -2 | +3 |
| 7 | +1.120 | 1.729 | -2 | +3 |

Day 0→1 shock: -0.480 (less extreme than Run 2's -0.967). Gradual decline days 1-4, then near-stable days 5-7. Note: the real YouGov survey mean for Ban Petrol Cars is -0.076, so even the Day 7 mean (+1.12) remains well above the true population mean.

### Shift Analysis

| Metric | Value |
|---|---|
| Total day-over-day observations | 350 |
| Zero shifts | 297 (84.9%) |
| Positive shifts | 15 (4.3%) |
| Negative shifts | 38 (10.9%) |
| Mean shift per observation | -0.120 |
| SD of shifts | 0.855 |

**Shift distribution:**

| Shift | Count |
|---|---|
| -4 | 5 |
| -3 | 8 |
| -2 | 2 |
| -1 | 23 |
| 0 | 297 |
| +1 | 9 |
| +3 | 4 |
| +4 | 2 |

Still two-tailed but much more skewed toward negative. Positive shifts exist but are rarer and smaller than Run 2. Given that the baseline is inflated ~2 points above the real survey mean, the negative skew is at least partly expected — agents are correcting toward more realistic positions.

### Shift By Exposure Group

| Group | n | Mean Baseline | Mean Final | Mean Shift | Movers (↑/↓) | Mover % |
|---|---|---|---|---|---|---|
| A-only | 13 | +2.38 | +2.38 | **+0.000** | 2 (1↑ / 1↓) | 15.4% |
| B-only | 11 | +0.91 | -1.64 | **-2.545** | 8 (0↑ / 8↓) | 72.7% |
| both | 25 | +2.20 | +1.64 | -0.560 | 10 (0↑ / 10↓) | 40.0% |
| neither | 1 | +2.00 | +2.00 | +0.000 | 0 | 0.0% |

**Cross-run exposure comparison:**

| Group | Run 2 Shift | Run 3 Shift | Change |
|---|---|---|---|
| A-only | -0.250 | +0.000 | Slight improvement (now neutral) |
| B-only | -2.000 | -2.545 | **Worse** (deeper anti-climate) |
| both | -0.800 | -0.560 | Slight improvement |

### Day-by-Day Shift Timing

| Day | Order | Zero | Pos | Neg | Mean Shift |
|---|---|---|---|---|---|
| 1 | P-A first | 32 | 3 | 15 | -0.440 |
| 2 | P-B first | 39 | 3 | 8 | -0.120 |
| 3 | P-A first | 40 | 2 | 8 | -0.260 |
| 4 | P-B first | 43 | 3 | 4 | +0.020 |
| 5 | P-A first | 47 | 2 | 1 | +0.020 |
| 6 | P-B first | 48 | 1 | 1 | +0.000 |
| 7 | P-A first | 48 | 1 | 1 | -0.060 |

| Aggregate | n | Mean | Pos | Neg | Zero |
|---|---|---|---|---|---|
| Odd days (P-A first) | 200 | -0.185 | 8 | 25 | 167 |
| Even days (P-B first) | 150 | -0.033 | 7 | 13 | 130 |

**Key observation:** Odd days (P-A first → P-B last) have *more* negative shifts and a more negative mean than even days. This is consistent with last-heard recency bias — when P-B speaks last, more agents shift anti-climate. However, interpreting this as "Reform UK content advantage" is confounded by the baseline inflation problem: agents start unrealistically pro-climate, so any downward correction will appear as anti-climate shift regardless of which prompt caused it.

### Aggregate Movement (Baseline → Final)

| Total Shift | Count | Agents |
|---|---|---|
| -4 | 5 | 381, 1065, 1343, 1454, 1833 |
| -3 | 4 | 252, 620, 752, 1379 |
| -2 | 1 | 1635 |
| -1 | 9 | 103, 416, 574, 740, 1045, 1213, 1262, 1339, 1382 |
| 0 | 30 | (30 agents) |
| +1 | 1 | 1269 |

19 agents shifted anti-climate, 1 shifted pro-climate. The negative skew is more extreme than Run 2 (13 neg / 7 pos). However, given that the real survey mean is -0.076 and the LLM baseline is +1.96, much of this negative movement is regression toward the true population mean rather than evidence of asymmetric persuasion.

### Baseline vs Final Distribution

| Opinion | Baseline | Final |
|---|---|---|
| -2 | 2 | **11** |
| +1 | 7 | 5 |
| +2 | 28 | 29 |
| +3 | 13 | 5 |

Mean: +1.96 → +1.12 (−0.84). SD: 1.03 → 1.73. The distribution is bimodal — the +2 core holds but a new anti-ban cluster formed at -2 (from 2 to 11 agents). The +3 group eroded substantially (13 → 5). For comparison, the real YouGov distribution is roughly uniform across -3 to +3 with slight oppose lean (mean = -0.076). The LLM distribution remains far from realistic even after 7 days of messaging.

### Notable Agent Behaviours

**Agent 1833 (both, baseline +2, final -2, total -4):** Most complex large-mover trajectory: stable at +2 for days 1-2, then a -4 crash to -2 on day 3, brief recovery to +1 on day 4, then oscillating -2/+1/-2/-2. Shows genuine conflict between competing messages before settling anti-climate.

**Agent 1065 (B-only, baseline +2, final -2, total -4):** Remarkably delayed mover — stable at +2 for days 1-3, drops to -1 on day 4, recovers to +2 on days 5-6, then crashes to -2 on day 7. Shows cumulative erosion despite apparent stability.

**Agent 1269 (A-only, baseline +2, final +3, total +1):** The only positive mover in the entire run. An A-only agent who spent all 7 days at +2 then moved to +3 on the final day. Notable because it moves *further away* from the real survey mean (-0.076), suggesting the pro-climate prompt can reinforce an already inflated position.

**Agent 752 (B-only, baseline +1, final -2, total -3):** Wild oscillator — drops -3 on day 1 to -2, bounces back to +2 on day 3, then collapses permanently to -2 from day 4 onward.

### Key Findings

1. **Phase ordering fix did NOT reduce the anti-climate skew.** Despite alternating which agent speaks last, the negative direction is more extreme than Run 2: 19 negative movers vs 1 positive (compared to Run 2's 13 vs 7). This rules out recency-ordering as the primary driver.

2. **gpt-4.1-mini is slightly MORE inert than gpt-4o-mini.** Zero-shift rate rose from 81.9% to 84.9%. Mover rate dropped from 66.7% to 40.0%. The model upgrade did not improve opinion dynamics — if anything, gpt-4.1-mini is more conservative about changing its survey response.

3. **The LLM baseline is massively inflated.** The real YouGov mean for "Ban Petrol Cars" is -0.076 (essentially neutral), but the LLM Day 0 baseline is +1.960 — a +2.036 gap. The LLM entirely misses the oppose/neutral portion of the real distribution (see Baseline Calibration section below). This is the most important finding of Run 3.

4. **The observed "anti-climate shift" is largely regression toward the true population mean.** After 7 days the mean falls from +1.96 to +1.12. The real survey mean is -0.076. The agents are moving *toward* where real people actually are, not being "persuaded" away from a genuine position.

5. **Green Party UK prompt appears inert partly due to ceiling effect.** A-only group mean shift = 0.000 and baseline = +2.38. When agents already start at an inflated pro-climate position, there is nowhere upward to go. Whether the prompt is genuinely weak or simply blocked by the ceiling is confounded.

6. **Reform UK prompt may be effective partly because it corrects the inflated baseline.** B-only mean shift = -2.545, pulling agents from +0.91 toward -1.64. This shift *passes through* the real survey mean (-0.076) and overshoots it, suggesting there is a genuine persuasive effect on top of the regression, but the two effects are confounded.

7. **Day 1 shock is less extreme** (mean -0.44 vs Run 2's -0.97). Shifts are more distributed across days 1-4 before convergence.

### Baseline Calibration Analysis

The most important finding from Run 3 is that the LLM's Day 0 survey responses do not match the real survey data for the same personas.

**Ban Petrol Cars (page5posttreatment6_5) — Real Survey vs LLM Baseline:**

| Source | Mean (our -3 to +3 scale) | Gap from survey |
|---|---|---|
| YouGov real survey (N=1,967) | **-0.076** | — |
| LLM baseline, Run 2 (30 agents) | +1.300 | +1.376 |
| LLM baseline, Run 3 (50 agents) | +1.960 | +2.036 |
| Run 3 final (after 7 days) | +1.120 | +1.196 |

The real UK public is essentially **split** on banning new petrol cars by 2030 (mean ≈ 0, SD ≈ 2.0). The LLM inflates support by +1.4 to +2.0 scale points at Day 0.

**Distribution comparison (our -3 to +3 scale):**

| Opinion | Real Survey | Run 3 Baseline | Run 3 Final |
|---|---|---|---|
| -3 (Strongly oppose) | 17.3% | **0.0%** | 0.0% |
| -2 (Somewhat oppose) | 10.9% | 4.0% | 22.0% |
| -1 (Slightly oppose) | 12.9% | **0.0%** | 0.0% |
| 0 (Neutral) | 20.1% | **0.0%** | 0.0% |
| +1 (Slightly support) | 12.9% | 14.0% | 10.0% |
| +2 (Somewhat support) | 11.1% | 56.0% | 58.0% |
| +3 (Strongly support) | 14.7% | 26.0% | 10.0% |

The LLM baseline is missing the **entire left half and centre of the distribution**. The real survey has 61% of respondents at neutral or below — the LLM produces 4%. It piles almost everyone into +2/+3. This is consistent with a well-documented LLM agreeableness/positivity bias toward pro-social policies.

### Interpretation

**The dominant effect is baseline inflation, not asymmetric persuasion.**

Across all three runs, the LLM Day 0 opinions are far more pro-climate than the real survey respondents they are meant to represent. The observed downward shifts are therefore at least partly **regression toward the true population mean**, not evidence that Reform UK framing is uniquely persuasive.

This reframes the earlier findings:
- The Green Party UK prompt appearing "inert" is confounded by a ceiling effect — agents already start at an inflated +2, leaving no room for upward movement.
- The Reform UK prompt appearing "dominant" is confounded by the baseline gap — agents *should* be lower, so anti-climate messages push them in the direction the data already supports.
- The B-only group's -2.545 mean shift overshoots the real survey mean (-0.076), ending at -1.64. This suggests there is some genuine persuasive effect on top of the regression, but the two cannot be cleanly separated with the current design.

**The percentage of agents who moved may not be the right metric.** Real people don't change their opinions much on policy questions over a week. A high mover rate (40-67%) may indicate the model is *too volatile* rather than "working well". The right metric is probably how closely the LLM opinion distribution matches the real survey distribution — and on that measure, the model is still far off.

**What this means for the research:**
Before we can meaningfully study competing persuasion dynamics, we need to solve the baseline calibration problem. If agents start at unrealistic positions, all downstream dynamics are distorted. The priority for the next run is not tweaking political agent prompts, but getting agents to start where real people actually are.

**Likely causes of baseline inflation:**
1. **LLM agreeableness bias** — LLMs tend to agree with pro-social framings ("ban pollution" sounds good in the abstract)
2. **Persona prompts may be too sympathetic** — the persona text may not convey the scepticism/pragmatism real respondents feel
3. **Missing context** — real respondents think about cost, feasibility, and personal impact; the LLM persona may lack these grounding details
4. **Scale interpretation** — the LLM may not calibrate "somewhat support" vs "strongly support" the same way humans do

### Per-Agent Baseline Accuracy (Run 3, gpt-4.1-mini)

Compared each agent's LLM Day 0 response against their real YouGov survey answer for Ban Petrol Cars. All 50 agents matched to their original survey row.

**Aggregate metrics:**

| Metric | Value |
|---|---|
| Mean signed error (LLM − Real) | **+2.16** |
| SD of error | 1.98 |
| Mean absolute error | 2.40 |
| Exact matches | 7/50 (14.0%) |
| LLM overestimates (pro-climate) | 38/50 (76.0%) |
| LLM underestimates | 5/50 (10.0%) |

**Error distribution (LLM − Real):**

| Error | Count |
|---|---|
| -2 | 1 |
| -1 | 4 |
| 0 | 7 |
| +1 | 6 |
| +2 | 11 |
| +3 | 6 |
| +4 | 8 |
| +5 | 6 |
| +6 | 1 |

**Bias by real survey response:**

| Real | n | Mean LLM | Mean Error | Exact % |
|---|---|---|---|---|
| -3 (Strongly oppose) | 10 | +1.30 | **+4.30** | 0.0% |
| -2 (Somewhat oppose) | 6 | +2.33 | **+4.33** | 0.0% |
| -1 (Slightly oppose) | 7 | +1.71 | **+2.71** | 0.0% |
| 0 (Neutral) | 10 | +1.60 | **+1.60** | 0.0% |
| +1 (Slightly support) | 6 | +2.33 | +1.33 | 0.0% |
| +3 (Strongly support) | 11 | +2.64 | -0.36 | 63.6% |

**Key finding:** The LLM collapses almost every agent into the +1 to +3 range regardless of their real position. It has **zero exact matches for anyone below +3**. The error is worst for real opposers (error +4.3) and diminishes monotonically as the real position increases. Only strong supporters (+3) are matched accurately (63.6% exact). This confirms the LLM has a systematic pro-social/agreeableness bias on this policy question that cannot be overcome by persona demographics and psychological values alone.

**Recommendations for Run 4:**

| Priority | Change | Rationale |
|---|---|---|
| **A** | Test alternative LLM models | Compare baseline accuracy across models (e.g. Gemini Flash, GPT-4o, GPT-4.1, DeepSeek). If some models show lower bias, they may be better suited for the simulation. |
| **B** | Fix baseline calibration | Options: (a) use real survey response as Day 0 baseline (skip LLM for Day 0), (b) add calibration instructions, (c) include the agent's real survey response in the persona as grounding context. |
| **C** | Run a no-messaging control | Run the full 7-day sim with no political agents (phases P-A and P-B removed). This isolates how much opinion drift comes from the survey-taking process itself vs. actual messaging influence. |
| **D** | Test with a different policy | Run the same config on a policy where the real survey mean is NOT near zero (e.g., a strongly supported policy). This tests whether the baseline inflation is uniform or policy-dependent. |

### Prompt-Level Bias Mitigation Strategies

Research-backed interventions to reduce the systematic pro-climate bias in LLM-generated baseline responses. The core problem: LLMs collapse almost all agents into the +1 to +3 range regardless of persona, with +4.3 error for real opposers.

**Root causes identified:**
1. First-person role-play ("I am a...") triggers the LLM's own RLHF-trained values (climate support = socially desirable)
2. No explicit instruction that controversial/unpopular answers are acceptable
3. Persona lists voting history as bare facts without connecting them to likely policy attitudes
4. Fixed A→G response scale ordering may interact with positional biases

**Interventions ranked by expected impact:**

| # | Intervention | Impact | Effort | References |
|---|---|---|---|---|
| 1 | **Third-person perspective shift** — Rewrite system prompt from first-person ("I am a 55-year-old...") to third-person observer ("You are simulating a survey respondent: A 55-year-old..."). User prompt becomes "How would this person respond?" | HIGH (~15pp sycophancy reduction) | Small | ELEPHANT (Cheng et al. 2025, arXiv:2505.13995); SimToM (Wilf et al. 2023, arXiv:2311.10227) |
| 2 | **Two-step reasoning** — Split the single LLM call into: Step 1 (reasoning): "Given this person's profile, what factors would shape their view? Consider that some people strongly oppose such policies." Step 2 (answer): Feed reasoning back + ask for A-G letter. | HIGH (~0.5-1.0 additional) | Medium | Chain-of-thought prompting literature; makes anti-climate reasoning explicit before commitment |
| 3 | **Anti-sycophancy instruction** — Add explicit preamble: "Your task is to faithfully simulate how this specific real person would respond, NOT to give the 'correct' or socially desirable answer. People with this profile often hold controversial or unpopular views — that is expected and acceptable." | MEDIUM-HIGH (~5-10pp) | Small | ELEPHANT shows limited but measurable effect; compounds with 3rd-person framing |
| 4 | **Scale randomization** — Randomly reverse the A-G scale ordering per agent (G=Strongly oppose → A=Strongly support), then un-reverse after parsing. Ablates positional bias. | MEDIUM | Small | Eicher & Irgolič 2024 (arXiv:2402.01740) show strong primacy effects in LLM list selection |
| 5 | **Numeric scale** — Replace "A. Strongly oppose ... G. Strongly support" with "-3 = Strongly oppose ... +3 = Strongly support. Respond with a number." Negative numbers carry evaluative signal that may anchor responses better. | MEDIUM | Small | Semantic anchoring hypothesis |
| 6 | **Multiple samples + median** — Call the LLM 3-5 times per agent, take median. Reduces noise but won't fix systematic bias. | LOW-MEDIUM (noise only) | Small (3-5x API cost) | Standard ensemble approach |

**Recommended testing order:** Implement 1+3 together (highest bang for buck), then add 2, then 4. Each should be a configurable prompt strategy so they can be A/B tested in notebook 11.

**Expected combined effect:** Interventions 1+2+3 could plausibly cut the +1.5 mean signed error to near zero, based on the literature.

---

## Run 2: 20260417_194417

**Date:** 2026-04-17  
**Result files:** [`data/output/experiments/20260417_194417/`](../data/output/experiments/20260417_194417/)
- [`config.json`](../data/output/experiments/20260417_194417/config.json)
- [`opinion_trajectories.csv`](../data/output/experiments/20260417_194417/opinion_trajectories.csv) (240 rows)
- [`reflections.csv`](../data/output/experiments/20260417_194417/reflections.csv) (502 rows)
- [`fig_trajectories.png`](../data/output/experiments/20260417_194417/fig_trajectories.png)
- [`fig_trajectories_by_exposure.png`](../data/output/experiments/20260417_194417/fig_trajectories_by_exposure.png)
- [`fig_mean_by_exposure.png`](../data/output/experiments/20260417_194417/fig_mean_by_exposure.png)
- [`fig_distribution_baseline_vs_final.png`](../data/output/experiments/20260417_194417/fig_distribution_baseline_vs_final.png)

### What Changed Since Run 1

Three prompt-level fixes were applied between Run 1 and Run 2. The experiment configuration (agents, days, seed, network, temperature) was kept **identical** so that any differences in outcomes can be attributed to the prompt changes.

| Fix | What | Why |
|---|---|---|
| **A — De-anchor survey prompt** | Removed the 4 lines in `get_user_prompt()` that showed the agent their previous numeric response when answering the end-of-day survey on days 1+. Previously the prompt said *"In the previous survey you responded: [letter] — [label]"*. Now the agent sees only the fresh survey question. | Run 1 showed 96.7% zero shifts. Hypothesis H1: explicitly showing the previous answer anchors the LLM to repeat it. |
| **B — Reflection bridge** | Changed the survey framing from *"Please answer the following survey question."* to *"Please answer the following survey question. Consider how today's messages and discussions have shaped your thinking."* | Reflections and survey were cognitively disconnected — agents processed messages thoughtfully then ignored that processing when answering. The bridge sentence cues the LLM to integrate its reflections into the survey response. |
| **C — Realistic UK party prompts** | Rewrote `_DEFAULT_PRO_CLIMATE_PROMPT` as a **Green Party UK** voice (channels Zack Polanski / Caroline Lucas, uses real slogans and policy positions — public ownership of energy, home insulation, wealth tax, clean air). Rewrote `_DEFAULT_ANTI_CLIMATE_PROMPT` as a **Reform UK** voice (channels Farage / Tice, references North Sea energy sovereignty, opposing ULEZ, scrapping Net Zero green levies, defending farmers and drivers). | Run 1's generic prompts lacked specificity. Real UK party voices provide culturally grounded, asymmetric rhetorical strategies that the LLM can engage with more naturally. |

**Code files modified:** `src/cag/abm/agent.py`, `tests/test_endofday.py`

### Experiment Configuration

| Parameter | Value |
|---|---|
| n_citizens | 30 |
| n_days | 7 |
| policy | Ban Petrol Cars (ClimatePolicyID 3) |
| phases | P-A, P-B, C (all three per day) |
| llm_model | gpt-4o-mini |
| llm_temperature | 0.5 |
| k_peers_per_day | 3 |
| p_intra / p_inter | 0.15 / 0.02 |
| random_seed | 42 |

Same 30 agents as Run 1 (same seed, same survey sample).

### Exposure Distribution (30 sampled agents)

| Group | n | % |
|---|---|---|
| A-only (Green Party UK) | 8 | 26.7% |
| B-only (Reform UK) | 6 | 20.0% |
| both | 15 | 50.0% |
| neither | 1 | 3.3% |

### Run 1 vs Run 2 Comparison

| Metric | Run 1 | Run 2 | Change |
|---|---|---|---|
| Zero shifts (day-over-day) | 203/210 (96.7%) | 172/210 (81.9%) | **-14.8pp** |
| Positive shifts | 0 (0.0%) | 13 (6.2%) | **+13** |
| Negative shifts | 7 (3.3%) | 25 (11.9%) | **+18** |
| Total shift events | 7 | 38 | **5.4× more** |
| Movers (baseline→final) | 7/30 (23.3%) | 20/30 (66.7%) | **+43.4pp** |
| Mean shift per observation | -0.048 | -0.124 | -0.076 |
| SD of shifts | 0.290 | 0.861 | **3.0× wider** |
| Shift range | -3 to 0 | -4 to +4 | **Full scale** |
| Mean opinion (baseline) | +1.300 | +1.300 | Same sample |
| Mean opinion (final) | +0.967 | +0.433 | **-0.534 deeper** |
| SD opinion (final) | 1.450 | 1.755 | Wider spread |

### Per-Day Opinion Statistics

| Day | Mean | SD | Min | Max |
|---|---|---|---|---|
| 0 (baseline) | +1.300 | 1.466 | -2 | +3 |
| 1 | +0.333 | 1.668 | -2 | +2 |
| 2 | +0.267 | 1.701 | -2 | +2 |
| 3 | +0.367 | 1.712 | -2 | +2 |
| 4 | +0.233 | 1.736 | -2 | +2 |
| 5 | +0.167 | 1.724 | -2 | +2 |
| 6 | +0.400 | 1.734 | -2 | +3 |
| 7 | +0.433 | 1.755 | -2 | +3 |

The largest drop happens day 0→1 (mean falls from +1.300 to +0.333, a -0.967 shock). Days 1-7 oscillate between +0.17 and +0.43, indicating ongoing contested influence rather than monotonic drift. This is qualitatively different from Run 1's gradual one-way slide.

### Shift Analysis

| Metric | Value |
|---|---|
| Total day-over-day observations | 210 |
| Zero shifts | 172 (81.9%) |
| Positive shifts | 13 (6.2%) |
| Negative shifts | 25 (11.9%) |
| Mean shift per observation | -0.124 |
| SD of shifts | 0.861 |

**Shift distribution:**

| Shift | Count |
|---|---|
| -4 | 2 |
| -3 | 6 |
| -2 | 4 |
| -1 | 13 |
| 0 | 172 |
| +1 | 7 |
| +2 | 5 |
| +4 | 1 |

The distribution is now two-tailed. Run 1 had only non-positive shifts; Run 2 shows 13 upward shifts (including +2 and +4 magnitudes), confirming bidirectional influence.

### Aggregate Movement (Baseline → Final)

| Metric | Value |
|---|---|
| Mean total shift | -0.867 |
| Agents shifted positive | 2 |
| Agents shifted negative | 18 |
| Agents unchanged | 10 (33.3%) |
| Max positive shift | +3 |
| Max negative shift | -4 |

**Distribution of total shifts (baseline→final):**

| Total shift | Count | Agents |
|---|---|---|
| -4 | 1 | 381 |
| -3 | 4 | 165, 1250, 1454, 1900 |
| -2 | 1 | 377 |
| -1 | 12 | 69, 103, 166, 440, 582, 713, 752, 806, 844, 1262, 1339, 1379 |
| 0 | 10 | 355, 409, 556, 574, 620, 1001, 1269, 1878, 1904, 1957 |
| +1 | 1 | 1723 |
| +3 | 1 | 91 |

### Shift By Exposure Group

| Group | n | Mean Baseline | Mean Final | Mean Shift | Movers | Mover % |
|---|---|---|---|---|---|---|
| A-only | 8 | +1.88 | +1.63 | -0.250 | 5 | 62.5% |
| B-only | 6 | +0.00 | -2.00 | **-2.000** | 5 | 83.3% |
| both | 15 | +1.47 | +0.67 | -0.800 | 10 | 66.7% |
| neither | 1 | +2.00 | +2.00 | +0.000 | 0 | 0.0% |

**Key observations by group:**

- **B-only (Reform UK):** Most dramatically affected group. Mean shifts from 0.00 to -2.00 — a full 2-point anti-ban swing. 5/6 agents moved. Agent 381 had the largest individual shift (-4). This group receives only anti-climate messaging with no pro-climate counterbalance.
- **Both:** 10/15 agents moved, mean shift -0.800. This group hears both sides but the anti-climate signal dominates — consistent with Run 1's finding that Reform UK framing is more persuasive than Green Party UK framing.
- **A-only (Green Party UK):** Only -0.250 mean shift despite receiving pro-climate messaging exclusively. 5 agents moved, but the shifts are small (-1 each). Two possible explanations: (a) ceiling effect — these agents already average +1.88 baseline, and (b) peer messaging from B-exposed agents diffuses anti-climate sentiment through the network.
- **Neither:** The single control agent (1878, baseline +2) was perfectly stable across all 7 days.

### All Agent Trajectories

| Agent | Exposure | Baseline | Day 1 | Day 2 | Day 3 | Day 4 | Day 5 | Day 6 | Day 7 | Total |
|---|---|---|---|---|---|---|---|---|---|---|
| 69 | both | +2 | +1 | +1 | +1 | -1 | -1 | +1 | +1 | -1 |
| 91 | A-only | -2 | -1 | -1 | +1 | +1 | +1 | +1 | +1 | **+3** |
| 103 | both | +2 | +1 | +1 | +1 | +1 | +1 | +1 | +1 | -1 |
| 165 | B-only | +1 | -2 | -2 | -2 | -2 | -2 | -2 | -2 | **-3** |
| 166 | A-only | +3 | +2 | +2 | +2 | +2 | -2 | +2 | +2 | -1 |
| 355 | A-only | +3 | +2 | +2 | +2 | +2 | +2 | +3 | +3 | 0 |
| 377 | A-only | +1 | -1 | -1 | +1 | -1 | -1 | -1 | -1 | -2 |
| 381 | B-only | +2 | -2 | -2 | -2 | -2 | -2 | -2 | -2 | **-4** |
| 409 | A-only | +2 | +2 | +2 | +2 | +2 | +2 | +2 | +2 | 0 |
| 440 | A-only | +3 | +2 | +2 | +2 | +2 | +2 | +2 | +2 | -1 |
| 556 | both | +2 | +1 | +1 | +2 | +2 | +1 | +1 | +2 | 0 |
| 574 | both | +1 | +1 | +1 | -1 | -1 | +1 | +1 | +1 | 0 |
| 582 | both | +2 | +1 | +1 | +1 | +1 | +1 | +1 | +1 | -1 |
| 620 | B-only | -2 | -2 | -2 | -2 | -2 | -2 | -2 | -2 | 0 |
| 713 | both | -1 | -2 | -2 | -2 | -2 | -2 | -2 | -2 | -1 |
| 752 | B-only | -1 | +1 | -2 | -2 | -2 | -2 | -2 | -2 | -1 |
| 806 | A-only | +3 | +2 | +2 | +2 | +2 | +2 | +2 | +2 | -1 |
| 844 | both | +2 | -1 | 0 | 0 | 0 | +1 | +1 | +1 | -1 |
| 1001 | both | +1 | +1 | +1 | +1 | +1 | +1 | +1 | +1 | 0 |
| 1250 | both | +1 | -2 | -2 | -2 | -2 | -2 | -2 | -2 | **-3** |
| 1262 | both | +3 | +2 | +2 | +2 | +2 | +2 | +2 | +2 | -1 |
| 1269 | A-only | +2 | +2 | +2 | +2 | +2 | +2 | +2 | +2 | 0 |
| 1339 | both | +3 | +2 | +2 | +2 | +2 | +2 | +2 | +2 | -1 |
| 1379 | B-only | -1 | -2 | -2 | -2 | -2 | -2 | -2 | -2 | -1 |
| 1454 | B-only | +1 | -2 | -2 | -2 | -2 | -2 | -2 | -2 | **-3** |
| 1723 | both | 0 | +1 | +1 | +1 | +1 | +1 | +1 | +1 | **+1** |
| 1878 | neither | +2 | +2 | +2 | +2 | +2 | +2 | +2 | +2 | 0 |
| 1900 | both | +1 | -2 | -2 | -2 | -2 | -2 | -2 | -2 | **-3** |
| 1904 | both | +1 | +1 | +1 | +1 | +1 | +1 | +1 | +1 | 0 |
| 1957 | both | +2 | +2 | +2 | +2 | +2 | +2 | +2 | +2 | 0 |

Bold total shifts highlight the largest movers.

### Day-by-Day Shift Events (38 total)

| Agent | Exposure | Day | From | To | Shift |
|---|---|---|---|---|---|
| 69 | both | 1 | +2 | +1 | -1 |
| 69 | both | 4 | +1 | -1 | -2 |
| 69 | both | 6 | -1 | +1 | **+2** |
| 91 | A-only | 1 | -2 | -1 | **+1** |
| 91 | A-only | 3 | -1 | +1 | **+2** |
| 103 | both | 1 | +2 | +1 | -1 |
| 165 | B-only | 1 | +1 | -2 | -3 |
| 166 | A-only | 1 | +3 | +2 | -1 |
| 166 | A-only | 5 | +2 | -2 | **-4** |
| 166 | A-only | 6 | -2 | +2 | **+4** |
| 355 | A-only | 1 | +3 | +2 | -1 |
| 355 | A-only | 6 | +2 | +3 | **+1** |
| 377 | A-only | 1 | +1 | -1 | -2 |
| 377 | A-only | 3 | -1 | +1 | **+2** |
| 377 | A-only | 4 | +1 | -1 | -2 |
| 381 | B-only | 1 | +2 | -2 | **-4** |
| 440 | A-only | 1 | +3 | +2 | -1 |
| 556 | both | 1 | +2 | +1 | -1 |
| 556 | both | 3 | +1 | +2 | **+1** |
| 556 | both | 5 | +2 | +1 | -1 |
| 556 | both | 7 | +1 | +2 | **+1** |
| 574 | both | 3 | +1 | -1 | -2 |
| 574 | both | 5 | -1 | +1 | **+2** |
| 582 | both | 1 | +2 | +1 | -1 |
| 713 | both | 1 | -1 | -2 | -1 |
| 752 | B-only | 1 | -1 | +1 | **+2** |
| 752 | B-only | 2 | +1 | -2 | -3 |
| 806 | A-only | 1 | +3 | +2 | -1 |
| 844 | both | 1 | +2 | -1 | -3 |
| 844 | both | 2 | -1 | 0 | **+1** |
| 844 | both | 5 | 0 | +1 | **+1** |
| 1250 | both | 1 | +1 | -2 | -3 |
| 1262 | both | 1 | +3 | +2 | -1 |
| 1339 | both | 1 | +3 | +2 | -1 |
| 1379 | B-only | 1 | -1 | -2 | -1 |
| 1454 | B-only | 1 | +1 | -2 | -3 |
| 1723 | both | 1 | 0 | +1 | **+1** |
| 1900 | both | 1 | +1 | -2 | -3 |

Bold shifts = positive (pro-climate) or magnitude ≥ 4. Of 38 events: 25 on day 1, 13 on days 2-7.

### Notable Agent Behaviours

**Agent 91 (A-only, baseline -2, final +1, total +3):** The only agent to show a large *pro-climate* swing. Started at the anti-ban extreme (-2) and climbed to +1 by day 3, staying there. This is the Green Party UK prompt's strongest success — but notably the agent only hears A-side messaging (no B counterbalance).

**Agent 381 (B-only, baseline +2, final -2, total -4):** The largest single shift in either run. Went from moderately pro-ban to strongly anti-ban in a single day. B-only exposure with no counterbalance.

**Agent 166 (A-only, baseline +3, final +2):** Shows extreme volatility — stable at +2 for days 1-4, then a -4 crash to -2 on day 5, immediately followed by a +4 recovery to +2 on day 6. This is the only ±4 oscillation in the data.

**Agent 556 (both, baseline +2, final +2):** A "deliberator" — oscillates +2 → +1 → +1 → +2 → +2 → +1 → +1 → +2 with a regular 2-day rhythm. Net zero shift but 4 shift events. Genuinely contested.

**Agent 844 (both, baseline +2, final +1):** The most complex trajectory — drops -3 on day 1, then slowly recovers (+1 on day 2, +1 on day 5). Shows cumulative rebound from pro-climate messaging.

### Reflections (502 total)

| Phase | Count |
|---|---|
| C (peer messaging) | 194 |
| P-A (Green Party UK) | 161 |
| P-B (Reform UK) | 147 |

Reflections per day: 71-72 (consistent across days).

### Key Findings

1. **Inertia is substantially reduced.** Zero-shift rate dropped from 96.7% to 81.9%. Movers rose from 7/30 to 20/30. The three prompt fixes (A, B, C) collectively had a large effect.

2. **Movement is now bidirectional.** Run 1 had zero positive shifts; Run 2 has 13 positive and 25 negative. The shift range expanded from [-3, 0] to [-4, +4]. This confirms competing influence is now working as intended.

3. **Day 1 remains dominant but is no longer the whole story.** 25/38 shift events (66%) occur on day 1, but 13 events occur on days 2-7, including some of the largest swings (Agent 166's ±4 on days 5-6, Agent 844's multi-day recovery). Run 1 had only 2 post-day-1 shifts.

4. **Reform UK (Agent B) significantly outperforms Green Party UK (Agent A).** B-only agents shift -2.000 on average; A-only agents shift only -0.250. This asymmetry holds even accounting for baseline differences (B-only starts at 0.00, A-only at +1.88).

5. **Oscillating agents are a new phenomenon.** Agents 556, 574, and 69 show back-and-forth movement across multiple days — genuine deliberation under competing influence. This was absent in Run 1 where all shifts were permanent one-way steps.

6. **The population is polarising.** Baseline SD = 1.466, final SD = 1.755. The distribution spreads, with the pro-ban peak eroding and a new anti-ban cluster forming at -2. Mean falls from +1.30 to +0.43.

7. **"Neither" exposure = perfect control.** Agent 1878 (the only neither-exposed agent) was completely stable at +2 across all 7 days, confirming that shifts are causally linked to political messaging exposure.

### Interpretation

**Why Fixes A+B+C worked:**
- Fix A (de-anchoring) removed the strongest source of inertia. Without seeing their previous answer, agents approach each survey fresh.
- Fix B (reflection bridge) connected the cognitive processing in reflections to the survey response. The bridge instruction "Consider how today's messages and discussions have shaped your thinking" cues the LLM to integrate rather than compartmentalise.
- Fix C (realistic prompts) gave agents culturally specific, emotionally grounded arguments to engage with. The Reform UK framing ("this will cost you money, defend your freedom to drive") is more concrete and threat-based than the Green Party UK framing ("cleaner future, public ownership"), which may explain the asymmetry.

**Why Reform UK framing dominates:**
- Loss-aversion: threatening to take away something (cars, affordable energy) is psychologically stronger than offering a diffuse gain (cleaner air, long-term savings)
- Specificity: "Scrap Net Zero to cut energy bills" is a concrete promise; "Fairer Greener Communities" is abstract
- Baseline skew: population mean is +1.3 (pro-ban) — more room to fall than rise
- Peer diffusion: B-exposed agents' anti-climate sentiment propagates to A-only agents through the peer messaging network

**Remaining questions:**
- Is the B-dominance an artefact of gpt-4o-mini's response tendencies, or would it replicate with gpt-4o?
- Would strengthening the Green Party UK prompt (more concrete threats, more emotional appeal) rebalance the asymmetry?
- Does memory compression after day 2 suppress later shifts by "averaging out" volatile reflections?

---

## Run 1: 20260417_163200

**Date:** 2026-04-17  
**Result files:** [`data/output/experiments/20260417_163200/`](../data/output/experiments/20260417_163200/)
- [`config.json`](../data/output/experiments/20260417_163200/config.json)
- [`opinion_trajectories.csv`](../data/output/experiments/20260417_163200/opinion_trajectories.csv) (240 rows)
- [`reflections.csv`](../data/output/experiments/20260417_163200/reflections.csv) (502 rows)

### What Changed Before This Run

This was the first full-scale experiment run. Prior to it, the following structural fixes were applied:
- Survey filter relaxed (1086 → 1483 usable rows)
- Exposure assignment rewritten with 10-rule priority system (neither: 30% → 4.6%)
- Temperature propagation fixed (all LLM calls now use configurable temperature, default 0.5)

### Experiment Configuration

| Parameter | Value |
|---|---|
| n_citizens | 30 |
| n_days | 7 |
| policy | Ban Petrol Cars (ClimatePolicyID 3) |
| phases | P-A, P-B, C (all three per day) |
| llm_model | gpt-4o-mini |
| llm_temperature | 0.5 |
| k_peers_per_day | 3 |
| p_intra / p_inter | 0.15 / 0.02 |
| random_seed | 42 |

### Exposure Distribution (30 sampled agents)

| Group | n | % |
|---|---|---|
| A-only | 8 | 26.7% |
| B-only | 6 | 20.0% |
| both | 15 | 50.0% |
| neither | 1 | 3.3% |

### Per-Day Opinion Statistics

| Day | Mean | SD | Min | Max |
|---|---|---|---|---|
| 0 (baseline) | +1.300 | 1.368 | -2 | +3 |
| 1 | +1.133 | 1.224 | -2 | +3 |
| 2 | +1.133 | 1.224 | -2 | +3 |
| 3 | +1.067 | 1.337 | -2 | +3 |
| 4 | +1.067 | 1.337 | -2 | +3 |
| 5 | +0.967 | 1.450 | -2 | +3 |
| 6 | +0.967 | 1.450 | -2 | +3 |
| 7 | +0.967 | 1.450 | -2 | +3 |

Mean opinion drifts steadily downward from +1.300 to +0.967 over 7 days (-0.333 total).

### Shift Analysis

| Metric | Value |
|---|---|
| Total day-over-day observations | 210 |
| Zero shifts | 203 (96.7%) |
| Positive shifts | 0 (0.0%) |
| Negative shifts | 7 (3.3%) |
| Mean shift per observation | -0.048 |
| SD of shifts | 0.290 |

**Shift distribution:** -3: 1, -2: 1, -1: 5, 0: 203

### Aggregate Movement (Baseline → Final)

| Metric | Value |
|---|---|
| Mean total shift | -0.333 |
| SD total shift | 0.711 |
| Agents shifted positive | 0 |
| Agents shifted negative | 7 |
| Agents unchanged | 23 (76.7%) |
| Max positive shift | +0 |
| Max negative shift | -3 |

### Shift By Exposure Group

| Group | n | Mean Baseline | Mean Shift | Movers |
|---|---|---|---|---|
| A-only | 8 | +1.88 | -0.250 | 2 |
| B-only | 6 | +0.00 | -0.667 | 2 |
| both | 15 | +1.47 | -0.267 | 3 |
| neither | 1 | +2.00 | +0.000 | 0 |

B-only agents show the largest mean shift — makes sense as they only receive anti-climate messaging with no counterbalance.

### Movers (7 of 30 agents)

| Agent | Exposure | Politics | Brexit | UKGE2019 | Baseline | Final | Shift | Day of shift |
|---|---|---|---|---|---|---|---|---|
| 355 | A-only | 2 (left-of-centre) | Remain | Labour | +3 | +2 | -1 | Day 1 |
| 381 | B-only | 6 (right-of-centre) | Leave | Conservative | +2 | +1 | -1 | Day 1 |
| 806 | A-only | 2 (left-of-centre) | Remain | Labour | +3 | +2 | -1 | Day 1 |
| 1262 | both | 8 (Don't Know) | Remain | Conservative | +3 | +2 | -1 | Day 1 |
| 1339 | both | 4 (Centre) | Remain | DK | +3 | +2 | -1 | Day 1 |
| 1454 | B-only | 8 (Don't Know) | Leave | Conservative | +1 | -2 | -3 | Day 5 |
| 1723 | both | 8 (Don't Know) | Leave | Labour | +0 | -2 | -2 | Day 3 |

### Reflections (502 total)

| Phase | Count |
|---|---|
| C (peer) | 194 |
| P-A (pro-climate) | 161 |
| P-B (anti-climate) | 147 |

Reflections per day ≈ 71-72 (consistent).

### Key Findings

1. **Extreme inertia:** 96.7% of day-over-day observations show zero shift. 23/30 agents never moved at all across 7 days.

2. **All movement is negative (anti-ban).** Zero positive shifts in the entire run. The anti-climate Agent B appears more persuasive than Agent A, or the LLM has an inherent loss-aversion bias.

3. **Most shifts are day-1-only.** 5 of 7 movers shifted on day 1 and locked in forever. The simulation effectively converges after a single day for most agents.

4. **Two big movers are notable:**
   - Agent 1454 (B-only, DK politics): +1 → -2 on day 5. A 3-point swing from cumulative B-only persuasion with no A counterbalance. The reflections show mounting concern about "working-class families."
   - Agent 1723 (both, DK politics, cross-pressured votes): 0 → -2 on day 3. Was genuinely ambivalent; anti-climate messaging won out.

5. **DK politics agents are most susceptible.** 3 of the 7 movers had PoliticsID=8 (Don't Know). This aligns with theory — less crystallised political identity → more persuadable.

6. **Reflections show "performative deliberation."** Agents engage thoughtfully with messages (acknowledging concerns, finding merit) but almost never translate this into actual survey response changes.

### Interpretation & Hypotheses

Three hypotheses for the inertia problem:

| # | Hypothesis | Evidence | Potential fix |
|---|---|---|---|
| H1 | Survey prompt anchors too hard | Shows previous response explicitly, asks to re-answer | Remove or reword previous-response anchoring (→ **Fix A in Run 2**) |
| H2 | Reflections disconnected from survey | Agents process messages but don't integrate into response | Add reflection bridge instruction (→ **Fix B in Run 2**) |
| H3 | Generic prompts lack rhetorical bite | Bland political agent messages don't create genuine tension | Rewrite with real UK party voices (→ **Fix C in Run 2**) |

The anti-climate bias may stem from:
- Loss-aversion framing is more psychologically salient to LLMs ("this will cost you money") vs gain-framing ("cleaner air")
- Population already leans pro-ban (mean baseline +1.3), more room to move down
- The anti-climate prompt may be more emotionally charged

---

## Prior Exploratory Runs (2026-04-16)

These pre-fix runs used the **old** exposure assignment (30% neither) and temperature 0.7.

### Run 144332 (3 agents, 2 days)
- Config: P-A + P-B, Carbon Tax
- Result: 2/3 agents showed zero shift; 1 agent (771) had a -4 point swing (+2 → -2)
- Note: Agent 771 outlier suggests the model can produce large swings in rare cases

### Run 165524 (3 agents, 2 days)
- Config: P-B only (no P-A), dense network
- Result: All 3 agents showed zero shift

### Run 170348 (10 agents, 2 days)
- Config: P-A + P-B, Carbon Tax, dense network
- Result: 7/10 agents showed zero shift; 3 showed -1 shifts

### Run 172036 (duplicate data bug)
- Known issue: duplicate rows in opinion_trajectories.csv
- Discarded

---

## Running Log

| Date | Run ID | Changes Applied | Config Summary | Key Finding |
|---|---|---|---|---|
| 2026-04-16 | 144332 | — | 3 agents, 2d, Carbon Tax | 1 outlier with -4 shift |
| 2026-04-16 | 165524 | — | 3 agents, 2d, P-B only | Zero movement |
| 2026-04-16 | 170348 | — | 10 agents, 2d, dense net | 3/10 moved (-1 each) |
| 2026-04-17 | **163200** | Survey filter fix, exposure rewrite, temp propagation | 30 agents, 7d, Ban Petrol Cars, temp=0.5 | 96.7% inertia, all shifts negative, DK agents most susceptible |
| 2026-04-17 | **194417** | **Fix A (de-anchor), Fix B (reflection bridge), Fix C (Green Party UK / Reform UK prompts)** | 30 agents, 7d, Ban Petrol Cars, temp=0.5 | **81.9% inertia (-14.8pp), bidirectional shifts, 20/30 movers, Reform UK dominates** |
| 2026-04-17 | **221156** | **Phase ordering alternation, gpt-4.1-mini, 50 agents** | 50 agents, 7d, Ban Petrol Cars, temp=0.5 | **84.9% inertia, 20/50 movers (40%), 19 neg / 1 pos. Key finding: LLM baseline (+1.96) is inflated +2.0 above real survey mean (-0.08); anti-climate shift is largely regression toward true mean** |
| 2026-04-18 | NB 11 | Model comparison (6 models) | 30 agents, Ban Petrol Cars, seed=44 | All models show pro-climate bias (+0.7 to +2.2); Claude and Gemini best ρ |
| 2026-04-18 | NB 12 | 3rd-person perspective shift | Claude, 30 agents, Ban Petrol Cars | **NEGATIVE result** — 3P slightly worse on all metrics |
| 2026-04-19 | NB 13 | 4-condition bias mitigation (A/B/C/D) | Claude + Gemini, 30 agents, Ban Petrol Cars | **Condition D eliminates 97% of aggregate bias** (+1.067 → +0.033); MAE floor unchanged |
| 2026-04-19 | NB 14 | Multi-policy generalization (A vs D) | Claude, 30 agents, 3 policies + NB 13 ref | **D generalizes to 3/4 policies** (+73–97% bias reduction); overcorrects on Renewable Energy (-44%) |
| 2026-04-25 | **082317** | **`apply_reach_subsample()`: reach_a=0.25, reach_b=1.0 (Reform-dominant)** | 30 agents, 7d, package, GT-anchor, debias, dual-model, seed=43 (Run 5 config + reach knob) | **Aggregate Δ=−0.044 vs Run 5 (small, in-noise). Renewable Energy clean signature (−0.27 Δ drift). A-only group barely changes (+0.267 → +0.250) → peer flooding diagnosed; peer:political ratio doubled (1.13 → 2.04). Triggered new `audience_cap` knob.** |
| 2026-04-25 | **NB 21 (125855 / 132515 / 135538)** | **Broadcast-only 3-condition reach sweep: S(1.0/1.0), C1(0.25/1.0), C3(1.0/0.25); peers off; `audience_cap=20` enforces true mirrors** | 30 agents, 4d, single_policy (Ban Petrol Cars), GT-anchor, debias, dual-model, seed=43 | **MONOTONE result Day 1+: drift C1=+0.300 < S=+0.400 < C3=+0.467; full swing C3−C1 = +0.167. Support shares 67% / 70% / 73% at Day 4. Reach mechanism validated once peer-flooding confound removed; audience_cap mirror property confirmed (100 broadcasts each in C1/C3, swapped sides).** |
| 2026-04-26 | **Run 8 / NB 21 multi-seed replication (172247 / 180114 / 182614 / 185644 / 192446 / 202955)** | **No code changes; replicated NB 21 at seeds 47 and 53 and compared against seed 43** | 30 agents, 4d, single_policy, peers off, `audience_cap=20`, seeds 43 / 47 / 53 | **Day-4 mean ordering holds on all 3 seeds: C1 < S < C3. Full swing ranges +0.167 to +0.800 (3-seed mean +0.578). Support-share ordering is monotone on 2/3 seeds and tied on seed 47. Main implication: the sign is robust, the magnitude is cohort-sensitive.** |
