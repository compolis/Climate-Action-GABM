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
- [Quick Start](#quick-start)
- [Current Status](#current-status)
- [Architecture](#architecture)
- [Notebooks](#notebooks)
- [License](#license)
- [Roadmap](#roadmap)
- [Change Log](#change-log)
- [Development History](#development-history)
- [Acknowledgements](#acknowledgements)


## Overview
**Climate-Action-GABM** is a generative-AI agent-based model (GABM) of UK climate-policy opinion dynamics, built on the [GABM](https://github.com/compolis/GABM/) framework. It is designed to study a question that classical opinion-dynamics models handle only crudely: how do two **competing committed minorities** — small, organised groups that press opposing messages — move the opinion of a larger majority, and under what conditions does one side gain ground?

In a GABM, agents are driven by Large Language Models (LLMs): each is given a human-like persona and generates natural-language messages, private reflections, and survey answers. Storing those prompts and responses and feeding them back as context lets the model represent how repeated exposure to persuasion — and to the reflections of network neighbours — reshapes an agent's stated position over time, and how those individual shifts cascade through a social network into collective change. Classical committed-minority models collapse a group's influence into a single abstract weight; because a GABM's agents process natural-language arguments against their own personas, it can pull those levers apart.

### The model
This first model simulates opinion on **six UK climate policies** — renewable energy, banning fossil-fuel extraction, banning petrol cars, green housing, a carbon tax, and climate compensation. It has three kinds of agent:

- **Citizen agents.** Each is anchored to a *real respondent* in a representative **YouGov survey** (UK, late April 2024), so the simulation **starts from observed opinions** rather than from a language model's typically over-optimistic prior. A model-ready subset of `N=1,483` respondents (from ~1,967 raw) is the sampling pool; reported runs draw a cohort of `N=100`. Each agent's persona — demographics, voting history, and a psychological value profile (Schwartz values, RWA/SDO) — is assembled into a prompt the LLM adopts for the whole run.
- **Two committed-minority agents.** Loosely modelled on **Reform UK** (climate-sceptic) and the **Green Party** (pro-climate), they broadcast persuasive messages drawn from a fixed, curated pool for each side. The messages are synthetic but each is grounded in the parties' real online climate communications (manifestos, parliamentary speeches, press statements).

A simulated **day** runs as: one or both minority agents broadcast to citizens over a configurable social network (default: a weak-homophily stochastic block model) → citizens reflect privately → citizens exchange peer messages with network neighbours and reflect again → every citizen is re-administered the original survey instrument, recording opinion on a 7-point scale (*Strongly oppose → Strongly support*). Who hears each broadcast is set by an **affinity-ranked exposure** rule that weights political signals above values above demographics.

### Memory and bias control
Each citizen carries a **six-section tiered memory** ([docs/Model_Design.md](docs/Model_Design.md) §28) that ranks context as persona + values → Day-0 anchor (verbatim from the agent's own Day-0 rationale) → daily summaries (older days) → recent reflections → own reasoning → today-so-far. A split between **context scope** (`policy_id`) and **question scope** (`target_policy_id`) lets package-mode end-of-day surveys see cross-policy reflections while staying anchored to the specific policy being asked. Two mechanisms hold known LLM survey bias in check: a **Day-0 ground-truth anchor** that ties each agent to its real starting opinion, and a **two-step debiased survey** prompt (reason first, then answer).

### What the experiments test
A resource advantage can take **different forms**, and the framework holds them apart so their effects can be estimated separately:

- **Reach** — how large a share of citizens a side can broadcast to (`reach_a` / `reach_b`);
- **Frequency** — how often a side broadcasts across a run (`--broadcasts-a/-b`);
- **Targeting** — how selectively a limited broadcast is aimed (`random` / `persuadable` / `degree` / `betweenness`).

The central finding of the accompanying paper is that the **form** of a resource asymmetry, not merely its magnitude, shapes which side moves the majority. Alongside the simulation, the repo ships a **fit-for-purpose evaluation protocol** — including a persona-null ablation that checks whether the model actually conditions on each agent's assigned persona. We are careful about epistemic status: the evidence targets **internal validity and algorithmic fidelity**, not a claim that the model reproduces real-world opinion change.

> The accompanying manuscript is in preparation in [paper/](paper/) (`sn-article.tex` + supplementary `sn-si.tex`). See [docs/result_report.md](docs/result_report.md) for experiment results and [docs/Model_Design.md](docs/Model_Design.md) for the full design specification.


## Quick Start

```bash
# 1. Clone
git clone https://github.com/compolis/Climate-Action-GABM.git
cd Climate-Action-GABM

# 2. Install the runtime dependencies (Python 3.12+)
pip install -r requirements.txt

# 3. Choose an LLM backend:
#    3a. Cloud (OpenAI / Anthropic / Google) — add your API keys, see API_KEYS.md
#    3b. Fully offline on a local LLM — install a local runtime and serve a
#        model, see docs/Local_LLM_Setup_Guide.md (pip install -r requirements-local.txt)

# 4. Preview the canonical smoke run (validates config, makes no LLM calls)
PYTHONPATH=src python3 -m cag --preset smoke --dry-run

# 5. See the available run presets and every configurable knob
PYTHONPATH=src python3 -m cag --list-presets
```

Prefer notebooks? Open [notebooks/01_agent_profiles.ipynb](notebooks/01_agent_profiles.ipynb) and work upward — each notebook demonstrates one simulation component end to end (see the [Notebooks](#notebooks) table).

- **Users** — full setup (Conda or pip), configuration paths, and run recipes: [User Guide](USER_GUIDE.md).
- **Contributors** — fork / clone / test setup: [Developer Quickstart](DEV_QUICKSTART.md) and [Developer Guide](DEV_GUIDE.md).
- **HPC (Leeds AIRE)** — clone-to-`sbatch` walkthrough: [AIRE Quickstart](docs/AIRE_Quickstart.md).


## Current Status

**v0.9 — first behaviour-bearing release after the v0.8 refactor track.** Adds a persona-null ablation (a manipulation check on whether the model conditions on each agent's persona), a broadcast-frequency-asymmetry CLI (one side can out-broadcast the other across a whole run), per-side reach targeting (`persuadable` / `degree` / `betweenness`), a degree-proportional peer-relay option (well-connected citizens can relay their reflection to more neighbours), a simplified three-tier affinity-weight ladder, and a full observability layer (per-agent prompt capture, reached-flags, bucket-summary + targeting-diagnostics tables, and eight new diagnostic figures). Default behaviour is unchanged — `persona_mode="real"`, 1-vs-1 broadcasting, `reach_targeting="random"`, and `peer_fanout_mode="constant"` reproduce prior canon bit-for-bit. All `src/cag/` modules now declare `__version__ = "0.9.0"`.

| Metric | Value |
|--------|-------|
| Tests | **680 passing, 1 skipped** |
| Behaviour additions (v0.9) | persona-null ablation (`apply_persona_mode`: real / shuffled / neutral); broadcast-frequency CLI (`--broadcasts-a/-b`, `--interleave`); per-side reach targeting (`--reach-targeting-a/-b`: random / persuadable / degree / betweenness); degree-proportional peer relay (`--peer-fanout-mode` degree / betweenness, `additive` / `preserve` budget, off by default); three-tier affinity-weight ladder (political 2.0 / values 1.0 / demographics 0.5) |
| Observability (v0.9) | `agent_prompts.csv` (stratified full prompt/response capture); `reached_by_a/_b` flags; `bucket_summary.csv` + `targeting_diagnostics.csv`; eight new diagnostic figures (trajectories-by-bucket, polarization, drift-from-GT, ridgeline, network before/after, targeting mechanism, reach QC, calibration) |
| Refactor track (v0.8) | [src/cag/abm/sim.py](src/cag/abm/sim.py) split 2755 → 838 lines; focused modules under [src/cag/io/](src/cag/io/) and [network_repair.py](src/cag/abm/network_repair.py); v2 six-section tiered-memory architecture (`policy_id` vs `target_policy_id` scope split) |
| Notebooks | 46 (01–46) |
| Source files | 32 under `src/cag/` |

See [ROADMAP.md](ROADMAP.md) for the full issue list and status.
See [docs/Model_Design.md](docs/Model_Design.md) for the design specification.
See [docs/Code_Tour.md](docs/Code_Tour.md) for a newcomer-friendly walkthrough of `src/cag/`.
See [docs/result_report.md](docs/result_report.md) for experiment results and analysis.
See [docs/Simulation_Configuration_Guide.md](docs/Simulation_Configuration_Guide.md) for canonical configuration options (supervisor brief + developer matrix).
See [docs/AIRE_Quickstart.md](docs/AIRE_Quickstart.md) for the v0.7 HPC walkthrough.
See [paper/](paper/) for the manuscript in preparation (`sn-article.tex` and supplementary `sn-si.tex`).


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
| 35 | Memory Ablation Demo | `MEMORY_PRESETS` ablation over the v2 six-section context (short / wide / no-anchor / no-compression variants) |
| 36 | Tier-P Persona-Null | Persona-conditioning manipulation check (`real` / `shuffled` derangement / `neutral` arms) |
| 37 | Tier-P Calibration | Calibration follow-up for the persona-null ablation |
| 38 | Tier-1 Bias Invariance | Bias-mitigation invariance check under the production stack |
| 39 | Tier-1 Per-Policy | Per-policy Tier-1 validation across the six climate policies |
| 40 | Tier-2 Scale Robustness | Robustness of results across citizen-sample scale |
| 41 | Tier-3 Network Robustness | Robustness across network topologies (SBM / BA / WS) |
| 42 | Reach-Targeting Smoke | Per-side reach targeting (persuadable + centrality) smoke with asserts + output checks |
| 43 | Observability Gallery | Prompt-capture walkthrough and diagnostic-figure gallery |
| 44 | Draft-45 Results Figures | Result figures for the draft-45 experiment program |
| 45 | Evaluation Audit | Provenance audit of the evaluation numbers into `paper/tables/` CSVs |
| 46 | Experiments Audit | Provenance audit of the experiment numbers into `paper/tables/` CSVs |


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
