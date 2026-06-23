<!-- Badges -->
<p align="left">
  <a href="https://github.com/compolis/Climate-Action-GABM/blob/main/LICENSE" title="License">
    <img src="https://img.shields.io/github/license/compolis/Climate-Action-GABM" alt="License" />
  </a>
  <a href="https://www.python.org/downloads/release/python-31212/" title="Python Version">
    <img src="https://img.shields.io/badge/python-3.12%2B-blue.svg" alt="Python Version" />
  </a>
  <!--
  <a href="https://compolis.github.io/Climate-Action-GABM/" title="Documentation">
    <img src="https://img.shields.io/badge/docs-Sphinx-green" alt="Documentation" />
  </a>
  -->
</p>

# Climate-Action-GABM


## Table of Contents
- [Overview](#overview)
- [Current Status](#current-status)
- [Architecture](#architecture)
- [Notebooks](#notebooks)
- [License](#license)
- [Roadmap](#roadmap)
- [Change Log](#change-log)
- [Development History](#development-history)
- [Acknowledgements](#acknowledgements)


## Overview
Climate-Action-GABM is based on [GABM](https://github.com/compolis/GABM/) - a generative agent-based modelling framework.

The framework is used herein to attempt to understand the dynamics of social tipping or polarization under the influence of competing persuasion from two competing committed minorities with opposing goals.

GABM provides a framework for using Large Language Model (LLM) models to develop agent-based models. Agents can be endowed with human-like personas and engage in natural-language conversations using LLM models. By storing prompts and responses, processing these and providing them as context in prompts it is possible to effectively debate and influence the beliefs/desires/stances of agents.

Changes in individual agents beliefs/desires/stances can cascade through their networks to shape collective attitudes.

The first model simulates how citizen opinions on six UK climate policies evolve over repeated "days" of competing political messaging and peer-to-peer deliberation. Two fixed political group agents — one pro-climate-action, one anti-climate-action — broadcast persuasive messages to citizen agents through a configurable network (default: stochastic block model). Between broadcasts, citizens converse with network neighbours and produce private reflections. At the end of each day, every citizen is re-administered the original survey instrument and their opinion is recorded on a 7-point scale (Strongly oppose → Strongly support). A post-hoc clamping function limits opinion shifts to empirically realistic magnitudes.

Citizen agents are constructed from real **YouGov survey data** (UK, April 2024). Each agent's persona — demographics, voting history, and psychological value profile — is assembled into a natural-language prompt that the LLM adopts for the duration of the simulation. A **v2 six-section tiered memory architecture** ([docs/Model_Design.md](docs/Model_Design.md) §28) ranks context as persona + values → Day-0 anchor (verbatim from the agent's own Day-0 rationale, target-scoped) → daily summaries (older days) → recent reflections → own reasoning → today-so-far (package mode only). The split between **context scope** (`policy_id`) and **question scope** (`target_policy_id`) lets package-mode end-of-day surveys see cross-policy reflections while staying anchored to the specific policy being asked.


## Current Status

**v0.8 — refactor track: `sim.py` modular split (2755 → 838 lines), v2 tiered-memory architecture (six-section ordering, `policy_id` vs `target_policy_id` scope split, Day-0 anchor compression removed), operational polish (network-type-aware `[peer]` config log, dead `output_dir` key removed, AIRE first-time-download callout), new [docs/Code_Tour.md](docs/Code_Tour.md) researcher onboarding doc, NB 34 v2-memory smoke. No `__version__` bump (refactor-only release).**

| Metric | Value |
|--------|-------|
| Tests | 557 collected; **556 passing, 1 skipped, 21 subtests passed** |
| Refactor track (v0.8) | [src/cag/abm/sim.py](src/cag/abm/sim.py) split from **2755 → 838 lines** (orchestration only); five new focused modules: [src/cag/abm/network_repair.py](src/cag/abm/network_repair.py), [src/cag/io/aggregators.py](src/cag/io/aggregators.py), [src/cag/io/plots.py](src/cag/io/plots.py), [src/cag/io/results.py](src/cag/io/results.py), [src/cag/io/checkpoint.py](src/cag/io/checkpoint.py). NB 32 bit-identical regression validation (deterministic outputs, 22 LLM-driven CSV schemas, distributional stats within `gpt-5-mini @ T=0.5` noise). |
| Memory architecture (v0.8) | `assemble_context()` rewritten as ordered six-section build; new `target_policy_id` parameter; `compress_day0_anchor()` LLM call + `day0_anchors.csv` schema removed (§2 now verbatim from `survey_reasoning`). v0.7 checkpoints resume cleanly into v0.8. |
| Operational (v0.8) | Dead `SIM_CONFIG["output_dir"]` key removed (now 33 keys); `[peer]` config-log line renders resolved `_resolve_network_params(cfg)` dict (Watts–Strogatz, Barabási–Albert, Erdős–Rényi, homophily-weighted now report actual params); [docs/AIRE_Quickstart.md](docs/AIRE_Quickstart.md) §6 first-time-model-download callout. |
| New onboarding doc (v0.8) | [docs/Code_Tour.md](docs/Code_Tour.md) — ~25-page newcomer walkthrough of `src/cag/`: audience + conventions, 30-min skim sequence, 15 file walkthroughs (medium depth on `sim.py` + `agent.py`), 2 side-trips (political-exposure affinity-rank, v2 memory annotated example), 6-recipe cookbook, 11-term glossary, AIRE pre-flight checklist. |
| Carried from v0.7 | AIRE / SLURM thin sbatch launchers + sweep submitter ([scripts/aire/](scripts/aire/)); preset-bundle CLI composition ([src/cag/presets.py](src/cag/presets.py), [src/cag/\_\_main\_\_.py](src/cag/__main__.py)); NB-31 package-mode survey-context fix; outputs expansion (29 saved artefacts, bucket-stratified CSVs, calibration table, network snapshot, per-agent timeline with 9 event types, full survey-prompt audit, monotonic `sim_step` counter); 3-layer network connectivity defence (literature-grounded SBM `p_inter=0.05`, adaptive small-N bump, deterministic auto-repair); `k_peers=0` short-circuit; per-day checkpointing CLI default-on. |
| Carried from v0.6 | Canonical SIM defaults align with research runs (`n_citizens=100`, package-mode alternating phases, local Qwen3 default, `debias=True`, `day0_anchor=ground_truth_with_rationale`); offline political-message source first-class with strict startup validation and message-level provenance (`political_message_id`). |
| Notebooks | 34 (01–34) |
| Source files | 29 under `src/cag/` |

See [ROADMAP.md](ROADMAP.md) for the full issue list and status.
See [docs/Model_Design.md](docs/Model_Design.md) for the design specification.
See [docs/Code_Tour.md](docs/Code_Tour.md) for a newcomer-friendly walkthrough of `src/cag/`.
See [docs/result_report.md](docs/result_report.md) for experiment results and analysis.
See [docs/Simulation_Configuration_Guide.md](docs/Simulation_Configuration_Guide.md) for canonical configuration options (supervisor brief + developer matrix).
See [docs/AIRE_Quickstart.md](docs/AIRE_Quickstart.md) for the v0.7 HPC walkthrough.


## Architecture

```
src/cag/
├── abm/
│   ├── agent.py               # SurveyedCitizen (v2 six-section assemble_context), PoliticalAgent
│   ├── environment.py         # SurveyedNation (network, broadcast, peer messaging)
│   ├── sim.py                 # run_simulation(), _run_one_day(), _resolve_runtime(), SIM_CONFIG (838 lines, orchestration only)
│   ├── network_repair.py      # 3-layer connectivity defence (_adjust_network_params_for_small_n, _auto_connect_components, _log_network_summary)
│   ├── networks.py            # Network factory (stochastic_block, watts_strogatz, barabasi_albert, erdos_renyi, homophily_weighted)
│   ├── political_messages.py  # Offline political-message loader, validation, selection
│   ├── attribute_maps.py      # ID → string maps for all demographic enums
│   ├── attributes/
│   │   ├── opinion.py         # ClimatePolicyID, survey constants, clamping, package index, PACKAGE_SCOPE
│   │   ├── politics.py        # Party / vote enums
│   │   ├── education.py | ethnicity.py | family.py | income.py | region.py | narratives.py
│   └── democracy/             # Brexit & UKGE2019 vote enums (from gabm)
├── io/
│   ├── llm.py                 # send_chat() (openai/genai/anthropic/local), load_api_key(), parse_letter_response(), configure_local(), ping_local()
│   ├── aggregators.py         # _collect_results post-processing: build_*_by_bucket, build_calibration_table, build_message_flow, build_agent_timeline (506 lines)
│   ├── plots.py               # save_result_plots + every per-figure plotter (555 lines)
│   ├── results.py             # save_results, _RESULT_CSV_SCHEMAS, _write_all_csvs, JSON serialisation (512 lines)
│   ├── checkpoint.py          # _write_checkpoint, _load_checkpoint, resume-key validation, sim_step rehydration (366 lines)
│   └── survey.py              # Survey loading utilities
├── presets.py                 # RUN_BUNDLE_PRESETS (smoke, r14_canonical) for CLI --preset composition
└── __main__.py                # Full argparse coverage for every SIM_CONFIG knob; --preset / --list-presets / --dry-run
```

A newcomer-friendly walkthrough of this layout — with a 30-minute skim sequence, file-by-file reading guide, and an AIRE pre-flight checklist — is in [docs/Code_Tour.md](docs/Code_Tour.md).


## Notebooks

Interactive demos live in `notebooks/`. Each covers one simulation component:

| # | Notebook | Description |
|---|----------|-------------|
| 01 | Agent Profiles | Build personas from YouGov survey data |
| 02 | LLMs and Surveys | Send chat prompts, administer baseline survey |
| 03 | Network and Exposure | Stochastic block model, exposure assignment |
| 04 | Political Agent Broadcast | Political agents generate messages, citizens reflect |
| 05 | Peer Messaging | Simultaneous neighbour message exchange |
| 06 | End-of-Day Survey | Re-survey after daily phases |
| 07 | Memory | Tiered memory compression |
| 08 | Full Simulation | End-to-end multi-day simulation run |
| 09 | YouGov Survey EDA | Exploratory analysis of source survey data |
| 10 | Experiment Runner | Interactive simulation configuration and execution |
| 11 | Model Baseline Comparison | 6-model comparison of survey reproduction fidelity |
| 12 | Third-Person Prompt Experiment | Test perspective shift for sycophancy reduction |
| 13 | Bias Mitigation Experiment | 4-condition experiment: reasoning, anti-sycophancy, scale |
| 14 | Multi-Policy Generalization | Test bias mitigation across 4 climate policies |
| 15 | Full Simulation + Ground Truth | Debias + thinking + dual-model + GT comparison |
| 16 | Package Mode Sanity Checks | Single broadcast / peer pass covers all six policies per phase |
| 17 | Full-Stack Smoke Test | Package + Day-0 anchor + debias + thinking + dual-model + timing harness |
| 18 | Checkpoint + Resume Smoke Test | Atomic per-day checkpoints, interrupt handling, and resume validation |
| 19 | Full Simulation | Production package-mode run with Day-0 anchor, debias, and checkpointing |
| 20 | Reach Asymmetry Pilot | First reach-subsample experiment under the full package-mode stack |
| 21 | Broadcast-Only Asymmetry | Reach sweep with peers disabled and `audience_cap` mirror control |
| 22 | Day-0 Accuracy (Sonnet) | Survey-path audit against ground truth under the production survey stack |
| 23 | Persona Signal Test | Null-model comparison for persona signal and higher-power calibration |
| 24 | Local Qwen3 Smoke Test | First end-to-end local-LLM run (Qwen3 8B 4-bit / mlx-lm / Apple Silicon) |
| 25 | Local LLM Integrated Smoke | Bit-for-bit parity check between monkey-patched prototype and first-class `provider="local"` path |
| 26 | Network Factory Demo | Stochastic block model factory and topology configurability walkthrough |
| 27 | Affinity Exposure Demo | `rule_affinity_rank` validation on the full YouGov pool (target presets, weight presets, validation gates) |
| 28 | Offline Political Messages Smoke | Curated offline message pool: loader, validation, selection/rotation, and `political_message_id` provenance |
| 29 | Canonical Full Smoke | End-to-end canonical defaults run (package mode, local Qwen3, debias, ground-truth anchor, offline messages) |
| 30 | Surgical Survey Replay | Cross-model surgical replay isolating the package-mode survey-context surface (pre-NB-31 discovery) |
| 31 | Package-Mode Fix Validation | NB-31 fix-replay confirming `PACKAGE_SCOPE` plumbing through `administer_survey()` / `run_end_of_day_survey()` |
| 32 | v0.6 Outputs Smoke | End-to-end validation of 29-artefact outputs expansion + network connectivity defence + v0.8 `sim.py` modular split regression |
| 33 | `assemble_context` v2 Sandbox | Iterative-design sandbox notebook used to scope the v0.8 six-section context order, `policy_id` vs `target_policy_id` split, and verbatim Day-0 anchor path before NB 34 |
| 34 | v2 Memory Smoke | End-to-end smoke for the v0.8 v2 six-section context order, `target_policy_id` scope split, and verbatim Day-0 anchor path (local Qwen3-8B-4bit) |


## License
See [LICENSE](LICENSE).


## Code of Conduct and Reporting
Please see our [Code of Conduct](CODE_OF_CONDUCT.md) for guidelines on expected behavior and reporting issues.

For security or conduct concerns, you can also use the `Contact maintainers` link on the GitHub repository, or see the [SECURITY.md](SECURITY.md) file in the documentation for details on confidential reporting.


## User Guide
Please use the [User Guide](USER_GUIDE.md).

Running on Leeds's AIRE HPC? Start with the [AIRE Quickstart](docs/AIRE_Quickstart.md) — clone-to-`sbatch` walkthrough with worked smoke + split50 examples.


## Developer Guide
Please use the [Developer Guide](DEV_GUIDE.md).


## Roadmap
See [ROADMAP.md](ROADMAP.md) for planned next steps and future goals.


## Change Log
See [CHANGE_LOG.md](CHANGE_LOG.md) for details of each release.


## Development History
The collaborative development of GABM is captured in the [DEVELOPMENT_HISTORY.md](DEVELOPMENT_HISTORY.md).


## Acknowledgements
This project was developed with significant assistance from [GitHub Copilot](https://github.com/features/copilot) for code generation, refactoring, and documentation improvements.

We gratefully acknowledge support from the [University of Leeds](https://www.leeds.ac.uk/). Funding for this project comes from a UKRI Future Leaders Fellowship awarded to [Professor Viktoria Spaiser](https://essl.leeds.ac.uk/politics/staff/102/professor-viktoria-spaiser) (grant reference: [UKRI2043](https://gtr.ukri.org/projects?ref=UKRI2043)).
