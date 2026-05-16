# Development History


## Table of Contents
- [Overview](#overview)
- [GitHub Copilot](#github-copilot)
- [Contributors](#contributors)
- [Development Timeline](#development-timeline)


## Overview
This document summarises the development of Climate-Action-GABM, including key decisions, milestones, and collaborative experiences. A summary of changes is provided in the [Change Log](CHANGE_LOG.md).


## GitHub Copilot
[GitHub Copilot](https://github.com/features/copilot) has been used to help automate release and cleanup tasks, develop document, test and formulate code.


## Contributors
See [CONTRIBUTORS].


## Development Timeline
- [2026-05-16] v0.5 — Prompt audit and unification. Every citizen-side LLM prompt in `src/cag/abm/agent.py` brought into consistent first-person framing (debias chain and Day-0 rationale prompts flipped from 2P/3P mix); end-of-day surveys (vanilla and debias Step 1) now explicitly reference the in-context memory; `get_persona()` is now the canonical merged-persona public method (old `get_persona` / `get_narrative` renamed to private `_build_demographics_text` / `_build_values_text`); end-of-context reminder line renamed to `"Remember who you are:"`; new `SURVEY_SHORT_LABELS` dict fixes the Day-0 rationale bullet truncation bug; `[P-A]/[P-B]/[C]` tags stripped from in-context reflection bullets (CSV audit trail unchanged); `compress_memories` extended from 2 → 4–5 phase-agnostic first-person sentences; single-policy `receive_peer_messages` extended for symmetry with package variant. Five existing test assertions updated; full suite **403 passing, 1 skipped** (unchanged). New canonical doc [Prompts_and_Personas_Guide_v2.md](docs/Prompts_and_Personas_Guide_v2.md) (verbatim prompt quotes, real worked example from [`data/output/experiments/20260425_082317/`](data/output/experiments/20260425_082317/)); V1 guide preserved with superseded banner. v0.5 prompt-overhaul section appended to [Model_Design.md](docs/Model_Design.md) (§20). Condition B bias-reduction re-measurement on the new 1P debias chain deferred.
- [2026-05-09] v0.5 — Local-LLM provider (`provider="local"`) added to `cag.io.llm`: substring-keyed `_MODEL_REGISTRY` (Qwen3 / Llama / Apertus / Mistral / DeepSeek-R1), `configure_local()` / `ping_local()` startup health-check, empty-thinking-truncation retry guard, `load_api_key("local")` short-circuit. Three new `SIM_CONFIG` keys (`local_base_url`, `local_extra_body`, `local_timeout_s`) wired through `_resolve_runtime` and added to `_RESUME_SOFT_KEYS`. NB 24 (monkey-patched smoke) and NB 25 (integrated parity, bit-for-bit identical metrics) added. Full V3 rewrite of [Local_LLM_Setup_Guide.md](docs/Local_LLM_Setup_Guide.md) covering mlx-lm / Ollama / vLLM / sglang / llama.cpp; new [requirements-local.txt](requirements-local.txt). Suite at 365 passing, 1 skipped (up from 339).
- [2026-04-23] v0.4 initial release work — Package communication mode, Day-0 ground-truth anchoring (3 modes: `llm_survey` / `ground_truth` / `ground_truth_with_rationale`), and the memory anchor refactor (numeric Day-0..N trajectory replaced with a Day-0 rationale block in `assemble_context()`) landed alongside notebooks 16 and 17.
- [2026-04-24] v0.4 — Checkpoint and resume added to `run_simulation()` (`checkpoint_dir`, `resume`, `checkpoint_every_day`), notebook 18 added, suite extended to 328 tests.
- [2026-04-25] v0.4 — Production package-mode run documented in NB 19; reach-control tooling added (`reach_a`, `reach_b`, `apply_reach_subsample()`), then mirrored with `audience_cap` / `apply_audience_cap()` and broadcast-only validation notebooks 20 and 21.
- [2026-04-26] v0.4 — Day-0 survey-path audit and persona-signal evaluation notebooks 22 and 23 added; `docs/result_report.md` extended through Runs 5–8 and calibration analyses; current baseline is 340 collected tests (339 passing, 1 skipped) across 15 test files.
- [2026-04-19] v0.3 — Bias calibration complete. Condition B debias integrated, Anthropic provider, ground truth utility, 276 tests, 4 experiment runs. See [result_report.md](docs/result_report.md).
- [2026-04-14] Baseline bias investigation: 6-model comparison, 4-condition experiment, multi-policy generalization (NB 11–14).
- [2026-04-10] v0.2 MVP complete — all 10 issues done, 226 tests, 8 demo notebooks (01–08).
- [2026-04-02] 10-issue implementation sprint begun (Issues 1–10 from [github_issues.md](docs/github_issues.md)).
- [2026-03-30] Dependency update to [GABM==0.2.18](https://pypi.org/project/gabm/0.2.18/).
- [2026-03-12] Dependency update to [GABM==0.2.17](https://pypi.org/project/gabm/0.2.17/).
- [2026-03-05] Dependency update to [GABM==0.2.16](https://pypi.org/project/gabm/0.2.16/).
- [2026-02-20] Dependency update to [GABM==0.2.6](https://pypi.org/project/gabm/0.2.6/).
- [2026-02-18] Dependency update to [GABM==0.2.2](https://pypi.org/project/gabm/0.2.2/).
- [2026-02-16] Planned release of Climate-Action-GABM==0.1.0.
- [2026-02-10] Documentation and Makefile added based on those developed for [GABM](https://github.com/compolis/GABM).
- [2026-02-03] Andy added as developer/maintainer. BSD License agreed and put in place.
- [2026-02-02] Climate-Action-GABM Repository transered to [compolis](https://github.com/compolis/)
- ...