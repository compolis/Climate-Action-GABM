#!/bin/bash -l
# =============================================================================
# Climate-Action-GABM — generic AIRE (Leeds HPC) launcher
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
# k_peers, reach_a/b, exposure_targets, day0_anchor, debias, thinking,
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
#   # 5. Reach-asymmetry experiment + per-day checkpointing:
#   sbatch --time=06:00:00 scripts/aire/run.sh \
#       --preset r14_canonical \
#       --exposure-targets split50 --reach-a 0.5 --reach-b 1.0 \
#       --checkpoint-every-day
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
# =============================================================================

# ---- Default Slurm resource request -----------------------------------------
# Each #SBATCH directive can be overridden on the command line, e.g.
#   sbatch --time=06:00:00 --mem=120G scripts/aire/run.sh ...
# The "LLM-" job-name prefix is REQUIRED by AIRE for LLM jobs (RSE policy).
#SBATCH --job-name=LLM-cag-run
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-task=1
#SBATCH --mem=80G
#SBATCH --time=04:00:00
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err

set -euo pipefail

# ---- Server plumbing (rarely changes) ---------------------------------------
HF_MODEL="${HF_MODEL:-Qwen/Qwen3-8B}"                     # change via:  HF_MODEL=swiss-ai/Apertus-8B-2509 sbatch ...
SIF_IMAGE="${SIF_IMAGE:-$HOME/vllm-openai-v0.8.5.sif}"
PORT="${PORT:-8000}"
BASE_URL="http://localhost:${PORT}/v1"

# Hugging Face token: env var wins, then $HOME/.cache/huggingface/token.
if [[ -z "${HF_TOKEN:-}" ]]; then
    HF_TOKEN_FILE="${HF_HOME:-$HOME/.cache/huggingface}/token"
    if [[ -r "$HF_TOKEN_FILE" ]]; then
        HF_TOKEN="$(<"$HF_TOKEN_FILE")"
    fi
fi
if [[ -z "${HF_TOKEN:-}" ]]; then
    echo "ERROR: HF_TOKEN is not set and \$HF_HOME/.cache/huggingface/token does not exist." >&2
    echo "       Either 'export HF_TOKEN=hf_xxx' or 'huggingface-cli login' once on AIRE." >&2
    exit 1
fi
export HF_TOKEN

# ---- Locate the repository and the output area ------------------------------
if [[ -n "${SLURM_SUBMIT_DIR:-}" ]]; then
    REPO_DIR="$SLURM_SUBMIT_DIR"
else
    REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi
cd "$REPO_DIR"

if [[ ! -d "$REPO_DIR/src/cag" ]]; then
    echo "ERROR: src/cag not found under REPO_DIR=$REPO_DIR" >&2
    echo "       Submit from the repo root:  cd <repo> && sbatch scripts/aire/run.sh ..." >&2
    exit 1
fi

# ---- Output dir + optional resume support ----------------------------------
RESUME_FLAG=""
if [[ -n "${RESUME_FROM:-}" ]]; then
    if [[ ! -d "${RESUME_FROM}/checkpoints" ]]; then
        echo "ERROR: RESUME_FROM='${RESUME_FROM}' but no checkpoints/ subdir exists." >&2
        exit 1
    fi
    OUTDIR="${RESUME_FROM}"
    RESUME_FLAG="--resume"
    echo "[sim] Resuming from ${RESUME_FROM}/checkpoints"
else
    OUTDIR="$SCRATCH/cag/runs/run_${SLURM_JOB_ID}"
fi
mkdir -p "$OUTDIR"

# HF weights cache under $SCRATCH (large, re-downloadable; not for $HOME).
export LOCAL_HF_CACHE="${LOCAL_HF_CACHE:-$SCRATCH/HF_cache}"
mkdir -p "$LOCAL_HF_CACHE"

echo "=================================================================="
echo " Climate-Action-GABM AIRE run"
echo "   job id      : ${SLURM_JOB_ID}"
echo "   job name    : ${SLURM_JOB_NAME:-LLM-cag-run}"
echo "   node        : $(hostname)"
echo "   repo        : ${REPO_DIR}"
echo "   model       : ${HF_MODEL}"
echo "   output dir  : ${OUTDIR}"
echo "   HF cache    : ${LOCAL_HF_CACHE}"
echo "   cag flags   : $*"
echo "=================================================================="

if [[ ! -f "$SIF_IMAGE" ]]; then
    echo "ERROR: vLLM container not found at: $SIF_IMAGE" >&2
    echo "       Build it once: module add apptainer && apptainer pull docker://vllm/vllm-openai" >&2
    exit 1
fi

# =============================================================================
# STEP 1 — start the vLLM server in the background
# =============================================================================
module add apptainer

APPTAINER_ARGS="--nv \
  -B ${LOCAL_HF_CACHE}:/root/.cache/huggingface \
  --env HF_HOME=/root/.cache/huggingface \
  --env HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}"

echo "[server] Starting vLLM (first run also downloads the model)..."
SERVER_LOG="${OUTDIR}/vllm_server.log"
apptainer exec ${APPTAINER_ARGS} "${SIF_IMAGE}" \
    vllm serve "${HF_MODEL}" --tensor-parallel-size 1 --port "${PORT}" \
    > "${SERVER_LOG}" 2>&1 &
SERVER_PID=$!
echo "[server] vLLM PID ${SERVER_PID}; logging to ${SERVER_LOG}"

cleanup() {
    echo "[server] Shutting down vLLM (PID ${SERVER_PID})..."
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
}
trap cleanup EXIT

# =============================================================================
# STEP 2 — wait until the server is ready
# =============================================================================
echo "[wait] Waiting for the server to become ready..."
READY=0
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-1500}"   # 25 minutes by default
WAITED=0
while (( WAITED < MAX_WAIT_SECONDS )); do
    if curl -sf "${BASE_URL}/models" > /dev/null 2>&1; then
        READY=1
        break
    fi
    if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
        echo "[wait] ERROR: vLLM process exited early. Last server log lines:" >&2
        tail -n 30 "${SERVER_LOG}" >&2
        exit 1
    fi
    sleep 10
    WAITED=$(( WAITED + 10 ))
    echo "[wait]   ...still waiting (${WAITED}s elapsed)"
done

if (( READY == 0 )); then
    echo "[wait] ERROR: server not ready after ${MAX_WAIT_SECONDS}s. Server log tail:" >&2
    tail -n 30 "${SERVER_LOG}" >&2
    exit 1
fi
echo "[wait] Server is ready at ${BASE_URL}"

# =============================================================================
# STEP 3 — run the simulation against the server
# =============================================================================
module load miniforge
eval "$(conda shell.bash hook)"
conda activate cag
echo "[sim] Launching the simulation; all caller flags forwarded:  $*"

PYTHONPATH=src python3 -m cag \
    --provider local \
    --model "${HF_MODEL}" \
    --base-url "${BASE_URL}" \
    --outdir "${OUTDIR}" \
    ${RESUME_FLAG} \
    "$@"

echo "=================================================================="
echo " Done. Results (CSVs, PNGs, run.log) are in:"
echo "   ${OUTDIR}"
echo "=================================================================="
# vLLM is stopped automatically by the cleanup trap on exit.
