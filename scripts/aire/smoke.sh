#!/bin/bash -l
# =============================================================================
# Climate-Action-GABM — single combined smoke test for AIRE (Leeds HPC)
# =============================================================================
# WHAT THIS DOES (one Slurm job, in order):
#   1. Starts a vLLM server (the Qwen AI model) on this GPU node, port 8000.
#   2. Waits until the server is ready to answer.
#   3. Runs the NB29 simulation (10 agents, 2 days) against that server.
#   4. Saves all results to $SCRATCH (never the code folder).
#   5. Shuts the server down.
#
# HOW TO RUN IT (from the repo root on an AIRE login node):
#       sbatch scripts/aire/smoke.sh
#   Then watch progress with:
#       squeue --me
#       tail -f LLM-cag-smoke_*.out
#   Results land in:  $SCRATCH/cag/runs/run_<jobid>/
#
# ONE-TIME PREP (do these once before the first submit — see the README notes
# at the bottom of this file for the exact commands):
#   - Build the conda env:        conda env create -f environment.yaml
#   - Pull the vLLM container:     module add apptainer
#                                  apptainer pull docker://vllm/vllm-openai
#   - Paste your Hugging Face token into the HF_TOKEN line below.
# =============================================================================

# ---- Slurm resource request -------------------------------------------------
# NOTE: the "LLM-" job-name prefix is REQUIRED by AIRE for LLM jobs so the RSE
# team can monitor GPU/energy use. Keep it.
#SBATCH --job-name=LLM-cag-smoke
#SBATCH --partition=gpu            # GPU partition (where the AI model runs)
#SBATCH --nodes=1                  # single node — simplest setup
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-task=1          # one GPU is plenty for an 8B model
#SBATCH --mem=80G
#SBATCH --time=01:00:00            # 1 hour wall-clock cap (generous for a smoke)
#SBATCH --output=%x_%j.out         # %x = job name, %j = job id
#SBATCH --error=%x_%j.err

set -euo pipefail

# ---- Things you may want to change -----------------------------------------
# The model the server loads AND the name the simulation must ask for — these
# two MUST match exactly. To try Apertus later, change only this one line
# (e.g. swiss-ai/Apertus-8B-2509) and re-submit.
HF_MODEL="Qwen/Qwen3-8B"

# Paste your Hugging Face read token here (looks like hf_xx...). It is needed
# to download the model weights. See the notes at the bottom of this file.
export HF_TOKEN="PASTE_YOUR_HUGGINGFACE_TOKEN_HERE"

# The vLLM container image produced by `apptainer pull docker://vllm/vllm-openai`.
# By default that command writes the SIF into the directory you ran it from;
# we look for it in your $HOME. Adjust if you put it elsewhere.
SIF_IMAGE="$HOME/vllm-openai_latest.sif"

# Local server address. The simulation (running on this same node) talks to the
# server over localhost. Apptainer shares the host network, so this just works.
PORT=8000
BASE_URL="http://localhost:${PORT}/v1"

# ---- Locate the repository and the output area ------------------------------
# This script lives in <repo>/scripts/aire/, so the repo root is two levels up.
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_DIR"

# All results go under $SCRATCH (large, fast, NOT backed up). Never write into
# the repo tree on a cluster.
OUTDIR="$SCRATCH/cag/runs/run_${SLURM_JOB_ID}"
mkdir -p "$OUTDIR"

# Hugging Face model cache also under $SCRATCH (weights are several GB and are
# re-downloadable, so they do not belong in the small backed-up $HOME).
export LOCAL_HF_CACHE="$SCRATCH/HF_cache"
mkdir -p "$LOCAL_HF_CACHE"

echo "=================================================================="
echo " Climate-Action-GABM AIRE smoke test"
echo "   job id      : ${SLURM_JOB_ID}"
echo "   node        : $(hostname)"
echo "   repo        : ${REPO_DIR}"
echo "   model       : ${HF_MODEL}"
echo "   output dir  : ${OUTDIR}"
echo "   HF cache    : ${LOCAL_HF_CACHE}"
echo "=================================================================="

