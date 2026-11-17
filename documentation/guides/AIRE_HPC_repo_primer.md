# Aire HPC reference for Climate-Action-GABM

This reference explains the cluster assumptions and the current CAG launcher
contract. For setup and submission commands, use [AIRE_Quickstart.md](AIRE_Quickstart.md).
It replaces the generic assistant-facing template; it is not a request to
generate alternative launchers or change the simulation.

## 1. Scope, sources, and verification

Reviewed on **2026-11-08** against the repository launcher and the public Leeds
documentation listed below. Leeds states that its documentation is transitioning
to the new Leeds HPC site during the Calder launch and Aire upgrade. Check the
service's current advice before a new account setup or resource request:

- [Aire documentation and transition notice](https://arcdocs.leeds.ac.uk/aire/welcome.html)
- [Logging on](https://arcdocs.leeds.ac.uk/aire/getting_started/logging_on.html)
- [Rules and regulations](https://arcdocs.leeds.ac.uk/aire/getting_started/rules_regulations.html)
- [Storage and filesystems](https://arcdocs.leeds.ac.uk/aire/system/storage_filesystem.html)
- [Software environments](https://arcdocs.leeds.ac.uk/aire/usage/software_env_management.html)
- [Job types and Slurm examples](https://arcdocs.leeds.ac.uk/aire/usage/job_type.html)
- [System overview](https://arcdocs.leeds.ac.uk/aire/system/start.html)

The Linux/Mac, Windows, VPN, and SSH gateway knowledge-base articles linked
from Leeds's login page require University authentication. Their exact host
names and account-specific connection steps were **not verified** in this
review. Use those articles or ask Research IT; do not copy a guessed hostname.
Leeds's public login page states that SSH key authentication for **Aire login**
is no longer supported. This is separate from an SSH key used **on Aire to
authenticate to GitHub**.

No Aire job, model download, GPU inference, or environment creation was executed
for this review. Local CLI checks cannot establish that a container/model pair
works on the current cluster. Historical timing estimates are not guarantees.

## 2. Shared-system use and storage

Leeds requires Slurm for compute-node processes and efficient, considerate use
of shared resources. Use login nodes for lightweight setup, transfers, editing,
and submission; submit inference and simulation workloads to compute nodes.
Follow current Research IT advice for expensive environment/container builds.
The public system overview describes three NVIDIA L40S GPUs per GPU node
(February 2025 configuration); this is not a promise about upgraded hardware.

The public storage guide lists:

| Area | Variable and documented path | Lifecycle and intended use |
|---|---|---|
| Home | `$HOME`, `/users/<username>` | Backed up; 65 GB and 1.5 million files. Code, configuration, credentials, and small persistent files. |
| Scratch | `$SCRATCH`, `/mnt/scratch/<username>` | Not backed up; 1 TB and 1.5 million files. Model weights and active run data; manual cleanup required. |
| Shared job flash | `$TMP_SHARED`, `/mnt/flash/tmp/job.<JOB-ID>` | Not backed up; removed at job completion. Job-scoped I/O-intensive work. |
| Node-local temporary | `$TMP_LOCAL` / `$TMPDIR` | Not backed up; removed at job completion; not shared between nodes. |

Check the actual variables and quotas on your account. Scratch has no routine
automatic deletion, but Leeds reserves emergency deletion when filesystems fill;
it is not archival storage. Copy important results to approved backed-up storage.
Keep large model caches and simulation I/O off the home filesystem.

CAG's documented convention is the `cag` client environment and pinned container
in home, with weights and run data in scratch. This is a **repository convention**,
not a claim that Leeds mandates one environment filename or package manager
manifest. Miniforge is Leeds's recommended alternative to Anaconda.

**Data approval comes before submission.** Leeds prohibits personal or sensitive
data on Aire; de-identification may make data suitable, but removing names alone
does not demonstrate this. Check the YouGov input, generated personas, prompts,
and outputs against the project's permissions and University data classification.
Seek advice if suitability is uncertain.

## 3. Current launcher contract

The implementation sources are [run.sh](../../scripts/hpc/aire/run.sh),
[sweep.sh](../../scripts/hpc/aire/sweep.sh), and
[environment.yaml](../../environment.yaml).

The client is `PYTHONPATH=src python -m cag`; it does not itself serve the model.
The default launcher requests one node, one task, eight CPUs, one GPU, 80 GB
node memory, and four hours in the `gpu` partition. It runs one vLLM server
and the simulation client on the same node. Extra CPU allocation does not
make CAG a distributed or multi-node simulation.

| Setting | Current launcher behaviour |
|---|---|
| `HF_MODEL` | Default `Qwen/Qwen3-14B`; selects the served model and the client model name. |
| `SIF_IMAGE` | Default `$HOME/vllm-openai-v0.8.5.sif`; a pinned repository choice, not a current-version recommendation. |
| `PORT` | Override if needed; otherwise `10000 + SLURM_JOB_ID % 50000`. Derived ports reduce collisions but do not reserve a free socket. |
| `MAX_WAIT_SECONDS` | Default `1500`; separate from Slurm's wall-clock limit. |
| `LOCAL_HF_CACHE` | Default `$SCRATCH/HF_cache`, bound to `/root/.cache/huggingface` inside the container. |
| `HF_TOKEN` | Environment takes precedence; otherwise read `${HF_HOME:-$HOME/.cache/huggingface}/token`. Required by this launcher even for an ungated model. |
| `RUN_LABEL` | Optional filename-safe suffix on `run_<jobid>_<label>`. |
| `RESUME_FROM` | Existing run directory with `checkpoints/`; reuses that output directory and injects `--resume`. |

Submit **from the repository root**: the launcher uses `SLURM_SUBMIT_DIR` to
locate `src/cag`. It loads Apptainer for the server, then explicitly loads
Miniforge and activates `cag` for the client. Do not rely on an interactive
shell's environment state being enough for a batch job.

Readiness is a successful **chat completion for `HF_MODEL`**, not merely
`/v1/models`. The server is stopped when the client/job script exits.
The launcher does not enable vLLM API authentication or restrict it with a
loopback `--host` argument. `localhost` in the client URL is **not an access-control
guarantee**. Follow Research IT advice on service binding/access before processing
approved data; do not expose the endpoint publicly. The archived article's Unix
socket suggestion is not implemented by this launcher or the CAG client.

The launcher injects `--provider`, `--model`, `--base-url`, and `--outdir` before
forwarding caller arguments. Argparse can accept a later duplicate override:
**do not pass these plumbing flags through `sbatch`**. Use `HF_MODEL`,
`PORT`, and `RESUME_FROM` where appropriate. A separate survey model is not
automatically served by this one-model container.

New runs write to `$SCRATCH/cag/runs/run_<jobid>[_<label>]`; resume uses exactly
`RESUME_FROM`. The launcher does not enforce that a supplied resume path is in
scratch. Slurm `.out`/`.err` default to the submission directory, while
`run.log` and `vllm_server.log` live in the run directory. The quickstart shows
explicit scratch paths for Slurm logs.

## 4. Resource requests, sweeps, and reproducibility

Pass Slurm options **before** the script path, and CAG options **after** it:

```bash
sbatch --time=06:00:00 --mem=120G scripts/hpc/aire/run.sh \
    --preset r14_canonical --exposure-targets split50
```

Inspect current partitions/limits through Leeds guidance and local Slurm tools;
do not copy generic `himem`, CUDA-module, memory-default, or array-job templates
as a CAG deployment recipe. The maintained launcher is the supported starting
point, and resource overrides should reflect measured usage.

The shipped sweep wrapper submits **one separate job per line**, not a Slurm
array. It supports an optional `LABEL=<token>` prefix and common Slurm overrides.
Its whitespace splitting does not implement shell quoting: keep per-line JSON
compact, without surrounding shell quotes or internal spaces. Do not put shell
commands, substitutions, or redirections in a sweep file. Submit from the repo
root. The wrapper appends job IDs to `<sweep_file>.log`.

Configuration precedence is `SIM_CONFIG` defaults, then a preset, then CLI
overrides. Use the [configuration guide](Simulation_Configuration_Guide.md)
and `python -m cag --help` for research settings instead of maintaining a
second complete flag table here.

Preserve resolved `config.json`, input/message-set provenance, source commit,
container identity, and environment versions alongside results. A pinned SIF
name alone is not a container digest. Fixed seeds do not guarantee identical
live LLM responses or exact checkpoint replay: the
[refactor plan](../planning/GABM_Refactor_Plan.md) records checkpoint validation
and remaining audit limitations. Sampled prompt-log persistence is opt-in;
see the [configuration guide](Simulation_Configuration_Guide.md#7-pausing-and-resuming-a-run).

## 5. Archived article: retained context and unresolved work

[RunningLLMsOnAire.md](../archive/RunningLLMsOnAire.md) remains a dated article
draft credited to John Hodrien, Jo Kershaw, and Andy Turner, not current CAG
setup instructions. Its distinct research/service topics remain useful:

- Multi-node Ray inference and alternative model deployments require a separate
  validated design; its two-node script, external tunnel hostname, and missing
  wrapper are not dependencies of the one-node CAG launcher.
- Filesystem-permission-controlled Unix sockets are an alternative deployment
  idea; performance/access claims and client support need verification.
- Shared model caches need licensing, permissions, and Research IT agreement.
  Job flash is documented as `$TMP_SHARED`, not an assumed persistent `$FLASH`.
  CAG currently uses scratch; flash staging/copy-back is not implemented.
- Energy monitoring and the `LLM-` job-name convention are attributed to the
  dated article/RSE request. The launcher retains the prefix; this review did
  not establish a public site-wide mandatory naming policy.
- The draft's authorship, publication-review intention, and UKRI acknowledgement
  are preserved in the archive; its unfinished prose is not folded into
  operational guidance.

Before declaring an Aire deployment validated, confirm current login/resource
and data permissions with Leeds, prepare a compatible cached model/container,
run a scheduled smoke job, check both server and client logs, and retain the
result/provenance records. This local documentation review is not that deployment
validation.

## 6. Related GABM guidance and Calder portability

GABM owns the general model-serving/HPC guidance; CAG owns this application's
launch, research configuration, and output checks. Consult upstream rather than
copying another generic serving guide into CAG:

- [Running On HPC Systems](https://github.com/compolis/gabm/blob/main/Running_On_HPC_Systems.md):
  Slurm/Apptainer/vLLM workflow, portability checklist, monitoring, and provenance.
- [RunningApertusOnCalder.md](https://github.com/compolis/gabm/blob/main/RunningApertusOnCalder.md):
  a redirect to that active guide and its archived Calder/Apertus snapshot.
- [Archived Calder/Apertus snapshot](https://github.com/compolis/gabm/blob/main/archive/RunningApertusOnCalder.md):
  historical serving observations, not current CAG submission instructions.

These were read from the adjacent GABM checkout at
[`2ea3f5f`](https://github.com/compolis/gabm/tree/2ea3f5f01b6b610fd92274be16b57484d9f2a553)
on 2026-11-08. They are repository evidence, not independently verified cluster
policy or fresh deployment tests. Their contents are not installed by the
`gabm==0.6.0` dependency pin.

The active guide records historical Apertus-v1.5-70B serving on four Calder
H200 GPUs with vLLM 0.23.1/0.23.1rc1 and tensor parallelism of four. This differs
from CAG's current one-GPU, vLLM v0.8.5 Aire launcher. Do not transplant its
resource/context settings or claim that changing `HF_MODEL` and `SIF_IMAGE`
alone makes the CAG launcher Calder-ready. The archive also contains conflicting
GPU, context-length, and memory descriptions; use the active guide as the
starting reference and revalidate resource choices.

A future CAG Calder slice should adapt serving from GABM's maintained examples
while retaining `python -m cag`, the CAG client environment, readiness checks,
scratch output layout, and research configuration. Check current hardware/
container architecture, partition directives, model/cache access, endpoint
reachability, and service binding before a scheduled smoke test. CAG-specific
output and golden-baseline acceptance gates still apply. This review neither
changes the Aire launcher nor adds Calder support.
