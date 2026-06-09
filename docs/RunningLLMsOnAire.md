## Metadata

- README
- Please provide feedback.
- Version 0.3
- 2026-05-27
- This is in preparation for:
- [ARC Website](https://arc.leds.ac.uk) article
- Word Document format is wanted for submitting content for review for the ARC Website. Following a successful review, the document gets reformatted for publication in the [knowledge-centre part of the Research IT Website](https://arc.leeds.ac.uk/knowledge-centre).
- [Aire](https://arcdocs.leeds.ac.uk/aire) (ARCDocs Aire documentation).
- Markdown format is wanted for the technical documentation. A PR will be wanted which will initiate a review process and the documentation will need linking appropriately. It is probably better to work on getting this right first and then link to the technical detail from the ARC Website article.

# Running LLMs on Aire

John Hodrien, Jo Kershaw, Andy Turner

## Contents

- Introduction
- vLLM
- Running on Aire
  - Prerequisites
  - Server Setup
  - LLM Download Configuration
  - Running the LLM Server
  - Sending Prompts and Receiving Responses
- Considerata
  - Security
  - System Architecture
  - Data Storage and Sharing
  - Sustainability
- Links and Abbreviations
- Acknowledgements

## Introduction

One way to run a [Large Language Model](https://en.wikipedia.org/wiki/Large_language_model) (LLM) on [Aire](https://arc.leeds.ac.uk/knowledge-centre/resources/aire/) is by using [vLLM](https://github.com/vllm-project/vllm/) – a library for LLM inference and serving. Section 2 introduces vLLM in more detail considering computational requirements and options for installing and using this on Aire. Section 3 details how to run a simple test for the [Apertus](https://apertus.ai/en/apps/apertus-model/) 8 Billion Vector LLM.

## vLLM

vLLM can be built from source or installed on a wide range of platforms. There are stable, latest and older versions. The versions that work on Aire are dependent on the [CUDA](https://en.wikipedia.org/wiki/CUDA) set up. There is documentation for each version:

- [vLLM stable release version documentation](https://docs.vllm.ai/en/stable/)
- [vLLM latest release version documentation](https://docs.vllm.ai/en/latest/getting_started/installation/)

vLLM version dependencies and underlying platform requirements may vary. Some LLMs may also have specific platform requirements and dependency versions. Also, the computational requirements for LLMs should be considered as some may run too slowly on single or multiple CPU cores and should be sped up by additionally utilising GPU cores. Memory requirements also vary. There can be a need for significant disk and fast access memory storage.

By default, vLLM is set up to download LLMs from [Hugging Face](https://huggingface.co/), but this can be changed.

There are two main installation options:

- [Conda](https://github.com/conda/conda)
- [Apptainer](https://apptainer.org/)

The Conda approach on Aire would use the [Miniforge](https://github.com/conda-forge/miniforge) Aire module and is not considered here. The Apptainer approach based on using a [Docker](https://www.docker.com/) Dockerfile is detailed next.

## Running on Aire

This section has subsections to provide details about prerequisites, the vLLM server set up, LLM download configuration for using the Hugging Face Hub,

### Prerequisites

As well as an account on Aire, you will need a LLM. This can be a local LLM or you can use a model repository hub like Hugging Face. The [Hugging Face Hub documentation](https://huggingface.co/docs/hub/index) has extensive details about the Machine Learning (ML) Artificial Intelligence (AI) platform.

vLLM reads the config, tokenizer, and weights from either the repository hub or a local directory. For the test runs of Apertus models on Aire, we each created accounts on Hugging Face and have used the Apertus model repositories on the Hugging Face Hub, but the details in the scripts below can be readily modified for other LLMs.

### Server setup

A vLLM Dockerfile can be used to construct a vLLM image that can be directly used to run an OpenAI compatible server on Aire. For details of options, please see the vLLM documentation, which for the latest and stable version can be found via the following URLs:

[https://docs.vllm.ai/en/latest/deployment/docker/](https://docs.vllm.ai/en/latest/deployment/docker/)

[https://docs.vllm.ai/en/stable/deployment/docker/](https://docs.vllm.ai/en/stable/deployment/docker/)

The latest vLLM Dockerfiles can be found in the vLLM GitHub repository via the following URLs:

[https://github.com/vllm-project/vllm/blob/main/docker/Dockerfile](https://github.com/vllm-project/vllm/blob/main/docker/Dockerfile)

This can be pulled from DockerHub via:

[https://hub.docker.com/r/vllm/vllm-openai/tags](https://hub.docker.com/r/vllm/vllm-openai/tags)

On Aire directly run:

```bash
module add apptainer
apptainer pull docker://vllm/vllm-openai
```

The SIF format Dockerfile can be used as a basis for containerisation as detailed in [Research Computing HPC2 Training Section on Containers](https://arctraining.github.io/hpc2-software/course/containers.html).

### LLM Download Configuration

To configure and run an OpenAI-Compatible Server on the compute nodes to connect to this to send prompts and receive responses to a running Apertus 8 Billion vector Chatbot running.

Users on Aire submit jobs via a Slurm scheduler to compute nodes

Before you can download models from HF you need to set up a HF account and register to use the models served out there or from other

### Running the LLM Server

The following Slurm Job submission script requests targets Aire's GPU nodes, requests 1 hour, 2 GPU nodes, 1 task per node, 8 CPUS and 1 GPU with 80G of memory per task and pushes the output into sensibly named error and output files. For this to work for you, replace HF_TOKEN with your Huggin Face token. The following script.sh can be submitted to the Slurm scheduler using the command:

```bash
sbatch script.sh
```

**script.sh**

```bash
#!/bin/bash -l
#SBATCH -p gpu
#SBATCH -t 1:0:0
#SBATCH -N 2
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-task=1
#SBATCH --mem=80G
#SBATCH --error="vllm-%j.err"
#SBATCH --output="vllm-%j.out"

# Load required modules
module add apptainer

# Initialise names
export HEAD_HOSTNAME="$(hostname -s)"
export HEAD_IPADDRESS="$(hostname --ip-address)"

# Fix pmix error (munge)
export PMIX_MCA_psec=native

# Choose a directory for the cache
export LOCAL_HF_CACHE="$SCRATCH/HF_cache"
mkdir -p ${LOCAL_HF_CACHE}

# Set the Hugging Face token
export HF_TOKEN="HF_TOKEN"

# Make sure the path to the SIF image is correct
# Here, the SIF image is in the same directory as this script
export SIF_IMAGE="vllm-openai_latest.sif"

export APPTAINER_ARGS=" --nv -B /$SCRATCH/HF_cache:/root/.cache/huggingface --env HF_HOME=/root/.cache/huggingface --env HUGGING_FACE_HUB_TOKEN=${HF_TOKEN} --env NCCL_DEBUG=WARN"

# Make sure you have been granted access to the model
export HF_MODEL="swiss-ai/Apertus-8B-2509"

export VLLM_HOST_IP=$HEAD_IPADDRESS

echo "HEAD NODE: ${HEAD_HOSTNAME}"
echo "IP ADDRESS: ${HEAD_IPADDRESS}"
echo "SSH TUNNEL (Execute on your local machine): ssh -p 8822 ${USER}@login.lxp.lu  -NL 8000:${HEAD_IPADDRESS}:8000"

# Get an available random port
export RANDOM_PORT=$(python3 -c 'import socket; s = socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()')

# Start the head and worker nodes
## Command to start the head node
export RAY_CMD_HEAD="ray start --block --head --port=${RANDOM_PORT} --node-ip-address $HEAD_IPADDRESS"
## Command to start workers
export RAY_CMD_WORKER="ray start --block --address=${HEAD_IPADDRESS}:${RANDOM_PORT}"

export TENSOR_PARALLEL_SIZE=1 # Set it to the number of GPU per node
export PIPELINE_PARALLEL_SIZE=${SLURM_NNODES} # Set it to the number of allocated GPU nodes

## Start head node
echo "Starting head node"
srun -J "head ray node-step-%J" -N 1 --ntasks-per-node=1  -c $(( SLURM_CPUS_PER_TASK/2 )) -w ${HEAD_HOSTNAME} ./wrapper apptainer exec ${APPTAINER_ARGS} ${SIF_IMAGE} ${RAY_CMD_HEAD} &
sleep 10

## Start worker nodes
echo "Starting worker node"
srun -J "worker ray node-step-%J" -N $(( SLURM_NNODES-1 )) --ntasks-per-node=1 -c ${SLURM_CPUS_PER_TASK} -x ${HEAD_HOSTNAME} ./wrapper apptainer exec ${APPTAINER_ARGS} ${SIF_IMAGE} ${RAY_CMD_WORKER} &
sleep 30

# Start server on head node to serve the model
echo "Starting server"
apptainer exec  ${APPTAINER_ARGS} ${SIF_IMAGE} vllm serve ${HF_MODEL} --tensor-parallel-size ${TENSOR_PARALLEL_SIZE} --pipeline-parallel-size ${PIPELINE_PARALLEL_SIZE}
```

When the server is running you can figure out where it is running using the squeue command for example:

```bash
squeue -u <username>
```

(Replace `<username>` with your actual Aire username). Alternatively, the details are written into the generated log files which should appear in the directory from where the job was submitted.

### Sending Prompts and Receiving Responses

When the server is running the nodes on which it is running are reported. These can then be connected to for sending prompts and receiving responses. The compute node can be connected to from a login node to send and receive, but for computationally intensive workflows, users should again submit jobs via the Slurm scheduler. The following script called test.sh connects to the server running on GPU node 011.

**test.sh**

```bash
curl http://gpu011:8000/v1/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "swiss-ai/Apertus-8B-2509",
        "prompt": "What is gravity?",
        "max_tokens": 100,
        "temperature": 0
    }'
```

If you run this and push the results into a file you should get something like the following:

```bash
$ ./test.sh > result.txt
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  1042  100   900  100   142    323     51  0:00:02  0:00:02 --:--:--   374

$ cat test.sh
curl http://gpu005:8000/v1/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "swiss-ai/Apertus-8B-2509",
        "prompt": "What is gravity?",
        "max_tokens": 100,
        "temperature": 0
    }'
```

## Considerata

There are numerous things to consider with the way this has been done. Firstly, this section considers security, it then considers system architecture and finally data storage and sharing.

### Data Storage and Sharing

…

### Security

A more secure way of running it is over a Unix socket, rather than over a TCP network socket:

```bash
apptainer exec ${APPTAINER_ARGS} ${SIF_IMAGE} vllm serve --uds $PWD/socket ${HF_MODEL}
```

A client can then connect to that socket:

```bash
curl --unix-socket $PWD/socket http://localhost:8000/v1/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "meta-llama/Llama-3.2-1B",
        "prompt": "Cheese is",
        "max_tokens": 100,
        "temperature": 0
    }'
```

It would be fractionally faster than a TCP socket, but more importantly, filesystem permissions restrict access to the socket, so it would not be open access.

### System Architecture

3 GPU cores per node is not a multiple of 2.

### Data Storage and Sharing

By default, some files are stored in the users `$HOME`.

`$SCRATCH` is significantly faster for IO and `$FLASH` is even faster yet.

Users can set up and share directories on `$SCRATCH`. `$FLASH` is not persistent between sessions, so it is necessary to copy data to `$FLASH` from `$SCRATCH` when starting up the server and for using a cache of prompts/responses. Any data to be saved needs copying from `$FLASH` to `$SCRATCH` before any scheduled Slurm job completes. Results on `$SCRATCH` that are to be kept also want copying to appropriate storage that is backed up.

Because models can be sizeable, it can help to share. Is there much need in having multiple copies of the same data?

### Sustainability

Large language models can place significant demands on resources, particularly GPUs. Recent [UK Guidance](https://www.gov.uk/government/publications/data-ethics-framework/data-and-ai-ethics-framework#environmental-sustainability-section) has highlighted the importance of monitoring and understanding the environmental impact of LLM workloads.

At the University of Leeds, we are interested in understanding how LLM workloads use shared HPC infrastructure, including their efficiency and energy usage. Better visibility into these workloads can help support more sustainable use of shared systems and reduce pressure on resources.

To help with this, we ask users to add the prefix LLM- to the names of jobs using LLMs on Aire.

```bash
#SBATCH --job-name=LLM-myproject
```

This will help the RSE team better understand overall LLM usage patterns on Aire. It will also allow us to identify these jobs while they are running and monitor resource usage and energy consumption in real time, supporting future work on sustainable and efficient use of the system.

## Links and abbreviations

- [Large Language Model](https://en.wikipedia.org/wiki/Large_language_model)
- [Aire](https://arc.leeds.ac.uk/knowledge-centre/resources/aire/)
- [Aire User Documentation](https://arcdocs.leeds.ac.uk/aire/)
- [vLLM](https://github.com/vllm-project/vllm/)
- [Apertus](https://apertus.ai/en/apps/apertus-model/)
- [CUDA](https://en.wikipedia.org/wiki/CUDA)
- [vLLM stable release version documentation](https://docs.vllm.ai/en/stable/)
- [vLLM latest release version documentation](https://docs.vllm.ai/en/latest/getting_started/installation/)
- [Hugging Face](https://huggingface.co/)
- [CPU](https://en.wikipedia.org/wiki/CPU)
- [GPU](https://en.wikipedia.org/wiki/GPU)

## Acknowledgements

This work was partly funded by UKRI as a Future Leaders Fellowship awarded to [Professor Viktoria Spaiser](https://essl.leeds.ac.uk/politics/staff/102/professor-viktoria-spaiser) (grant reference: [UKRI2043](https://gtr.ukri.org/projects?ref=UKRI2043)).
