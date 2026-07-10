# Local LLM Setup Guide

This repo can run against a fully local LLM through `provider="local"` in `SIM_CONFIG`.
It speaks the OpenAI Chat Completions protocol, so **any** OpenAI-compatible server works
(Ollama, vLLM, sglang, llama.cpp, LM Studio, …) — you only ever set `llm_model` and
`local_base_url`, no source changes. This guide covers the one path we use for local
development on an Apple-Silicon Mac: mlx-lm serving **Qwen3-8B-4bit**.

---

## 1. Install and serve the model (Apple Silicon, no admin)

```bash
# One-time setup — user-owned virtualenv, no sudo
python3 -m venv ~/venvs/mlx
source ~/venvs/mlx/bin/activate
pip install --upgrade pip
pip install mlx-lm

# Download the weights (~6 GB; fits a 16 GB M-series Mac)
hf download mlx-community/Qwen3-8B-4bit

# Start the server in a dedicated terminal and leave it running
mlx_lm.server --model mlx-community/Qwen3-8B-4bit --port 8080
```

Sanity check from a second terminal — a non-empty JSON reply means the server is up:

```bash
curl http://localhost:8080/v1/models
```

---

## 2. Point the simulation at it

```python
from cag.abm.sim import run_simulation, SIM_CONFIG

SIM_CONFIG.update({
    "llm_provider": "local",
    "llm_model": "mlx-community/Qwen3-8B-4bit",
    # local_base_url defaults to http://localhost:8080/v1, so it can be omitted
})
results = run_simulation(SIM_CONFIG, nation)
```

That is the whole integration. `mlx-community/Qwen3-8B-4bit` is already the Mac
`SIM_CONFIG` default, so those two lines are only needed if you have changed it.

---

## 3. Any other backend

Because the path is just an OpenAI-compatible endpoint, any other server works the same
way — start it however you like and set `llm_model` + `local_base_url` to match. For
example, with Ollama:

```bash
ollama serve &
ollama pull qwen3:8b
# SIM_CONFIG: llm_model="qwen3:8b", local_base_url="http://localhost:11434/v1"
```

On AIRE the launcher wires this up for you with vLLM — see
[AIRE_Quickstart.md](AIRE_Quickstart.md).
