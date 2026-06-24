# Code Tour — `src/cag/`

*A researcher-oriented walkthrough of the Climate-Action-GABM source tree for a newcomer who knows the science but has not opened `src/cag/` before. Reading time: ~30 minutes for sections A–B, ~2 hours for the full tour.*

---

## A. Who this is for, and how to read it

**You** know the science: the YouGov-anchored UK climate panel, the two-side political broadcast / peer-messaging design, the calibration story (Day-0 LLM bias, Condition-B debias from NB 13), the package-mode vs single-policy distinction, and the exposure-presets work (NB 27). You have **not** opened `src/cag/` before, or only briefly.

This doc treats every Python file as a doorway: it tells you what the file is for, what the 2–5 important names inside it are, and **one concrete breadcrumb** — the single function or constant that, once read, unlocks the rest. There is no API reference here; for that, run `python -m pydoc cag.<module>` or grep.

**How to use it:**

- **First 30 minutes** → read sections **A**, **B**, and the five files §C-2, C-3, C-4, C-5, C-13 in that order. After that you can launch a run, read a result CSV, and find your way back to the relevant code.
- **Reference mode** → use §E "I want to ___" to find the right doorway for a specific task. §F is a glossary.
- **AIRE launch path** → §G is a one-page pre-flight checklist.

**Conventions:**

- Function and constant names in `backticks`. File paths as Markdown links: [src/cag/abm/sim.py](../src/cag/abm/sim.py).
- "v2 memory" refers to the tiered-memory architecture rolled out 2026-06-22..23. Pre-v2 details are not covered.
- Anywhere this doc says *Day 0*, that means the day the agent is seeded from the YouGov ground truth — before any broadcast or peer messaging. *Day 1* is the first day of real simulation.

---

## B. The 30-minute skim sequence

> **Five files, ~30 minutes, and you have the skeleton of the whole simulator.**
>
> 1. [src/cag/__main__.py](../src/cag/__main__.py) — *5 min.* How a researcher's `--flag` becomes a `SIM_CONFIG` key.
> 2. [src/cag/presets.py](../src/cag/presets.py) — *3 min.* What a named run-bundle (e.g. `r14_canonical`) actually is.
> 3. [src/cag/abm/sim.py](../src/cag/abm/sim.py) — *10 min.* `SIM_CONFIG` (~35 keys), `make_phases()`, the day loop in `_run_one_day` and `run_simulation`.
> 4. [src/cag/abm/agent.py](../src/cag/abm/agent.py) — *8 min.* `assemble_context` 6-section order, `manage_memory` → `compress_daily_memory`, `administer_survey` debias branch.
> 5. [src/cag/io/results.py](../src/cag/io/results.py) — *4 min.* `_RESULT_CSV_SCHEMAS` and `save_results`. Tells you what comes out of every run.
>
> The mental model after these five: **config → phases → day-loop → agent memory → end-of-day survey → output CSVs**. Everything else is detail.

A diagram of the package layout to keep open while you read:

```
src/cag/
├── __init__.py                 # version marker, nothing else
├── __main__.py                 # the CLI entry point (`python -m cag …`)
├── presets.py                  # named run-bundles
└── abm/
    ├── sim.py                  # orchestration: SIM_CONFIG, run_simulation
    ├── agent.py                # SurveyedCitizen + PoliticalAgent
    ├── environment.py          # SurveyedNation + political-exposure assignment
    ├── networks.py             # 5 peer-network topologies (default: stochastic-block)
    ├── network_repair.py       # post-build connectivity diagnostics
    ├── political_messages.py   # offline-pool loader for political broadcasts
    └── attributes/
        ├── opinion.py          # 6 ClimatePolicyID values, A–G scale, PACKAGE_SCOPE
        ├── narratives.py       # value-scale attribute maps (SDO, RWA, openness…)
        ├── region.py / education.py / income.py / family.py / ethnicity.py
        ├── politics.py
        └── democracy/          # election ID maps (UKGE2019, Brexit)
└── io/
    ├── llm.py                  # send_chat() dispatcher: openai / anthropic / genai / local
    ├── results.py              # _collect_results + save_results entry point
    ├── checkpoint.py           # per-day CSV save/restore + resume validation
    ├── aggregators.py          # DataFrame transforms (shares, calibration, timeline)
    ├── plots.py                # matplotlib output
    └── survey.py               # YouGov CSV loader
```

---

## C. File-by-file walkthrough

Each entry: **one sentence** · **key names** · **breadcrumb**.

### C-1. [src/cag/__init__.py](../src/cag/__init__.py)

The package marker. Holds `__version__` only. Skip.

---

### C-2. [src/cag/__main__.py](../src/cag/__main__.py)

**One sentence:** Headless CLI entry point (`python -m cag …`) that turns command-line flags into a fully-resolved `SIM_CONFIG`, builds the nation from the YouGov CSV, calls `run_simulation`, then writes results.

**Key names:**

- `_ARG_TO_SIM` (line 101) — explicit map from argparse `dest` names that don't already match SIM_CONFIG keys (e.g. `seed` → `random_seed`, `k_peers` → `k_peers_per_day`, `model` → `llm_model`). Most flags use direct pass-through; this dict only covers the renames.
- `_maybe_json(value)` (line 124) — for `--exposure-targets` and `--affinity-weights`: accepts either a preset *name* ("split50") or a literal JSON dict (`'{"A-only": 0.5, …}'`). Single-quote your JSON in shell.
- `--list-presets` / `--dry-run` — inspection helpers. `--dry-run` prints the fully merged config (defaults ← preset ← CLI) and exits.
- `build_config(preset_dict, cli_dict)` (line 264) — the precedence rule in one place: defaults are baked into `SIM_CONFIG`; preset overrides defaults; CLI overrides preset.
- `main(argv=None)` (line 501) — the actual entry point. Parses → resolves → validates required keys → builds nation → calls `run_simulation` → writes outputs.

