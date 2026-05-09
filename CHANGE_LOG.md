# Change Log


## Table of Contents
- [Overview](#overview)
- [0.4](#04)
- [0.3](#03)
- [0.2](#02)
- [0.1](#01)


## Overview
Notable changes are to be documented in this file.


## [0.5]
- **Local LLM Provider** — new `provider="local"` branch in `cag.io.llm.send_chat`, routing to any OpenAI-compatible local server (mlx-lm, Ollama, vLLM, sglang, llama.cpp/llama-server, LM Studio). Substring-keyed `_MODEL_REGISTRY` auto-applies sampling presets and per-family quirks (Qwen3 `enable_thinking` toggle, DeepSeek-R1 reasoning defaults, Llama / Apertus / Mistral baselines). Unknown models work with bare defaults and a one-time INFO log.
- **Local-LLM SIM_CONFIG keys** — `local_base_url`, `local_extra_body`, `local_timeout_s` (all optional, with `CAG_LOCAL_BASE_URL` / `CAG_LOCAL_TIMEOUT_S` env-var fallbacks). Added to soft-warn list in `_check_resume_config_compatibility` for checkpoint reproducibility. `_resolve_runtime` calls `configure_local()` and `ping_local()` once at simulation start, so a missing or misconfigured local server fails fast with a remediation message instead of mid-run.
- **Empty-thinking truncation guard** — when a thinking-mode call returns empty content (reasoning budget exhausted), the local provider auto-retries once with thinking disabled and the non-thinking sampling preset, logging a WARNING.
- **`load_api_key("local")` short-circuit** — returns the `"not-needed"` sentinel without touching the CSV or environment, so `provider="local"` works on any machine without API-key plumbing.
- **Mixed-provider workflows** — cheap local broadcasts + high-fidelity cloud surveys are now a documented one-line config (`survey_provider="anthropic"` on top of `llm_provider="local"`). Wiring already supported it; v0.5 makes it explicit and tested.
- **`requirements-local.txt`** — new optional dependency file listing local-runtime extras (mlx-lm on Apple Silicon, vLLM on NVIDIA Linux, Ollama via binary install). Cloud-only users are unaffected.
- **Notebook 24** — first end-to-end local-LLM smoke test (Qwen3 8B 4-bit / mlx-lm / M1 16 GB / Ban Petrol Cars / 10 agents × 1 day). Headline: 0 errors, 46.6 min wall-time, reflections at 133-token median, Day-0 aggregate bias +0.50 (best on record). Full write-up in `docs/result_report.md`.
- **`docs/Local_LLM_Setup_Guide.md` rewritten to V3** — quickstart, alternative backends (mlx-lm / Ollama / vLLM / sglang / llama.cpp), model gallery (Qwen3 / Llama 3.x / Apertus / Mistral / DeepSeek-R1 distills with license + quant + RAM), `SIM_CONFIG` reference, registry-extension recipe, troubleshooting, HPC parallelism notes. V2 / V1 sections retained as legacy.
- **`tests/test_llm_local.py`** — 26 new tests covering dispatcher routing, base-URL / timeout resolution, `MODEL_REGISTRY` lookup, registry injection (Qwen3 thinking on/off, Llama no-extras, unknown model fallback), user `extra_body` override precedence, empty-thinking retry behaviour, and the `load_api_key("local")` short-circuit. Existing 339 tests unchanged.


## [0.4]
- **Package Communication Mode** — `communication_mode="package"` collapses the per-day broadcast and peer-messaging passes into a single phase covering all six climate policies; `compute_package_index()` averages the six responses into a −3..+3 index; new `package_index_trajectories` results DataFrame; `collect_package_ground_truth()` companion to `collect_ground_truth()`; `PACKAGE_SCOPE` sentinel propagated through `assemble_context()` and the survey path
- **Day-0 Ground-Truth Anchoring** — new `day0_anchor` config key with three modes (`llm_survey` | `ground_truth` | `ground_truth_with_rationale`); `seed_opinion_from_ground_truth()` and `seed_opinion_with_rationale()` on `SurveyedCitizen`; `_run_day0()` dispatcher in `sim.py`; `VALID_DAY0_ANCHORS` validation; aligns Day-0 cohort mean exactly with the YouGov sample mean so subsequent drift is attributable to simulation dynamics rather than baseline LLM bias
- **Memory Anchor Refactor** — removed the numeric "Your opinion trajectory so far: Day 0: C, Day 1: E, …" block from `assemble_context()` (strongest LLM self-consistency cue on prior survey answers); replaced with "Your earlier reasoning on these policies:" Day-0 rationale block via new `_build_day0_rationales()` helper; `opinion_history` unchanged at the data layer
- **Checkpoint + Resume** — `run_simulation()` now accepts `checkpoint_dir`, `resume`, and `checkpoint_every_day` parameters. With `checkpoint_every_day=True` a per-day CSV snapshot is written atomically (temp-file + `os.replace`) after each day's `manage_memory` step, capturing all four agent state fields plus `nation.message_log` and a `checkpoint_meta.json` fingerprint. With `resume=True` the run hydrates from the checkpoint, skips Day 0, and continues day numbering from `last_completed_day + 1`. Hard-fails on incompatible structural config (`n_citizens`, `random_seed`, `p_intra`, `p_inter`, `network_type`, `communication_mode`, `package_policies`, `day0_anchor`, agent ID set) and on a `cfg["days"][0:last_completed_day]` prefix mismatch (past days are immutable; future entries may be extended); warns on `llm_model`/`provider`/`debias`/`thinking`/`temperature` changes. `_load_checkpoint` normalises NaN cells to `None` (`df.where(pd.notna(df), None)`) and `_to_policy` early-returns `""` for NaN/None/empty inputs, preventing the literal string `'nan'` from poisoning `messages.csv` `policy_id` cells across multi-cycle resumes in package mode. `agent_ids` in `checkpoint_meta.json` are sorted by `str(...)` for stable on-disk fingerprints. Daily loop body extracted into `_run_one_day()`; `save_results` refactored to share `_write_all_csvs()` with the checkpoint writer (derived share CSVs are produced on every checkpoint as well, making the checkpoint dir drop-in usable as a result dir).
- **Broadcast Reach Controls** — new config knobs `reach_a` and `reach_b` plus `SurveyedNation.apply_reach_subsample()` allow deterministic subsampling of each political agent's broadcast audience before the run starts, enabling controlled asymmetric-reach experiments while preserving reproducibility under `random_seed`.
- **Audience Mirror Control** — new `audience_cap` config key plus `SurveyedNation.apply_audience_cap()` cap each political agent's audience before reach subsampling so symmetric and mirror conditions can be compared on equal-sized audiences; the cap is now part of the resume compatibility surface.
- **Notebooks 16–23** — package-mode, Day-0 anchoring, checkpoint/resume, production full-stack runs, reach-asymmetry pilots, broadcast-only mirror sweeps, Day-0 survey-path audits, and persona-signal evaluation notebooks are now part of the documented v0.4 workflow.
- **Result Documentation** — `docs/result_report.md` now covers the production package-mode run (Run 5 / NB 19), reach-asymmetry experiments (Runs 6–8 / NB 20–21), Day-0 survey-path accuracy audit (NB 22), and persona-signal validation work (NB 23).
- **340 tests collected (339 passed, 1 skipped)** across 15 test files


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

