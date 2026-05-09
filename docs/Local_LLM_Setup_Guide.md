# Local LLM Setup Guide (V3)

This repo supports a fully local LLM backend via `provider="local"` in `SIM_CONFIG`. It works with **any** OpenAI-compatible HTTP server — mlx-lm (Apple Silicon), Ollama (cross-platform), vLLM (NVIDIA HPC), sglang (NVIDIA HPC), llama.cpp / `llama-server` (any), LM Studio. No source changes are needed to swap models or runtimes — only `llm_model` and `local_base_url`.

> **Status.** First validated end-to-end with Qwen3 8B 4-bit on M1 16 GB (NB 24, 2026-05-09): full pipeline runs cleanly, reflections rich, Day-0 aggregate bias +0.50 (best on record). Full results in [docs/result_report.md](result_report.md).

---

## 1. Quickstart — mlx-lm + Qwen3 8B (M-series Mac, no admin)

```bash
# One-time setup
python3 -m venv ~/venvs/mlx
source ~/venvs/mlx/bin/activate
pip install --upgrade pip
pip install mlx-lm

# Pull the weights (~5 GB)
hf download mlx-community/Qwen3-8B-4bit

# In a dedicated terminal, leave running:
mlx_lm.server --model mlx-community/Qwen3-8B-4bit --port 8080
```

Sanity check:

```bash
curl http://localhost:8080/v1/models
```

Use it from this repo:

```python
from cag.abm.sim import run_simulation, SIM_CONFIG

SIM_CONFIG.update({
    "llm_provider": "local",
    "llm_model": "mlx-community/Qwen3-8B-4bit",
    "thinking": True,        # Qwen3 toggles enable_thinking automatically
    "debias": True,
    # Optional: defaults to http://localhost:8080/v1
    # "local_base_url": "http://localhost:8080/v1",
})
results = run_simulation(SIM_CONFIG, nation)
```

That's the whole integration. `provider="local"` works the same way for every alternative backend below.

---

## 2. Alternative backends

All four speak the OpenAI Chat Completions protocol, so the only thing that changes is **how you start the server** and **what URL you point at**. Set `local_base_url` in `SIM_CONFIG` (or export `CAG_LOCAL_BASE_URL`).

| Backend | Best for | Default URL | Install |
|---|---|---|---|
| **mlx-lm** | Apple Silicon, fast on M-series | `http://localhost:8080/v1` | `pip install mlx-lm` |
| **Ollama** | Cross-platform laptops, easy model swap | `http://localhost:11434/v1` | https://ollama.com/download (binary) |
| **vLLM** | NVIDIA GPU / HPC, batched throughput | `http://localhost:8000/v1` | `pip install vllm` |
| **sglang** | NVIDIA GPU / HPC, RadixAttention prefix cache | `http://localhost:30000/v1` | `pip install "sglang[all]"` |
| **llama.cpp** | CPU-only or any GPU vendor, GGUF models | `http://localhost:8080/v1` | build from source / `brew install llama.cpp` |

Examples of starting each:

```bash
# Ollama
ollama serve &
ollama pull qwen3:8b
# SIM_CONFIG: llm_model="qwen3:8b", local_base_url="http://localhost:11434/v1"

# vLLM (NVIDIA)
vllm serve mlx-community/Qwen3-8B-4bit --port 8000
# SIM_CONFIG: local_base_url="http://localhost:8000/v1"

# sglang (NVIDIA)
python -m sglang.launch_server --model-path Qwen/Qwen3-8B --port 30000
# SIM_CONFIG: local_base_url="http://localhost:30000/v1"

# llama.cpp
llama-server -m qwen3-8b-q4_k_m.gguf --port 8080
```

---

## 3. Model gallery

All entries are known to work with `provider="local"`. Models tagged "registered" get auto-tuned sampling presets and (where applicable) thinking-mode toggles via the model registry in [src/cag/io/llm.py](../src/cag/io/llm.py). Unregistered models still work — they fall through to bare defaults; pass `local_extra_body=...` in `SIM_CONFIG` to override.