**Breadcrumb.** Read `_ARG_TO_SIM` (≤15 lines) and `build_config` (≤20 lines). Together they answer "how does `sbatch run.sh --preset r14_canonical --exposure-targets split50` end up as a Python dict?"

---

### C-3. [src/cag/presets.py](../src/cag/presets.py)

**One sentence:** Named bundles of partial `SIM_CONFIG` overrides — currently `smoke` (10 agents, 2 days, no peer messaging) and `r14_canonical` (50 agents, 5 days, ground-truth-seeded Day 0).

**Key names:**

- `RUN_BUNDLE_PRESETS` — the registry dict. New experiments add a new entry here.
- `list_presets()` — pretty-prints the registry. Wired to `--list-presets`.

**Breadcrumb.** Read `r14_canonical`. Three observations:

1. It **deliberately omits** `political_exposure_targets`. Each submission line pins it explicitly so the sweep file *is* the experimental design (see `scripts/aire/sweeps/r14_v2.txt`).
2. It does **not** override the local-LLM keys (`llm_provider`, `llm_model`, `local_base_url`). That's intentional: the AIRE launcher injects those from env vars.
3. `days: 5` is an `int`, not a list. `__main__.build_days()` expands it into a default alternating P-A/P-B/C schedule.

---

### C-4. [src/cag/abm/sim.py](../src/cag/abm/sim.py) ★ (slow read)

**One sentence:** Orchestrates a full run — validates config, sets up the network and political exposure, runs Day 0, loops days 1..N executing phases → memory compression → EOD survey, optionally writes per-day checkpoints, returns a dict of result DataFrames.

**Key names (in execution order):**

1. **`SIM_CONFIG`** (line 22) — the ~35-key default dictionary. **Read this whole block once.** Every knob the simulator respects lives here. Comments next to each line are load-bearing; for example the rationale for `p_inter: 0.05` (raised from 0.02 in v0.6) cites the Bakshy 2015 and Halberstam & Knight 2016 cross-cutting exposure estimates.
2. **`VALID_DAY0_ANCHORS`** (line 103) — `("llm_survey", "ground_truth", "ground_truth_with_rationale")`. The research canon is the third: numeric Day-0 answer comes from YouGov, LLM only writes the rationale.
3. **`make_phases()`** (line 114) — sugar that turns a count-style spec (`broadcasts_a=2, broadcasts_b=1, peer=True`) into a list like `["P-A", "P-A", "P-B", "C"]`. Most of the time you won't call this directly — you'll pass `"phases": ["P-A", "P-B", "C"]` explicitly in the config.
4. **`_resolve_runtime(cfg)`** (line 293) — one-time setup that runs *before* the day loop. Loads API key (or pings the local server), resolves survey-vs-broadcast model overrides, loads the offline message pool, validates that every required (side, policy) cell has at least one message. Failures here abort the run before Day 0.
5. **`_run_day0()`** (line 238) — seeds every agent's Day-0 opinion. Three modes, dispatched by `anchor_mode`: a full LLM survey, the YouGov ground truth alone, or the ground truth with an LLM-written rationale. Writes to `agent.opinion_history[policy_id]` and (for the rationale variant) `agent.survey_reasoning[policy_id]`.
6. **`_run_one_day(nation, day, day_config, n_days, rt)`** (line 363) — single day end-to-end. Best read in three chunks:
   - **Phases loop** (lines 380–411): for each phase letter in `day_config["phases"]`, dispatches to `nation.run_package_broadcast` / `run_package_peer_messaging` (or the single-policy counterparts).
   - **Memory compression** (lines 414–427): calls `agent.manage_memory(day, …)` on every agent. This is *before* the EOD survey, by design (see v2 memory rationale below).
   - **EOD survey** (lines 429–451): in package mode, the policy order is shuffled deterministically per day (`random.Random(seed*1000 + day)`) — same shuffle for every agent on that day. This eliminates the position-effect bias from the v1 fixed `1→6` walk.
7. **`run_simulation(config, nation, …)`** (line 549) — the public entry point. Reads cleanly top-to-bottom:
   - Lines 578–605: validate `day0_anchor`, `reach_a/b`, `audience_cap`.
   - Lines 614–620: `_resolve_runtime`.
   - Lines 622–649: deterministic structure setup — political agents A and B, exposure assignment, audience cap + reach subsample, network build, connectivity safety net.
   - Lines 654–702: branch on `resume=True` (hydrate from CSVs and skip Day 0) vs fresh start (run Day 0).
   - Lines 707–711: the day loop itself. **Three lines.** That's the entire skeleton.
8. **Re-exports at the bottom of the file** (lines 711–760) — `_RESUME_HARD_KEYS`, `_RESUME_SOFT_KEYS`, `_collect_results`, `save_results`, `build_agent_timeline`, etc. are imported here from the `cag.io` submodules so old notebooks still find them at `cag.abm.sim`. Don't be misled — the implementations live in `cag/io/results.py` and `cag/io/checkpoint.py`.

**Annotated excerpt — the main day loop:**

```python
# from run_simulation, ~line 707
for day_index in range(start_day_index, n_days):
    day = day_index + 1
    _run_one_day(nation, day, days[day_index], n_days, rt)
    if checkpoint_every_day:
        _write_checkpoint(nation, cfg, last_day=day, checkpoint_dir=checkpoint_dir)
```

That's it. Everything you care about — the phases, the surveys, the memory compression, the network — happens inside `_run_one_day`, which itself is a 100-line file you can read in five minutes.

