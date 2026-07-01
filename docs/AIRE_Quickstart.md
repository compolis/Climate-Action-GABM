# AIRE Quickstart — from zero to a split50 Run-14

A repo-specific, copy-pasteable walkthrough for running Climate-Action-GABM on Leeds's [AIRE](https://arc.leeds.ac.uk/aire/) HPC. By the end you will have:

1. A working clone of the repo on AIRE with the conda env and vLLM container in place.
2. A completed **smoke** job (~5–15 min) verifying the full pipeline.
3. A submitted **split50 Run-14** job (~40–90 min on Qwen3-14B) producing the canonical CSVs and PNGs.
4. The mental model — and the flag reference — to compose a third experiment without editing any code.

This document is the repo-specific walkthrough. For generic AIRE / Slurm fundamentals (account setup, storage rules, `#SBATCH` reference, partitions), see the companion primer: [AIRE_HPC_repo_primer.md](AIRE_HPC_repo_primer.md). This quickstart links to it rather than duplicating it.

> **Mac local dev sidebar.** Most steps work locally too. On a Mac, start `mlx_lm.server --port 8080` with `mlx-community/Qwen3-8B-4bit`, then run `PYTHONPATH=src python -m cag --preset smoke --outdir data/output/smoke`. `SIM_CONFIG` defaults already point at `http://localhost:8080/v1` so nothing else is needed. The rest of this guide assumes AIRE.

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [SSH into AIRE](#2-ssh-into-aire)
3. [One-time prep on AIRE](#3-one-time-prep-on-aire)
4. [Free sanity checks (no GPU)](#4-free-sanity-checks-no-gpu)
5. [First sbatch — the smoke job](#5-first-sbatch--the-smoke-job)
6. [First real experiment — split50 Run-14](#6-first-real-experiment--split50-run-14)
7. [Reading the output](#7-reading-the-output)
8. [Pull results back to your laptop](#8-pull-results-back-to-your-laptop)
9. [Monitoring and cancelling jobs](#9-monitoring-and-cancelling-jobs)
10. [Modifying for your next experiment — the flag reference](#10-modifying-for-your-next-experiment--the-flag-reference)
11. [Resume a killed job](#11-resume-a-killed-job)
12. [Multi-job sweep](#12-multi-job-sweep)
13. [Common errors and fixes](#13-common-errors-and-fixes)
14. [Updating the repo on AIRE later](#14-updating-the-repo-on-aire-later)

---

## 1. Prerequisites

| You need | Why | How |
| --- | --- | --- |
| An AIRE account | To `ssh` and run jobs | Request via the Leeds RSE / ARC team (see [primer §1](AIRE_HPC_repo_primer.md)) |
| GitHub access to the repo | To `git clone` | Account with read access to `ajaymanivannan/Climate-Action-GABM` |
| A Hugging Face account | To download the model weights | Free at <https://huggingface.co>; create a **read** token at *Settings → Access Tokens* |
| An SSH client locally | To reach AIRE | macOS/Linux: built-in `ssh`. Windows: WSL or PuTTY |

If anything is missing, stop here and fix it before continuing. The rest of this guide assumes you can `ssh` into AIRE.

---

## 2. SSH into AIRE

From your laptop:

```bash
ssh <your-username>@<aire-login-host>
```

(See the primer for the actual login host name and any required VPN.) You should land in your `$HOME` on a login node. Everything below runs on AIRE unless explicitly marked **(on your laptop)**.

**Next:** verify your shell is on AIRE (`hostname` should report a login node), then continue to §3.

---

## 3. One-time prep on AIRE

Do these steps once per AIRE account. If you re-clone the repo, you only need to repeat §3.4 (clone) and possibly §3.5 (env), not the rest.

> **⚠ Every new login shell needs `module load miniforge`.** AIRE does **not** auto-load conda — in a fresh shell `conda activate cag` will give you `conda: command not found` until you load the module. The same goes for `module add apptainer` if you ever re-pull the SIF. If you want it automatic, append `module load miniforge` to `~/.bashrc`.

### 3.1 Move to your home directory

```bash
cd ~
```

### 3.2 Generate an SSH key on AIRE and add it to GitHub

The repo is private. The cleanest way to clone is with an SSH key generated **on the AIRE login node** and registered with GitHub.

> **Alternative — HTTPS + PAT.** If you can't use SSH for any reason, you can clone over HTTPS with a [GitHub Personal Access Token](https://github.com/settings/tokens) (fine-grained, "Contents: Read" on the repo). Replace step 4 below with `git clone https://<token>@github.com/ajaymanivannan/Climate-Action-GABM.git`. We recommend SSH because the token doesn't end up baked into your remote URL.

**Step 1 — generate the key pair on AIRE.** Press Enter at every prompt to accept defaults (no passphrase is fine on a personal AIRE account; add one if you prefer).

```bash
ssh-keygen -t ed25519 -C "you@example.com"
```

You'll get:

```text
Your identification has been saved in /home/<user>/.ssh/id_ed25519
Your public key has been saved in /home/<user>/.ssh/id_ed25519.pub
```

**Step 2 — print the public key so you can copy it.**

```bash
cat ~/.ssh/id_ed25519.pub
```

Copy the **entire line** (starts with `ssh-ed25519`, ends with your email comment).

**Step 3 — register it with GitHub.** On your laptop browser:

- For account-wide access: <https://github.com/settings/keys> → *New SSH key* → paste → save.
- For repo-only access (deploy key): the repo's *Settings → Deploy keys → Add deploy key* → paste → save (leave write access off).

**Step 4 — verify from AIRE.**

```bash
ssh -T git@github.com
```

Expected:

```text
Hi <your-github-username>! You've successfully authenticated, but GitHub does not provide shell access.
```

If you see "Permission denied (publickey).", the key wasn't registered correctly — go back to step 3.

### 3.3 Clone the repo

Still in `$HOME`:

```bash
git clone git@github.com:ajaymanivannan/Climate-Action-GABM.git
cd Climate-Action-GABM
```

> **If your AIRE key isn't the default `~/.ssh/id_ed25519`** (e.g. you keep a dedicated `~/.ssh/aire_repo`), the bare `git clone git@...` form won't pick it up. Use:
>
> ```bash
> git clone -c core.sshCommand="ssh -i ~/.ssh/aire_repo -o IdentitiesOnly=yes" \
>     git@github.com:ajaymanivannan/Climate-Action-GABM.git
> cd Climate-Action-GABM
> git config core.sshCommand "ssh -i ~/.ssh/aire_repo -o IdentitiesOnly=yes"
> ```
>
> The first command clones with the right key; the second persists it in `.git/config` so future `git pull`/`fetch` use the same key without flag soup. `IdentitiesOnly=yes` stops ssh from trying every other key in your agent first (which can trigger `Permission denied` on accounts with multiple GitHub identities).

### 3.4 Build the conda environment

```bash
module load miniforge
conda env create -f environment.yaml
```

This creates a conda env named `cag` with every Python dependency. First-time build takes ~5–10 minutes. If it ever drifts (someone added a dependency), update with `conda env update -f environment.yaml --prune` from inside the repo.

### 3.5 Hugging Face token

`scripts/aire/run.sh` reads `HF_TOKEN` from either an environment variable **or** the file `~/.cache/huggingface/token`. The persistent file is recommended — it survives across all future logins and never lands in shell history or environment-variable dumps.

Grab a **read** token at <https://huggingface.co/settings/tokens> first. Fine-grained `Read` is sufficient. While you're signed in, also accept the model licence at <https://huggingface.co/Qwen/Qwen3-14B> — otherwise the first sbatch will 401 on download even with a valid token.

**Recommended — write the token file directly** (no extra dependency, no shell-history leak):

```bash
mkdir -p ~/.cache/huggingface && \
    read -rsp 'Paste HF token: ' HF_TOKEN_VAL && \
    printf '%s' "$HF_TOKEN_VAL" > ~/.cache/huggingface/token && \
    chmod 600 ~/.cache/huggingface/token && \
    unset HF_TOKEN_VAL && echo
```

`read -rsp` reads silently (your token is not echoed and not stored in `~/.bash_history`); `printf '%s'` writes the token with no trailing newline; `chmod 600` locks it to your user only; `unset` clears it from the shell.

**Verify the file exists, and inspect what you actually wrote:**

```bash
[[ -r ~/.cache/huggingface/token ]] && echo OK || echo MISSING
wc -c ~/.cache/huggingface/token   # ~37 bytes for a fresh HF token; ~74 = you double-pasted
cat ~/.cache/huggingface/token; echo   # look at it; the file is chmod 600 so only you can read it
```

If the byte count or contents look wrong, just rerun the write command — it overwrites cleanly.

> **Alternative — environment variable.** `echo 'export HF_TOKEN=hf_...' >> ~/.bashrc && source ~/.bashrc`. Works, but the token now sits plaintext in your dotfile and any subprocess can see it via `env`. Prefer the file form above.
>
> **Alternative — `huggingface-cli login`.** Writes the same file. Requires installing `huggingface_hub` (`pip install huggingface_hub` inside the `cag` env). Skip it unless you want the CLI for other reasons — the sim itself doesn't need it.

### 3.6 Pull the vLLM container

`scripts/aire/run.sh` defaults to `$HOME/vllm-openai-v0.8.5.sif` — pulled once, reused forever. Pinned at `v0.8.5` for reproducibility.

```bash
cd ~
module add apptainer
apptainer pull docker://vllm/vllm-openai:v0.8.5
```

You'll get `vllm-openai-v0.8.5.sif` (~6 GB) in `$HOME`. The script finds it there by default; override with `SIF_IMAGE=/path/to/other.sif sbatch ...` if you put it elsewhere.

**Next:** all one-time prep is done. Return to the repo (`cd ~/Climate-Action-GABM`) and continue to §4.

---

## 4. Free sanity checks (no GPU)

Before submitting a job (which queues for a GPU), confirm the env is healthy. These two commands run on the login node, take milliseconds, and burn zero compute budget.

> **Fresh login?** `module load miniforge` first, otherwise `conda activate` will report `conda: command not found`. See the box at the top of §3.

```bash
cd ~/Climate-Action-GABM
module load miniforge
conda activate cag
PYTHONPATH=src python -m cag --list-presets
```

Expected (abbreviated):

```text
smoke
  Fast smoke-test run shape: 10 agents, 2 days, no peer messaging. ...
  config:
    n_citizens = 10
    days = 2
    k_peers_per_day = 0
    thinking = False

r14_canonical
  Run-14 baseline run shape: 50 agents, 5 days, ...
  config:
    n_citizens = 50
    days = 5
    ...
```

Now dry-run the smoke preset — this resolves the final `SIM_CONFIG` overrides and prints JSON without ever calling an LLM:

```bash
PYTHONPATH=src python -m cag --preset smoke --dry-run
```

If both commands print sensible output, your env imports cleanly and your CLI is wired up. **Next:** submit the smoke sbatch (§5).

---

## 5. First sbatch — the smoke job

A 10-agent, 2-day run that exercises every code path (server bring-up, prompt chain, surveys, peer messaging skipped, CSV write, plot render). Use it as a cheap canary before your real run.

```bash
cd ~/Climate-Action-GABM
sbatch scripts/aire/run.sh --preset smoke
```

Expected immediate output:

```text
Submitted batch job 12345
```

Wall-clock estimate: **~5–15 minutes**. The first time you run any sbatch, vLLM also has to download the model weights (a few GB), which can extend the first job by 10–20 min.

**Which model does the smoke run use?** The `smoke` preset does **not** pin a model — it's a pure run-shape bundle. On AIRE, `scripts/aire/run.sh` hardcodes `--model "$HF_MODEL"`, and `HF_MODEL` defaults to `Qwen/Qwen3-14B` (served by vLLM inside the SIF). To test a different model, prefix the sbatch line: `HF_MODEL=other/model sbatch scripts/aire/run.sh --preset smoke`.

What the command does:

- `scripts/aire/run.sh` is a thin Slurm script. It boots a vLLM server on this node, waits until `http://localhost:8000/v1/models` answers, then runs `python -m cag --provider local --base-url ... --outdir $SCRATCH/cag/runs/run_<jobid> <your flags>`. The trailing `--preset smoke` is forwarded verbatim.
- Output goes to `$SCRATCH/cag/runs/run_<jobid>/`.
- The Slurm stdout/stderr files (`LLM-cag-run_<jobid>.out`/`.err`) land in the directory you submitted from (the repo root).

**Next:** monitor it with §9, then move on to §6 once the job finishes successfully.

---

## 6. First real experiment — split50 Run-14

Once the smoke succeeds, submit the canonical research run. Same `run.sh`, different flags.

```bash
sbatch scripts/aire/run.sh \
    --preset r14_canonical \
    --exposure-targets split50
```

Translation of every part of that command:

| Token | What it does |
| --- | --- |
| `sbatch scripts/aire/run.sh` | Queue the AIRE launcher script (vLLM bring-up + `python -m cag` + cleanup) |
| `--preset r14_canonical` | Apply the Run-14 baseline bundle (50 agents, 5 days, `k_peers_per_day=0`, `day0_anchor=ground_truth_with_rationale`, `thinking=False`, and the default `memory` preset; the Condition-B two-step survey is always on) |
| `--exposure-targets split50` | Pin the political-exposure mix to a `{A-only: 0.5, B-only: 0.5}` split (everyone gets exactly one side's broadcasts). This is the canonical persuasion test condition |

Wall-clock estimate: **~40–90 minutes** depending on prompt yield with Qwen3-14B.

> **Important — first-time model download.** The first time you submit with a model that isn't already in the Hugging Face cache, the model download can exceed the **1500 s** vLLM-readiness wait baked into `run.sh`, and the job will fail before any LLM call. Use **`--time=06:00:00`** on that first submission (next code block). Once cached, subsequent runs warm up in < 2 min and the standard wall-clock is fine.

Per-day checkpointing is **on by default** — every run writes `<outdir>/checkpoints/` after each completed day, so a wall-clock kill always leaves the most recent completed day on disk and you can `--resume` it (see §11). If you want extra headroom for a longer run:

```bash
sbatch --time=06:00:00 scripts/aire/run.sh \
    --preset r14_canonical \
    --exposure-targets split50
```

`--time` is an `sbatch` flag — it overrides the `#SBATCH --time` header inside the script. Any Slurm directive is overridable this way (`--mem=120G`, `--cpus-per-task=16`, ...). Pass `--no-checkpoint-every-day` to the Python CLI if you want to skip checkpoints for a throwaway smoke test.

**Next:** while it runs, read §7 so you know what to look for when it finishes.

---

## 7. Reading the output

Each run lands in `$SCRATCH/cag/runs/run_<jobid>/`. Layout:

```text
run_<jobid>/
├── run.log                          # full sim log; final TIMING block is the summary
├── vllm_server.log                  # server bring-up; first lines confirm which model loaded
├── config.json                      # exact resolved SIM_CONFIG (the run's fingerprint)
├── opinion_trajectories.csv         # per-(agent, day, policy) numeric opinion
├── package_index_trajectories.csv   # per-(agent, day) pro-climate index (package mode only)
├── opinion_shares.csv               # derived: % support over time, per policy
├── package_index_shares.csv         # derived: % support over time, package level
├── reflections.csv                  # internal monologue after each exposure event
├── messages.csv                     # every broadcast and peer message, sender→recipient
├── survey_reasoning.csv             # end-of-day survey rationale
├── survey_raw_response.csv          # raw LLM survey text (pre-parse)
├── daily_summaries.csv              # per-day per-agent compressed memory
├── ground_truth.csv                 # YouGov anchor values per (agent, policy)
├── package_ground_truth.csv         # YouGov anchor index (package mode only)
├── opinion_trajectory.png           # plot
├── package_index_trajectories.png   # plot
├── opinion_shares.png               # plot
├── package_index_shares.png         # plot
└── checkpoints/                     # always (default-on); use --no-checkpoint-every-day to suppress
    └── checkpoint_meta.json + per-day CSV dumps
```

What to check first when a run finishes:

1. **`run.log` final TIMING block.** Confirms simulation time, per-agent-day cost, no late crashes.
2. **`config.json`.** The exact resolved configuration. If two runs disagree, diff their `config.json`s — that's the ground truth, not your sbatch line.
3. **`vllm_server.log` first 50 lines.** Confirms `Loading model 'Qwen/Qwen3-14B'` (or whatever you intended) — catches the "I thought I asked for X but got Y" class of bugs.
4. **`opinion_trajectories.csv`.** A non-empty file with `5 days × 50 agents × 6 policies = 1500` rows for a default r14 run. Sanity: agents.unique() should be 50, days.max() should be 4 (zero-indexed).

**Next:** transfer results to your laptop for analysis (§8) and/or move to your second experiment via §10.

---

## 8. Pull results back to your laptop

> **⚠ Run this on your laptop, NOT inside the AIRE ssh session.** The destination path (`~/cag_results/...`) lives on your laptop. If you run `rsync` while still ssh'd into AIRE you'll get `mkdir failed: No such file or directory` because that path doesn't exist on the login node. Either `exit` the AIRE shell first, or open a fresh terminal on your laptop.

`rsync` over SSH. The filter pulls CSVs / PNGs / JSON / logs and skips anything else.

```bash
LOCAL_DIR=~/cag_results/run_12345                          # on your laptop
REMOTE_DIR=<user>@<aire-login-host>:/mnt/scratch/<user>/cag/runs/run_12345

mkdir -p "$LOCAL_DIR"
rsync -avh \
    --include='*/' \
    --include='*.csv' --include='*.png' --include='*.json' --include='*.log' \
    --exclude='*' \
    "$REMOTE_DIR"/ "$LOCAL_DIR"/
```

Notes:

- **Use the literal `/mnt/scratch/<user>/...` path, not `$SCRATCH`.** `$SCRATCH` only expands on AIRE; from your laptop it's an empty string and rsync silently picks the wrong source.
- **`mkdir -p` first.** rsync creates the leaf directory but not its parents, so `~/cag_results/` must exist before the transfer or you'll get `mkdir failed`.
- **Trailing slash on `$REMOTE_DIR/`** copies the *contents* of the run dir into `$LOCAL_DIR`; drop it to nest the run dir inside instead.
- **Want the vLLM server log too?** It's already covered by `*.log`. To skip it explicitly, add `--exclude='vllm_server.log'`.
- **Off-campus / Duo MFA:** rsync over SSH triggers the same Duo two-factor prompt your interactive `ssh` does. You'll get an `SMS` / `Enter passcode` prompt mid-command; respond once and rsync proceeds. On-campus and VPN'd users skip this. See the `ControlMaster` tip below for skipping the Duo prompt on repeat connections.

**Shortcut — SSH config alias (Leeds AIRE goes through the `rash` bastion).** Put this once in `~/.ssh/config` on your laptop:

```sshconfig
Host rash
    HostName rash.leeds.ac.uk
    User <your-leeds-username>
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 10m

Host aire
    HostName aire.leeds.ac.uk
    User <your-leeds-username>
    ProxyJump rash
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 10m
```

What each line buys you:

- `ProxyJump rash` — AIRE login nodes aren't directly reachable from outside Leeds; ssh hops through `rash.leeds.ac.uk` automatically. No more manual bastion shell.
- `ControlMaster auto` + `ControlPath` + `ControlPersist 10m` — reuses one TCP connection (and one Duo authentication) for 10 min. The first `ssh aire` triggers Duo; the next `rsync aire:...` or `ssh aire` inside that window is instant.

After saving the config, every command shortens to `aire:/mnt/scratch/<user>/cag/runs/run_<jobid>/`:

```bash
rsync -avh aire:/mnt/scratch/<user>/cag/runs/run_<jobid>/ ~/cag_results/run_<jobid>/
```

**Next:** open the CSVs in your notebook of choice (see `notebooks/19_full_simulation.ipynb` for the canonical analysis pattern).

---

## 9. Monitoring and cancelling jobs

```bash
squeue --me                                  # all your queued/running jobs
squeue -j <jobid>                            # one job
tail -f LLM-cag-run_<jobid>.out              # live stdout (the .out file is in your submit dir)
sacct -j <jobid> --format=JobID,State,Elapsed,MaxRSS,ExitCode   # post-mortem accounting
scancel <jobid>                              # cancel a job
```

Useful patterns:

```bash
# Cancel every running cag job you submitted:
scancel --user="$USER" --name=LLM-cag-run

# Tail the most recently submitted job:
tail -f $(ls -t LLM-cag-run_*.out | head -1)

# Track GPU utilisation on a running job (jump onto the node):
srun --jobid=<jobid> --pty nvidia-smi
```

See the [primer §4](AIRE_HPC_repo_primer.md) for the full Slurm reference.

---

## 10. Modifying for your next experiment — the flag reference

Every `SIM_CONFIG` knob is a `--flag`. To test a new hypothesis, compose flags on the sbatch line — **do not edit the script**. Tables below group every available flag by category. Defaults marked "SIM_CONFIG" mean: omit the flag and `cag.abm.sim.SIM_CONFIG` supplies the value. Preset values override SIM_CONFIG; CLI flags override the preset.

### 10.1 Run shape

How long and how big the run is.

| Flag | Type | Default | Use when you want to... |
| --- | --- | --- | --- |
| `--n-citizens N` | int | (required) | Change the agent pool size. R14 used 50; smoke uses 10 |
| `--days D` | int | (required) | Change the number of simulated days. Expands to alternating P-A/P-B/C |
| `--k-peers K` | int | SIM_CONFIG (`3`) | Set peer-messaging count per agent per day. `0` disables peer messaging (broadcast-only research mode) |
| `--seed N` | int | SIM_CONFIG (`42`) | Vary the random seed (different agent sample + RNG paths) |

### 10.2 LLM

Which model serves the prompts and how.

| Flag | Type | Default | Use when you want to... |
| --- | --- | --- | --- |
| `--provider P` | str | SIM_CONFIG (`local`) | Swap provider (`local`, `openai`, `anthropic`, `genai`). On AIRE, `run.sh` already forces `local` |
| `--model M` | str | SIM_CONFIG (`mlx-community/Qwen3-8B-4bit`) | Tell the client which model name to ask for. On AIRE, `run.sh` already forces `$HF_MODEL` |
| `--base-url URL` | str | SIM_CONFIG (Mac `:8080/v1`) | Point at a non-default local endpoint. On AIRE `run.sh` injects `http://localhost:8000/v1` |
| `--temperature T` | float | SIM_CONFIG (`0.5`) | Tune sampling stochasticity. Higher = more diverse, more failure modes |
| `--thinking` / `--no-thinking` | bool | SIM_CONFIG (`False`) | Enable / disable model "thinking" reasoning. Slows runs; rarely a research win |
| `--survey-model M` | str | None | Use a different model just for end-of-day surveys (dual-model runs) |
| `--survey-provider P` | str | None | Same, but for the provider |
| `--local-timeout S` | float | SIM_CONFIG | Bump the per-request HTTP timeout for slow models |
| `--local-extra-body '{"k":v}'` | JSON | None | Inject vLLM-specific request body kwargs (e.g. `top_k`) |

To swap the served model on AIRE, set `HF_MODEL` (an env var read by `run.sh`):

```bash
HF_MODEL=swiss-ai/Apertus-8B-2509 sbatch scripts/aire/run.sh --preset r14_canonical --exposure-targets split50
```

### 10.3 Exposure

Which agents see which political broadcasts.

| Flag | Type | Default | Use when you want to... |
| --- | --- | --- | --- |
| `--exposure-mode M` | enum | SIM_CONFIG (`rule_affinity_rank`) | Pick the assignment algorithm (`rule_priority_chain`, `rule_signal_count`, `rule_affinity_rank`) |
| `--exposure-targets X` | preset OR JSON | SIM_CONFIG (`committed_minority_symmetric`) | Set the target mix. Preset names: `split50`, `neither`, `committed_minority_symmetric`, `committed_minority_uk_2024`, `legacy_v05`. OR a JSON dict like `'{"A-only":0.5,"B-only":0.5,"both":0,"neither":0}'` |
| `--affinity-weights W` | preset OR JSON | SIM_CONFIG (`balanced`) | Pick the affinity-score weighting (`balanced`, `vote_dominant`, `values_dominant`) or supply a literal dict |

### 10.4 Broadcast / audience

How political broadcasts reach the agents they're matched to.

| Flag | Type | Default | Use when you want to... |
| --- | --- | --- | --- |
| `--reach-a R` | float (0–1) | SIM_CONFIG (`1.0`) | Subsample agent_a's audience each broadcast (reach asymmetry experiments) |
| `--reach-b R` | float (0–1) | SIM_CONFIG (`1.0`) | Same, for agent_b |
| `--audience-cap N` | int or `none` | SIM_CONFIG (`none`) | Hard-cap each political agent's audience size before reach subsampling |
| `--message-source S` | enum | SIM_CONFIG (`offline`) | `offline` = use the curated message pool; `llm` = generate per-day on the fly |
| `--message-set V` | str | SIM_CONFIG (`v1`) | Pick a versioned offline pool under `data/political_messages/` |

### 10.5 Structure

Higher-level shape of the experiment.

| Flag | Type | Default | Use when you want to... |
| --- | --- | --- | --- |
| `--communication-mode M` | enum | SIM_CONFIG (`package`) | `package` = broadcast all policies together; `single_policy` = one policy per phase |
| `--package-policies P` | `all` or `1,3,5` | SIM_CONFIG (`all`) | Restrict the package to a subset of policy IDs |
| `--day0-anchor A` | enum | SIM_CONFIG (`ground_truth_with_rationale`) | Pick Day-0 seeding (`llm_survey`, `ground_truth`, `ground_truth_with_rationale`) |
| `--memory X` | preset OR JSON | SIM_CONFIG (`default`) | Set the agent memory / prompt-assembly config. Preset names: `default`, `short_memory`, `wide_memory`, `no_compression`, `no_anchor`, `anchor_ttl2`, `no_own_reasoning`, `reflections_only`, `persona_only`. OR a JSON dict of section toggles / `verbatim_window_days` / per-stage overrides |
| `--network-type T` | str | SIM_CONFIG (`stochastic_block`) | Peer network factory (`stochastic_block`, `watts_strogatz`, `barabasi_albert`, `erdos_renyi`) |
| `--network-params '{...}'` | JSON | None | Per-factory parameter dict |
| `--p-intra X` | float | SIM_CONFIG (`0.15`) | Legacy stochastic-block intra-block edge probability |
| `--p-inter X` | float | SIM_CONFIG (`0.02`) | Legacy stochastic-block inter-block edge probability |
| `--diagnostics-timeout S` | float | SIM_CONFIG (`30.0`) | Wall-clock cap on the network-diagnostics block |

### 10.6 Checkpoint / resume

Per-day checkpointing is on by default so any wall-clock kill is recoverable.

| Flag | Type | Default | Use when you want to... |
| --- | --- | --- | --- |
| `--checkpoint-every-day` | flag | **on** | Default. Dumps full CSV bundle to `<outdir>/checkpoints/` after every day |
| `--no-checkpoint-every-day` | flag | — | Opt out (throwaway smoke tests; saves a small per-day I/O cost) |
| `--resume` | flag | off | Pick up where a killed run left off (see §11). Implies checkpointing on |

### Worked examples

```bash
# Reach-asymmetry sweep with a longer wall-clock (checkpoints default-on):
sbatch --time=06:00:00 scripts/aire/run.sh \
    --preset r14_canonical \
    --exposure-targets split50 \
    --reach-a 0.5 --reach-b 1.0

# Single-policy mode on Carbon Tax (id=5), 30 agents, smaller network:
sbatch scripts/aire/run.sh \
    --n-citizens 30 --days 5 --k-peers 0 \
    --communication-mode single_policy --package-policies 5 \
    --exposure-targets split50

# Bypass the offline message pool and have the LLM generate political text:
sbatch scripts/aire/run.sh \
    --preset r14_canonical \
    --exposure-targets split50 \
    --message-source llm

# Inline JSON for a one-off exposure mix (no preset name needed):
sbatch scripts/aire/run.sh \
    --preset r14_canonical \
    --exposure-targets '{"A-only":0.4,"B-only":0.4,"both":0.1,"neither":0.1}'

# Memory ablation — drop the Day-0 anchor to test how much it pins opinions
# (compare against the same run with --memory default):
sbatch scripts/aire/run.sh \
    --preset r14_canonical \
    --exposure-targets split50 \
    --memory no_anchor

# Hand-tuned memory — widen the verbatim window and hide the anchor at survey
# time only (inline JSON):
sbatch scripts/aire/run.sh \
    --preset r14_canonical \
    --exposure-targets split50 \
    --memory '{"verbatim_window_days":3,"stages":{"survey":{"day0_anchor":{"enabled":false}}}}'
```

The exact memory config each job used is printed on the startup `[memory]` line in `run.log` and stored in `config.json → memory_resolved`, so ablation variants are always auditable after the fact.

**Next:** the new experiment is just a new `sbatch` line. No script edit, no commit.

---

## 11. Resume a killed job

If a job hits the wall-clock limit (or is cancelled, or the node dies), you can resume from the last completed day — checkpoints are on by default so this works for every run unless you explicitly passed `--no-checkpoint-every-day`:

```bash
RESUME_FROM=$SCRATCH/cag/runs/run_<old_jobid> sbatch scripts/aire/run.sh \
    --preset r14_canonical \
    --exposure-targets split50
```

The new job:

- Writes back into the **same** `OUTDIR` (`$RESUME_FROM`). Don't pass `--outdir`; `run.sh` sets it from `RESUME_FROM`.
- Forwards `--resume` to `python -m cag` automatically.
- Replays from `<outdir>/checkpoints/` and continues.

Resume contract — checked at startup, fails loudly on mismatch:

- **Hard keys (must match exactly):** `n_citizens`, `random_seed`, `network_type`, `communication_mode`, `package_policies`, `day0_anchor`, `reach_a`, `reach_b`, `audience_cap`, `political_exposure_mode`, `political_exposure_targets`, `affinity_weights`, `political_message_source`, `political_message_set`, `memory`. Structural — changing these would invalidate prior agent state. (`memory` is hard because the verbatim window drives which days get compressed into `daily_summaries`, so a mid-run change would make the stored summaries inconsistent.)
- **Soft keys (changeable; warning emitted):** `llm_model`, `llm_provider`, `survey_model`, `survey_provider`, `thinking`, `llm_temperature`, `local_base_url`, `local_extra_body`, `local_timeout_s`. You can swap models mid-run if you really want to.

If you need to change a hard key, start a fresh run instead of resuming.

**Next:** for a planned multi-condition study, prefer §12 over manual repeated `sbatch`.

---

## 12. Multi-job sweep

For ≥3 related jobs (different exposure targets, different reach values, etc.), use the sweep wrapper: one text file lists the per-job flag suffix on each line, the wrapper submits one `sbatch` per line.

The shipped example, [scripts/aire/sweeps/r14_v2.txt](../scripts/aire/sweeps/r14_v2.txt):

```text
--preset r14_canonical --exposure-targets split50
--preset r14_canonical --exposure-targets neither
--preset r14_canonical --exposure-targets neither --day0-anchor llm_survey
```

Submit all three:

```bash
bash scripts/aire/sweep.sh scripts/aire/sweeps/r14_v2.txt
```

Each line becomes one `sbatch scripts/aire/run.sh <that line>`. The wrapper prints every submitted job ID and appends them to `<sweep_file>.log` for later cross-reference.

Pass extra `sbatch` flags applied to **every** job in the sweep after the file name:

```bash
bash scripts/aire/sweep.sh scripts/aire/sweeps/r14_v2.txt --time=06:00:00 --mem=120G
```

When to use sweep vs. plain `sbatch`:

- **Sweep is better:** ≥3 related jobs, you want a single artefact (the .log) that records the entire experiment grid, you want identical Slurm settings.
- **Plain sbatch is better:** one-off, or each job needs different Slurm settings.

To author a new sweep, drop a new `.txt` file under [scripts/aire/sweeps/](../scripts/aire/sweeps/) — one line per job, `#` for comments. No code change.

**Next:** errors? §13.

---

## 13. Common errors and fixes

| Symptom (in `LLM-cag-run_<jobid>.err` or `.out`) | Cause | Fix |
| --- | --- | --- |
| `ERROR: HF_TOKEN is not set` | Token missing on this account | `huggingface-cli login` once, OR `export HF_TOKEN=hf_...` in `~/.bashrc` |
| `ERROR: vLLM container not found at: $HOME/vllm-openai-v0.8.5.sif` | Image not pulled, or in wrong place | Re-do §3.6, or `SIF_IMAGE=/your/path.sif sbatch ...` |
| `[wait] ERROR: server not ready after 1500s` | First run downloading multi-GB weights | Re-submit with `MAX_WAIT_SECONDS=3000 sbatch scripts/aire/run.sh ...`. Subsequent runs reuse the cache and don't need this |
| `ERROR: src/cag not found under REPO_DIR=...` | You submitted `sbatch` from outside the repo | `cd ~/Climate-Action-GABM && sbatch ...` |
| `Cannot resume: config key 'X' changed` | You changed a hard key while passing `--resume` | Either revert the key, or start a fresh run (drop `--resume` and `RESUME_FROM`) |
| `ModuleNotFoundError: No module named 'cag'` | Conda env not activated, or `PYTHONPATH` not set | `conda activate cag`; for local invocations include `PYTHONPATH=src` |
| `error: missing required config key(s): ['n_citizens', 'days']` | You forgot both, and didn't pass a preset that supplies them | Add `--n-citizens N --days D` or `--preset smoke` |
| `Job exited 1 immediately, no run.log written` | The Python invocation crashed before logging started — check `LLM-cag-run_<jobid>.err` | Most often: bad JSON in `--exposure-targets`, or a typo in a preset name (argparse rejects with exit 2) |

Anything else: open `LLM-cag-run_<jobid>.out` and search for `ERROR` from the bottom up.

---

## 14. Updating the repo on AIRE later

The repo will change. To pull updates into your AIRE clone:

```bash
cd ~/Climate-Action-GABM
git pull
```

If `environment.yaml` changed:

```bash
conda env update -f environment.yaml --prune
```

If `scripts/aire/run.sh` mentions a newer vLLM image version, repeat §3.6 with that version. The previous SIF can be deleted (or kept side-by-side and selected with `SIF_IMAGE=...`).

The conda env, the model weights cache (`$SCRATCH/HF_cache`), and the SIF live outside the repo tree — none of those need to be touched on a `git pull`.

---

## Cheat sheet

```bash
# Free sanity checks (login node, no GPU):
PYTHONPATH=src python -m cag --list-presets
PYTHONPATH=src python -m cag --preset smoke --dry-run

# Smoke job (cheap full-stack canary):
sbatch scripts/aire/run.sh --preset smoke

# Canonical split50 Run-14:
sbatch scripts/aire/run.sh --preset r14_canonical --exposure-targets split50

# Same run, longer wall-clock + per-day checkpointing:
sbatch --time=06:00:00 scripts/aire/run.sh --preset r14_canonical --exposure-targets split50 --checkpoint-every-day

# Resume a killed run (same OUTDIR, same hard keys):
RESUME_FROM=$SCRATCH/cag/runs/run_<old_jobid> sbatch scripts/aire/run.sh --preset r14_canonical --exposure-targets split50

# Multi-job sweep from a one-line-per-job text file:
bash scripts/aire/sweep.sh scripts/aire/sweeps/r14_v2.txt

# Monitoring:
squeue --me
tail -f $(ls -t LLM-cag-run_*.out | head -1)
sacct -j <jobid> --format=JobID,State,Elapsed,MaxRSS,ExitCode

# Pull results back (on your laptop, NOT inside the AIRE ssh session):
mkdir -p ~/cag_results/run_<jobid> && \
    rsync -avh --include='*/' --include='*.csv' --include='*.png' --include='*.json' --include='*.log' --exclude='*' \
    aire:/mnt/scratch/<user>/cag/runs/run_<jobid>/ ~/cag_results/run_<jobid>/
```

When in doubt: `--dry-run` first, then commit GPU time.