| Family | Suggested checkpoint | License | Approx. RAM (4-bit) | Registered | Notes |
|---|---|---|---|---|---|
| Qwen3 8B | `mlx-community/Qwen3-8B-4bit` | Apache-2.0 | ~6 GB | yes | First validated path; `thinking=True` toggles `enable_thinking` |
| Qwen3 4B | `mlx-community/Qwen3-4B-Instruct-2507-4bit` | Apache-2.0 | ~3 GB | yes | Speed baseline for laptop |
| Qwen3 14B | `mlx-community/Qwen3-14B-4bit` | Apache-2.0 | ~10 GB | yes | Fits 16 GB M1, slower |
| Qwen3 32B | `Qwen/Qwen3-32B` | Apache-2.0 | ~20 GB+ (HPC) | yes | HPC target via vLLM |
| Llama 3.1 8B | `mlx-community/Meta-Llama-3.1-8B-Instruct-4bit` | Llama 3.1 (Meta) | ~6 GB | yes | Read the Llama license |
| Llama 3.2 3B | `mlx-community/Llama-3.2-3B-Instruct-4bit` | Llama 3.2 (Meta) | ~3 GB | yes | Lightweight alternative |
| Apertus | `swiss-ai/Apertus-8B-Instruct-2509` | Apache-2.0 | ~6 GB | yes | Open Swiss-AI model, multilingual |
| Mistral 7B | `mlx-community/Mistral-7B-Instruct-v0.3-4bit` | Apache-2.0 | ~5 GB | yes | Stable baseline |
| DeepSeek-R1-Distill | `mlx-community/DeepSeek-R1-Distill-Qwen-7B-4bit` | MIT | ~5 GB | yes | Reasoning-on by default; no toggle |

Adding a new family is a one-line entry to `_MODEL_REGISTRY` in [src/cag/io/llm.py](../src/cag/io/llm.py) — see "Extending the registry" below.

---

## 4. SIM_CONFIG keys

| Key | Default | Purpose |
|---|---|---|
| `llm_provider` | `"openai"` | Set to `"local"` to use a local server |
| `llm_model` | `"gpt-5-mini"` | The model name the local server expects (must match the loaded model exactly) |
| `local_base_url` | `None` → `CAG_LOCAL_BASE_URL` → `http://localhost:8080/v1` | OpenAI-compatible endpoint |
| `local_extra_body` | `None` | Dict merged into every request body (overrides registry defaults) |
| `local_timeout_s` | `None` → `CAG_LOCAL_TIMEOUT_S` → `600` | Per-call HTTP timeout (s) |
| `thinking` | `False` | Forwarded only to surveys; for Qwen3, toggles `enable_thinking` |

`SIM_CONFIG` keys for `survey_provider` / `survey_model` work the same way — you can run **mixed-provider experiments** with cheap local broadcasts and high-fidelity cloud surveys:

```python
SIM_CONFIG.update({
    "llm_provider": "local",
    "llm_model": "mlx-community/Qwen3-8B-4bit",
    "survey_provider": "anthropic",
    "survey_model": "claude-sonnet-4-6",
    "thinking": True,
})
```

---

## 5. Extending the registry

The registry in [src/cag/io/llm.py](../src/cag/io/llm.py) is a list of substring-keyed entries. To add a family:

```python
_MODEL_REGISTRY.append({
    "match": "phi-4",                                   # lowercase substring of model name
    "sampling_non_thinking": {"temperature": 0.7},
    "sampling_thinking":     {"temperature": 0.6},
    "max_tokens_msg":        2048,
    "max_tokens_thinking":   8192,
    # Optional: thinking-mode chat-template injection
    # "thinking_extra_body": lambda thk: {"chat_template_kwargs": {"some_flag": thk}},
})
```

For one-off overrides without code changes, use `SIM_CONFIG["local_extra_body"]` — it shallow-merges on top of any registry entry.

---

## 6. Troubleshooting

