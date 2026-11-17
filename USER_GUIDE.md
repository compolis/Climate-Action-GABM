# User Guide

## Table of Contents
- [Overview](#overview)
- [Support Policy (pre-1.0)](#support-policy-pre-10)
- [Getting Started](#getting-started)
- [Run Recipes (Current)](#run-recipes-current)
- [Running on HPC / AIRE](#running-on-hpc--aire)
- [Troubleshooting](#troubleshooting)
- [Additional Resources](#additional-resources)


## Overview
This guide is the current, practical runbook for Climate-Action-GABM users.
It focuses on setup, smoke validation, canonical baseline runs, and where to go
next for configuration and output interpretation.


## Support Policy (pre-1.0)
Before a 1.0 release, this project supports the **current documentation and
current runtime path only**.

Historical version-specific guidance has been moved to
[USER_GUIDE_pre_1_0_archive.md](documentation/history/USER_GUIDE_pre_1_0_archive.md).
Use it as background reference, not as an actively supported run path.


## Getting Started

### Prerequisites
Use one of:
- [Conda](https://conda.org/) (Anaconda/Miniconda/Miniforge), or
- [Python](https://www.python.org/) 3.12+

Check Python:

```bash
python3 --version
```

### Initial setup (Conda)

```bash
conda create -n gabm
conda activate gabm
conda install python=3.12
git clone https://github.com/compolis/Climate-Action-GABM.git
cd Climate-Action-GABM
pip install -e .
pip install -r requirements.txt
```

### Initial setup (venv)

```bash
python3 -m venv gabm-venv
source gabm-venv/bin/activate  # On Windows: gabm-venv\\Scripts\\activate
pip install --upgrade pip
git clone https://github.com/compolis/Climate-Action-GABM.git
cd Climate-Action-GABM
pip install -e .
pip install -r requirements.txt
```

### Set up API keys
Create `data/api_key.csv` with your API keys. See
[API_KEYS.md](API_KEYS.md) for required fields and examples.

### Validate installation (no LLM calls)
From the project root:

```bash
PYTHONPATH=src python3 -m cag --preset smoke --dry-run
```

This validates resolved configuration without making provider calls.


## Run Recipes (Current)

### Canonical baseline run
Run the standard baseline:

```bash
PYTHONPATH=src python3 -m cag --preset r14_canonical --exposure-targets split50
```

### Configure runs
Use [Simulation_Configuration_Guide.md](documentation/guides/Simulation_Configuration_Guide.md)
as the canonical source of truth for active configuration options and
interactions.

### Inspect outputs
Use [Run_Output_Guide.md](documentation/guides/Run_Output_Guide.md) to inspect
generated CSV/JSON/plot artefacts and interpret run outcomes.


## Running on HPC / AIRE

For University of Leeds AIRE usage, use:
- [AIRE_Quickstart.md](documentation/guides/hpc/AIRE_Quickstart.md) for zero-to-run setup
- [AIRE_HPC_repo_primer.md](documentation/guides/hpc/AIRE_HPC_repo_primer.md) for policies, constraints, and troubleshooting

Minimal pattern:
1. Clone onto AIRE storage and install dependencies in a venv.
2. Submit one run via `sbatch scripts/hpc/aire/run.sh`.
3. Submit sweeps via `bash scripts/hpc/aire/sweep.sh scripts/hpc/aire/sweeps/<file>.txt`.


## Troubleshooting
- Re-run the dry-run check:
  - `PYTHONPATH=src python3 -m cag --preset smoke --dry-run`
- Confirm Python and dependencies match this guide.
- For HPC failures, use the AIRE guides above first.
- Check [reported issues](https://github.com/compolis/Climate-Action-GABM/issues)
  and [open a new issue](https://github.com/compolis/Climate-Action-GABM/issues/new/choose)
  if needed.


## Additional Resources
- [README.md](README.md)
- [DEV_GUIDE.md](DEV_GUIDE.md)
- [Simulation_Configuration_Guide.md](documentation/guides/Simulation_Configuration_Guide.md)
- [Run_Output_Guide.md](documentation/guides/Run_Output_Guide.md)
- [documentation/history/](documentation/history/)