**Breadcrumb.** Read `SIM_CONFIG` end-to-end, then `_run_one_day`. After those two, sim.py is no longer a black box.

---

### C-5. [src/cag/abm/agent.py](../src/cag/abm/agent.py) ★ (slow read)

**One sentence:** Defines `SurveyedCitizen` (one agent — holds demographics, opinions, reflections, memories) and `PoliticalAgent` (one of two broadcasters — pro-climate "A" and anti-climate "B"). All LLM-facing prompt construction happens here.

**`SurveyedCitizen` state — the dicts that matter:**

| Attribute | Shape | What it holds |
|---|---|---|
| `opinion_history` | `{policy_id: [(day, numeric), …]}` | Numeric opinions on the centred −3…+3 scale, one (day, value) per measured day. |
| `survey_reasoning` | `{policy_id: [(day, text), …]}` | The Step-1 rationale from the Condition-B 2-step survey (only when `debias=True`). Plus the Day-0 rationale when `day0_anchor="ground_truth_with_rationale"`. |
| `survey_raw_response` | `{policy_id: [(day, text), …]}` | The raw LLM string for the final letter step (diagnostic / auditing the parser). |
| `survey_assembled_context` | `{policy_id: [(day, text), …]}` | The **exact system prompt** that was sent to the LLM for that survey call. This is the diagnostic gold standard — if you're confused about why an agent answered the way it did, read its assembled context. |
| `reflections` | `[ {day, phase, policy_id, text, messages_received, sim_step}, … ]` | One entry per "I received messages, here's what I thought" event. Phase letter ∈ {P-A, P-B, C}. |
| `daily_summaries` | `{(day, policy_id): summary_text}` | 4–5 sentences distilling day d-2 once `manage_memory(d, …)` has run. |
| `_*_steps` | parallel dicts | Monotonic event indices so `agent_timeline.csv` can interleave everything in true execution order. |

**The v2 memory architecture (the single most important section in this file):**

`assemble_context(day, policy_id, target_policy_id)` builds the entire system prompt the LLM will see. The full 6-section order, skipping any section that is empty:

```
┌────────────────────────────────────────────────────────────────────┐
│ assemble_context(day=d, policy_id=ctx, target_policy_id=target)    │
├────────────────────────────────────────────────────────────────────┤
│ §1 Persona + values         (always; get_persona())                │
│ §2 Day-0 anchor             (verbatim Day-0 rationale for TARGET)  │
│ §3 Summary of recent days   (daily_summaries for days < d-1)       │
│ §4 Recent reflections       (reflections from days d-1 and d)      │
│ §5 Own reasoning d-1, d     (survey_reasoning for TARGET, recent)  │
│ §6 Today's other answers    (package mode only: prior answers      │
│                              within day d for OTHER policies)      │
└────────────────────────────────────────────────────────────────────┘
```

The split between `policy_id` and `target_policy_id` is the key v2 invariant:

- `policy_id` filters §3 + §4 (the "what is this agent currently thinking about" scope).
- `target_policy_id` scopes §2 + §5 + §6 (the "we are about to ask you about THIS policy" scope).

In single-policy mode the two are equal. In **package mode**, the EOD survey passes `context_policy_id=PACKAGE_SCOPE` (to keep cross-policy reflections in §4) but `target_policy_id=policy_id` (to keep §2 + §5 + §6 narrowed to the one policy being asked).

**Memory compression — `manage_memory()` → `compress_daily_memory()` → `compress_memories()`:**

Called once per agent per day, **before** the EOD survey. If `day > 2`, compresses day `d-2` into one 4–5-sentence summary stored in `daily_summaries[(d-2, policy_id)]`. Days `d-1` and `d` stay in the "vivid window" as full reflections.

Annotated excerpt:

```python
# agent.py line 474
def manage_memory(self, day, policy_id, …):
    """Called once per day (before the EOD survey, post v2) to compress old memories.

    Compresses day d-2 into a unified daily summary. Days d-1 and d
    remain as full verbatim reflections / own reasoning in the
    vivid window.
    """
    if day > 2:
        compress_day = day - 2
        if (compress_day, policy_id) not in self.daily_summaries:
            self.compress_daily_memory(compress_day, policy_id, …)
```

The compression LLM call is system-prompted with `"You are a concise summariser."` — this is how the instrumentation cell in `notebooks/34_memory_v2_smoke.ipynb` counts daily-summary calls separately from reflection / survey calls.

**`administer_survey()` — the Condition-B debias 2-step (research canon since v0.3):**

When `debias=True` (the default), every survey is **two** LLM calls:

1. **Step 1**: send the assembled context + an anti-sycophancy preamble + the policy question, ask for reasoning. Store in `survey_reasoning`.
2. **Step 2**: append the Step-1 reasoning to the system prompt, ask for a single letter A–G. Parse the letter, map to numeric −3…+3.

When `debias=False` (NB 11–12 baseline), it's one call, no reasoning step. NB 13 showed Condition B reduces Day-0 pro-climate bias by ~97% on Ban Petrol Cars; NB 14 showed it generalises to 3/4 policies. NB 15 confirmed Day-1+ stickiness goes up under debias too (Run 4 inertia 69%, best ever).

**Other useful methods to know exist:**

