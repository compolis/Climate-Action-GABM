#!/bin/bash -l
# =============================================================================
# Submit a sweep of Climate-Action-GABM runs from a plain-text file.
# =============================================================================
# Each non-blank, non-comment line in the sweep file is forwarded verbatim as
# extra arguments to `scripts/aire/run.sh`. One Slurm job is submitted per
# line. Lines starting with `#` are comments.
#
# Per-line run label (optional): if a line begins with a `LABEL=<token>`
# prefix, that token is stripped off and exported as RUN_LABEL for *that* job
# only, so its output lands in `run_<jobid>_<token>` (see run.sh). The label
# must be a single shell-safe token (no spaces). Lines without a LABEL= prefix
# behave exactly as before. Example:
#   LABEL=tier1_baseline_s42 --preset tier1 --reach-a 1.0 --reach-b 1.0 --seed 42
#
# USAGE (from the repo root):
#   bash scripts/aire/sweep.sh scripts/aire/sweeps/r14_v2.txt
#
#   # Forward extra sbatch flags to every job in the sweep (e.g. longer time):
#   bash scripts/aire/sweep.sh scripts/aire/sweeps/r14_v2.txt --time=06:00:00
#
# The sweep file path is relative to the repo root (or absolute). All
# submitted job ids are echoed and appended to <sweep_file>.log.
# =============================================================================

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "usage: $0 <sweep_file> [extra sbatch flags...]" >&2
    exit 2
fi

SWEEP_FILE="$1"
shift
EXTRA_SBATCH=("$@")

if [[ ! -r "$SWEEP_FILE" ]]; then
    echo "ERROR: sweep file not readable: $SWEEP_FILE" >&2
    exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_SH="$REPO_DIR/scripts/aire/run.sh"
LOG="${SWEEP_FILE}.log"
echo "# sweep started $(date -Iseconds)" >> "$LOG"

submitted=0
while IFS= read -r line || [[ -n "$line" ]]; do
    # Trim leading/trailing whitespace.
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    # Skip blanks and comments.
    [[ -z "$line" || "${line:0:1}" == "#" ]] && continue

    # Optional per-line `LABEL=<token>` prefix -> RUN_LABEL for this job only.
    label=""
    if [[ "$line" == LABEL=* ]]; then
        label_token="${line%%[[:space:]]*}"   # e.g. LABEL=tier1_baseline_s42
        label="${label_token#LABEL=}"
        # Drop the token and any following whitespace to leave the run args.
        line="${line#"$label_token"}"
        line="${line#"${line%%[![:space:]]*}"}"
    fi

    echo "[sweep] RUN_LABEL=${label:-<none>} sbatch ${EXTRA_SBATCH[*]} $RUN_SH $line"
    # shellcheck disable=SC2086 # word-splitting on the line is intentional
    out="$(RUN_LABEL="$label" sbatch "${EXTRA_SBATCH[@]}" "$RUN_SH" $line)"
    echo "$out"
    echo "$out  # label: ${label:-<none>}  args: $line" >> "$LOG"
    submitted=$(( submitted + 1 ))
done < "$SWEEP_FILE"

echo "[sweep] submitted $submitted job(s); log: $LOG"
