# Roadmap

## Table of Contents
1. [Overview](#overview)
2. [1.0](#10)
3. [0.4 — Package Mode, Anchoring, Checkpointing, and Reach Controls](#04--package-mode-anchoring-checkpointing-and-reach-controls)
4. [0.3 — Bias Calibration & Validation](#03--bias-calibration--validation)
5. [0.2 — MVP: Competing-Minority Climate Opinion Model](#02--mvp-competing-minority-climate-opinion-model)


## Overview
This file outlines planned next steps and future goals.

Version 0.5 has not been planned yet. This roadmap therefore records the completed v0.4 surface and the longer-term 1.0 backlog only.

The full design specification lives in [docs/Model_Design.md](docs/Model_Design.md).
Detailed issue descriptions and acceptance criteria are in [docs/github_issues.md](docs/github_issues.md).
Experiment results and analysis are in [docs/result_report.md](docs/result_report.md).


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
- **Local LLM provider (v0.5, in flight)** — `provider="local"` for any OpenAI-compatible server (mlx-lm, Ollama, vLLM, sglang, llama.cpp). First end-to-end validated with Qwen3 8B 4-bit on M1 16 GB (NB 24). Next: 30–50-agent persona-fidelity rerun, then HPC scale-out with vLLM/sglang and async dispatch.
- Publication-ready analysis and visualisation pipeline
