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

Citizen agents are constructed from real **YouGov survey data** (UK, April 2024). Each agent's persona — demographics, voting history, and psychological value profile — is assembled into a natural-language prompt that the LLM adopts for the duration of the simulation. A tiered memory architecture (full reflections → daily summaries → weekly summaries) manages context window limits while preserving experiential continuity.


## Current Status

**v0.4 — Day-0 ground-truth anchoring and package communication mode.**

| Metric | Value |
|--------|-------|
| Tests | 315 passing |
| Issues done | 10 of 10 |
| Notebooks | 17 (01–17) |
| Source files | 21 under `src/cag/` |

See [ROADMAP.md](ROADMAP.md) for the full issue list and status.
See [docs/Model_Design.md](docs/Model_Design.md) for the design specification.
See [docs/result_report.md](docs/result_report.md) for experiment results and analysis.


## Architecture

```
src/cag/
├── abm/
│   ├── agent.py           # SurveyedCitizen, PoliticalAgent
│   ├── environment.py     # SurveyedNation (network, broadcast, peer messaging)
│   ├── sim.py             # run_simulation(), SIM_CONFIG, collect_ground_truth()
│   ├── attributes/
│   │   └── opinion.py     # ClimatePolicyID, survey constants, clamping
│   └── democracy/         # Brexit & UKGE2019 vote enums (from gabm)
├── io/
│   ├── llm.py             # send_chat(), load_api_key(), parse_letter_response()
│   └── survey.py          # Survey loading utilities
└── __main__.py
```


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


## License
See [LICENSE](LICENSE).


## Code of Conduct and Reporting
Please see our [Code of Conduct](CODE_OF_CONDUCT.md) for guidelines on expected behavior and reporting issues.

For security or conduct concerns, you can also use the `Contact maintainers` link on the GitHub repository, or see the [SECURITY.md](SECURITY.md) file in the documentation for details on confidential reporting.


## User Guide
Please use the [User Guide](USER_GUIDE.md).


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
