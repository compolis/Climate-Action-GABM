#!/bin/bash -l
# =============================================================================
# Climate-Action-GABM — generic Calder (Leeds HPC) launcher
# =============================================================================
# WHAT THIS DOES (one Slurm job, in order):
#   1. Starts a vLLM server on this GPU node (model = $HF_MODEL).
#   2. Waits until the server answers /v1/models.
#   3. Runs `python -m cag` against that server with every flag the user
#      passed in on the sbatch command line ("$@"), plus the fixed local-
#      provider plumbing (--provider local --base-url --outdir).
#   4. Saves all results to $SCRATCH (never the repo tree).
#   5. Shuts the server down.
#
# DESIGN NOTE
# -----------
# This script is intentionally THIN. Every research knob (n_citizens, days,
# k_peers, reach_a/b, exposure_targets, day0_anchor, memory, thinking,
# audience_cap, package_policies, ...) is set on the sbatch command line
# and passed through as "$@". Slurm headers (--time, --mem, --gpus-per-task,
# --job-name) are also overridable at sbatch time. To add a new experiment
# you should NOT have to edit this script — see the canonical examples in
# the header block below, or scripts/aire/sweeps/*.txt for batch submissions.
#
# HOW TO RUN IT — canonical examples (from the repo root on an AIRE login node):
#
#   # 1. List available presets (no GPU; just sanity-check the venv):
#   PYTHONPATH=src python3 -m cag --list-presets
#
#   # 2. Smoke run on your local Mac (uses mlx-lm http://localhost:8080/v1;
#   #    does NOT use this sbatch script — runs in-process):
#   PYTHONPATH=src python3 -m cag --preset smoke --outdir data/output/smoke
#
#   # 3. Canonical Run-14 baseline on AIRE (uses preset for the bulk, then
#   #    pins the only fork that the preset deliberately leaves out):
#   sbatch scripts/aire/run.sh \
#       --preset r14_canonical \
#       --exposure-targets split50
#
#   # 4. Sensitivity sweep — same preset, different exposure (no script edit):
#   sbatch --job-name=LLM-cag-neither scripts/aire/run.sh \
#       --preset r14_canonical --exposure-targets neither
#
#   # 5. Reach-asymmetry experiment (checkpoints default-on; --no-checkpoint-every-day to opt out):
#   sbatch --time=06:00:00 scripts/aire/run.sh \
#       --preset r14_canonical \
#       --exposure-targets split50 --reach-a 0.5 --reach-b 1.0
#
#   # 6. Resume a killed run (same model + config, same OUTDIR):
#   RESUME_FROM=$SCRATCH/cag/runs/run_<old_jobid> \
#       sbatch scripts/aire/run.sh --preset r14_canonical --exposure-targets split50
#
# ONE-TIME PREP
# -------------
#   - Set HF_TOKEN: either export it in your shell profile, or put it at
#     $HOME/.cache/huggingface/token (this script reads both).
#   - conda env create -f environment.yaml   (creates the `cag` env)
#   - module add apptainer && apptainer pull docker://vllm/vllm-openai
#   - Pre-download model weights on the login node (compute nodes have no internet):
#       module load miniforge && conda activate cag
#       HF_HOME=$SCRATCH/HF_cache huggingface-cli download Qwen/Qwen3-14B
#     Change the model name to match $HF_MODEL if you override it.
# =============================================================================

# ---- Default Slurm resource request -----------------------------------------
# Each #SBATCH directive can be overridden on the command line, e.g.
#   sbatch --time=06:00:00 --mem=120G scripts/aire/run.sh ...
# The "LLM-" job-name prefix is REQUIRED by AIRE for LLM jobs (RSE policy).
#SBATCH --job-name=LLM-cag-run
#SBATCH --partition=gpu_hopper
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --mem=256G
#SBATCH --time=01:00:00
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err

set -euo pipefail

# set -x causes every command to be echoed into the Slurm output file as it's executed.
set -x

module load calder/hopper
module load cuda/13.3.0
module load nccl/2.29.7-1
module load miniforge3

MODEL_DIR="/users/$USER/.cache/huggingface/hub/Apertus-v1.5-70B"

SIF_IMAGE="$HOME/calder/apertus15.sif"

# Avoid PORT collisions rather than setting PORT=8000
PORT=$((10000 + SLURM_JOB_ID % 50000))

BASE_URL="http://localhost:${PORT}/v1"
REPO_DIR="${SLURM_SUBMIT_DIR}"
cd "$REPO_DIR"
OUTDIR="$HOME/cag_runs/run_${SLURM_JOB_ID}"
mkdir -p "$OUTDIR"

# Launch Apertus
SERVER_LOG="${OUTDIR}/vllm_server.log"
apptainer exec \
  --cleanenv \
  --nv \
  --env CUDA_HOME=/usr/local/cuda \
  --env CUDACXX=/usr/local/cuda/bin/nvcc \
  "${SIF_IMAGE}" \
  vllm serve "${MODEL_DIR}" \
  --served-model-name Apertus-v1.5-70B \
  --tensor-parallel-size $SLURM_GPUS_ON_NODE \
  --gpu-memory-utilization 0.9 \
  --max-model-len 262144 \
  --compilation-config.pass_config.fuse_allreduce_rms=false \
  --chat-template-content-format string \
  --port "${PORT}" \
  > "${SERVER_LOG}" 2>&1 &

SERVER_PID=$!

# Readiness loop
until curl -sf "${BASE_URL}/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{
    "model":"Apertus-v1.5-70B",
    "messages":[{"role":"user","content":"ping"}],
    "max_tokens":1
  }' >/dev/null 2>&1
do
  sleep 10
done

# Run cag
eval "$(conda shell.bash hook)"
conda activate test-cag

PYTHONPATH=src python -m cag \
  --provider local \
  --model Apertus-v1.5-70B \
  --base-url "${BASE_URL}" \
  --outdir "${OUTDIR}" \
  "$@"

# Shutdown
cleanup() {
  kill "${SERVER_PID}" 2>/dev/null || true
  wait "${SERVER_PID}" 2>/dev/null || true
}
trap cleanup EXIT