- **"Local LLM server not reachable"** — `ping_local()` runs at simulation start. Confirm the server is up (`curl <base_url>/models`) and `local_base_url` matches.
- **Empty responses with `thinking=True`** — the model burned its budget on reasoning and got truncated. The provider auto-retries once with thinking disabled and logs a WARNING. To suppress, raise `max_tokens_thinking` in the registry entry, or set `thinking=False`.
- **Slow first call** — model loading. mlx-lm typically warms up in ~10 s; vLLM in ~30 s. Subsequent calls are at steady-state throughput.
- **OOM on Apple Silicon** — drop to the 4B variant or close other apps. Monitor with Activity Monitor → Memory.
- **Garbled / repeated output** — sampling preset mismatch. Either register the family in `_MODEL_REGISTRY` with the right T/top_p, or pass them via `local_extra_body`.
- **Model name mismatch** — the `llm_model` string in `SIM_CONFIG` must **exactly** match what the server reports at `/v1/models`. mlx-lm uses the HuggingFace path; Ollama uses its own short tag (e.g. `qwen3:8b`).

---

## 7. HPC / parallelism notes

- Within-day calls (broadcast reflections, peer reflections, EOD surveys) are independent. Today the dispatcher is synchronous; an async dispatcher (Phase G in the local-LLM track) will give near-linear speedup against N replica servers.
- vLLM and sglang both do continuous batching and shared-prefix caching, which is a perfect fit for our long-persona / short-question call shape. Expect 5–20× per-replica throughput vs mlx-lm at the same model size.
- For multi-replica HPC: stand up `K` `vllm serve` instances on `K` GPUs, place a small load balancer (HAProxy / nginx / Caddy) in front, and point `local_base_url` at the balancer — no client-side changes needed.

---

## Legacy guides

The original V2 (mlx-lm only) and V1 (Qwen 2.5) walkthroughs are kept below for reference. They predate the integrated `provider="local"` and assumed a notebook-side monkey-patch, but the server-setup steps are still correct.

---

# Running Qwen 3 Locally on Apple Silicon (No Admin Rights) - V2 Plan

## Context

This v2 plan assumes an Apple Silicon Mac M1 with 16 GB RAM and **no admin rights**. It uses **MLX-LM only**. The recommended first target is `mlx-community/Qwen3-8B-4bit`, which is the strongest practical Qwen starting point for this machine class. If 8B feels too slow or causes memory pressure in real use, the fallback is `mlx-community/Qwen3-4B-Instruct-2507-4bit`.

This plan is meant for practical local setup first. It does not depend on changing the repo code.

## Recommended approach: MLX-LM only

### 1. One-time setup (no admin)

Use any Python available to your user account. Everything stays under `~/`:

```bash
# Create a user-owned virtualenv
python3 -m venv ~/venvs/mlx
source ~/venvs/mlx/bin/activate

# Install the runtime
pip install --upgrade pip
pip install mlx-lm
```

This installs into the virtualenv only. No `sudo`, no system installer, no app bundle.

### 2. Pull the Qwen 3 8B 4-bit weights

Warm the local cache up front so the first real run is predictable:

```bash
source ~/venvs/mlx/bin/activate
huggingface-cli download mlx-community/Qwen3-8B-4bit
```

The model files land in `~/.cache/huggingface/hub/`. This size class should fit on a 16 GB machine, but you should still close heavy apps if you want smoother inference.

### 3. Start the local server

```bash
source ~/venvs/mlx/bin/activate
mlx_lm.server \
    --model mlx-community/Qwen3-8B-4bit \
    --port 8080
```

Leave that terminal open. The server listens on `http://localhost:8080/v1/chat/completions`.

### 4. Sanity check with curl

From a second terminal:

```bash
curl http://localhost:8080/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
      "model": "mlx-community/Qwen3-8B-4bit",
      "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Give me a short summary of why local LLMs are useful."}
      ],
      "temperature": 0.5,
      "max_tokens": 256
    }'
```

If you get a non-empty reply back, the local stack is working.

### 5. Call it from Python with the OpenAI client

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="not-needed",
)

