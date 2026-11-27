# Running on HPC Systems

This page is the entrypoint for running Climate-Action-GABM on HPC systems.
Use it to choose the right guide/script set and avoid mixing local and cluster
assumptions.

## Recommended path

1. Start with [Aire_Quickstart.md](Aire_Quickstart.md) for a copy-paste path
   from first login to completed smoke and canonical runs.
2. Use [Aire_HPC_repo_primer.md](Aire_HPC_repo_primer.md) for policy,
   storage/data constraints, launcher contract, and verification limits.

## Script locations

- [scripts/hpc/README.md](../../../scripts/hpc/README.md)
- [scripts/hpc/aire/](../../../scripts/hpc/aire/)
- [scripts/hpc/calder/](../../../scripts/hpc/calder/)

## Cluster coverage

### AIRE (primary maintained path)

Use [scripts/hpc/aire/run.sh](../../../scripts/hpc/aire/run.sh) for single runs
and [scripts/hpc/aire/sweep.sh](../../../scripts/hpc/aire/sweep.sh) for multi-job
sweeps. Documentation and examples are maintained against this path first.

### Calder (secondary portability path)

Use scripts in [scripts/hpc/calder/](../../../scripts/hpc/calder/) when working
on Calder-specific workflows or adaptation. Defaults are user-portable, but site
settings (partition names, module stacks, storage paths) should be confirmed
against current cluster guidance before submission.

## Before you submit long runs

Run one short canary first:

```bash
sbatch scripts/hpc/aire/run.sh --preset smoke
```

Then scale to longer or canonical runs only after confirming:

- job starts successfully,
- vLLM serves responses,
- run outputs are written to expected scratch paths.
