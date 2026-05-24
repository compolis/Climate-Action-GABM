# Roadmap

## Table of Contents
1. [Overview](#overview)
2. [1.0](#10)
3. [0.6 — Canonical Defaults, Offline Political Messages, and Full-Stack Smoke Docs](#06--canonical-defaults-offline-political-messages-and-full-stack-smoke-docs)
4. [0.5 — Local LLM Provider, Prompt Unification, and Committed-Minority Audience Reframe](#05--local-llm-provider-prompt-unification-and-committed-minority-audience-reframe)
5. [0.4 — Package Mode, Anchoring, Checkpointing, and Reach Controls](#04--package-mode-anchoring-checkpointing-and-reach-controls)
6. [0.3 — Bias Calibration & Validation](#03--bias-calibration--validation)
7. [0.2 — MVP: Competing-Minority Climate Opinion Model](#02--mvp-competing-minority-climate-opinion-model)


## Overview
This file outlines planned next steps and future goals.

Version 0.5 was opened mid-stream rather than as a single planned sprint; this roadmap therefore records the completed v0.5 surface as it actually landed, alongside the earlier releases.

The full design specification lives in [docs/Model_Design.md](docs/Model_Design.md).
Detailed issue descriptions and acceptance criteria are in [docs/github_issues.md](docs/github_issues.md).
Experiment results and analysis are in [docs/result_report.md](docs/result_report.md).


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
- **Local LLM provider (v0.5, ✅ landed)** — `provider="local"` for any OpenAI-compatible server (mlx-lm, Ollama, vLLM, sglang, llama.cpp). First end-to-end validated with Qwen3 8B 4-bit on M1 16 GB (NB 24); integrated-provider parity confirmed in NB 25. Open work tracked in the v0.5 backlog above.
- Publication-ready analysis and visualisation pipeline