- `seed_opinion_from_ground_truth(policy_id, day=0)` — pulls the agent's real YouGov answer for the policy and appends to `opinion_history`. Used by `_run_day0` when `day0_anchor="ground_truth"`.
- `seed_opinion_with_rationale(policy_id, …)` — as above, then runs one LLM call to write a rationale. Used when `day0_anchor="ground_truth_with_rationale"`.
- `receive_political_message(message, policy_id, side, day, phase)` — broadcast in, reflection out. Side ∈ {`"pro_climate"`, `"anti_climate"`}.
- `generate_peer_message(policy_id, …)` and `receive_peer_messages(messages, …)` — peer-to-peer leg of phase C.
- Package counterparts: `receive_package_political_message`, `generate_package_peer_message`, `receive_package_peer_messages`. Same pattern, with `policy_ids` list instead of single id, message tagged `PACKAGE_SCOPE`.

**`PoliticalAgent` class** (lines ~850+): simple. Two singletons, A (`pro_climate`) and B (`anti_climate`). `generate_message(policy_id)` and `generate_package_message(policy_ids)` produce the LLM-generated broadcast when `political_message_source="llm"`. When `political_message_source="offline"` (the research-canon default), these methods are never invoked — see `cag/abm/political_messages.py` instead.

**Breadcrumb.** Read `assemble_context` (lines 273–328) and `manage_memory` (lines 474–484). Then open one row of `survey_assembled_context.csv` from a recent run and trace the §1–§6 sections inside it.

---

### C-6. [src/cag/abm/environment.py](../src/cag/abm/environment.py)

**One sentence:** Holds `SurveyedNation` (the population owner) plus the political-exposure assignment machinery (affinity-score weights, exposure targets, top-K ranking).

**Key names:**

- `TARGET_PRESETS` (line 94) — 5 named exposure-cell distributions. The research canon is `committed_minority_symmetric` (A-only 11%, B-only 11%, both 33%, neither 45% — see NB 27 §6 for the derivation).
- `AFFINITY_WEIGHT_PRESETS` (line 169) — 3 weight bundles for the affinity-score signals. `balanced` is the default; `vote_dominant` and `values_dominant` are sensitivity-test sweeps.
- `_green_affinity_score(citizen, year, weights)` (line 302) and `_reform_affinity_score` (line 343) — the two scoring functions. Read these to see how the values + demographics + vote signals combine into one scalar per side per citizen.
- `assign_political_exposure(mode, targets, weights, seed)` (line 647) — the dispatcher. Default mode `rule_affinity_rank` does deterministic top-K: score every citizen on side A and side B, sort, fill the cell quotas from highest score down. Other modes (`rule_priority_chain`, `rule_signal_count`) are legacy and rarely used.
- `run_political_broadcast` (line 1066) / `run_package_broadcast` (line 1152) / `run_peer_messaging` / `run_package_peer_messaging` — the four phase entry points called from `_run_one_day`.
- `run_end_of_day_survey(policy_id, day, …, context_policy_id=…)` (line 607) — one EOD survey for one policy. Note the `context_policy_id` kwarg: in package mode this is passed `PACKAGE_SCOPE` so cross-policy reflections survive the per-policy filter in `assemble_context`.
- `_sim_step` counter — monotonic event index across the whole simulation. Drives `agent_timeline.csv`.

**Breadcrumb.** Read the `TARGET_PRESETS` block and the comment paragraphs *above* `DEFAULT_AFFINITY_WEIGHTS` (lines 95–168). The literature justifications for every weight (Fletcher & Nielsen 2017, Schwartz values, Bakshy 2015) are written in those comments. Then read `assign_political_exposure` to see the top-K assignment in code.

---

### C-7. [src/cag/abm/networks.py](../src/cag/abm/networks.py) + [network_repair.py](../src/cag/abm/network_repair.py)

**One sentence:** Pluggable peer-network factory supporting 5 topologies; default is a 2-block stochastic block model with `p_intra=0.15` and `p_inter=0.05` (a 3:1 within/cross-cutting ratio that matches the Bakshy 2015 / Halberstam & Knight 2016 empirical estimates).

**Key names:**

- `build_network(network_type, agents, params, seed)` — returns a `networkx.Graph` keyed by agent ID.
- `NETWORK_TYPES` — `("stochastic_block", "erdos_renyi", "watts_strogatz", "barabasi_albert", "homophily_weighted")`.
- `_adjust_network_params_for_small_n` — auto-bumps `p_intra` and `p_inter` for `n < 100` to avoid disjoint graphs. Logged at INFO level.
- `_auto_connect_components` (in `network_repair.py`) — post-build safety net. Adds the minimum number of bridge edges if the SBM happened to produce islands.

**Breadcrumb.** If a network question comes up, look in the log line `network: edges=… mean_deg=… components=…` first. The repair layer guarantees `components=1`.

---

### C-8. [src/cag/abm/political_messages.py](../src/cag/abm/political_messages.py)

**One sentence:** Loads the curated offline broadcast pool from `data/political_messages/v1/messages_v1.csv` and serves messages in a seeded rotation, one per (side, policy) cell per call.

**Key names:**

- `MessagePool` — the loaded pool. `next(side, policy_key)` advances the cursor and returns the next message.
- `load_message_pool(set_name, seed)` — reads the CSV, validates schema, builds the cursors.
- `validate_required(pool, sides, policies)` — called from `_resolve_runtime`. Aborts the run *before* Day 0 if any (side, policy) cell is empty.
- `PACKAGE_KEY` — sentinel string used as the policy_key for package-mode broadcasts.

**Breadcrumb.** Read the CSV header in `data/political_messages/v1/messages_v1.csv`. The cell convention `(side, str(policy_id))` or `(side, PACKAGE_KEY)` is the whole API.

---

### C-9. [src/cag/abm/attributes/opinion.py](../src/cag/abm/attributes/opinion.py)

**One sentence:** Defines the 6 climate policies, the A–G response scale (centred −3…+3), the `PACKAGE_SCOPE` sentinel, opinion-clamping, and the package-index computation.

**Key names:**

