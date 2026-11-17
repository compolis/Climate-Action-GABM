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

You will either need a local installation of [Conda](https://conda.org/), or [Python](https://www.python.org/) at or above version 3.12. To check your default Python version run:

```bash
python3 --version
```

### Initial set up

#### Using Conda
If you use [Conda](https://conda.org/) which is distributed with [Anaconda](https://www.anaconda.com/), [Miniconda](https://docs.conda.io/en/latest/miniconda.html), or [Miniforge](https://github.com/conda-forge/miniforge), you can set up Climate-Action-GABM in a new environment as follows:

```bash
conda create -n cag -y
conda activate cag
conda install python=3.12 -y
git clone https://github.com/compolis/Climate-Action-GABM.git
cd Climate-Action-GABM
pip install -r requirements.txt
```

You can then check all installed dependencies and create your own requirements file with:

```bash
conda list -e > requirements.txt
```


### Initial setup (venv)

```bash
python3 -m venv cag-venv
source cag-venv/bin/activate  # On Windows: gabm-venv\\Scripts\\activate
pip install --upgrade pip
git clone https://github.com/compolis/Climate-Action-GABM.git
cd Climate-Action-GABM
pip install -r requirements.txt
```

Once installed you can check installed dependencies and create a requirements file:

```bash
pip freeze > requirements.txt
```


#### Optional: Local LLM Server Setup

The default runtime path uses `provider=local`, which expects an
OpenAI-compatible local server at `http://localhost:8080/v1`.

If you plan to run non-dry-run simulations locally, set up and start a local
server first. See
[Local_LLM_Setup_Guide.md](documentation/guides/Local_LLM_Setup_Guide.md).

Any OpenAI-compatible server works (for example vLLM on HPC, or Ollama
locally). Use whichever is available in your environment.

Quick start example (Ollama, local workstation):

```bash
ollama serve
```

In another terminal:

```bash
ollama pull qwen3:8b
curl http://localhost:11434/v1/models
```

Then run Climate-Action-GABM with:

```bash
PYTHONPATH=src python3 -m cag \
  --preset r14_canonical \
  --provider local \
  --model qwen3:8b \
  --base-url http://localhost:11434/v1 \
  --outdir "data/output/experiments/$(date +%Y%m%d_%H%M%S)_r14_local"
```

Quick start example (vLLM):

```bash
vllm serve Qwen/Qwen3-8B --port 8000
curl http://localhost:8000/v1/models
```

Then point CAG to it with `--base-url http://localhost:8000/v1`.


### Set up API keys

Create `data/api_key.csv` with your API keys. For all supported LLM providers (including PublicAI/Apertus), see [API_KEYS.md](API_KEYS.md) for up-to-date details and instructions.


## Run the Main Program

### Run from the command line

Validate configuration first (no provider calls):

```bash
PYTHONPATH=src python3 -m cag --preset smoke --dry-run
```

Expected result:
- The command exits successfully and prints resolved configuration JSON
  (including keys such as `days`, `k_peers_per_day`, and `n_citizens`).

Run the canonical baseline:

```bash
PYTHONPATH=src python3 -m cag \
  --preset r14_canonical \
  --exposure-targets split50 \
  --outdir "data/output/experiments/$(date +%Y%m%d_%H%M%S)_r14_canonical"
```

Expected result:
- A new run directory is created at the `--outdir` path you provide.
- The run writes CSV/JSON artefacts and plots for analysis.
- Exact files vary by configuration; see
  [Run_Output_Guide.md](documentation/guides/Run_Output_Guide.md) for the
  expected bundle.

If you see an error like:
`Local LLM server not reachable at http://localhost:8080/v1/models`,
start a local server first (see
[Local_LLM_Setup_Guide.md](documentation/guides/Local_LLM_Setup_Guide.md)), or
set a hosted provider explicitly with CLI flags and API keys.

Example (hosted OpenAI path):

```bash
PYTHONPATH=src python3 -m cag \
  --preset r14_canonical \
  --provider openai \
  --model gpt-4o-mini \
  --outdir "data/output/experiments/$(date +%Y%m%d_%H%M%S)_r14_openai"
```

### Run using the Makefile

From the repository root:

```bash
make run-local
```

This launches `python3 -m cag` with output rooted at
`data/output/experiments/`.

For direct CLI runs (without `make run-local`), include `--outdir` on any
non-inspection run.

### What to check after a run

1. Confirm a new timestamped folder exists under `data/output/experiments/`.
2. Open `config.json` in that run folder to verify the resolved settings used.
3. Review key outputs using
   [Run_Output_Guide.md](documentation/guides/Run_Output_Guide.md).

### Configure and interpret runs
Use [Simulation_Configuration_Guide.md](documentation/guides/Simulation_Configuration_Guide.md)
as the canonical source of truth for active configuration options and
interactions.

Use [Run_Output_Guide.md](documentation/guides/Run_Output_Guide.md) to inspect
generated CSV/JSON/plot artefacts and interpret run outcomes.

### Runtime expectations (rough guidance)

Wall-clock runtime depends heavily on provider latency, queueing/rate limits,
and whether responses are local or hosted. As a rough guide:

- `--preset smoke --dry-run`: usually seconds (config-only, no LLM calls).
- `--preset smoke` with hosted OpenAI: often around 10–20 minutes.
- `--preset r14_canonical` with hosted APIs: typically much longer than smoke;
  expect tens of minutes to multiple hours depending on model/provider
  throughput.

Recent observed example on this repository/environment:
- `--preset smoke --provider openai --model gpt-4o-mini` completed in
  **10.6 minutes total wall-clock** (`simulation=10.5 min`, setup/save ~5s).
- The run log reported `sim per agent-day: 21.09s` for that run.

Quick planning estimate:
- runtime ≈ `sim_per_agent_day × n_citizens × (days + 1)`.
- `days + 1` includes Day 0 baseline survey.

Example using 21.09s from the smoke run:
- `r14_canonical` (`n=50`, `days=5`) → `21.09 × 50 × 6 ≈ 6327s` ≈ **1.75h**
  simulation time, plus a small save/setup overhead.

If you need fast iteration, validate changes with `--preset smoke` first, then
run `r14_canonical` once configuration is stable.

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
