# User Guide


## Table of Contents
- [Overview](#overview)
- [Getting Started](#getting-started)
- [v0.5 configuration keys (committed-minority audience reframe)](#v05-configuration-keys-committed-minority-audience-reframe)
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
pip install cag==0.3.0
```

You can then check all installed dependencies and create your own requirements file with:

```bash
conda list -e > requirements.txt
```


#### Using Python >=3.12
Install from [PyPI](https://pypi.org/) using [Pip](https://pypi.org/project/pip/) as follows:

```bash
python3 -m venv gabm-venv
source gabm-venv/bin/activate  # On Windows: gabm-venv\\Scripts\\activate
pip install --upgrade pip
pip install cag==0.3.0
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


## v0.5 configuration keys (committed-minority audience reframe)

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