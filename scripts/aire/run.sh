#!/bin/bash -l
# Compatibility wrapper for scripts/hpc/aire/run.sh.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec "$REPO_DIR/scripts/hpc/aire/run.sh" "$@"