- `ClimatePolicyID` — the 6-value enum: `RENEWABLE_ENERGY`, `BAN_FOSSIL_FUEL`, `BAN_PETROL_CARS`, `GREEN_HOUSING`, `CARBON_TAX`, `CLIMATE_COMPENSATION`. `ALL_CLIMATE_POLICIES` is the tuple of all six.
- `PACKAGE_SCOPE` — the string `"climate_policy_package"`. Used everywhere a "policy_id" column needs to represent "the bundle, not a single policy".
- `SURVEY_COLUMN_MAP` — `ClimatePolicyID → YouGov column name` (e.g. `RENEWABLE_ENERGY → "page5posttreatment6_1"`).
- `SURVEY_SHORT_LABELS` — readable 8–16-char labels. These are what `_section_today_so_far` injects into the LLM prompt.
- `SURVEY_QUESTIONS` — the 84-char preamble + the per-policy question.
- `RESPONSE_SCALE` — `{"A": -3, "B": -2, …, "G": +3}`. `RESPONSE_LABELS` is the human-readable counterpart ("Strongly support", "Slightly oppose", …).
- `survey_to_numeric` — converts a YouGov 1–7 ordinal to the centred −3…+3 scale.
- `clamp_opinion_shift(previous, new, max_shift=1)` — per-day clamp on absolute change. Applied in `run_end_of_day_survey`.
- `compute_package_index(numeric_values, centered)` — average of the 6 policy answers, the headline aggregate.

**Breadcrumb.** "How do I add a 7th policy?" is answered in §E-1; `opinion.py` is the file. There are 4 add-points: the enum, `SURVEY_COLUMN_MAP`, `SURVEY_QUESTIONS`, `SURVEY_SHORT_LABELS`. Everything downstream picks the new policy up automatically through `ALL_CLIMATE_POLICIES`.

---

### C-10. [src/cag/abm/attributes/narratives.py](../src/cag/abm/attributes/narratives.py)

**One sentence:** The 7 value-scale attribute maps (`SelftranscMap`, `SelfenhMap`, `OpennessMap`, `ConformTradMap`, `SDOMap`, `EDOMap`, `RWAMap`) plus the helper functions that rescale Schwartz 1–6 / SDO-RWA 1–7 ordinals into agent state. Read the docstrings at the top of the file for the literature mapping.

---

### C-11. [src/cag/abm/democracy/](../src/cag/abm/democracy/)

Election-specific maps (`elections/ukge2019.py` → `UKGE2019VoteMap`, `elections/brexit.py` → `BrexitVoteMap`). Loaded once during nation construction in `__main__.py::build_nation`. Not touched during a run.

---

### C-12. [src/cag/io/llm.py](../src/cag/io/llm.py)

**One sentence:** Unified `send_chat(system_prompt, user_prompt, …, provider)` dispatcher with resilient parameter negotiation; supports OpenAI, Anthropic, Google GenAI, and any OpenAI-compatible local server.

**Key names:**

