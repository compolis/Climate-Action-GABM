# Roadmap

## Table of Contents
1. [Overview](#overview)
2. [1.0](#10)
3. [0.8 — Refactor Track: `sim.py` Split, v2 Memory Architecture, and Operational Polish](#08--refactor-track-simpy-split-v2-memory-architecture-and-operational-polish)
4. [0.7 — HPC-First Infrastructure, Audit-Trail Outputs, and Network Defence](#07--hpc-first-infrastructure-audit-trail-outputs-and-network-defence)
5. [0.6 — Canonical Defaults, Offline Political Messages, and Full-Stack Smoke Docs](#06--canonical-defaults-offline-political-messages-and-full-stack-smoke-docs)
6. [0.5 — Local LLM Provider, Prompt Unification, and Committed-Minority Audience Reframe](#05--local-llm-provider-prompt-unification-and-committed-minority-audience-reframe)
7. [0.4 — Package Mode, Anchoring, Checkpointing, and Reach Controls](#04--package-mode-anchoring-checkpointing-and-reach-controls)
8. [0.3 — Bias Calibration & Validation](#03--bias-calibration--validation)
9. [0.2 — MVP: Competing-Minority Climate Opinion Model](#02--mvp-competing-minority-climate-opinion-model)


## Overview
This file outlines planned next steps and future goals.

Version 0.5 was opened mid-stream rather than as a single planned sprint; this roadmap therefore records the completed v0.5 surface as it actually landed, alongside the earlier releases.

The full design specification lives in [docs/Model_Design.md](docs/Model_Design.md).
Detailed issue descriptions and acceptance criteria are in [docs/github_issues.md](docs/github_issues.md).
Experiment results and analysis are in [docs/result_report.md](docs/result_report.md).


## 0.8 — Refactor Track: `sim.py` Split, v2 Memory Architecture, and Operational Polish

v0.8 is a **refactor-track release**: it consolidates two structural overhauls (the `sim.py` modular split and the v2 tiered-memory architecture) plus a cluster of operational polish, with no `__version__` bump. The 2755-line `src/cag/abm/sim.py` is split into six focused modules, the in-context memory assembly is rewritten as an ordered six-section build with a `policy_id` vs `target_policy_id` scope split, the Day-0 anchor compression LLM call is removed, and a researcher-onboarding [docs/Code_Tour.md](docs/Code_Tour.md) is added.

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | `sim.py` modular split — [src/cag/abm/sim.py](src/cag/abm/sim.py) 2755 → 838 lines; five new modules ([src/cag/abm/network_repair.py](src/cag/abm/network_repair.py), [src/cag/io/aggregators.py](src/cag/io/aggregators.py), [src/cag/io/plots.py](src/cag/io/plots.py), [src/cag/io/results.py](src/cag/io/results.py), [src/cag/io/checkpoint.py](src/cag/io/checkpoint.py)) | ✅ Done |
| 2 | NB 32 bit-identical regression validation (deterministic outputs, 22 LLM-driven CSV schemas, distributional stats within gpt-5-mini @ T=0.5 noise) | ✅ Done |
| 3 | v2 tiered memory architecture — [src/cag/abm/agent.py](src/cag/abm/agent.py) `assemble_context()` rewritten as ordered six-section build (§1 persona + values, §2 Day-0 anchor, §3 daily summaries, §4 recent reflections, §5 own reasoning, §6 today-so-far) | ✅ Done |
| 4 | New `policy_id` vs `target_policy_id` scope split — context filter is independent of question scope; package-mode EOD survey now sees cross-policy reflections while anchored to the specific policy being asked | ✅ Done |
| 5 | Day-0 anchor compression LLM call removed — `compress_day0_anchor()`, `agent.day0_anchors` dict, post-`_run_day0` compression loop, `day0_anchors.csv` schema, and checkpoint hydration block all deleted; §2 now verbatim from `survey_reasoning[target_policy_id]` | ✅ Done |
| 6 | Dead `SIM_CONFIG["output_dir"]` key removed (now 33 keys); also stripped from `tests/test_checkpoint.py` and NB 32 parity assertion | ✅ Done |
| 7 | Network-type-aware `[peer]` config-log line — renders resolved `_resolve_network_params(cfg)` dict for Watts–Strogatz, Barabási–Albert, Erdős–Rényi, homophily-weighted (no more misleading SBM-only `p_intra` / `p_inter`) | ✅ Done |
| 8 | [docs/AIRE_Quickstart.md](docs/AIRE_Quickstart.md) §6 first-time-model-download callout (recommend `--time=06:00:00` on cold-cache HuggingFace downloads) | ✅ Done |
| 9 | New [docs/Code_Tour.md](docs/Code_Tour.md) — ~25-page researcher onboarding doc (audience + conventions, 30-min skim sequence, 15 file walkthroughs, 2 side-trips, 6-recipe cookbook, 11-term glossary, AIRE pre-flight checklist) | ✅ Done |
| 10 | NB 34 v2-memory smoke ([notebooks/34_memory_v2_smoke.ipynb](notebooks/34_memory_v2_smoke.ipynb)) — configured for local Qwen3-8B-4bit; full Day-0 deferred to AIRE for throughput | ✅ Done |
| 11 | Docs sweep — `CHANGE_LOG.md` [0.8] extension, `ROADMAP.md` 0.8 (this section), `DEVELOPMENT_HISTORY.md` 2026-06-23 entries, `Model_Design.md` §27 / §28 / §29, `README.md` status bump | ✅ Done |
| 12 | Test suite — `TestCompressDay0Anchor` removed; `TestSectionOrder` + `TestDay0AnchorSection` rewritten for verbatim/target-scoped path; suite **556 passed, 1 skipped, 21 subtests passed** (+18 from new coverage) | ✅ Done |
| 13 | No `__version__` bump — v0.8 is a refactor-only label; bump held until next behaviour-bearing release | ✅ Done |

**Current integration suite context:** 556 passed, 1 skipped, 21 subtests passed.

### v0.8 carry-forward backlog (toward 1.0)

- AIRE production smoke at n=30–100 to validate the v2 memory architecture end-to-end on a real LLM and a multi-day horizon (local Apple-Silicon throughput too low for in-laptop Day-0).
- Deep rewrite of [docs/Run_Output_Guide.md](docs/Run_Output_Guide.md) and [docs/Simulation_Configuration_Guide.md](docs/Simulation_Configuration_Guide.md) — carried from v0.7.
- Condition B 1P-debias bias re-measurement (NB 13 partial rerun, ~120 API calls) — carried from v0.5 / v0.6 / v0.7.
- 30–50-agent Qwen3 rerun for per-agent Spearman ρ stability — carried from v0.5 / v0.6 / v0.7.
- Async/parallel dispatch implementation from [docs/Model_Design.md](docs/Model_Design.md) §16 — carried from v0.7.
- Package-message v2 authoring (bespoke package-level copy replacing concatenated placeholders) — carried from v0.6 / v0.7.


## 0.7 — HPC-First Infrastructure, Audit-Trail Outputs, and Network Defence

v0.7 is a substantial single release that subsumes the previously-internal "v0.6" label (v0.6 was never tagged on `origin`, so the public ladder becomes 0.5 → 0.7). Four headline themes: (1) production-ready HPC/AIRE infrastructure with thin sbatch launchers, preset bundles, and a sweep submitter; (2) a critical NB-31 package-mode survey-context fix that was silently burying every cross-bucket persuasion signal since v0.4; (3) a major outputs-and-instrumentation expansion taking the saved run bundle from 17 → 29 artefacts with a monotonic `sim_step` counter, per-event agent timeline, and full survey-prompt audit; (4) a 3-layer network connectivity defence with literature-grounded SBM defaults so disjoint peer networks can no longer corrupt opinion dynamics silently.

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | AIRE / HPC infrastructure — [scripts/aire/run.sh](scripts/aire/run.sh), [scripts/aire/sweep.sh](scripts/aire/sweep.sh), [scripts/aire/sweeps/r14_v2.txt](scripts/aire/sweeps/r14_v2.txt) | ✅ Done |
| 2 | Preset bundles in new [src/cag/presets.py](src/cag/presets.py) (`smoke`, `r14_canonical`) with CLI composition layer | ✅ Done |
| 3 | New [docs/AIRE_HPC_repo_primer.md](docs/AIRE_HPC_repo_primer.md) and [docs/AIRE_Quickstart.md](docs/AIRE_Quickstart.md) | ✅ Done |
| 4 | [src/cag/\_\_main\_\_.py](src/cag/__main__.py) full argparse coverage for every `SIM_CONFIG` knob; `--preset`, `--list-presets`, `--dry-run` | ✅ Done |
| 5 | NB-31 package-mode survey-context fix (`PACKAGE_SCOPE` plumbed through `administer_survey()` / `run_end_of_day_survey()`); Run-14 v2 measured +0.667 Day-5 gap-widening vs +0.053 pre-fix (12.6× amplification) | ✅ Done |
| 6 | `k_peers=0` short-circuit in peer messaging; ~240 LLM calls saved per r14-style run | ✅ Done |
| 7 | Per-day checkpointing default-on in CLI (`--checkpoint-every-day` default `True`; `--no-checkpoint-every-day` opts out) | ✅ Done |
| 8 | Outputs expansion Phase 1 — `collect_agent_attributes` + cached `_affinity_score_a/b`; `agent_attributes.csv` to checkpoints + final | ✅ Done |
| 9 | Outputs expansion Phase 2 — bucket-stratified CSVs (`package_index_by_bucket`, `opinion_shares_by_bucket`, `day0_vs_dayN_shifts`) | ✅ Done |
| 10 | Outputs expansion Phase 3 — bucket plots (`plot_package_index_by_bucket`, `plot_opinion_shares_by_bucket`, `plot_gap_widening`) | ✅ Done |
| 11 | Outputs expansion Phase 4 — `build_calibration_table` + `plot_calibration_by_policy`; `build_message_flow`; `_safe_network_snapshot` → `network_snapshot.json` + `plot_network_graph` | ✅ Done |
| 12 | Outputs expansion Phase 5 — `survey_assembled_context` capture per (agent, day, policy); `build_agent_timeline` long-format with 9 event types and stratified sampling; final-output only via `_CHECKPOINT_SKIP_KEYS` | ✅ Done |
| 13 | Monotonic `nation._sim_step` counter wired through every event-logging site; `sim_step` column on 5 existing CSVs | ✅ Done |
| 14 | Network connectivity 3-layer defence — Layer 1 adaptive small-N bump, Layer 2 deterministic auto-repair, Layer 3 visibility log + `auto_connected_edges` field in `network_diagnostics.json` | ✅ Done |
| 15 | New SBM `p_inter` default 0.02 → 0.05 (Bakshy/Halberstam-Knight ~25% cross-cutting); ER `p` default 0.05 → 0.10 | ✅ Done |
| 16 | Empirical connectivity sweep in [scripts/estimate_connectivity_threshold.py](scripts/estimate_connectivity_threshold.py) | ✅ Done |
| 17 | Three new notebooks — [NB 30](notebooks/30_surgical_survey_replay.ipynb) (surgical replay), [NB 31](notebooks/31_package_mode_fix_validation.ipynb) (fix validation), [NB 32](notebooks/32_v06_outputs_smoke.ipynb) (outputs smoke) | ✅ Done |
| 18 | Test suite — new [tests/test_timeline_and_outputs.py](tests/test_timeline_and_outputs.py) (30); +13 connectivity tests in [tests/test_networks.py](tests/test_networks.py); `k_peers=0` + CLI-checkpoint tests; suite at **538 / 1 skipped** (was 432) | ✅ Done |
| 19 | `__version__` bulk-bumped to 0.7.0 across 18 source modules; retires the 0.2.0 / 0.3.0 / 0.5.0 / 0.6.0 / 1.0.0 inconsistency | ✅ Done |
| 20 | Docs sweep — `CHANGE_LOG.md` [0.7], `ROADMAP.md` 0.7, `DEVELOPMENT_HISTORY.md`, `Model_Design.md` §22–§26, `USER_GUIDE.md` v0.7 + HPC pointer, `README.md` status bump | ✅ Done |

**Current integration suite context:** 538 passed, 1 skipped.

### v0.7 carry-forward backlog (toward 1.0)

- Deep rewrite of [docs/Run_Output_Guide.md](docs/Run_Output_Guide.md) and [docs/Simulation_Configuration_Guide.md](docs/Simulation_Configuration_Guide.md) to cover the 12 new outputs and 2 new SIM_CONFIG keys (`timeline_sample_size`, `timeline_sample_agent_ids`)
- Condition B 1P-debias bias re-measurement (NB 13 partial rerun, ~120 API calls) — carried from v0.5/v0.6
- 30–50-agent Qwen3 rerun for per-agent Spearman ρ stability — carried from v0.5/v0.6
- Async/parallel dispatch implementation from [docs/Model_Design.md](docs/Model_Design.md) §16
- Package-message v2 authoring (replace concatenated placeholders with bespoke package-level copy) — carried from v0.6
- Production AIRE run at n=50–100 to validate v0.7 outputs + connectivity defence under load and bucket-asymmetric persuasion under the new SBM defaults


## 0.6 — Canonical Defaults, Offline Political Messages, and Full-Stack Smoke Docs

v0.6 consolidates the runtime path that was previously spread across incremental v0.5 work: canonical SIM defaults are now explicit in `sim.py`, offline political messages are first-class with strict startup validation, and the full-stack smoke acceptance flow is documented through NB28/NB29 and the new simulation configuration guide.

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | Canonical default profile in `SIM_CONFIG` (`n_citizens=100`, package alternating day plan, `local` Qwen3 default, `debias=True`, `day0_anchor=ground_truth_with_rationale`, offline political messages) | ✅ Done |
| 2 | Offline political-message subsystem (`src/cag/abm/political_messages.py`, `data/political_messages/messages_v1.csv`, `data/political_messages/sources_v1.csv`) | ✅ Done |
| 3 | Strict startup validation of required offline message cells; explicit `political_message_source` mode checks | ✅ Done |
| 4 | Broadcast provenance surfaced in outputs (`political_message_id` in `messages.csv`) | ✅ Done |
| 5 | Resume hard-key expansion for message-source consistency (`political_message_source`, `political_message_set`) | ✅ Done |
| 6 | Test harness alignment for local-provider startup mocks (`tests/conftest.py`) and default-shifted sim tests | ✅ Done |
| 7 | New message-pool test coverage (`tests/test_political_messages.py`) | ✅ Done |
| 8 | NB28 offline-message smoke notebook | ✅ Done |
| 9 | NB29 canonical full-stack smoke notebook | ✅ Done |
| 10 | `docs/Simulation_Configuration_Guide.md` (supervisor brief + developer config matrix) | ✅ Done |
| 11 | Runtime wording/default corrections in docs (YouGov April 2024 dataset context; current default population 100) | ✅ Done |

**Current integration suite context:** 465 passed, 1 skipped (latest full-run state during v0.6 consolidation).

### v0.6 carry-forward backlog (toward 1.0)

- Condition B bias re-measurement on the unified 1P chain (NB13 partial rerun).
- 30–50-agent Qwen3 rerun and seed-sweep stability checks.
- Async/parallel dispatch implementation from `Model_Design.md` §16.
- Package-message v2 authoring (replace concatenated placeholders with bespoke package-level copy).
- Source `__version__` alignment and release-tag cleanup (explicitly deferred from v0.6 docs pass).


## 0.5 — Local LLM Provider, Prompt Unification, and Committed-Minority Audience Reframe

A mid-stream release line: a first-class `provider="local"` branch in `cag.io.llm` (any OpenAI-compatible server), an end-to-end audit of every citizen-side prompt for consistency, and the v0.5 committed-minority audience reframe replacing the vote-only `priority_chain` rule with a configurable `rule_affinity_rank` mode driven by named target presets. Notebooks 24–27 cover local-LLM smoke + integrated parity, the demo run referenced in the prompt audit, and the affinity-exposure sanity check; experiment write-ups are appended to `docs/result_report.md`.

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | Local-LLM provider (`provider="local"`, `_MODEL_REGISTRY` for Qwen3 / Llama / Apertus / Mistral / DeepSeek-R1; `configure_local()` / `ping_local()`; empty-thinking retry guard; `load_api_key("local")` short-circuit) | ✅ Done |
| 2 | Local-LLM `SIM_CONFIG` keys (`local_base_url`, `local_extra_body`, `local_timeout_s`) + `_resolve_runtime` integration + `_RESUME_SOFT_KEYS` entries | ✅ Done |
| 3 | NB 24 — first end-to-end local-LLM smoke (Qwen3 8B 4-bit, M1 16 GB, Ban Petrol Cars) | ✅ Done |
| 4 | NB 25 — integrated-provider parity (bit-for-bit identical metrics vs NB 24 monkey-patch) | ✅ Done |
| 5 | Per-day broadcast-frequency sugar (`broadcasts_a` / `broadcasts_b` / `peer` / `interleave` / `a_first` keys; `make_phases()`; `_resolve_day_phases()`) | ✅ Done |
| 6 | Prompt audit and unification — every citizen-side prompt brought into consistent 1P framing; `get_persona()` canonical merge; `SURVEY_SHORT_LABELS`; reflection-bullet cleanup; `compress_memories` rewrite; `Prompts_and_Personas_Guide_v2.md` | ✅ Done |
| 7 | Committed-minority audience reframe (`rule_affinity_rank` mode, target presets `committed_minority_symmetric` / `committed_minority_uk_2024` / `legacy_v05`, weight presets `balanced` / `vote_dominant` / `values_dominant`) | ✅ Done |
| 8 | NB 27 — affinity-exposure sanity check on full YouGov pool (N = 1483); all four validation gates pass | ✅ Done |
| 9 | `_safe_int` GABM-attribute bugfix + `TestSafeInt` regression class | ✅ Done |
| 10 | `rule_affinity_logistic` mode removed (systematic ±18 pp target miss on anti-correlated A/B scores) | ✅ Done |

**432 tests passing, 1 skipped across 16 test files.**

### v0.5 backlog (carried into 1.0 unless taken up sooner)

- Condition B bias re-measurement on the new 1P debias chain (NB 13 partial rerun, ~120 API calls)
- 30–50-agent Qwen3 rerun to resolve per-agent persona ρ ≈ 0 question from NB 24/25
- Qwen3 14B 4-bit / 4B 2507 / 32B on HPC
- Async/parallel dispatch (§16 of `Model_Design.md`)
- End-to-end simulation run exercising the committed-minority audience reframe (Run 9 / NB 28)
- README current-status table + `__version__` bump across source modules


## 0.4 — Package Mode, Anchoring, Checkpointing, and Reach Controls

Post-v0.3 work expanded into a broader v0.4 release line: the six-policy
package mode, Day-0 grounding against the real YouGov cohort, prompt-memory
cleanup, atomic checkpoint/resume for long runs, and reach-control knobs used
to test asymmetric political influence. The same release cycle also produced
the current notebook / experiment stack (NB16–23) and the corresponding
analysis written up in `docs/result_report.md`.

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | Package communication mode (`communication_mode="package"`, `compute_package_index()`, `package_index_trajectories`, `collect_package_ground_truth()`, `PACKAGE_SCOPE`) | ✅ Done |
| 2 | Day-0 ground-truth anchoring (`day0_anchor` config: `llm_survey` / `ground_truth` / `ground_truth_with_rationale`; `seed_opinion_from_ground_truth()`, `seed_opinion_with_rationale()`, `_run_day0()` dispatcher) | ✅ Done |
| 3 | Memory anchor refactor — numeric Day-0..N trajectory removed from `assemble_context()`, replaced with Day-0 rationale block via `_build_day0_rationales()` | ✅ Done |
| 4 | Checkpoint + resume (`checkpoint_dir`, `checkpoint_every_day`, `resume`, atomic CSV/JSON writes, config compatibility checks) | ✅ Done |
| 5 | Reach subsampling (`reach_a`, `reach_b`, `apply_reach_subsample()`) for asymmetric political-broadcast experiments | ✅ Done |
| 6 | Audience mirror control (`audience_cap`, `apply_audience_cap()`) to equalise political-agent audience sizes before reach subsampling | ✅ Done |
| 7 | NB16–18 — package mode, anchoring, and checkpoint/resume smoke tests | ✅ Done |
| 8 | NB19–21 — production package-mode run and reach-asymmetry studies | ✅ Done |
| 9 | NB22–23 — Day-0 survey-path audit and persona-signal evaluation | ✅ Done |

**340 tests collected; 339 passing and 1 skipped across 15 test files.**


## 0.3 — Bias Calibration & Validation

Post-MVP work investigating and mitigating LLM baseline bias, adding multi-provider
support, and establishing ground truth comparison tooling. Research documented in
notebooks 11–15 and `docs/result_report.md`.

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | Baseline bias investigation — 6-model comparison (NB 11) | ✅ Done |
| 2 | Third-person prompt experiment — sycophancy reduction test (NB 12) | ✅ Done |
| 3 | 4-condition bias mitigation experiment (NB 13) | ✅ Done |
| 4 | Multi-policy generalization of Condition D (NB 14) | ✅ Done |
| 5 | Condition B debias integration into `administer_survey()` | ✅ Done |
| 6 | Survey model override — `survey_model` / `survey_provider` config | ✅ Done |
| 7 | Anthropic provider support in `send_chat()` | ✅ Done |
| 8 | Extended thinking support (`thinking=True`) | ✅ Done |
| 9 | Ground truth utility — `collect_ground_truth()` in `sim.py` | ✅ Done |
| 10 | Experiment Runs 1–4 documented in `docs/result_report.md` | ✅ Done |

**276 tests passing across 15 test files.**


## 0.2 — MVP: Competing-Minority Climate Opinion Model

A 10-issue sprint delivering an end-to-end simulation of citizen opinion dynamics
under competing political messaging. Citizens are initialised from YouGov survey
data, placed in a stochastic-block-model network, exposed to political broadcasts,
exchange peer messages, and re-surveyed daily.

### Phase 1 — Foundation
| # | Issue | Status |
|---|-------|--------|
| 1 | Climate Policy Opinion System — 6 policy questions, response scales, clamping | ✅ Done |
| 2 | LLM Chat Integration — `send_chat()` wrapper for OpenAI / Gemini | ✅ Done |

### Phase 2 — Agents & Network
| # | Issue | Status |
|---|-------|--------|
| 3 | Baseline Survey Administration (Day 0) — persona-driven LLM survey | ✅ Done |
| 4 | Political Agent Class — fixed-stance persuasive communicators | ✅ Done |
| 5 | Network + Political Exposure — SBM graph, exposure assignment from voting history | ✅ Done |

### Phase 3 — Simulation Phases
| # | Issue | Status |
|---|-------|--------|
| 6 | Political Broadcast (Phases P-A, P-B) — broadcast → reflection cycle | ✅ Done |
| 7 | Peer Messaging (Phase C) — simultaneous neighbour exchange | ✅ Done |
| 8 | End-of-Day Survey + Clamping — re-survey with ±1/day opinion shift cap | ✅ Done |

### Phase 4 — Memory
| # | Issue | Status |
|---|-------|--------|
| 9 | Tiered Memory Architecture — daily/weekly compression of reflections | ✅ Done |

### Phase 5 — Loop & Output
| # | Issue | Status |
|---|-------|--------|
| 10 | Simulation Loop + Phase Ordering + Output — `SimulationConfig`, CSV, plots | ✅ Done |

### Dependency Graph
```
Issues 1, 2  (independent)
    ├── Issue 3  (depends on 1, 2)
    ├── Issue 4  (depends on 1, 2)
    │       └── Issue 5  (depends on 4)
    │               ├── Issue 6  (depends on 3, 4, 5)
    │               │       ├── Issue 7  (depends on 5, 6)
    │               │       └── Issue 9  (depends on 6)
    │               └── Issue 8  (depends on 3, 6, 7)
    └── Issue 10  (depends on all)
```

**All 10 issues complete. 226 tests passing across 14 test files.**


## 1.0
- Longer simulation campaigns (10+ days) to study equilibrium and oscillation
- Larger-N and multi-seed reach-asymmetry sweeps
- Per-exposure-group analysis tooling and visualisation
- True peer-to-peer conversation (dialogue, not one-way messaging)
- Dynamic network rewiring based on opinion distance
- Calibration against longitudinal survey panel data
- Parallelisation of agent-local LLM calls
- Additional LLM providers and model comparisons
- **Local LLM provider (v0.5, ✅ landed)** — `provider="local"` for any OpenAI-compatible server (mlx-lm, Ollama, vLLM, sglang, llama.cpp). First end-to-end validated with Qwen3 8B 4-bit on M1 16 GB (NB 24); integrated-provider parity confirmed in NB 25.
- **HPC-first infrastructure (v0.7, ✅ landed)** — AIRE / SLURM thin sbatch launchers, sweep submitter, preset bundles, full CLI argparse coverage. End-to-end Run-14 v2 production run completed on AIRE.
- **Audit-trail outputs (v0.7, ✅ landed)** — 29 saved artefacts (was 17) including bucket-stratified CSVs, per-agent timeline, calibration table, message flow, network snapshot, and full survey-prompt audit. Catalogues every event with monotonic `sim_step`. Open work: deep rewrites of [docs/Run_Output_Guide.md](docs/Run_Output_Guide.md) / [docs/Simulation_Configuration_Guide.md](docs/Simulation_Configuration_Guide.md) tracked in v0.7 carry-forward.
- **Network connectivity defence (v0.7, ✅ landed)** — 3-layer adaptive bump / auto-repair / visibility log; literature-grounded SBM `p_inter=0.05` (Bakshy 2015, Halberstam-Knight 2016).
- Publication-ready analysis and visualisation pipeline
