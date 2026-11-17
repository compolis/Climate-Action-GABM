#!/bin/bash -l
# Compatibility wrapper for scripts/hpc/aire/sweep.sh.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET="$REPO_DIR/scripts/hpc/aire/sweep.sh"

if [[ $# -gt 0 ]]; then
    SWEEP_FILE="$1"
    shift
    CANDIDATE="$SWEEP_FILE"
    if [[ "$CANDIDATE" == *"scripts/aire/sweeps/"* ]]; then
        CANDIDATE="${CANDIDATE//scripts\/aire\/sweeps\//scripts\/hpc\/aire\/sweeps\/}"
    fi
    if [[ ! -r "$SWEEP_FILE" && -r "$CANDIDATE" ]]; then
        SWEEP_FILE="$CANDIDATE"
    fi
    exec "$TARGET" "$SWEEP_FILE" "$@"
fi

exec "$TARGET"
