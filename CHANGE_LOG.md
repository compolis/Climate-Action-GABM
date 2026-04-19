# Change Log


## Table of Contents
- [Overview](#overview)
- [0.3](#03)
- [0.2](#02)
- [0.1](#01)


## Overview
Notable changes are to be documented in this file.


## [0.3]
- **Baseline Bias Investigation** (NB 11–14) — 6-model comparison showed all LLMs exhibit pro-climate bias (+0.7 to +2.2); third-person prompting was ineffective; 4-condition experiment found Condition D eliminates 97% aggregate bias; multi-policy generalization confirmed for 3 of 4 policies
- **Condition B Debias Integration** — two-step reasoning + anti-sycophancy preamble in `administer_survey()`, activated via `debias=True` config key; preserves original A–G letter scale while reducing aggregate bias by 37–57%
- **Survey Model Override** — `survey_model` / `survey_provider` config keys allow a separate (typically more capable) LLM for baseline and end-of-day surveys while keeping broadcast, peer messaging, and memory on a cheaper model
- **Anthropic Provider Support** — Claude models in `send_chat()` via the `anthropic` library; provider auto-detection from config
- **Extended Thinking Support** — `thinking=True` config key activates adaptive extended thinking for Anthropic models (`max_tokens=16000`)
- **Ground Truth Utility** — `collect_ground_truth()` in `sim.py` extracts each agent's real YouGov survey response for all 6 policies; saved as `ground_truth.csv`
- **Experiment Runs 1–4** — documented in `docs/result_report.md` with per-run configuration, ground truth comparison, bias trajectories, dynamics metrics, and reflections analysis
- **7 new notebooks** (09–15): YouGov EDA, experiment runner, model comparison, 3P prompt, bias mitigation, multi-policy generalization, full simulation + ground truth
- **276 tests** across 15 test files


## [0.2]
- **Climate Policy Opinion System** — 6 policy questions (`ClimatePolicyID`), 7-point response scale, `clamp_opinion_shift()`, shared constants in `opinion.py`
- **LLM Chat Integration** — `send_chat()` wrapper supporting OpenAI and Gemini, `load_api_key()` from CSV, `parse_letter_response()` for survey answers
- **Baseline Survey Administration** — `SurveyedCitizen` class with persona generation, system prompt, and Day 0 LLM-driven survey (`administer_survey()`, `run_baseline()`)
- **Political Agent Class** — `PoliticalAgent` with fixed stance and `generate_message()` for persuasive broadcast content
- **Network + Political Exposure** — `SurveyedNation` with stochastic block model network, exposure assignment from Brexit/UKGE2019 voting history
- **Political Broadcast Phases** — `run_political_broadcast()` implementing Phase P-A / P-B broadcast → citizen reflection cycle
- **Peer Messaging Phase** — `run_peer_messaging()` with simultaneous update: generate all messages first, then deliver and reflect
- **End-of-Day Survey + Clamping** — `administer_survey()` with day-context prompt, `clamp_opinion_shift()` enforcing ±1 per day maximum shift
- **Tiered Memory Architecture** — `assemble_context()`, `compress_daily_memory()`, `compress_weekly_memory()` with configurable intervals and persona reinforcement
- **Simulation Loop + Output** — `run_simulation()` in `sim.py`, `SIM_CONFIG` defaults, CSV/JSON export, panel plot utility in `output.py`
- **8 demo notebooks** (01–08) covering each simulation component
- **226 tests** across 14 test files

## [0.1]
- README.md
- DEVELOPMENT_HISTORY.md
- CHANGE_LOG.md
- ROADMAP.md
- CODE_OF_CONDUCT.md
- DEV_GUIDE.md
- DEV_QUICKSTART.md
- USER_GUIDE.md
- CONTRIBUTORS
- LICENSE
- Makefile
- requirements.txt
- requirements-dev.txt
- docs
- tests
- scripts
- src/cag
- Simple ABM runs.

## Pre-versioning
- Exploratory code in modules and sandbox directories