resp = client.chat.completions.create(
    model="mlx-community/Qwen3-8B-4bit",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain in two sentences what a climate opinion model is."},
    ],
    temperature=0.5,
    max_tokens=256,
)

print(resp.choices[0].message.content)
```

### 6. If Qwen 3 8B is too slow, drop to the 4B fallback

If 8B works but feels too slow for repeated calls, switch to a smaller Qwen 3 checkpoint:

```bash
source ~/venvs/mlx/bin/activate
huggingface-cli download mlx-community/Qwen3-4B-Instruct-2507-4bit

mlx_lm.server \
    --model mlx-community/Qwen3-4B-Instruct-2507-4bit \
    --port 8080
```

Then change the model string in your `curl` or Python call to `mlx-community/Qwen3-4B-Instruct-2507-4bit`.

### 7. What to expect on this laptop

- Qwen3 8B 4-bit is the highest practical first target for an M1 16 GB machine.
- It should be good enough for local experimentation and short prompt-response loops.
- It may still feel slow for many repeated ABM calls or long contexts.
- If responsiveness matters more than model strength, the 4B fallback is the safer daily-driver option.

## Verification checklist

- [ ] The MLX virtualenv activates cleanly.
- [ ] `huggingface-cli download mlx-community/Qwen3-8B-4bit` completes successfully.
- [ ] `mlx_lm.server` starts and binds to port `8080`.
- [ ] The `curl` smoke test returns a non-empty answer.
- [ ] The Python snippet prints a coherent response.
- [ ] If 8B is too slow, the 4B fallback works with only a model-name swap.

## Notes

- `mlx_lm.server` is suitable for local experimentation, not production deployment.
- For your laptop, Qwen3 8B is the right first trial; do not start with 14B or larger.
- If you later want tighter control over latency, the next step is prompt-length reduction or switching the same setup to the 4B model.

## Legacy reference

The original Qwen 2.5 plan is kept below for reference.

# Running Qwen 2.5 Locally on Apple Silicon (No Admin Rights)

## Context

This guide covers standing up a local LLM (Qwen 2.5 7B Instruct, 4-bit quantized) on an Apple Silicon Mac (M1, 16 GB RAM) **without admin rights** — useful for experimenting with local inference before deciding whether to integrate it into the simulation pipeline at [src/cag/io/llm.py](../src/cag/io/llm.py).

Two runtimes were considered: **Ollama** and **MLX-LM**. MLX-LM is the recommended path because it installs as a pure pip package into a user-owned virtualenv (no system installer, no `.app` drag, no kernel extension) and is Apple-native — typically ~25–40% faster than Ollama on M1 for the same quantization. Both expose an OpenAI-compatible HTTP API, so the integration shape into this repo's existing OpenAI codepath is identical.

## Recommended approach: MLX-LM

### 1. One-time setup (no admin)

Use any Python available to your user account (`/usr/bin/python3`, pyenv, mambaforge — all fine). Everything stays under `~/`:

```bash
# Create a user-owned virtualenv
python3 -m venv ~/venvs/mlx
source ~/venvs/mlx/bin/activate

# Install the runtime
pip install --upgrade pip
pip install mlx-lm
```

`mlx-lm` pulls in `mlx`, `transformers`, and `huggingface_hub`. All install to the venv's `site-packages` — no `/usr/local`, no `sudo`.

### 2. Pull the Qwen 2.5 7B Instruct 4-bit weights

The MLX community ships pre-quantized Qwen on Hugging Face. The first run downloads ~4.5 GB to `~/.cache/huggingface/hub/`:

```bash
# Optional: warm the cache up front. The server will otherwise pull on first use.
huggingface-cli download mlx-community/Qwen2.5-7B-Instruct-4bit
```

Resident memory at runtime: ~5–6 GB. Comfortable on 16 GB, leaves headroom for VS Code, a browser, and the simulation process.

### 3. Start the OpenAI-compatible server

```bash
source ~/venvs/mlx/bin/activate
mlx_lm.server \
    --model mlx-community/Qwen2.5-7B-Instruct-4bit \
    --port 8080
