# User Guide


## Table of Contents
- [Overview](#overview)
- [Getting Started](#getting-started)
- [v0.8 Configuration Path](#v08-configuration-path)
- [v0.7 Configuration Path](#v07-configuration-path)
- [Running on HPC / AIRE](#running-on-hpc--aire)
- [v0.6 Configuration Path](#v06-configuration-path)
- [Troubleshooting](#troubleshooting)
- [Running Models](#running-models)
- [Managing Logs and Caches](#managing-logs-and-caches)
- [Additional Resources](#additional-resources)


## Overview
This guide helps users get started with Climate-Action-GABM, find documentation, and get support. Documentation will be updated as more features and configuration options are added.

In the rest of the document "you" means you as a Climate-Action-GABM user.


## Getting Started

### Pre-requisits
 You will either need a local installation of [Conda](https://conda.org/), or [Python](https://www.python.org/) at or above version 3.12. To check your default Python version run:

```bash
python3 --version
```

### Initial set up

#### Using Conda
If you use [Conda](https://conda.org/) which is distributed with[Anaconda](https://www.anaconda.com/)/[Miniconda](https://docs.conda.io/en/latest/miniconda.html) and [Miniforge](https://github.com/conda-forge/miniforge) you can set up Climate-Action-GABM in a new environment as follows:

```bash
conda create -n gabm
conda activate gabm
conda install python=3.12
git clone https://github.com/your-org/Climate-Action-GABM.git
cd Climate-Action-GABM
pip install -e .
pip install -r requirements.txt
```

Climate-Action-GABM is **not** yet published on PyPI; install from source by cloning the repository and running `pip install -e .` in editable mode. You can then check all installed dependencies and create your own requirements file with:

```bash
conda list -e > requirements.txt
```


#### Using Python >=3.12
Install from source (Climate-Action-GABM is not yet published on PyPI):

```bash
python3 -m venv gabm-venv
source gabm-venv/bin/activate  # On Windows: gabm-venv\\Scripts\\activate
pip install --upgrade pip
git clone https://github.com/your-org/Climate-Action-GABM.git
cd Climate-Action-GABM
pip install -e .
pip install -r requirements.txt
```

You can then check installed dependencies with:

```bash
pip freeze > requirements.txt
```


### Set Up API Keys
Create `data/api_key.csv` with your API keys. See [API_KEYS.md](API_KEYS.md) for details and instructions.


### Run the Main Program
From the project root:

```bash
python3 -m cag
```

When you run:

```bash
python3 -m cag
```

the main program for Climate-Action-GABM is executed. This will:

- Initialize the simulation environment, including any subclasses such as `Political_Environment`.
- Create agent populations, including `Person` agents with attributes like year of birth and gender.
- Set up any required groups, relationships, or initial conditions for the agents.
- Begin the simulation loop, where agents interact, update their states, and the environment may change over time.
- Output results, logs, or summaries to the console and/or files in the `data/output/` directory. This may include:
  - Simulation progress and status messages
  - Key statistics or metrics from the run
  - Any errors or warnings encountered
- Save logs and data for further analysis or reproducibility.

The specific output and behavior may depend on your configuration, model parameters, and any customizations you have made. For more details, check the logs and output files generated in the `data/output/` directory after running the command.


## v0.8 Configuration Path

v0.8 makes the agent's **memory / prompt-assembly** configurable so ablation experiments no longer require editing `agent.py`. It also relocates the exposure target/weight vocabularies out of `environment.py` into a dedicated `src/cag/abm/config/` subpackage (all public names are re-exported, so existing imports keep working). Full design rationale is in [docs/Model_Design.md](docs/Model_Design.md) §30.

### The `memory` SIM_CONFIG key

One new key controls the entire context-assembly pipeline:

| Key | Default | Meaning |
|---|---|---|
| `memory` | `"default"` | A memory-config **preset name**, or a literal dict of overrides. Resolved + validated at runtime and attached to every agent. `"default"` reproduces the v0.8 §28 tiered-memory behaviour bit-for-bit. |

The agent context has six sections (persona, Day-0 anchor, daily summaries, recent reflections, own reasoning, today-so-far) plus an optional off-by-default numeric `opinion_trajectory` block. Each can be toggled, and a single `verbatim_window_days` knob (default `2`) controls how many recent days are kept verbatim before older days are compressed into summaries.

**Built-in presets** (`cag.abm.config.memory.MEMORY_PRESETS`):

| Preset | Effect |
|---|---|
| `default` | current behaviour — all sections on, 2-day verbatim window |
| `short_memory` | 1-day verbatim window |
| `wide_memory` | 4-day verbatim window |
| `no_compression` | unbounded verbatim window (never compresses to summaries) |
| `no_anchor` | Day-0 anchor removed (tests whether the anchor causes opinion lock-in) |
| `anchor_ttl2` | Day-0 anchor retires after day 2 |
| `no_own_reasoning` | agent's own prior survey reasoning removed |
| `reflections_only` | anchor + own-reasoning + today-so-far removed |
| `persona_only` | everything except persona removed |

### CLI

`--memory` accepts either a preset name or a JSON dict:

```bash
python -m cag --memory no_anchor
python -m cag --memory short_memory
python -m cag --memory '{"verbatim_window_days": 3, "day0_anchor": {"ttl_days": 2}}'
```

Because the verbatim window determines which days are compressed into stored summaries, `memory` is a **hard resume key** — a checkpoint can only be resumed with the same memory config it was created with.

### Per-stage overrides (advanced)

A dict config may include a `stages` block to vary sections by prompt stage (`peer_message`, `reflection`, `survey`), e.g. drop the anchor only at survey time:

```json
{"stages": {"survey": {"day0_anchor": {"enabled": false}}}}
```

See [notebooks/35_memory_ablation_demo.ipynb](notebooks/35_memory_ablation_demo.ipynb) for an offline (no-LLM) walkthrough showing how one agent's assembled context changes across presets.


## v0.7 Configuration Path

v0.7 consolidates a long block of work (originally labelled "v0.6" internally; v0.6 was never tagged on `origin` so the public ladder is 0.5 → 0.7). For day-to-day runs, treat [docs/Simulation_Configuration_Guide.md](docs/Simulation_Configuration_Guide.md) as the canonical source of truth — a deep rewrite covering the new v0.7 outputs and CLI is on the immediate backlog. Until that lands, the v0.6 configuration path below remains accurate for the runtime defaults, and this section calls out only what's new.

### CLI

`python -m cag` in v0.7 exposes every `SIM_CONFIG` knob as an argparse flag. Three composition-layer flags simplify production runs:

- `--preset NAME` — loads a named bundle from `src/cag/presets.py` (`RUN_BUNDLE_PRESETS`). v0.7 ships `"smoke"` (10-agent × 2-day fast smoke, used by NB 32) and `"r14_canonical"` (50-agent × 5-day Run-14 v2 baseline). Individual `--flag` overrides layer on top.
- `--list-presets` — enumerates available bundles.
- `--dry-run` — prints the fully-resolved `SIM_CONFIG` and exits without I/O. Useful for verifying a sweep line before submission.

### Per-day checkpointing default-on (CLI)

`--checkpoint-every-day` is now `argparse.BooleanOptionalAction, default=True`, so every batch run is wall-clock-kill-recoverable without remembering the flag. Opt out with `--no-checkpoint-every-day`. The Python-side `run_simulation(..., checkpoint_every_day=False)` default is intentionally unchanged so interactive notebooks don't accumulate per-day artefacts unless asked.

### Two new SIM_CONFIG keys for the agent timeline

| Key | Default | Meaning |
|---|---|---|
| `timeline_sample_size` | `3` | Number of agents to include in the saved `agent_timeline.csv` long-format DataFrame. |
| `timeline_sample_agent_ids` | `None` | If set, list of explicit `agent_id` values to sample. If `None`, auto-stratify one agent per top-3-by-size exposure bucket (ties broken by sorted `agent_id`; if fewer than 3 buckets, evenly-spaced sampling along `agent_id`). |

The timeline is **final-output only** (excluded from per-day checkpoints via `_CHECKPOINT_SKIP_KEYS`) because it can be GB-scale on long runs.

### What's new in the run bundle (17 → 29 artefacts)

v0.7 expands the saved run bundle so the headline diagnostic questions are answered by the bundle itself, not by ad-hoc notebook analysis. New artefacts include:

- `agent_attributes.csv` (per-agent bucket, both affinity scores, demographic IDs, full persona text).
- Bucket-stratified CSVs: `package_index_by_bucket.csv`, `opinion_shares_by_bucket.csv`, `day0_vs_dayN_shifts.csv`.
- `calibration_table.csv` (per `(policy_id, day)` `pearson_r / spearman_rho / mae / mean_signed_bias` vs ground truth).
- `message_flow.csv` (`day × phase × sender_side × recipient_bucket` aggregation).
- `network_snapshot.json` (JSON-safe `{nodes, edges}` payload) + `network_diagnostics.json` extended with `auto_connected_edges`.
- `survey_assembled_context.csv` (the **exact ~1–18 KB system prompt** each agent saw at every survey call — the diagnostic affordance that surfaced the NB-31 package-mode bug).
- `agent_timeline.csv` (long-format with 9 event types: `broadcast_received`, `broadcast_reflection`, `peer_message_received`, `peer_message_sent`, `peer_reflection`, `survey_assembled_context`, `survey_raw_response`, `survey_reasoning`, `survey_numeric`).
- New plots: `plot_package_index_by_bucket`, `plot_opinion_shares_by_bucket`, `plot_gap_widening`, `plot_calibration_by_policy`, `plot_network_graph`.
- New `sim_step` column on `messages`, `reflections`, `survey_reasoning`, `survey_raw_response`, `survey_assembled_context`, and `daily_summaries` CSVs (monotonic event counter — canonical sort key for interleaved replay is `(agent_id, sim_step)`).

A deep file-by-file rewrite of [docs/Run_Output_Guide.md](docs/Run_Output_Guide.md) is on the immediate backlog. Until that lands, [docs/result_report.md](docs/result_report.md) (top section: NB 32 smoke validation) is the most current narrative description, and [notebooks/32_v06_outputs_smoke.ipynb](notebooks/32_v06_outputs_smoke.ipynb) prints the per-CSV schema and shows every plot inline.

### Network connectivity 3-layer defence

v0.7 changes two network defaults to grounded values: SBM `p_inter` 0.02 → **0.05** (Bakshy et al. 2015 *Science* / Halberstam & Knight 2016 ~25% cross-cutting exposure) and ER `p` 0.05 → **0.10** (above the n=50 classical connectivity threshold). On top of the new defaults sit three operator-visible layers:

- **Layer 1 — adaptive small-N bump.** For `n < 30` SBM bumps `p_inter` to `max(p_inter, 0.10)` and logs WARNING; for `30 ≤ n < 100` bumps to `max(p_inter, 0.06)` and logs INFO. ER has the same shape. Only ever raises values, never lowers.
- **Layer 2 — deterministic auto-repair.** If the realised graph has multiple components after `assign_network_blocks`, exactly `(k − 1)` bridging edges are added (one from each smaller component to the largest), seeded for reproducibility, and a WARNING is logged with component count, sizes, n_added, seed.
- **Layer 3 — visibility log + diagnostic field.** A single INFO line summarises `n_nodes / n_edges / n_components / mean_degree / auto_connected_edges` on every run; `network_diagnostics.json` gains an `auto_connected_edges` field.

Full design rationale and the empirical sweep that motivated the new defaults are in [docs/Model_Design.md](docs/Model_Design.md) §25 and [scripts/estimate_connectivity_threshold.py](scripts/estimate_connectivity_threshold.py).


## Running on HPC / AIRE

v0.7 ships first-class support for the University of Leeds AIRE cluster (SLURM, GPU partitions, vLLM-served local LLMs). The integration is *thin and edit-free* — launching a new experiment is one entry in a Python preset dict plus one line in a sweep file.

The full walkthrough is in [docs/AIRE_Quickstart.md](docs/AIRE_Quickstart.md) (copy-pasteable zero-to-Run-14) and [docs/AIRE_HPC_repo_primer.md](docs/AIRE_HPC_repo_primer.md) (cluster fundamentals, storage rules, hard constraints, troubleshooting). In short:

1. `git clone` the repo onto AIRE storage; create a venv; `pip install -e .` + requirements.
2. Submit a single experiment: `sbatch scripts/aire/run.sh` with `HF_MODEL=...` and any `SIM_CONFIG` flags as environment variables. vLLM auto-starts on the GPU node.
3. Submit a parameter sweep: `bash scripts/aire/sweep.sh scripts/aire/sweeps/r14_v2.txt` reads one condition per line and submits one `sbatch` per condition.

Add a new experiment by adding one entry to `RUN_BUNDLE_PRESETS` in [src/cag/presets.py](src/cag/presets.py) plus one line to a sweep file. No shell-script edits.


## v0.6 Configuration Path

For day-to-day runs, treat [`docs/Simulation_Configuration_Guide.md`](docs/Simulation_Configuration_Guide.md) as the canonical source of truth.

- **Supervisor path (quick read):** Sections 1-3 explain the canonical run profile and what is frozen vs tunable.
- **Operator/developer path (detailed):** Sections 4 onward provide a key-by-key matrix for every active `SIM_CONFIG` option, valid values, interactions, and tested defaults.

Current canonical runtime defaults are package mode + local Qwen3 + offline political messages, with Day-0 ground-truth-with-rationale anchoring and `debias=True`. If you need legacy behavior (for example single-policy runs or LLM-generated political messages), switch explicitly in `SIM_CONFIG` and record that override in your run notes.

### Political-exposure controls (introduced in v0.5, still active in v0.6)

v0.5 introduces three `SIM_CONFIG` keys controlling political-broadcast audience assignment. Existing v0.4 configs still run unchanged, but when `political_exposure_mode` is omitted the new default is `"rule_affinity_rank"`. Set `political_exposure_mode="rule_priority_chain"` to preserve the legacy assignment rule.

| Key | Default | Allowed values | Meaning |
|---|---|---|---|
| `political_exposure_mode` | `"rule_affinity_rank"` | `"rule_priority_chain"` (legacy) / `"rule_affinity_rank"` (new default) | Which assignment rule decides which citizens go into the `A-only` / `B-only` / `both` / `neither` audience cells. The new `rule_affinity_rank` mode is deterministic top-K on per-citizen affinity scores and respects `political_exposure_targets`. The legacy `rule_priority_chain` mode is vote-only and ignores the targets. |
| `political_exposure_targets` | `None` (resolves to `"committed_minority_symmetric"`) | preset name (`"committed_minority_symmetric"` / `"committed_minority_uk_2024"` / `"legacy_v05"`) **or** a dict with keys `{"A-only", "B-only", "both", "neither"}` that sum to 1.0 | Target shares for the four cells. Symmetric is the v0.5 baseline (`0.11 / 0.11 / 0.33 / 0.45`); `committed_minority_uk_2024` is the UK-realistic asymmetric preset (`0.08 / 0.14 / 0.33 / 0.45`); `legacy_v05` retains the earlier `0.225 / 0.225 / 0.20 / 0.35` defaults. Custom dicts are also accepted. |
| `affinity_weights` | `None` (resolves to `"balanced"`) | preset name (`"balanced"` / `"vote_dominant"` / `"values_dominant"`) **or** a dict with the per-signal weight buckets | How the green-affinity and Reform-affinity scores combine vote history, psychometric scales, demographics, region, age, and education. Only consulted in `rule_affinity_rank` mode. |

Brief sketch — opting into the UK-realistic asymmetric preset:

```python
SIM_CONFIG = {
    # ...existing keys...
    # political_exposure_mode defaults to "rule_affinity_rank" in v0.5,
    # so it only needs to be set explicitly to opt back into the legacy rule.
    "political_exposure_targets": "committed_minority_uk_2024",
    "affinity_weights": "balanced",
}
```

Full design rationale is in [docs/Model_Design.md](docs/Model_Design.md) §18 (especially §18.15 for the v0.5 sanity-check write-up and the two bug fixes that landed alongside it). Literature support for the target presets is in [docs/Literature_Political_Exposure.md](docs/Literature_Political_Exposure.md) §6 and §6.3. The end-to-end structural sanity check on the YouGov pool is [notebooks/27_affinity_exposure_demo.ipynb](notebooks/27_affinity_exposure_demo.ipynb), summarised in [docs/result_report.md](docs/result_report.md).


## Troubleshooting
If you experience issues when installing, configuring, or running GABM, check here for guidance or updates. As the project evolves, troubleshooting tips and frequently asked questions will be added here.

If you encounter errors, check your Python version and that all dependencies are installed. If all versions match the documentation, please peruse [reported issues](https://github.com/compolis/Climate-Action-GABM/issues), comment on a relevent open issue or [open an issue](https://github.com/compolis/Climate-Action-GABM/issues/new/choose) to request support.


## Managing Logs and Caches
Climate-Action-GABM creates logs and caches (such as prompt/response caches for LLM services) that can grow large over time. User friendly ways to tidy up logs and caches and compile data into reproducible research objects are being developed for a future release. Similarly, more details will be provided as these features are implemented.


## Additional Resources
- [README.md](README.md)
- [Reported Issues](https://github.com/compolis/Climate-Action-GABM/issues)