# ---- Sanity checks ----------------------------------------------------------
if [[ "$HF_TOKEN" == "PASTE_YOUR_HUGGINGFACE_TOKEN_HERE" ]]; then
    echo "ERROR: HF_TOKEN is not set. Edit this script and paste your" >&2
    echo "       Hugging Face read token into the HF_TOKEN line." >&2
    exit 1
fi
if [[ ! -f "$SIF_IMAGE" ]]; then
    echo "ERROR: vLLM container not found at: $SIF_IMAGE" >&2
    echo "       Build it once with:" >&2
    echo "         module add apptainer" >&2
    echo "         apptainer pull docker://vllm/vllm-openai" >&2
    exit 1
fi

# =============================================================================
# STEP 1 — start the vLLM server in the background
# =============================================================================
module add apptainer

# Arguments passed to the container:
#   --nv                          give the container access to the GPU
#   -B <host>:<container>         mount the HF cache into the container
#   --env HF_HOME=...             tell HF libraries where the cache is
#   --env HUGGING_FACE_HUB_TOKEN  pass the download token
APPTAINER_ARGS="--nv \
  -B ${LOCAL_HF_CACHE}:/root/.cache/huggingface \
  --env HF_HOME=/root/.cache/huggingface \
  --env HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}"

echo "[server] Starting vLLM (first run also downloads the model — can take a while)..."
SERVER_LOG="${OUTDIR}/vllm_server.log"
apptainer exec ${APPTAINER_ARGS} "${SIF_IMAGE}" \
    vllm serve "${HF_MODEL}" --tensor-parallel-size 1 --port "${PORT}" \
    > "${SERVER_LOG}" 2>&1 &
SERVER_PID=$!
echo "[server] vLLM PID ${SERVER_PID}; logging to ${SERVER_LOG}"

# Make sure the server is stopped no matter how this script ends.
cleanup() {
    echo "[server] Shutting down vLLM (PID ${SERVER_PID})..."
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
}
trap cleanup EXIT

# =============================================================================
# STEP 2 — wait until the server is ready
# =============================================================================
# Poll the /v1/models endpoint until it answers (HTTP 200). On the very first
# run this also waits for the multi-GB model download, so allow up to ~25 min.
echo "[wait] Waiting for the server to become ready..."
READY=0
MAX_WAIT_SECONDS=1500   # 25 minutes
WAITED=0
while (( WAITED < MAX_WAIT_SECONDS )); do
    if curl -sf "${BASE_URL}/models" > /dev/null 2>&1; then
        READY=1
        break
    fi
    # If the server process died, stop waiting and show why.
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
# Make `conda activate` work inside a non-interactive batch script.
eval "$(conda shell.bash hook)"
conda activate cag

echo "[sim] Launching the simulation (timing is printed at the end)..."
PYTHONPATH=src python3 -m cag \
    --provider local \
    --model "${HF_MODEL}" \
    --base-url "${BASE_URL}" \
    --outdir "${OUTDIR}" \
    --seed 42 \
    --n-citizens 10 \
    --days 2 \
    --no-thinking      # faster first run; drop this flag to match NB29 exactly

echo "=================================================================="
echo " Done. Results (CSVs, PNGs, run.log) are in:"
echo "   ${OUTDIR}"
echo "=================================================================="
# vLLM is stopped automatically by the cleanup trap on exit.

# =============================================================================
# ONE-TIME PREP NOTES (read once; not executed)
# -----------------------------------------------------------------------------
# 1. Get a Hugging Face token (free):
#      - create an account at https://huggingface.co
#      - Settings -> Access Tokens -> New token -> Read permission -> copy it
#      - paste it into the HF_TOKEN line near the top of this file
#
# 2. Build the Python environment (once):
#      module load miniforge
#      conda env create -f environment.yaml
#
# 3. Download the vLLM container (once):
#      module add apptainer
#      apptainer pull docker://vllm/vllm-openai
#      # this creates vllm-openai_latest.sif in the current folder; this script
#      # expects it in $HOME, so run the pull from your home directory (cd ~).
#
# 4. Submit:
#      sbatch scripts/aire/smoke.sh
# =============================================================================
