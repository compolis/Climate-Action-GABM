# User Guide

## Table of Contents
- [Overview](#overview)
- [Getting Started](#getting-started)
- [Run the Main Program](#run-the-main-program)
- [Advanced Guides](#advanced-guides)
- [Running on HPC / AIRE](#running-on-hpc--aire)
- [Troubleshooting](#troubleshooting)
- [Additional Resources](#additional-resources)


## Overview
This guide is the current, practical runbook for Climate-Action-GABM users.
It focuses on setup, smoke validation, canonical baseline runs, and where to go
next for configuration and output interpretation.


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


## Run the Main Program

### Run from the command line

Validate configuration first (no provider calls):

```bash
PYTHONPATH=src python3 -m cag --preset smoke --dry-run
```

Run the canonical baseline:

```bash
PYTHONPATH=src python3 -m cag --preset r14_canonical --exposure-targets split50
```

### Run using the Makefile

From the repository root:

```bash
make run-local
```

This launches `python3 -m cag` with output rooted at
`data/output/experiments/`.

### Configure and interpret runs
Use [Simulation_Configuration_Guide.md](documentation/guides/Simulation_Configuration_Guide.md)
as the canonical source of truth for active configuration options and
interactions.

Use [Run_Output_Guide.md](documentation/guides/Run_Output_Guide.md) to inspect
generated CSV/JSON/plot artefacts and interpret run outcomes.

## Advanced Guides

- [Simulation_Configuration_Guide.md](documentation/guides/Simulation_Configuration_Guide.md)
- [Run_Output_Guide.md](documentation/guides/Run_Output_Guide.md)
- [AIRE_Quickstart.md](documentation/guides/hpc/AIRE_Quickstart.md)
- [AIRE_HPC_repo_primer.md](documentation/guides/hpc/AIRE_HPC_repo_primer.md)


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
