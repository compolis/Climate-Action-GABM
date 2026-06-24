# Documentation Index

This folder holds the long-form documentation for **Climate-Action-GABM** — a generative
agent-based model of UK climate-policy opinion dynamics. The files below cover the model's
design, how to configure and run it, what it produces, and how to read the code. Most are
plain Markdown you can read on GitHub; a few are Sphinx machinery that builds the rendered
docs site.

> Project-level docs (`README.md`, `USER_GUIDE.md`, `DEV_GUIDE.md`, `ROADMAP.md`,
> `CHANGE_LOG.md`, etc.) live in the **repository root**, not here.

---

## Start here

Pick the doc that matches what you want to do:

| I want to… | Read |
|---|---|
| Understand the model's design and research questions | [Model_Design.md](Model_Design.md) |
| Configure and launch a simulation | [Simulation_Configuration_Guide.md](Simulation_Configuration_Guide.md) |
| Understand the files a run produces | [Run_Output_Guide.md](Run_Output_Guide.md) |
| See the exact prompts and personas sent to the LLM | [Prompts_and_Personas_Guide_v2.md](Prompts_and_Personas_Guide_v2.md) |
| Find my way around the source code | [Code_Tour.md](Code_Tour.md) |
| Run a fully local LLM backend | [Local_LLM_Setup_Guide.md](Local_LLM_Setup_Guide.md) |
| Run on the AIRE HPC cluster | [AIRE_Quickstart.md](AIRE_Quickstart.md) |
| Check what past experiments found | [result_report.md](result_report.md) |

---

## Design & research rationale

| File | Role | Use it when… |
|---|---|---|
| [Model_Design.md](Model_Design.md) | The full, **append-only** design specification and decision log — agent types, phases, scales, and every subsequent design decision added as a new numbered section. | You need the authoritative "why it works this way" and the historical record of design choices. |
| [research_notes.md](research_notes.md) | Append-only log of research-direction thinking — framing decisions, what the model is and isn't measuring, where the next sweep is pointed. | You want the strategic/scientific context that spans multiple runs and PRs. |
| [yougov_survey_data.md](yougov_survey_data.md) | Documentation of the YouGov "Ecofascism in the UK" (April 2024) survey that agents are anchored to — sample, design, weighting. | You need to understand the empirical ground truth behind agent opinions. |

## Configuration & usage

| File | Role | Use it when… |
|---|---|---|
| [Simulation_Configuration_Guide.md](Simulation_Configuration_Guide.md) | Two-layer reference for the `SIM_CONFIG` dict — a supervisor brief on the canonical run plus a developer matrix of every key (type, valid values, interactions, profiles). | You're composing or tuning a run. |
| [Prompts_and_Personas_Guide_v2.md](Prompts_and_Personas_Guide_v2.md) | Reader-friendly tour of every LLM prompt and the persona text, byte-identical to the code templates (post-v0.5 overhaul). | You want to know exactly what the LLM is asked and how personas are built. |
| [Run_Output_Guide.md](Run_Output_Guide.md) | Walk-through of every artefact a run produces — each CSV/JSON/PNG, its columns, and a qualitative-review workflow. | You're reviewing a run directory or analysing outputs. |
| [Local_LLM_Setup_Guide.md](Local_LLM_Setup_Guide.md) | How to run an OpenAI-compatible local LLM server (mlx-lm, Ollama, vLLM, etc.) via `provider="local"`. | You want to run models locally instead of via an API. |

## Code orientation

| File | Role | Use it when… |
|---|---|---|
| [Code_Tour.md](Code_Tour.md) | A guided, two-layer walk through `src/cag/` — bold lines for a fast pass, "Staying?" notes for depth, with grep breadcrumbs instead of line numbers. | You know the science but haven't opened the code. |

## HPC (AIRE)

| File | Role | Use it when… |
|---|---|---|
| [AIRE_HPC_repo_primer.md](AIRE_HPC_repo_primer.md) | Generic AIRE / Slurm contract — cluster configuration, storage rules, `#SBATCH` reference, repository requirements. | You need the fundamentals and hard constraints of the cluster. |
| [AIRE_Quickstart.md](AIRE_Quickstart.md) | Repo-specific, copy-pasteable walkthrough — from clone to a smoke job to a full run on AIRE. | You want to actually launch jobs on AIRE. |

## Results

| File | Role | Use it when… |
|---|---|---|
| [result_report.md](result_report.md) | Ongoing, newest-first record of experiments — settings, findings, iteration notes, and a paper cross-reference table. | You want to know what each run showed or which result backs which paper section. |

## Dependencies (documentation mirrors)

| File | Role | Use it when… |
|---|---|---|
| [requirements.md](requirements.md) | Documentation-only mirror of the runtime dependencies. | You want a readable view of the run requirements (install from the root `requirements.txt`). |
| [requirements-dev.md](requirements-dev.md) | Documentation-only mirror of the developer/test dependencies. | You want a readable view of the dev requirements (install from the root `requirements-dev.txt`). |

## Sphinx documentation site

These files build the rendered docs site and are not meant to be read as prose.

| File / folder | Role |
|---|---|
| [index.md](index.md) | MyST entry point and table of contents for the rendered site. |
| [index.rst](index.rst) | Placeholder kept for Sphinx compatibility; navigation lives in `index.md`. |
| [api.rst](api.rst) | Auto-generated API reference (Sphinx `automodule`) for the `cag` package. |
| [conf.py](conf.py) | Sphinx configuration. |
| [cag_handover_deck.html](cag_handover_deck.html) | Self-contained handover slide deck (HTML). |
| `_autosummary/` | Generated API-summary stubs. Do not edit by hand. |
| `_build/` | Generated Sphinx build output. Do not edit by hand. |

## Other

| Folder | Role |
|---|---|
| `supplementary_docs/` | Old and temporary files. Not maintained — kept for reference only. |
