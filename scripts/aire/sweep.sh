#!/bin/bash -l
# =============================================================================
# Submit a sweep of Climate-Action-GABM runs from a plain-text file.
# =============================================================================
# Each non-blank, non-comment line in the sweep file is forwarded verbatim as
# extra arguments to `scripts/aire/run.sh`. One Slurm job is submitted per
# line. Lines starting with `#` are comments.
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

    echo "[sweep] sbatch ${EXTRA_SBATCH[*]} $RUN_SH $line"
    # shellcheck disable=SC2086 # word-splitting on the line is intentional
    out="$(sbatch "${EXTRA_SBATCH[@]}" "$RUN_SH" $line)"
    echo "$out"
    echo "$out  # args: $line" >> "$LOG"
    submitted=$(( submitted + 1 ))
done < "$SWEEP_FILE"

echo "[sweep] submitted $submitted job(s); log: $LOG"
