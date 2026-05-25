# Climate-Action-GABM — Simulation Configuration Guide

A two-layer reference for the dict you pass to [`run_simulation(config, nation)`](../src/cag/abm/sim.py).

- **Layer 1 — Supervisor brief** (§1–§3): a short narrative of what the canonical run does, which six defaults define the research design, and what is frozen versus tunable. A supervisor can stop reading after Layer 1 and have a defensible mental model.
- **Layer 2 — Developer / operator matrix** (§4 onward): every active `SIM_CONFIG` key with source location, type, valid values, validating notebook, interactions with other keys, and copy-paste canonical profiles.

> **Companion docs.** Prompts and persona text: [Prompts_and_Personas_Guide_v2.md](Prompts_and_Personas_Guide_v2.md). Output artefacts: [Run_Output_Guide.md](Run_Output_Guide.md). Local-LLM server setup: [Local_LLM_Setup_Guide.md](Local_LLM_Setup_Guide.md). Design rationale and decision history: [Model_Design.md](Model_Design.md).

> **All line numbers in this guide are accurate as of the commit that introduced this doc.** If a `file.py:NNN` pointer no longer matches, search for the named symbol — those are stable.

---

## 1. What the canonical run is configured to do

Out of the box `SIM_CONFIG` ([sim.py L29–L99](../src/cag/abm/sim.py#L29-L99)) describes one specific experimental setup. A run with **no overrides** would:

1. Simulate **100 citizens** drawn from the YouGov April 2024 climate survey.
2. Use **local Qwen3-8B-4bit** served from `http://localhost:8080/v1` (an `mlx_lm.server` process) as the LLM for every prompt — citizen reflections, peer messages, surveys, Day-0 rationales. API providers (OpenAI / Anthropic / Google) are supported but treated as an *outsider path*: documented and tested, but not the research default.
3. Run **package mode**: every broadcast and peer message addresses **all 6 climate policies at once** (Carbon Tax, Ban Petrol Cars, Climate Compensation, Government Subsidies, Renewable Energy, Local Forest Protection). Days alternate phase order — odd days `[P-A, P-B, C]`, even days `[P-B, P-A, C]` — to balance recency effects across sides.
4. Pull political-broadcast text from the **offline pool** under `data/political_messages/messages_v1.csv` (40 package cells, 20 per side, plus single-policy cells). No LLM call is made on the political-agent side; the run aborts at start if any required cell is missing.
5. Seed **Day-0 opinions from YouGov ground truth** and ask the LLM only to write the rationale (`day0_anchor='ground_truth_with_rationale'`). This eliminates the Day-0 pro-climate bias the LLM otherwise exhibits (NB11–14) without throwing away the qualitative narrative trace.
6. Apply **Condition B debias** to every end-of-day survey (`debias=True`) — a two-step prompt chain validated in NB13–15 to remove most of the LLM's residual pro-climate inflation on end-of-day surveys.
7. Build a **stochastic-block peer network** with intra-block edge probability 0.15 and inter-block 0.02, partitioned by `political_exposure` (A-only / B-only / both / neither).
8. Assign `political_exposure` by the **affinity-rank rule** targeting a **committed-minority symmetric** preset (11% A-only / 11% B-only / 33% both / 45% neither), using the **balanced** affinity-weight preset.
9. Use **symmetric reach** (`reach_a = reach_b = 1.0`) and **no audience cap** — every exposed citizen receives every broadcast on their side.
10. Have each citizen send peer messages to **3 network neighbours per day**.

`config` passed to `run_simulation()` is merged on top of `SIM_CONFIG` (`cfg = {**SIM_CONFIG, **config}`, [sim.py L529](../src/cag/abm/sim.py#L529)), so only keys you want to *change* need to appear in your override dict.

---

## 2. The six defaults that define the research design

These are the **canon defaults**. Changing them invalidates the validating notebook chain (NB11–15, NB25, NB29) and should be done only deliberately.

| Key | Canon value | Validated by | Why this default |
|---|---|---|---|
| `llm_model` | `mlx-community/Qwen3-8B-4bit` | NB25 (parity with API providers) | Local, reproducible, no API spend; Qwen3 has a clean thinking-mode toggle. |
| `llm_provider` | `local` | NB24, NB25 | Decouples research runs from API rate limits and pricing changes. |
| `communication_mode` | `package` | NB16 (sanity), NB29 (full smoke) | Single-policy mode artificially under-states cross-policy spillover; package mode is the research direction. |
| `day0_anchor` | `ground_truth_with_rationale` | (locked in v0.6 defaults overhaul) | Eliminates Day-0 LLM pro-climate bias by construction while preserving rationale traces for qualitative review. |
| `debias` | `True` | NB13 (Condition B), NB14 (4-policy generalisation), NB15 (Sonnet + thinking) | Reduces residual LLM pro-climate inflation on end-of-day surveys by 73–97%. |
| `political_message_source` | `offline` | NB16, NB29 | Real-world political text (party press releases / MP speeches) is the research direction; LLM-generated political messages are a fallback. |

Day-0 anchor and debias **interact**: when `day0_anchor != "llm_survey"`, the `debias` flag is *ignored on Day 0* (a Day-0 LLM survey is not run; rationale is generated by a different code path) but still applies to end-of-day surveys. The simulation logs an INFO message at start ([sim.py L304–L308](../src/cag/abm/sim.py#L304-L308)).

---

## 3. Frozen vs tunable, and what is deferred

**Frozen (research canon — do not change without re-validation):**
the six keys above, plus the broadcast / peer / survey / memory prompt templates in [agent.py](../src/cag/abm/agent.py) (audited in [Prompts_and_Personas_Guide_v2.md](Prompts_and_Personas_Guide_v2.md)).

**Tunable per run (experimental knobs):**
`n_citizens`, `days` (length, phase order, broadcast frequency), `k_peers_per_day`, `network_type` + `network_params`, `reach_a` / `reach_b`, `audience_cap`, `political_exposure_targets` (preset or literal), `affinity_weights` (preset or literal), `random_seed`. The reach / audience / target / weight knobs are explicitly designed as experimental controls — see [Literature_Political_Exposure.md](Literature_Political_Exposure.md) §6–§7.

**Deferred decisions** (in flight; see [Model_Design.md §20](Model_Design.md) and the progress log):

- **Day-0 anchoring side-by-side comparison.** All three modes (`llm_survey`, `ground_truth`, `ground_truth_with_rationale`) are implemented; running all three in parallel on the same cohort to disentangle priming from regression-to-prior remains future work.
- **Condition B re-measurement on the v0.5 first-person prompt chain.** NB13's ~97% bias-reduction figure was measured on the pre-v0.5 mixed-perspective prompts; a partial NB13 rerun on the unified 1P chain is queued.
- **Async / parallel agent dispatch** ([Model_Design.md §16](Model_Design.md)).
- **Version bump** 0.3.0 → 0.6.0 across the 12 source modules (currently lagging; CHANGE_LOG is ahead).

---

## 4. How to read the matrix

Every key in §6 uses a four-block layout:

1. **Signature** — `key`, default, type / range.
2. **What it does at runtime** — code pointer in `file:line` form.
3. **Why this default** — citation to a notebook (`NB11`–`NB29`) or a [Model_Design.md](Model_Design.md) section.
4. **Interactions / gotchas** — which other keys it couples with.

Tag legend used in the at-a-glance table (§5):

- `[canon]` — research-canon default; do not change without re-validation.
- `[tune]` — tunable per run; explicitly designed as an experimental knob.
- `[infra]` — infrastructure / I/O; safe to change for environment reasons.

`config` passed to `run_simulation()` is merged with `**SIM_CONFIG`, so partial overrides are the norm.

---

## 5. The 32 keys at a glance

Source: [sim.py L29–L99](../src/cag/abm/sim.py#L29-L99). Grouped by family.

| # | Key | Default | Type | Tag | Validated by |
|---|---|---|---|---|---|
| **Population** | | | | | |
| 1 | `n_citizens` | `100` | int | [tune] | NB29 |
| **Day plan** | | | | | |
| 2 | `days` | `[{"phases":["P-A","P-B","C"]}, {"phases":["P-B","P-A","C"]}]` | list[dict] | [tune] | NB29 |
| 3 | `k_peers_per_day` | `3` | int ≥ 0 | [tune] | NB05 |
| **Peer network** | | | | | |
| 4 | `network_type` | `"stochastic_block"` | str (see §6.3) | [tune] | NB26 (factory demo) |
| 5 | `network_params` | `None` | dict \| None | [tune] | NB26 |
| 6 | `p_intra` | `0.15` | float [0,1] | [tune] | legacy SBM default |
| 7 | `p_inter` | `0.02` | float [0,1] | [tune] | legacy SBM default |
| 8 | `block_sizes` | `None` | list[int] \| None | [tune] | — |
| 9 | `diagnostics_timeout_s` | `30.0` | float ≥ 0 | [infra] | — |
| **LLM (canonical)** | | | | | |
| 10 | `llm_model` | `"mlx-community/Qwen3-8B-4bit"` | str | [canon] | NB25 |
| 11 | `llm_provider` | `"local"` | str | [canon] | NB24, NB25 |
| 12 | `llm_temperature` | `0.5` | float | [tune] | — |
| 13 | `survey_model` | `None` | str \| None | [tune] | NB15 (split-model run) |
| 14 | `survey_provider` | `None` | str \| None | [tune] | NB15 |
| 15 | `thinking` | `False` | bool | [tune] | NB15, NB22 |
| 16 | `debias` | `True` | bool | [canon] | NB13, NB14, NB15 |
| **Communication mode** | | | | | |
| 17 | `communication_mode` | `"package"` | str | [canon] | NB16, NB29 |
| 18 | `package_policies` | `ALL_CLIMATE_POLICIES` (6) | tuple[ClimatePolicyID] | [tune] | NB16 |
| **Political messaging** | | | | | |
| 19 | `political_message_source` | `"offline"` | str | [canon] | NB29 |
| 20 | `political_message_set` | `"v1"` | str | [tune] | NB29 |
| **Day-0 anchor** | | | | | |
| 21 | `day0_anchor` | `"ground_truth_with_rationale"` | str (3 options) | [canon] | v0.6 defaults overhaul |
| **Reach / audience** | | | | | |
| 22 | `reach_a` | `1.0` | float [0,1] | [tune] | NB20, NB21 |
| 23 | `reach_b` | `1.0` | float [0,1] | [tune] | NB20, NB21 |
| 24 | `audience_cap` | `None` | int ≥ 0 \| None | [tune] | NB21 |
| **Political exposure** | | | | | |
| 25 | `political_exposure_mode` | `"rule_affinity_rank"` | str (3 options) | [tune] | NB23 |
| 26 | `political_exposure_targets` | `None` (→ committed_minority_symmetric) | str preset \| dict \| None | [tune] | Literature_Political_Exposure §6 |
| 27 | `affinity_weights` | `None` (→ balanced) | str preset \| dict \| None | [tune] | NB23 |
| **Reproducibility / IO** | | | | | |
| 28 | `random_seed` | `42` | int | [tune] | — |
| 29 | `output_dir` | `"data/output/experiments"` | str (path) | [infra] | — |
| **Local-LLM runtime** | | | | | |
| 30 | `local_base_url` | `None` (→ env or `http://localhost:8080/v1`) | str \| None | [infra] | NB24, NB25 |
| 31 | `local_extra_body` | `None` | dict \| None | [infra] | Local_LLM_Setup_Guide |
| 32 | `local_timeout_s` | `None` (→ env or 600 s) | float \| None | [infra] | NB24 |

---

## 6. Per-key reference

### 6.1 Population

#### `n_citizens` — int, default `100`

- *Runtime:* upper bound on YouGov rows loaded; actual cohort size = `len(nation.agents_active)` after dropping unusable rows. Used by `_run_baseline_surveys` and every per-agent loop in [sim.py](../src/cag/abm/sim.py).
- *Why this default:* 100 is the current source default and a practical mid-point between smoke-scale checks and full cohorts; the [Model_Design.md](Model_Design.md) target is often 30–50 agents for full research runs depending on cost and throughput.
- *Interactions:* couples with `n_citizens` is what `apply_audience_cap` and `apply_reach_subsample` operate on; a cohort smaller than ~30 produces extreme stochasticity in exposure cells and is only appropriate for smoke tests (NB29 uses 10).

### 6.2 Day plan

#### `days` — list[dict], default `[{"phases":["P-A","P-B","C"]}, {"phases":["P-B","P-A","C"]}]`

- *Runtime:* iterated literally by `run_simulation` ([sim.py L671](../src/cag/abm/sim.py#L671)); each entry is one simulated day. `_resolve_day_phases` ([sim.py L195](../src/cag/abm/sim.py#L195)) expands a day entry to a phase list.
- *Two ways to specify a day:*
  - **Canonical:** `{"phases": ["P-A", "P-B", "C"]}` — verbatim list of `P-A` / `P-B` / `C` tokens. Repeats allowed (`["P-A","P-A","P-B","C"]` makes agent A broadcast twice).
  - **Sugar via [`make_phases`](../src/cag/abm/sim.py#L102):** `{"broadcasts_a": 3, "broadcasts_b": 1, "peer": True, "interleave": False, "a_first": True}` — convenient for asymmetric-broadcast experiments.
  - Mixing `phases` with sugar keys in the same day entry **raises `ValueError`** ([sim.py L201–L205](../src/cag/abm/sim.py#L201-L205)).
- *Single-policy mode also needs `policy`*: in `communication_mode='single_policy'`, every day dict **must** also contain `"policy": ClimatePolicyID.X`. Under `package` mode any `policy` key is silently ignored ([sim.py L42–L46](../src/cag/abm/sim.py#L42-L46) comment).
- *Why this default:* alternating phase order balances which side speaks first on a given day, mitigating recency bias in the end-of-day survey.

#### `k_peers_per_day` — int ≥ 0, default `3`

- *Runtime:* number of network neighbours each citizen sends a peer message to during a `C` phase ([sim.py L463–L468 / L479–L484](../src/cag/abm/sim.py#L463-L484)).
- *Why this default:* matches v0.3 NB05 baseline. Higher values multiply LLM cost linearly per peer phase.
- *Interactions:* if the network is very sparse (e.g. Erdős–Rényi with low `p`) some citizens will have fewer than `k_peers_per_day` neighbours and simply send to all of them.

### 6.3 Peer network

#### `network_type` — str, default `"stochastic_block"`

One of the five builders registered in [networks.py L40](../src/cag/abm/networks.py#L40):

| `network_type` | `network_params` keys (with defaults) | Use case |
|---|---|---|
| `"stochastic_block"` | `p_intra` (0.15), `p_inter` (0.02) | Default; 2 blocks driven by `political_exposure` (A-only → block 0, B-only → block 1, swing round-robined) |
| `"erdos_renyi"` | `p` (0.05) | `G(n, p)` null model |
| `"watts_strogatz"` | `k` (6, even, < n), `beta` (0.1) | Small-world |
| `"barabasi_albert"` | `m` (3, 1 ≤ m < n) | Preferential attachment / scale-free |
| `"homophily_weighted"` | `attributes` (defaults to `("ukge2019_vote_id", "brexit_vote_id", "region_id")`), `weights` (None → uniform; must be same length as `attributes`), `scale` (6.0), `threshold` (3.0) | Continuous similarity-weighted random graph; edge probability `sigmoid(scale·sim − threshold)` |

Source: per-builder docstrings in [networks.py L100–L270](../src/cag/abm/networks.py#L100-L270).

- *Runtime:* `nation.create_network(network_type, network_params, seed)` ([environment.py L944](../src/cag/abm/environment.py#L944)) dispatches via `build_network()`.

#### `network_params` — dict | None, default `None`

- *Runtime:* type-specific param dict; merged with `p_intra` / `p_inter` legacy keys via `_resolve_network_params` ([sim.py L221–L237](../src/cag/abm/sim.py#L221-L237)) for back-compat with the SBM.
- *Example overrides:*
  ```python
  # Watts–Strogatz small-world
  {"network_type": "watts_strogatz", "network_params": {"k": 8, "beta": 0.2}}
  # Homophily on a custom attribute set with explicit weights
  {"network_type": "homophily_weighted",
   "network_params": {
       "attributes": ["ukge2019_vote_id", "selftransc_id", "openness_id"],
       "weights":    [2.0, 1.0, 1.0],
       "scale": 6.0, "threshold": 3.0,
   }}
  ```

#### `p_intra` (0.15), `p_inter` (0.02), `block_sizes` (None) — legacy SBM flat keys

- *Runtime:* recognised by `_resolve_network_params` only when `network_type == "stochastic_block"`. Folded into `network_params` if not already present there. `block_sizes` defaults to equal split.
- *Resume behaviour:* these keys are *folded into the resolved network params before resume comparison* ([sim.py L1042–L1051](../src/cag/abm/sim.py#L1042-L1051)), so upgrading a config from flat keys to `network_params={...}` does not trigger a spurious resume mismatch.

#### `diagnostics_timeout_s` — float ≥ 0, default `30.0`

- *Runtime:* wall-clock cap (POSIX-only, SIGALRM-based) on the conditional metric block in `compute_diagnostics` (clustering / shortest-path / diameter). The cheap metrics (degree, density, components, assortativity) always run. Set `0` or `None` to disable. Per-metric size caps (5000 / 2000 / 2000 nodes) still apply.

### 6.4 LLM (canonical)

#### `llm_model` — str, default `"mlx-community/Qwen3-8B-4bit"`

- *Runtime:* passed to `send_chat()` for every non-survey LLM call ([sim.py L455–L488](../src/cag/abm/sim.py#L455-L488)). For local provider, fuzzily matched against `_MODEL_REGISTRY` in [llm.py L104–L148](../src/cag/io/llm.py#L104-L148) to pick sampling defaults and `max_tokens`.
- *Local-LLM model registry* (substring match, first wins):

  | Family match | Sampling (non-thinking) | Sampling (thinking) | Thinking knob | `max_tokens_msg` / `_thinking` |
  |---|---|---|---|---|
  | `qwen3` | temp 0.7, top_p 0.8 | temp 0.6, top_p 0.95 | `chat_template_kwargs.enable_thinking` | 2048 / 16384 |
  | `deepseek-r1` | temp 0.6, top_p 0.95 | temp 0.6, top_p 0.95 | (always reasons) | 4096 / 16384 |
  | `llama` | temp 0.7, top_p 0.9 | temp 0.7, top_p 0.9 | — | 2048 / 4096 |
  | `apertus` | temp 0.7, top_p 0.9 | temp 0.7, top_p 0.9 | — | 2048 / 4096 |
  | `mistral` | temp 0.7, top_p 0.9 | temp 0.7, top_p 0.9 | — | 2048 / 4096 |
- *Why this default:* parity-tested in NB25 against API providers; Qwen3 has a clean thinking-mode toggle and fits in 8B-4bit MLX memory budget.

#### `llm_provider` — str, default `"local"`

- *Runtime:* selects the backend in `send_chat()`. Valid: `"local"`, `"openai"`, `"anthropic"`, `"google"`.
- *Side effect when `local`:* `_resolve_runtime` calls `configure_local()` + `ping_local()` at start ([sim.py L344–L352](../src/cag/abm/sim.py#L344-L352)); a missing server **aborts the run** before any agent call.
- *Why this default:* see §2.

#### `llm_temperature` — float, default `0.5`

- *Runtime:* sampling temperature for every LLM call. For local provider, **the model registry overrides this** with per-family defaults unless `local_extra_body` explicitly sets `temperature`.
- *Gotcha:* changing only `llm_temperature` on a local Qwen3 run has no effect; pass `local_extra_body={"temperature": X}` instead.

#### `survey_model` — str | None, default `None`

- *Runtime:* if set, overrides `llm_model` for **end-of-day surveys and Day-0 LLM survey** only ([sim.py L380–L389](../src/cag/abm/sim.py#L380-L389)). `None` → use `llm_model` for surveys too.
- *Why:* lets you run cheap-model broadcasts/reflections but a stronger-model survey (used in NB15 Sonnet-survey setup).

#### `survey_provider` — str | None, default `None`

- *Runtime:* if set, overrides `llm_provider` for surveys. Used together with `survey_model` to enable dual-provider runs.

#### `thinking` — bool, default `False`

- *Runtime:* **passed only to surveys** — `_run_day0` ([sim.py L283](../src/cag/abm/sim.py#L283)) and `nation.run_end_of_day_survey` ([sim.py L484–L489](../src/cag/abm/sim.py#L484-L489)). **NOT** passed to broadcasts, peer messaging, or memory management — those always run with `thinking=False` defaults at the agent/environment layer.
- *Why decoupled:* survey reasoning quality benefits most from thinking mode; reflections and peer messages are length-bound and thinking blows past the budget. See NB15 for the rationale.

#### `debias` — bool, default `True`

- *Runtime:* turns on the two-step Condition B prompt chain in `administer_survey()` and `run_end_of_day_survey()`. On Day 0, the flag is **ignored** when `day0_anchor != "llm_survey"` (logged at INFO, [sim.py L304–L308](../src/cag/abm/sim.py#L304-L308)).
- *Why this default:* NB13 (97% bias reduction on Ban Petrol Cars), NB14 (3/4 policies improved), NB15 (Sonnet + debias + thinking gave the strongest run to date).

### 6.5 Communication mode

#### `communication_mode` — str, default `"package"`

- *Valid:* `"package"` or `"single_policy"`.
- *Runtime:* `_is_package_mode(cfg)` ([sim.py L213](../src/cag/abm/sim.py#L213)) selects the entire P-A / P-B / C / EOD-survey / memory pipeline ([sim.py L443–L500](../src/cag/abm/sim.py#L443-L500)).
- *Single-policy mode contract:* every entry in `days` **must** contain `"policy": ClimatePolicyID.X`. Under `package` mode `policy` is silently ignored.

#### `package_policies` — tuple[ClimatePolicyID], default `ALL_CLIMATE_POLICIES`

- *Runtime:* the policies broadcast together each phase and surveyed each end-of-day. Used in `run_package_broadcast`, `run_package_peer_messaging`, `run_end_of_day_survey` loop.
- *Override example:* `{"package_policies": (ClimatePolicyID.CARBON_TAX, ClimatePolicyID.RENEWABLE_ENERGY)}` to restrict the package to a 2-policy subset.

### 6.6 Political messaging

#### `political_message_source` — str, default `"offline"`

- *Valid:* `"offline"` or `"llm"`. Anything else **raises `ValueError`** at start ([sim.py L356–L360](../src/cag/abm/sim.py#L356-L360)).
- *Offline contract:* `_resolve_runtime` calls `load_message_pool(cfg["political_message_set"])` then `message_pool.validate_required(sides=("A","B"), policy_ids=..., include_package=...)` ([sim.py L362–L380](../src/cag/abm/sim.py#L362-L380)). Any missing cell aborts the run **before the first LLM call**. No silent fallback.

#### `political_message_set` — str, default `"v1"`

- *Runtime:* resolves to `data/political_messages/messages_<set>.csv` + `sources_<set>.csv`. The shipping set is `v1` (40 package + 240 single-policy rows).

### 6.7 Day-0 anchor

#### `day0_anchor` — str, default `"ground_truth_with_rationale"`

- *Valid:* `"llm_survey"` | `"ground_truth"` | `"ground_truth_with_rationale"` (`VALID_DAY0_ANCHORS`, [sim.py L101](../src/cag/abm/sim.py#L101)). Anything else **raises `ValueError`** at start.
- *Runtime semantics* ([sim.py L268–L316](../src/cag/abm/sim.py#L268-L316)):
  - **`llm_survey`** — administer the full LLM survey on Day 0 (legacy v0.3 behaviour; preserves the NB11–14 bias-measurement story).
  - **`ground_truth`** — seed `opinion_history[(0)]` directly from YouGov; **no LLM call** on Day 0.
  - **`ground_truth_with_rationale`** — seed from YouGov *and* ask the LLM to write a rationale for that position; rationale stored in `survey_reasoning.csv`.
- *Interactions:* `debias` is ignored on Day 0 when this is not `llm_survey`; the warning is logged once.

### 6.8 Reach / audience

#### `reach_a`, `reach_b` — float [0, 1], default `1.0`

- *Runtime:* `nation.apply_reach_subsample(reach_a, reach_b, seed)` ([environment.py L885](../src/cag/abm/environment.py#L885)). Replaces each political agent's `connected_citizens` with `floor(reach * |connected|)` random members. RNG seeds: `seed` for A, `seed + 1` for B — independent draws, reproducible.
- *Validation:* values outside `[0.0, 1.0]` **raise `ValueError`** at start ([sim.py L549–L553](../src/cag/abm/sim.py#L549-L553)).
- *Use case:* model asymmetric broadcast reach (e.g. Reform UK media presence > Green party).

#### `audience_cap` — int ≥ 0 | None, default `None`

- *Runtime:* `nation.apply_audience_cap(cap, seed)` ([environment.py L826](../src/cag/abm/environment.py#L826)) — uniform random subsample to at most `cap` per political agent. RNG seeds: `seed + 100` for A, `seed + 101` for B (independent).
- *Order:* `assign_political_exposure` → `apply_audience_cap` → `apply_reach_subsample`. So `reach` is a fraction of the **capped** audience.
- *Why this knob exists:* at small N the YouGov sample composition produces structurally asymmetric audiences (e.g. A=27 vs B=20 at N=30). Setting `cap = min(|A|, |B|)` makes `reach_a = reach_b = 1.0` a true symmetric baseline.
- *Validation:* non-int / bool / negative → **`ValueError`** at start ([sim.py L555–L562](../src/cag/abm/sim.py#L555-L562)).

### 6.9 Political exposure

#### `political_exposure_mode` — str, default `"rule_affinity_rank"`

- *Valid* (`VALID_EXPOSURE_MODES`, [environment.py L165](../src/cag/abm/environment.py#L165)):
  - `"rule_affinity_rank"` — **default.** Deterministic top-K on a weighted affinity score; realised marginals hit `targets` exactly (±1 per cell from rounding).
  - `"rule_priority_chain"` — legacy v0.5 vote-based rule. Cells fall out of the YouGov sample; `targets` ignored. Preserved for reproducibility.
  - `"rule_signal_count"` — currently an alias of `priority_chain` (reserved).

#### `political_exposure_targets` — str preset | dict | None, default `None`

- *Preset registry* (`TARGET_PRESETS`, [environment.py L84](../src/cag/abm/environment.py#L84)):

  | Preset | A-only | B-only | both | neither | Notes |
  |---|---|---|---|---|---|
  | `committed_minority_symmetric` *(default when `None`)* | 0.11 | 0.11 | 0.33 | 0.45 | Symmetric committed minorities; 45% disengaged anchored to Reuters DNR 2024 + Hansard Audit 16. |
  | `committed_minority_uk_2024` | 0.08 | 0.14 | 0.33 | 0.45 | Asymmetric (B > A), JL Partners GB News viewer panel (Apr 2024). |
  | `legacy_v05` | 0.225 | 0.225 | 0.20 | 0.35 | v0.5 default; pre-committed-minority. |
- *Literal dict allowed:* `{"A-only": ..., "B-only": ..., "both": ..., "neither": ...}` — must sum to 1.0.
- *Why this default:* see the long block comment at [environment.py L37–L72](../src/cag/abm/environment.py#L37-L72) and [Literature_Political_Exposure.md](Literature_Political_Exposure.md) §6.

#### `affinity_weights` — str preset | dict | None, default `None`

- *Preset registry* (`AFFINITY_WEIGHT_PRESETS`, [environment.py L157](../src/cag/abm/environment.py#L157)):

  | Preset | Idea | Headline weights (per side; identical A and B) |
  |---|---|---|
  | `balanced` *(default when `None`)* | All three signal families contribute | `openness` 1.5, `selftransc` 1.5, `conformtrad` 1.0, `sdo` 1.0, `rwa` 1.0, `age` 1.0, `education` 1.0, `region` 0.75, `brexit` 1.5, `politics` 1.5, `vote_bonus` 2.0 |
  | `vote_dominant` | "Is it all just vote choice?" | doubles `brexit` / `politics` / `vote_bonus`, halves values + demographics |
  | `values_dominant` | "Can values alone reproduce the cells?" | doubles values + SDO + RWA + conformtrad, halves vote-related signals |
- *Literal dict allowed:* `{"A": {...}, "B": {...}}` with the same key set as the presets.
- *Why these weights:* full rationale at [environment.py L92–L122](../src/cag/abm/environment.py#L92-L122):
  - Vote bonus highest (2.0) — vote choice is the strongest empirical proxy for partisan media diet (Fletcher & Nielsen 2017). Bonus is signed in `[−2, +2]` so a Brexit vote can subtract from the green score.
  - Openness and self-transcendence at 1.5 — strongest values-level predictors of pro-environmental attitudes (Steg & de Groot 2010).
  - SDO / RWA / conformity-tradition at 1.0 — broader authoritarianism markers, not climate-specific.
  - Demographics at 0.75–1.0 — proxies rather than direct attitudinal indicators.
- *Why hand-picked, not fitted:* no UK individual-level ground truth for who is in which echo chamber, so fitted coefficients would be circular. Hand-picked priors anchored to published correlations are honest about the uncertainty.

### 6.10 Reproducibility / IO

#### `random_seed` — int, default `42`

- *Runtime:* threaded through every stochastic step — exposure assignment, audience cap (`seed+100`, `seed+101`), reach subsample (`seed`, `seed+1`), network builder, message pool selection.
- *Use:* change it to vary the seed family; keep it fixed to reproduce a run bit-for-bit (subject to LLM determinism caveats — see below).

#### `output_dir` — str, default `"data/output/experiments"`

- *Runtime:* base directory under which `save_results()` writes the timestamped run folder. See [Run_Output_Guide.md](Run_Output_Guide.md).

### 6.11 Local-LLM runtime (provider="local" only)

All three optional; left at `None` they fall back to environment variables, then built-in defaults.

#### `local_base_url` — str | None, default `None`

- *Fallback chain:* arg → `CAG_LOCAL_BASE_URL` env → `http://localhost:8080/v1` ([llm.py L67–L74](../src/cag/io/llm.py#L67-L74)).
- *Side effect:* the first call to `configure_local()` from `_resolve_runtime` sets the process-wide default for the run.

#### `local_extra_body` — dict | None, default `None`

- *Runtime:* extra request-body keys merged on top of the model-registry entry. Use to override sampling presets or pass server-specific knobs (e.g. `{"chat_template_kwargs": {"enable_thinking": False}}`).
- *Gotcha:* this is the **only** way to override the per-call temperature on local Qwen3 — `llm_temperature` alone is shadowed by the model registry.

#### `local_timeout_s` — float | None, default `None`

- *Fallback chain:* arg → `CAG_LOCAL_TIMEOUT_S` env → 600 s ([llm.py L76–L88](../src/cag/io/llm.py#L76-L88)).
- *Why so high:* local thinking calls can run for 90+ s; the default is much higher than the OpenAI-client default.

---

## 7. Canonical profiles

### 7.1 Research full run (local, package, debias, GT+rationale)

```python
config = {}  # take SIM_CONFIG defaults wholesale
results = run_simulation(config, nation)
```

Effective settings: §1 above, verbatim.

### 7.2 Smoke profile (NB29)

```python
config = {
    "n_citizens": 10,                                # SMOKE OVERRIDE (full=100)
    "days": [
        {"phases": ["P-A", "P-B", "C"]},
        {"phases": ["P-B", "P-A", "C"]},
    ],
    "k_peers_per_day": 2,
    # Everything else uses SIM_CONFIG defaults:
    #   llm_provider='local', llm_model='mlx-community/Qwen3-8B-4bit',
    #   communication_mode='package', package_policies=ALL_CLIMATE_POLICIES,
    #   day0_anchor='ground_truth_with_rationale', debias=True,
    #   political_message_source='offline', political_message_set='v1',
    #   network_type='stochastic_block', p_intra=0.15, p_inter=0.02,
    #   reach_a=1.0, reach_b=1.0, audience_cap=None,
    #   political_exposure_mode='rule_affinity_rank',
    #   political_exposure_targets=None  # → committed_minority_symmetric
    #   affinity_weights=None            # → balanced
    #   random_seed=42
}
```

### 7.3 Outsider path (API provider)

```python
config = {
    "llm_provider":          "openai",
    "llm_model":             "gpt-4.1-mini",
    "llm_temperature":       0.5,
    # Optional: stronger model just for surveys (NB15 pattern)
    "survey_provider":       "anthropic",
    "survey_model":          "claude-sonnet-4-5",
    "thinking":              True,           # survey-only thinking
}
```

Requires API keys in `data/api_key.csv` (see [API_KEYS.md](../API_KEYS.md)).

### 7.4 Asymmetric-reach experimental control

```python
config = {
    "audience_cap":   None,        # leave structural asymmetry
    "reach_a":        1.0,         # A reaches all of its (smaller) audience
    "reach_b":        0.5,         # B reaches half of its (larger) audience
    "political_exposure_targets": "committed_minority_uk_2024",  # B > A asymmetry
}
```

---

## 8. Cross-cutting decisions

### 8.1 Day-0 anchoring — which mode to choose

| Mode | Use when |
|---|---|
| `ground_truth_with_rationale` *(canon)* | Default for research runs. Eliminates Day-0 bias by construction; keeps a rationale trace for qualitative review. |
| `ground_truth` | Cost-sensitive runs (no Day-0 LLM call at all). Loses rationale text. |
| `llm_survey` | Bias-measurement studies (NB11–14 line of work) on a new model. Required if you want to **measure** the LLM's pro-climate prior. |

The three modes are not equivalent and have different theoretical interpretations. The ongoing **side-by-side comparison** is in deferred work (§3).

### 8.2 Debias chain (Condition B)

- *What it is:* a two-step prompt sequence in `administer_survey()` and `run_end_of_day_survey()` that asks the LLM to first reflect on the public's likely range of views, then commit to a position.
- *Where it runs:* every end-of-day survey when `debias=True`. On Day 0 it runs only when `day0_anchor == "llm_survey"`.
- *Validation:* NB13 (Carbon Tax + Ban Petrol Cars, ~97% bias reduction), NB14 (3/4 policies improved, statistically significant on Climate Compensation, overcorrected on Renewable Energy), NB15 (Sonnet + debias + thinking).
- *Caveat:* the headline NB13 figure was measured on the pre-v0.5 mixed-perspective prompt chain. A partial re-measurement on the unified 1P chain is queued (§3).

### 8.3 Package vs single-policy

| Mode | When |
|---|---|
| `package` *(canon)* | Default. Cross-policy spillover (e.g. supporting Carbon Tax bleeds into supporting Renewable Energy) is the research target. |
| `single_policy` | Legacy v0.3 mode. Use only when you need to isolate one policy's dynamics from spillover, or when reproducing pre-v0.5 results. Requires `"policy": ClimatePolicyID.X` in every `days` entry. |

### 8.4 Offline vs LLM political messages

| Source | When |
|---|---|
| `offline` *(canon)* | Default. Reproducible; uses curated real-world political text under `data/political_messages/`. Aborts at start if any required cell is missing. |
| `llm` | Use when piloting a new policy not yet represented in the message set, or for a fully-LLM self-contained demonstration. Higher cost; no real-world grounding. |

### 8.5 Local vs API provider

| Provider | When |
|---|---|
| `local` *(canon)* | Research default. Reproducible, no API spend, no rate limits. Requires `mlx_lm.server` (or compatible) running — see [Local_LLM_Setup_Guide.md](Local_LLM_Setup_Guide.md). |
| `openai` / `anthropic` / `google` | Outsider path. Use for capability ceilings (e.g. NB15 Sonnet+thinking) or when you do not have a local GPU/MLX setup. Requires `data/api_key.csv`. |

Mixing is supported: `llm_provider="local"` for reflections + `survey_provider="anthropic"` for end-of-day surveys is a valid split (NB15 pattern).

---

## 9. Validation contract — what `run_simulation` rejects at start

Source: [sim.py L538–L568](../src/cag/abm/sim.py#L538-L568) and downstream.

| Condition | Effect |
|---|---|
| `day0_anchor` not in `VALID_DAY0_ANCHORS` | `ValueError` |
| `reach_a` or `reach_b` not a number in `[0.0, 1.0]` | `ValueError` |
| `audience_cap` is bool, negative, or non-int (and not `None`) | `ValueError` |
| `resume=True` or `checkpoint_every_day=True` without `checkpoint_dir` | `ValueError` |
| `political_message_source` not in `("offline", "llm")` | `ValueError` ([sim.py L356–L360](../src/cag/abm/sim.py#L356-L360)) |
| `political_message_source == "offline"` and any required side/policy cell missing in the pool | `ValueError` from `message_pool.validate_required` |
| `political_exposure_mode` not in `VALID_EXPOSURE_MODES` | `ValueError` ([environment.py L649–L653](../src/cag/abm/environment.py#L649-L653)) |
| `political_exposure_targets` dict cells do not sum to 1.0 | `ValueError` from `_resolve_targets` |
| `network_type` not in `NETWORK_TYPES` | `ValueError` from `build_network` |
| Network builder rejects its params (e.g. `watts_strogatz` `k` odd or ≥ n) | `ValueError` from the builder |
| Day entry mixes `phases` with sugar keys | `ValueError` from `_resolve_day_phases` |
| `llm_provider="local"` but server unreachable | `RuntimeError` from `ping_local()` |

---

## 10. Resume / checkpoint contract

Source: [sim.py L963–L1100](../src/cag/abm/sim.py#L963-L1100).

A checkpoint is written after each day's `manage_memory` step when `checkpoint_every_day=True`. Resume hydrates agent + nation state from `checkpoint_dir`, validates the new config against the saved one, and continues day numbering from `last_completed_day + 1`.

**Hard keys** (`_RESUME_HARD_KEYS`, [sim.py L966–L973](../src/cag/abm/sim.py#L966-L973)) — any change **aborts** the resume:

```
n_citizens, random_seed, network_type,
communication_mode, package_policies, day0_anchor,
reach_a, reach_b, audience_cap,
political_exposure_mode, political_exposure_targets, affinity_weights,
political_message_source, political_message_set
```

Plus: **resolved** network params (so a legacy-flat → `network_params` dict upgrade is *not* rejected), the past prefix of `days` (future days may grow), and the active agent ID set.

**Soft keys** (`_RESUME_SOFT_KEYS`, [sim.py L975–L979](../src/cag/abm/sim.py#L975-L979)) — change is **warned** but proceeds:

```
llm_model, llm_provider, survey_model, survey_provider,
debias, thinking, llm_temperature,
local_base_url, local_extra_body, local_timeout_s
```

> **NB29 did not exercise resume.** It ran straight through (no `resume_from=...`, no `checkpoint_every_day=True`). The resume machinery's last smoke test was NB18; treat resume as smoke-tested but not full-stack-validated under the new v0.6 defaults.

---

## 11. Pointers

- [Model_Design.md](Model_Design.md) — design rationale and the canonical change-log of §-level decisions.
- [Prompts_and_Personas_Guide_v2.md](Prompts_and_Personas_Guide_v2.md) — every LLM prompt used in the run, verbatim.
- [Local_LLM_Setup_Guide.md](Local_LLM_Setup_Guide.md) — how to run `mlx_lm.server` so `llm_provider="local"` works.
- [Run_Output_Guide.md](Run_Output_Guide.md) — what each file in the run directory contains.
- [Literature_Political_Exposure.md](Literature_Political_Exposure.md) — empirical sourcing for the exposure targets and affinity weights.
- [`notebooks/29_canonical_full_smoke.ipynb`](../notebooks/29_canonical_full_smoke.ipynb) — the canonical full-stack smoke run; treat as the copy-paste template for a fresh experiment.
