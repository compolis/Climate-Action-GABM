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
| Understand the model's design and research questions | the paper in [`paper/`](../paper/) (see also [Simulation_Configuration_Guide.md](Simulation_Configuration_Guide.md)) |
| Configure and launch a simulation | [Simulation_Configuration_Guide.md](Simulation_Configuration_Guide.md) |
| Understand the files a run produces | [Run_Output_Guide.md](Run_Output_Guide.md) |
| See the exact prompts and personas sent to the LLM | [Prompts_and_Personas_Guide_v2.md](Prompts_and_Personas_Guide_v2.md) |
| Find my way around the source code | [Code_Tour.md](Code_Tour.md) |
| Run a fully local LLM backend | [Local_LLM_Setup_Guide.md](Local_LLM_Setup_Guide.md) |
| Run on the AIRE HPC cluster | [AIRE_Quickstart.md](AIRE_Quickstart.md) |
| Check what past experiments found | [result_report.md](result_report.md) |
| Read the paper draft (manuscript + SI) | [`paper/`](../paper/) |

---

## Design & research rationale

> **⚠ `Model_Design.md` is an internal history file, not a current spec.** It is an append-only
> log that was updated over many iterations, so roughly half of it describes earlier model
> versions that no longer match the code. Treat it as a historical / internal reference only.
> For current behaviour, use [Simulation_Configuration_Guide.md](Simulation_Configuration_Guide.md),
> [Code_Tour.md](Code_Tour.md), the paper in [`paper/`](../paper/), and the code itself; the
> maintained change history lives in the root [CHANGE_LOG.md](../CHANGE_LOG.md) and
> [DEVELOPMENT_HISTORY.md](../DEVELOPMENT_HISTORY.md).

| File | Role | Use it when… |
|---|---|---|
| [Model_Design.md](Model_Design.md) | Append-only design / decision log spanning the project's history. **Partly outdated** — an internal reference for tracking how the model evolved, not an authoritative current spec (see warning above). | You want the historical record of a design decision. |
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

## Paper

The manuscript lives in the top-level [`paper/`](../paper/) folder (Springer Nature
single-file `sn-jnl` format), separate from these docs.

| File / folder | Role |
|---|---|
| [`paper/sn-article.tex`](../paper/sn-article.tex) | Main manuscript — the current working draft. |
| [`paper/sn-si.tex`](../paper/sn-si.tex) | Supplementary Information (Sections S1–S5, Tables S1–S9). |
| [`paper/tables/`](../paper/tables/) | Machine-readable audit tables (`audit_evaluation.csv`, `audit_experiments.csv`, `table1_experiments.csv`) that every reported number is recomputed from. |
| [`paper/figures/`](../paper/figures/) | The figures the tex references. |

**Current contents (draft, work in progress).** The paper reports a fit-for-purpose
*evaluation* of the model — does it read personas, respond to the lever, avoid a
scale-ceiling artefact, and replicate across graph and model — followed by *four
resource-advantage experiments* pitting two competing committed minorities against each
other: broadcast **reach**, broadcast **frequency**, **targeting**, and
**breadth-vs-depth** at a fixed impression budget. The intro, model framework,
experimental design, results (with Table 1) and discussion are drafted, and the SI is
populated; the literature review and the result figures are still to do. Every number is
traceable to the audit notebooks
([`notebooks/45_evaluation_audit.ipynb`](../notebooks/45_evaluation_audit.ipynb) and
[`notebooks/46_experiments_audit.ipynb`](../notebooks/46_experiments_audit.ipynb)); see
[result_report.md](result_report.md) → "Paper Cross-Reference" for the section-by-section
map.

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
