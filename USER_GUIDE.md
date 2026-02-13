# User Guide


## Table of Contents
- [Overview](#overview)
- [Getting Started](#getting-started)
- [Troubleshooting](#troubleshooting)
- [Running Models](#running-models)
- [Managing Logs and Caches](#managing-logs-and-caches)
- [Additional Resources](#additional-resources)


## Overview
This guide helps users get started with Climate-Action-GABM, find documentation, and get support. Documentation will be updated as more features and configuration options are added.

In the rest of the document "you" means you as a Climate-Action-GABM user.


## Getting Started

### Pre-requisits
 You will either need a local installation of [Conda](https://conda.org/), or [Python](https://www.python.org/) at or above version 3.12. To check your default Python version run:

```bash
python3 --version
```

### Initial set up

#### Using Conda
If you use [Conda](https://conda.org/) which is distributed with[Anaconda](https://www.anaconda.com/)/[Miniconda](https://docs.conda.io/en/latest/miniconda.html) and [Miniforge](https://github.com/conda-forge/miniforge) you can set up Climate-Action-GABM in a new environment as follows:

```bash
conda create -n gabm
conda activate gabm
conda install python=3.12
pip install cag==0.1.0
```

You can then check all installed dependencies and create your own requirements file with:

```bash
conda list -e > requirements.txt
```


#### Using Python >=3.12
Install from [PyPI](https://pypi.org/) using [Pip](https://pypi.org/project/pip/) as follows:

```bash
python3 -m venv gabm-venv
source gabm-venv/bin/activate  # On Windows: gabm-venv\\Scripts\\activate
pip install --upgrade pip
pip install cag==0.1.0
```

You can then check installed dependencies with:

```bash
pip freeze > requirements.txt
```


### Set Up API Keys
Create `data/api_key.csv` with your API keys. See [API_KEYS.md](API_KEYS.md) for details and instructions.


### Run the Main Program
From the project root:

```bash
python3 -m cag
```

```
Describe what should happen...
```


## Troubleshooting
If you experience issues when installing, configuring, or running GABM, check here for guidance or updates. As the project evolves, troubleshooting tips and frequently asked questions will be added here.

If you encounter errors, check your Python version and that all dependencies are installed. If all versions match the documentation, please peruse [reported issues](https://github.com/compolis/Climate-Action-GABM/issues), comment on a relevent open issue or [open an issue](https://github.com/compolis/Climate-Action-GABM/issues/new/choose) to request support.


## Running Models
It is intended that you will be able to configure and run models. This section is to explain how to do this. This documentation will be updated in due course...


## Managing Logs and Caches
Climate-Action-GABM creates logs and caches (such as prompt/response caches for LLM services) that can grow large over time. User friendly ways to tidy up logs and caches and compile data into reproducible research objects are being developed for a future release. Similarly, more details will be provided as these features are implemented.


## Additional Resources
- [README.md](README.md)
- [Reported Issues](https://github.com/compolis/Climate-Action-GABM/issues)