```

Leave that terminal open. The server speaks the OpenAI Chat Completions protocol at `http://localhost:8080/v1/chat/completions`.

Sanity check from a second terminal:

```bash
curl http://localhost:8080/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
      "model": "mlx-community/Qwen2.5-7B-Instruct-4bit",
      "messages": [
        {"role": "system", "content": "You are a healthy eating promoter."},
        {"role": "user", "content": "I made a ham and cheese sandwich. How is it?"}
      ],
      "temperature": 0.5
    }'
```

### 4. Call it from Python the same way the repo calls OpenAI

The OpenAI SDK supports a `base_url` override. This lets you reuse exactly the same call shape that [`_send_openai()` in src/cag/io/llm.py:191-218](../src/cag/io/llm.py#L191-L218) uses, just pointed at the local server. Save this as e.g. `scripts/try_local_qwen.py`:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="not-needed",          # MLX-LM ignores it; SDK requires a non-empty string
)

resp = client.chat.completions.create(
    model="mlx-community/Qwen2.5-7B-Instruct-4bit",
    messages=[
        {"role": "system", "content": "You are a healthy eating promoter."},
        {"role": "user", "content": "I made a ham and cheese sandwich. How is it?"},
    ],
    temperature=0.5,
)
print(resp.choices[0].message.content)
```

## Alternative: Ollama without admin

If you prefer Ollama (e.g. easier `ollama pull` for swapping models):

1. Download the standalone tarball — does **not** require the `.app` installer or admin:
   ```bash
   mkdir -p ~/bin
   curl -L https://ollama.com/download/Ollama-darwin.tgz -o /tmp/ollama.tgz
   tar -xzf /tmp/ollama.tgz -C ~/bin
   export PATH="$HOME/bin:$PATH"   # add to ~/.zshrc to persist
   ```
2. Run the daemon (port 11434, no privileged ports needed):
   ```bash
   ollama serve &
   ollama pull qwen2.5:7b-instruct-q4_K_M
   ```
3. Same Python snippet as above, but `base_url="http://localhost:11434/v1"` and `model="qwen2.5:7b-instruct-q4_K_M"`.

If the tarball URL has changed, the standalone binary is also at the GitHub releases page (`ollama/ollama` → Releases → `ollama-darwin*` asset) — same idea, drop into `~/bin`.

## Verification

End-to-end checklist:

- [ ] Server terminal shows the model loaded and a "running on http://127.0.0.1:8080" line.
- [ ] `curl` smoke test returns a non-empty `choices[0].message.content`.
- [ ] The Python snippet prints a coherent reply in under ~5 s for a short prompt.
- [ ] Rough throughput: short prompts return in 1–3 s; ~30 tok/s sustained generation is normal on M1 16 GB. If you see <5 tok/s, you're likely swapping — close other apps or drop to the 3B variant (`mlx-community/Qwen2.5-3B-Instruct-4bit`).
- [ ] MLX-LM's server queues sequentially, which matches this repo's existing synchronous call pattern — no concurrency assumptions are broken.

## Forward-looking note: integrating into the simulation

When you're ready to wire local Qwen into the simulation pipeline, the integration is small because [src/cag/io/llm.py](../src/cag/io/llm.py) already dispatches by a `provider` string in `send_chat()`. The cheapest route is to add a `provider="local"` branch that reuses the OpenAI SDK with a `base_url` argument — most of [`_send_openai()`](../src/cag/io/llm.py#L191-L218) carries over verbatim, minus the `reasoning_effort` injection (lines 207–213) which is OpenAI-specific. The existing `_resilient_call()` helper will auto-strip any params Qwen rejects, so no manual compatibility list is needed.

Once wired, existing notebooks switch over by just passing `provider="local", model="mlx-community/Qwen2.5-7B-Instruct-4bit"` — agent code in [src/cag/abm/agent.py](../src/cag/abm/agent.py) needs no changes.
