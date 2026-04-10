# Roadmap

## Table of Contents
1. [Overview](#overview)
2. [1.0](#10)
3. [0.2 — MVP: Competing-Minority Climate Opinion Model](#02--mvp-competing-minority-climate-opinion-model)


## Overview
This file outlines planned next steps and future goals.

The full design specification lives in [docs/Model_Design.md](docs/Model_Design.md).
Detailed issue descriptions and acceptance criteria are in [docs/github_issues.md](docs/github_issues.md).


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
| 8 | End-of-Day Survey + Clamping — re-survey with ±1/day opinion shift cap | ⬜ To do |

### Phase 4 — Memory
| # | Issue | Status |
|---|-------|--------|
| 9 | Tiered Memory Architecture — daily/weekly compression of reflections | ⬜ To do |

### Phase 5 — Loop & Output
| # | Issue | Status |
|---|-------|--------|
| 10 | Simulation Loop + Phase Ordering + Output — `SimulationConfig`, CSV, plots | ⬜ To do |

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


## 1.0
- Multi-day simulation campaigns with configurable parameters
- True peer-to-peer conversation (dialogue, not one-way messaging)
- Extended policy set beyond the initial 6 questions
- Calibration against longitudinal survey panel data
- Additional LLM providers and model comparisons
- Publication-ready analysis and visualisation pipeline
