# Change Log


## Table of Contents
- [Overview](#overview)
- [0.2](#02)
- [0.1](#01)


## Overview
Notable changes are to be documented in this file.


## [0.2]
- **Climate Policy Opinion System** — 6 policy questions (`ClimatePolicyID`), 7-point response scale, `clamp_opinion_shift()`, shared constants in `opinion.py`
- **LLM Chat Integration** — `send_chat()` wrapper supporting OpenAI and Gemini, `load_api_key()` from CSV, `parse_letter_response()` for survey answers
- **Baseline Survey Administration** — `SurveyedCitizen` class with persona generation, system prompt, and Day 0 LLM-driven survey (`administer_survey()`, `run_baseline()`)
- **Political Agent Class** — `PoliticalAgent` with fixed stance and `generate_message()` for persuasive broadcast content
- **Network + Political Exposure** — `SurveyedNation` with stochastic block model network, exposure assignment from Brexit/UKGE2019 voting history
- **Political Broadcast Phases** — `run_political_broadcast()` implementing Phase P-A / P-B broadcast → citizen reflection cycle
- **Peer Messaging Phase** — `run_peer_messaging()` with simultaneous update: generate all messages first, then deliver and reflect
- **8 demo notebooks** (01–08) covering each simulation component
- **171 tests** across 12 test files

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

