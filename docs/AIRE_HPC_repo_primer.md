# AIRE HPC — Context Primer for an LLM Assistant

> **How to use this file.** Paste the whole thing into a new chat with the assistant that will modify your repository, or keep it in the repo (e.g. as `AIRE.md` / part of `CLAUDE.md`). It tells the assistant how the cluster is configured and what the repository must look like to run there. Sections marked `<FILL IN>` are the only things you need to customise.

---

## 0. Your role (read first)

You are helping prepare a Python simulation repository to run on **AIRE**, the University of Leeds HPC cluster. Your job is to make code and configuration changes so the repo runs **unattended, as scheduled batch jobs, on shared compute nodes** — not interactively on a laptop. When you propose changes, conform to the rules and the repository contract below. These rules are **enforced by the cluster administrators**; violating the storage rules in particular can get the account suspended, so treat them as hard constraints, not suggestions.

Repository specifics:
- Repo name: `<FILL IN>`
- Main simulation entry point (current): `<FILL IN, e.g. src/main.py>`
- What one run produces: `<FILL IN, e.g. CSV time series + a few PNG figures>`
- Parallelism today: `<FILL IN: single-threaded? multiprocessing? numpy/BLAS-threaded? GPU?>`
- Typical sweep: `<FILL IN, e.g. 200 random seeds × 3 policy scenarios>`

---

## 1. How AIRE is configured

**Scheduler.** AIRE uses **Slurm**. You never run heavy work directly; you submit a *job script* and Slurm queues it, then runs it on a compute node when resources free up. Allocation is fair-share, not first-come-first-served.

**Node types you interact with:**
- **Login node** — where you SSH in. Use it only to edit files, manage data, build environments, and submit jobs. Do **not** run simulations here.
- **Compute nodes** — where jobs actually run. Standard nodes have **168 cores** and ~773 GB total (~4601 MB/core). You get a slice via Slurm, never by SSH-ing in directly.
- **GPU nodes** — request explicitly (see §5). Ordinary CPU code will not use a GPU.
- **High-memory nodes** — 2.32 TB each; request explicitly only if a job genuinely exceeds standard-node memory.

**Critical environment fact:** modules and conda environments loaded on the **login node do NOT carry over to a compute node.** Every job script must re-run its `module load` and `conda activate` lines itself. A new login shell is created for each job/interactive session and runs `.bashrc`.

**Software / Python.** Python is provided through the **Miniforge** module (conda/mamba, defaulting to the conda-forge channel — Anaconda is disallowed for licensing reasons). Load it with:
```bash
module load miniforge/24.7.1   # `module load miniforge` also works
```

---

## 2. Storage rules (HARD CONSTRAINTS)

There are two locations that matter. Verify the exact paths once on the cluster with `echo $HOME` and `echo $SCRATCH`.

| Location | Path | Env var | Quota | Backed up? | Use for |
|---|---|---|---|---|---|
| **Home** | `/users/<username>` | `$HOME` (`~`) | 65 GB, 1.5M files | **Yes** | Code, scripts, **conda environments** |
| **Scratch** | `/mnt/scratch/<username>` (some docs show `/mnt/scratch/users/<username>`) | `$SCRATCH` | 1 TB, 1.5M files | **No** | **All simulation output / large data** |

**Rules to obey in code and scripts:**
1. **Conda environments must live in `$HOME`.** Do not relocate `.conda`.
2. **All run output must be written under `$SCRATCH`,** never into `$HOME` and never inside the repo working tree. Writing job output into home can degrade the system for everyone and risks account suspension.
3. Scratch is **not backed up** and is **not auto-cleaned** — code should write self-describing, organised output (e.g. one subdirectory per run/parameter set) so results can be found and pruned later. Anything precious must be copied to home or off-cluster afterwards.

---

## 3. Repository contract (what you must ensure exists)

Make the repo satisfy all of the following. If something is missing, add it.

### 3.1 `environment.yaml` at the repo root
AIRE builds environments from a conda YAML file, not `requirements.txt`. Create/maintain `environment.yaml`:
```yaml
name: <env-name>
dependencies:
  - python=3.12          # pin the interpreter
  - numpy
  - pandas
  - <other conda-forge packages>
  - pip
  - pip:
      - <packages only available via pip>
```
- Pin anything where a version change would break behaviour; leave the rest flexible.
- Keep this file authoritative: add packages **here** and rebuild, rather than via ad-hoc `conda install`. Update an existing env with `conda env update --file environment.yaml --prune` (the `--prune` prevents the env from bloating the 65 GB home quota).
- If a current `requirements.txt` exists, translate its contents into this file (conda-forge names where possible, otherwise under the `pip:` block).

