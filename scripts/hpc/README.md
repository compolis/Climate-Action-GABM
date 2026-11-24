# HPC Scripts Overview

This folder contains cluster launcher scripts for Climate-Action-GABM.

## Scope and status

- **AIRE** scripts in `scripts/hpc/aire/` are the primary maintained path.
- **Calder** scripts in `scripts/hpc/calder/` are provided for portability and
  local cluster adaptation.

For policy, data, and setup guidance, use:

- `documentation/guides/hpc/Running_On_HPC_Systems.md`
- `documentation/guides/hpc/AIRE_Quickstart.md`
- `documentation/guides/hpc/AIRE_HPC_repo_primer.md`

## Script map

### AIRE

- `aire/run.sh` — one-job launcher: starts vLLM, runs `python -m cag`, writes
  outputs to scratch, and stops vLLM.
- `aire/sweep.sh` — submits one job per line from a sweep file.
- `aire/sweeps/*.txt` — example parameter sets for sweep submissions.

### Calder

- `calder/run.sh` — one-job launcher (server + `python -m cag` in one job).
- `calder/run_server.sh` — server-only launcher.
- `calder/run_client.sh` — client/reproducibility helper (targets an existing
  server endpoint).

## Typical usage

From the repository root:

```bash
# AIRE smoke canary
sbatch scripts/hpc/aire/run.sh --preset smoke

# AIRE canonical run
sbatch scripts/hpc/aire/run.sh --preset r14_canonical --exposure-targets split50
```

```bash
# Calder integrated run
sbatch scripts/hpc/calder/run.sh --preset smoke
```

## Notes

- Pass Slurm overrides before the script path (for example `--time`, `--mem`,
  `--partition`).
- Pass Climate-Action-GABM options after the script path.
- Keep large outputs and model caches on cluster scratch storage.