- `send_chat(system_prompt, user_prompt, api_key=None, model=…, provider=…, temperature=0.5, thinking=False)` — the **single** name every part of the simulator uses to talk to an LLM. Wrapping `cag.abm.agent.send_chat` is how the NB 34 instrumentation cell counts LLM calls by category.
- `load_api_key(provider)` — reads from `data/api_key.csv` or the matching env var (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_GENAI_API_KEY`). Returns `None` for `provider="local"` (short-circuit).
- `ping_local(base_url)` — synchronous GET to `/v1/models`. Used at the top of every research notebook and inside `_resolve_runtime` to fail fast if the local server is down.
- `configure_local(base_url, extra_body, timeout_s)` — sets process-wide defaults; `_resolve_runtime` calls this before any LLM dispatch.
- `_MODEL_REGISTRY` (private but worth knowing) — per-model sampling presets keyed by substring match. This is how `thinking=True` is mapped to the right parameter name for each backend (`reasoning_effort` for OpenAI gpt-5, the `thinking` field for Anthropic, `extra_body={"chat_template_kwargs": {"enable_thinking": True}}` for Qwen3 on mlx_lm).
- `_resilient_call(fn, kwargs, model, provider)` — retry loop. If the server rejects a parameter (HTTP 400 with a recognisable message), strip the offending kwarg and retry. Caches known-unsupported `(provider, model, param)` triples to avoid repeated 400s.
- `parse_letter_response(text)` — regex to extract a single A–G from a free-text LLM response. The whole "did the LLM answer the question" failure mode collapses to this function.

**Breadcrumb.** If a survey is producing junk numerics, the order to check is: `survey_raw_response.csv` (the LLM's literal output) → `parse_letter_response` regex → `RESPONSE_SCALE` mapping. The three together determine the numeric value that ends up in `opinion_history`.

---

### C-13. [src/cag/io/results.py](../src/cag/io/results.py)

**One sentence:** Owns the CSV schemas, the DataFrame collection (`_collect_results`), the atomic CSV writes, and the public `save_results()` entry point.

**Key names:**

- `_RESULT_CSV_SCHEMAS` — a dict mapping CSV-file basename → ordered column list. **This is the canonical list of every output file the simulator can produce.** Currently: `opinion_trajectories`, `package_index_trajectories`, `reflections`, `messages`, `survey_reasoning`, `survey_raw_response`, `survey_assembled_context`, `daily_summaries`, `ground_truth`, `package_ground_truth`, `agent_attributes`, `agent_timeline`, …
- `_collect_results(nation, config)` — pure function that reads every agent's state dicts and returns one dict of DataFrames matching `_RESULT_CSV_SCHEMAS`. Also embeds the resolved `config` and network diagnostics.
- `save_results(results, output_dir="data/output/experiments")` — public entry point. Creates a timestamped subdir, writes every CSV atomically, calls aggregators + plotters, returns the subdir Path. **Watch out: `output_dir` here is a relative path by default; notebooks that don't pass an absolute or `../`-prefixed path will write into `notebooks/data/…` instead of `data/…`.** `__main__.py` handles this correctly via its `--outdir` CLI flag.
- `collect_ground_truth(agents, policy_ids)` — extracts the real YouGov answer per agent per policy.
- `collect_package_ground_truth(agents)` — computes the real package index from the YouGov pro-climate support column.
- `build_agent_timeline(results, sample_ids)` (re-exported from `aggregators.py`) — interleaves every event a sampled agent experienced (broadcasts received, peer messages, reflections, EOD surveys, daily summaries, debias trace) in true execution order. **This is the single most useful diagnostic file in the output dir.**

**Breadcrumb.** Open `data/output/experiments/<latest>/` and read these four CSVs in order: `agent_attributes.csv` (who are the agents), `opinion_trajectories.csv` (what they answered each day), `survey_assembled_context.csv` (what the LLM saw), `agent_timeline.csv` (one agent's full day-by-day experience). Together they tell the whole story of a run.

---

### C-14. [src/cag/io/checkpoint.py](../src/cag/io/checkpoint.py)

**One sentence:** Per-day CSV snapshots of every agent's mutable state, plus the resume-validation rules.

**Key names:**

- `CHECKPOINT_SCHEMA_VERSION` — currently `1`. Bump when adding new agent state columns.
- `_RESUME_HARD_KEYS` (14 keys) — `n_citizens`, `random_seed`, `network_type`, `communication_mode`, `package_policies`, `day0_anchor`, `reach_a`, `reach_b`, `audience_cap`, `political_exposure_mode`, `political_exposure_targets`, `affinity_weights`, `political_message_source`, `political_message_set`. **If you change any of these between checkpoint and resume, the simulator hard-fails.**
- `_RESUME_SOFT_KEYS` — `llm_model`, `llm_provider`, `survey_model`, `survey_provider`, `debias`, `thinking`, `llm_temperature`, `local_base_url`, `local_extra_body`, `local_timeout_s`. Can change between checkpoint and resume; the simulator warns and proceeds.
- `_write_checkpoint(nation, cfg, last_day, checkpoint_dir)` — atomic CSV dump + `checkpoint_meta.json`.
- `_load_checkpoint(nation, checkpoint_dir)` — hydrates agent state. Returns `last_day` (the next day to run is `last_day + 1`).
- `_validate_resume_config(meta, cfg, nation)` — applies the hard/soft rules.

**Breadcrumb.** Hard vs soft keys are *the* contract for resumes. Read the two tuples once; they're <20 lines combined.

---

### C-15. [src/cag/io/aggregators.py](../src/cag/io/aggregators.py) + [plots.py](../src/cag/io/plots.py) + [survey.py](../src/cag/io/survey.py)

**`aggregators.py` — pure DataFrame transforms:**

- `build_opinion_shares(results)` — support/neutral/against percentages per policy per day.
- `build_package_index_shares(results)` — same for the package index.
- `build_opinion_shares_by_bucket(results)` — stratified by exposure cell (A-only / B-only / both / neither).
- `build_calibration_table(results)` — Day-0 vs Day-N shift per policy. The headline calibration table from the result reports.
- `build_message_flow(results)` — sender → recipient graph.
- `build_agent_timeline(results, sample_ids)` — re-exported above.

**`plots.py` — matplotlib output called by `save_results`:**

- `plot_opinion_trajectories`, `plot_opinion_shares`, `plot_package_index_trajectories`, `plot_package_index_shares`, `plot_calibration_by_policy`, `plot_gap_widening`. The `save_result_plots(results, out_path)` entry point calls them all.

**`survey.py` — YouGov CSV loader:**

- `load(path)` — reads, validates columns, drops NaN-bearing rows for required attributes, filters out unmapped attribute values. Returns a `pd.DataFrame`.

**Breadcrumb.** If you want a quick aggregate read of a run, three calls: `build_opinion_shares`, `build_calibration_table`, `build_agent_timeline` on a sampled agent ID. That's most of the result-report material.

---

## D. Two side-trips

### D-1. Political-exposure assignment — the affinity-rank story

This is the second-most-important concept in the codebase after the v2 memory architecture. The mechanism, in five lines:

1. For each citizen, compute a **green-affinity score** (`_green_affinity_score`) and a **reform-affinity score** (`_reform_affinity_score`). Each is a weighted sum of:
   - values: Schwartz openness + self-transcendence (positive for green), SDO + RWA + conformity-tradition (positive for reform);
   - demographics: age band (young→green, old→reform), education (degree-holder→green), region (London/Scotland/Wales→green, other England→reform);
   - vote choice: signed bonus per UKGE2019 vote ID (Green +2.0 for green, Brexit +2.0 for reform);
   - politics 1–7 scale: linearly mapped (1 = very left → green, 7 = very right → reform);
   - Brexit referendum vote: Remain +1.0 for green, Leave +1.0 for reform.
2. Resolve the target distribution. `political_exposure_targets=None` → preset `committed_minority_symmetric` = `{A-only: 0.11, B-only: 0.11, both: 0.33, neither: 0.45}` (NB 27 derivation).
3. Resolve the weights. `affinity_weights=None` → preset `balanced` (values and vote signals carry the heaviest weight; demographics secondary).
4. Sort citizens by descending green-score. Assign the top `0.11 × N + 0.33 × N` to either "A-only" or "both" depending on their reform-score (highest goes to "both"). Symmetrically for the reform-sorted list. Remaining citizens → "neither".
5. The four cells determine who receives each broadcast (P-A reaches A-only + both; P-B reaches B-only + both; neither gets nothing in the broadcast phases) and who gets sampled in the peer-messaging phase (everyone).

The weights are **hand-picked, not fitted**, because no UK individual-level ground truth exists for echo-chamber membership. The literature anchors are written in comments above `DEFAULT_AFFINITY_WEIGHTS` — read them once. NB 27 validated that the rank-mode + `committed_minority_symmetric` preset hits both target presets to ±0.001 and that all four gates (A-only openness, A-only Remain%, B-only RWA, B-only Leave%) pass.

### D-2. v2 memory deep-dive — annotated `survey_assembled_context`

Here is a hypothetical Day-3 EOD survey context for one agent on the Carbon Tax policy, in package mode (P-A then P-B then C earlier today, daily summaries up to Day 1 already compressed):

```
You are a 42-year-old British woman who works as a teacher and lives  ← §1 Persona
in London. You hold strongly pro-environmental values and tend toward
openness to change.

Original prior position on "Carbon Tax":                              ← §2 Day-0 anchor
On Day 0, you said: "Polluters should pay. A carbon tax is the          (verbatim from
fairest way to make the cost of climate damage visible in the price     survey_reasoning
of goods, and the revenue can fund green programmes."                   for target policy)

Summary of recent days:                                                ← §3 Summary
Day 1: You engaged with a pro-climate broadcast about renewables          (daily_summaries
and a peer message about affordability; you found the affordability       for days < d-1,
argument compelling but not enough to shift your overall view.            i.e. day 1 only)

Recent reflections following received messages:                        ← §4 Vivid
- Day 2: The anti-climate broadcast about export-competitiveness was      (reflections from
new to me and I'm thinking about it more, but I still believe the         days d-1 and d)
benefits outweigh the costs.
- Day 3: A peer raised the point that carbon-tax revenue can be
recycled to lower-income households; this reinforces my support.

Your considered position in recent days:                               ← §5 Own reasoning
- Day 2: I'd say slightly support — the export argument introduces        (survey_reasoning
some doubt but doesn't override my values-based stance.                   from days d-1, d,
                                                                          target-scoped)

Your answers so far in today's survey:                                 ← §6 Today so far
- Renewable Energy: Strongly support — clean energy is essential.        (only present in
- Ban Petrol Cars: Slightly support — but only with affordable             package mode,
  alternatives.                                                            policies already
                                                                           answered today)

[Then the actual user prompt follows, asking the agent
to answer the Carbon Tax question with a letter A–G.]
```

What to notice:

- §2 is **target-scoped**: it shows only the Day-0 rationale for *Carbon Tax*, not all six.
- §3 and §4 are filtered by `policy_id=PACKAGE_SCOPE`, so they keep cross-policy material.
- §5 is **target-scoped** like §2.
- §6 only appears if at least one *other* policy has already been answered today. The first policy of the day's shuffled order will have an empty §6.

This entire prompt is captured into `survey_assembled_context.csv`. When debugging unexpected agent answers, **always start with this file** — it's what the LLM actually saw.

---

## E. "I want to ___" — the researcher cookbook

### E-1. Add a 7th climate policy

1. Add to the enum in [src/cag/abm/attributes/opinion.py](../src/cag/abm/attributes/opinion.py): `ClimatePolicyID.MY_NEW_POLICY = 7`.
2. Add to `SURVEY_COLUMN_MAP` (the YouGov column name).
3. Add to `SURVEY_QUESTIONS` (full 84-char preamble + the question).
4. Add to `SURVEY_SHORT_LABELS` (8–16 char readable label).
5. Add at least one message to `data/political_messages/v1/messages_v1.csv` for each side × the new policy.
6. `ALL_CLIMATE_POLICIES` regenerates automatically (it's `tuple(ClimatePolicyID)`).
7. Bump `political_message_set` to `"v2"` if you're starting a new message set; otherwise update v1 in place.

### E-2. Swap LLM provider

Change two `SIM_CONFIG` keys: `llm_provider` (`"openai"` / `"anthropic"` / `"genai"` / `"local"`) and `llm_model`. For `provider="local"`, also set `local_base_url`. For provider-specific quirks (thinking mode, parameter names), look at `_MODEL_REGISTRY` in [src/cag/io/llm.py](../src/cag/io/llm.py).

### E-3. Run with a new exposure preset

Add a new entry to `TARGET_PRESETS` or `AFFINITY_WEIGHT_PRESETS` in [src/cag/abm/environment.py](../src/cag/abm/environment.py). Reference it from the CLI as `--exposure-targets my_new_preset` or `--affinity-weights my_new_preset`. Or pass a literal JSON dict.

### E-4. Add a new political-message set

Create `data/political_messages/v2/messages_v2.csv` with the same schema as v1. Bump `political_message_set="v2"` in `SIM_CONFIG` (or pass `--message-set v2`). The validator in `_resolve_runtime` will refuse to start if any (side, policy) cell is empty.

### E-5. Trace one agent's full experience

1. Find the agent's ID from `agent_attributes.csv`.
2. Open `agent_timeline.csv` and filter to that ID.
3. Rows are sorted by `sim_step` in true execution order. You'll see broadcasts received, reflections written, peer messages sent and received, EOD surveys answered, daily summaries compressed, all interleaved.
4. To see the exact LLM prompt for any survey, cross-reference `survey_assembled_context.csv` on `(agent_id, day, policy_id)`.

### E-6. Debug a suspicious survey response

Three CSVs in order:

1. `survey_assembled_context.csv` — the system prompt the LLM was given. Does it contain the right Day-0 anchor, the right recent reflections, the right today-so-far block?
2. `survey_raw_response.csv` — the literal LLM output. Did it answer with a letter, or did it ramble?
3. `survey_reasoning.csv` — for debias runs only, the Step-1 rationale. Does it commit to a position that contradicts the final letter?

If the letter doesn't match the rationale, the issue is in `parse_letter_response` in [src/cag/io/llm.py](../src/cag/io/llm.py). If the rationale doesn't match the context, the issue is in `assemble_context` in [src/cag/abm/agent.py](../src/cag/abm/agent.py).

---

## F. Glossary

| Term | Meaning |
|---|---|
| **PACKAGE_SCOPE** | The sentinel string `"climate_policy_package"` used as a `policy_id` when the row represents the bundle, not a single policy. Most useful in `reflections`, `daily_summaries`, and `messages`. |
| **debias** | Condition B from NB 13. A 2-step EOD survey: Step 1 elicits reasoning with an anti-sycophancy preamble; Step 2 asks for the letter, with the Step-1 reasoning appended to the system prompt. Cuts Day-0 pro-climate bias by ~97% on Ban Petrol Cars. Research canon since v0.3. |
| **day0_anchor** | How the Day-0 numeric opinion is seeded. `"llm_survey"` = ask the LLM cold (the NB 11–14 bias-measurement story). `"ground_truth"` = take the YouGov answer verbatim, no rationale. `"ground_truth_with_rationale"` = take the YouGov answer and ask the LLM to write a rationale for it (this populates §2 in `assemble_context`). |
| **reach_a / reach_b** | Fraction of the political agent's audience reached by each broadcast. 1.0 = full audience. Used to study asymmetric reach (e.g. NB 21). |
| **audience_cap** | Hard cap on each political agent's audience size. Applied uniformly at random *before* the reach subsample. |
| **political_exposure_mode** | How citizens are sorted into the 4 cells. Default `rule_affinity_rank` (deterministic top-K on the affinity scores). Legacy: `rule_priority_chain`, `rule_signal_count`. |
| **affinity_weights** | The per-signal weights inside `_green_affinity_score` and `_reform_affinity_score`. Presets: `balanced`, `vote_dominant`, `values_dominant`. |
| **thinking** | Enable the model's extended-reasoning mode. Backend-specific: `reasoning_effort` for OpenAI gpt-5, `thinking` for Anthropic, `enable_thinking` in `extra_body` for Qwen3 on mlx_lm. |
| **P-A / P-B / C** | The three daily phases: P-A = political agent A (pro-climate) broadcasts; P-B = political agent B (anti-climate) broadcasts; C = peer-to-peer messaging. Order is per-day-configurable. |
| **package mode** | All 6 climate policies broadcast together each phase (one message covering the bundle, not 6 separate messages). EOD survey loops over all 6 policies in a deterministic per-day shuffle. |
| **vivid window** | Days `d-1` and `d`. Full reflections + own reasoning are kept verbatim in `assemble_context` for this window. |
| **gist memory** | Days `<= d-2`. Compressed into a single 4–5-sentence summary by `manage_memory` → `compress_daily_memory`. |

---

## G. AIRE pre-flight checklist

Before submitting your first sbatch on AIRE:

```bash
# 1. Hugging Face token file exists (NOT the env var — that resets each login)
ls -lh ~/.cache/huggingface/token

# 2. vLLM container image pulled
ls -lh ~/vllm-openai-v0.8.5.sif

# 3. CLI works on the login node
cd <repo>
module load miniforge && conda activate cag
PYTHONPATH=src python -m cag --list-presets

# 4. Dry-run prints the full resolved config
PYTHONPATH=src python -m cag --preset smoke --dry-run

# 5. First smoke submission — give yourself extra wall-clock for the model download
sbatch --time=06:00:00 scripts/aire/run.sh --preset smoke

# 6. Check it landed
squeue --me
tail -f LLM-cag-run_<jobid>.out

# 7. Outputs land at $SCRATCH/cag/runs/run_<jobid>/, NOT $HOME or the repo

# 8. Resume a killed job (same flags, RESUME_FROM points at the exact run dir)
RESUME_FROM=$SCRATCH/cag/runs/run_<jobid> \
    sbatch scripts/aire/run.sh --preset r14_canonical --exposure-targets split50

# 9. Sweep mode (one job per non-comment line)
bash scripts/aire/sweep.sh scripts/aire/sweeps/r14_v2.txt

# 10. Pull results back from your laptop
rsync -avh aire:/mnt/scratch/<user>/cag/runs/run_<jobid>/ ~/cag_results/run_<jobid>/
```

**Common first-time pitfalls:**

- The model-download readiness wait in `run.sh` is 1500 s (25 min). First Apertus-8B or Qwen-32B pull can exceed that — pass `--time=06:00:00` on the *first* sbatch. Once the model is cached, subsequent runs warm up in <2 min.
- Outputs **must** go to `$SCRATCH` (1 TB quota). `$HOME` is 65 GB and AIRE will suspend accounts that fill it.
- HF_TOKEN as an env var resets each login. Use the file method (`huggingface-cli login` once, or write the token to `~/.cache/huggingface/token` manually).
- Flag order: `sbatch [sbatch flags] scripts/aire/run.sh [python flags]`. Anything after `run.sh` is forwarded to `python -m cag`.

---

*End of Code Tour. For deeper questions on any one subsystem, the test suite is the most reliable second-opinion: `tests/test_memory.py` covers the v2 memory architecture, `tests/test_cli.py` covers `__main__.py`'s flag-to-config mapping, `tests/test_exposure.py` covers the political-exposure presets, `tests/test_llm_local.py` covers the local-server provider path. All of them are mocked — no live LLM required.*
