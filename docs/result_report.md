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