### 3.2 A single, parameterised entry point
The main simulation file must be runnable **headless from the command line with all parameters passed as arguments** (or a config file path) — no interactive prompts, no editing source to change parameters. Use `argparse`:
```python
import argparse, os

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--scenario", type=str, default="baseline")
    # ... all other run parameters ...
    p.add_argument("--outdir", type=str, required=True,
                   help="Output directory (point at $SCRATCH at submit time)")
    return p.parse_args()

def main():
    args = parse_args()
    os.makedirs(args.outdir, exist_ok=True)   # never assume the dir exists
    # ... run simulation, write all artefacts under args.outdir ...

if __name__ == "__main__":
    main()
```
Requirements for this entry point:
- **Output location comes from `--outdir`** and nothing is hardcoded. The submit script sets `--outdir` to a path under `$SCRATCH`.
- **`os.makedirs(outdir, exist_ok=True)`** so a fresh compute node doesn't fail on a missing folder.
- **Seed/parameters fully controllable via args** so the same code runs across a parameter sweep (see array jobs, §5).
- **Determinism:** seed all RNGs (`random`, `numpy`, framework RNGs) from `--seed` for reproducibility.

### 3.3 Headless execution
- If matplotlib is used, force a non-interactive backend **before** importing pyplot, and save figures instead of showing them:
  ```python
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  # ... plt.savefig(os.path.join(args.outdir, "fig.png")) ...  # never plt.show()
  ```
- No Jupyter/Spyder/RStudio-style interactive development on the cluster — it is explicitly discouraged. Code must be runnable as `python entry_point.py <args>`.

### 3.4 Logging
- Write progress/log messages to **stdout/stderr** (use the `logging` module or prints). Slurm captures these into the job's `.out`/`.err` files automatically, which is how runs are monitored and debugged. Do not depend on a live terminal.

### 3.5 Tests (recommended)
- Keep the test suite runnable with `pytest`. A green suite is what lets the environment be updated safely without silently breaking results.

---

## 4. End-to-end workflow on AIRE

This is the full sequence from empty account to results. Steps 1–4 happen once (or when dependencies change); steps 5–7 happen per experiment.

```bash
# 1. Get the code (run on the login node)
cd ~
git clone <repo-url>            # private repo: use a PAT or an SSH key added to GitHub
cd <repo>

# 2. Build the conda environment (lives in $HOME)
module load miniforge/24.7.1
conda env create -f environment.yaml
conda activate <env-name>

# 3. Smoke-test ONCE, interactively, on a compute node (not the login node)
srun -t 00:30:00 --pty /bin/bash      # grabs an interactive compute node
module load miniforge/24.7.1          # re-load: login-node env does NOT carry over
conda activate <env-name>
python <entry_point> --seed 0 --outdir $SCRATCH/<repo>/smoketest
exit                                  # releases the interactive node

# 4. Make a scratch output area for real runs
mkdir -p $SCRATCH/<repo>/runs

# 5. Submit a batch job (see template in §5)
sbatch run_job.sh                     # returns a job ID, e.g. "Submitted batch job 42"

# 6. Monitor
squeue --me                           # R = running, PD = pending/queued
tail -f $SCRATCH/<repo>/runs/slurm-<jobid>.out   # watch live output
scancel <jobid>                       # cancel if needed

# 7. Collect results from $SCRATCH; copy anything to keep into $HOME or off-cluster
```

---

## 5. Slurm job-script templates

### 5.1 Single batch job (`run_job.sh`)
```bash
#!/bin/bash
#SBATCH --job-name=sim_run
#SBATCH --time=02:00:00            # REQUIRED. hh:mm:ss (or d-hh:mm:ss). Add ~20% margin; job is killed if exceeded.
#SBATCH --cpus-per-task=1          # Set to the number of cores the code actually uses. Default 1.
#SBATCH --mem=4G                   # Memory per node. Default 1G. Don't over-request.
#SBATCH --ntasks=1
#SBATCH --output=%x_%j.out         # %x = job name, %j = job id
#SBATCH --error=%x_%j.err

module load miniforge/24.7.1       # MUST be in the script; login-node modules don't carry over
conda activate <env-name>

OUTDIR=$SCRATCH/<repo>/runs/run_${SLURM_JOB_ID}
python <entry_point> --seed 0 --scenario baseline --outdir "$OUTDIR"
```

