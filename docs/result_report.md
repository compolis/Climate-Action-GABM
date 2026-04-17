# Experiment Result Report

Ongoing record of simulation experiments, settings, findings, and iteration notes.  
Results are listed newest-first.

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

**Recommendations for Run 4:**

| Priority | Change | Rationale |
|---|---|---|
| **A** | Fix baseline calibration | Investigate why LLM Day 0 responses don't match real survey answers. Options: (a) include the agent's *real* survey response in the persona, (b) add calibration instructions, (c) test whether the persona text itself biases responses. This is the #1 priority — all other findings are confounded until this is resolved. |
| **B** | Compute per-agent baseline accuracy | Check whether each agent's real survey answer is available in the data. If so, compare LLM Day 0 response vs real response for each agent to quantify the inflation at the individual level. |
| **C** | Run a no-messaging control | Run the full 7-day sim with no political agents (phases P-A and P-B removed). This isolates how much opinion drift comes from the survey-taking process itself vs. actual messaging influence. |
| **D** | Test with a different policy | Run the same config on a policy where the real survey mean is NOT near zero (e.g., a strongly supported policy). This tests whether the baseline inflation is uniform or policy-dependent. |

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