### 5.2 Parameter sweep via task array (`run_array.sh`)
Use this to run the **same code many times with different parameters** in one submission — this is the main reason to use the cluster for simulation work. Slurm sets `$SLURM_ARRAY_TASK_ID` for each task; map it to a parameter (here, a seed).
```bash
#!/bin/bash
#SBATCH --job-name=sim_sweep
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --array=0-199              # 200 tasks; $SLURM_ARRAY_TASK_ID runs 0..199
#SBATCH --output=%x_%A_%a.out      # %A = array job id, %a = task index
#SBATCH --error=%x_%A_%a.err

module load miniforge/24.7.1
conda activate <env-name>

OUTDIR=$SCRATCH/<repo>/runs/sweep_${SLURM_ARRAY_JOB_ID}/task_${SLURM_ARRAY_TASK_ID}
python <entry_point> --seed ${SLURM_ARRAY_TASK_ID} --scenario baseline --outdir "$OUTDIR"
```
Submit with a single `sbatch run_array.sh`; cancel all tasks with a single `scancel <array_job_id>`. For sweeps over multiple dimensions (e.g. seed × scenario), either widen the array and compute both indices from `$SLURM_ARRAY_TASK_ID`, or read a parameter table line keyed by the task id.

### 5.3 GPU job (only if the code is GPU-enabled)
```bash
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
# also: module load cuda   (or provide CUDA via the conda env), inside the script
```

### 5.4 High-memory job (only if standard-node memory is insufficient)
```bash
#SBATCH --partition=himem
```

### Key `#SBATCH` options
| Option | Meaning | Default |
|---|---|---|
| `--time=hh:mm:ss` / `-t` | Wall-clock limit. **Required.** Job killed if exceeded; large over-estimates delay scheduling. | — |
| `--cpus-per-task=N` / `-c` | Cores per task (for threaded code). | 1 |
| `--mem=<size>` | Memory per node (e.g. `8G`). | 1G |
| `--mem-per-cpu=<size>` | Memory per core (alternative to `--mem`). | 1G |
| `--ntasks=N` / `-n` | Number of tasks/processes (MPI). | 1 |
| `--array=<a>-<b>` | Task array; sets `$SLURM_ARRAY_TASK_ID`. | — |
| `--partition=<name>` / `-p` | Non-standard pool: `gpu`, `himem`. | standard |
| `--gres=gpu:N` | Request N GPUs (with `--partition=gpu`). | — |
| `--output` / `--error` | Stdout/stderr file patterns (`%x` name, `%j` id, `%A`/`%a` array). | — |
| `--mail-type=END,FAIL` + `--mail-user=...@leeds.ac.uk` | Email on job events. | — |

---

## 6. Gotchas to avoid

- **Resource requests must match reality.** A single-threaded Python script uses one core regardless of `--cpus-per-task`; requesting many cores just wastes the allocation and lengthens the queue wait. If the code is parallel (multiprocessing / threaded BLAS / Dask), set `--cpus-per-task` to match and configure the library's worker/thread count accordingly.
- **Re-load modules in every script** — login-node setup does not persist to compute nodes.
- **Windows line endings break scripts** (`/bin/bash^M: bad interpreter`). If a `.sh` file is edited on Windows, run `dos2unix run_job.sh` on the cluster.
- **Never write output into `$HOME` or the repo tree** — only under `$SCRATCH`.
- **Scratch is not backed up.** Copy anything that must survive into `$HOME` or off-cluster.
- **Snapshot the environment with results** for reproducibility, e.g. add to the job script:
  `conda env export > "$OUTDIR/env-record.yaml"`.

---

## 7. Definition of done (verify before declaring the repo ready)

- [ ] `environment.yaml` exists at repo root and builds cleanly with `conda env create -f environment.yaml`.
- [ ] A single CLI entry point runs the simulation headless with all parameters as arguments.
- [ ] Output directory is taken from `--outdir`; nothing is hardcoded; the entry point `makedirs(..., exist_ok=True)`.
- [ ] No interactive plotting / no `plt.show()`; matplotlib (if used) set to `Agg`.
- [ ] RNGs seeded from `--seed`; a fixed seed reproduces a run.
- [ ] Logging goes to stdout/stderr.
- [ ] `run_job.sh` and `run_array.sh` exist, load the module + activate the env inside the script, and point `--outdir` at `$SCRATCH`.
- [ ] A 30-minute interactive smoke test (`srun --pty`) completes one run end-to-end.
- [ ] `pytest` passes.
