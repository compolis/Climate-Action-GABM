# Code Tour — `src/cag/`

*A breezy-but-detailed walk through the Climate-Action-GABM source, for someone who knows the science but hasn't opened the code. Read the bold lines for the fast pass (~15 min); drop into the **Staying?** notes wherever you want depth.*

---

## How to read this

Every file below is written in two layers:

> **`path/to/file.py`** — one sentence: what it's for.
>   **Staying?** The 2–4 names worth knowing (as things to `grep`, not line numbers), the single *breadcrumb* that unlocks the rest, and — where it applies — the output CSV the file shows up in.

Skim the bold lines and you'll come out oriented. Read the indented notes and you'll come out dangerous.

**Conventions**

- File paths are workspace-relative so you can click them: [src/cag/abm/sim.py](src/cag/abm/sim.py).
- I give you **names to grep**, never line numbers — line numbers rot the moment anyone edits above them; `grep -n "def run_simulation" src/cag/abm/sim.py` never lies.
- *Day 0* means the day each agent is seeded from its real YouGov answer, before any messaging. *Day 1* is the first simulated day.
- Line counts are a snapshot (see [§8](#8-keeping-this-doc-honest) for the one-liner that regenerates them). They're here only as a "where's the weight" signal.

---

## 1. The 90-second version

Climate-Action-GABM asks: if you drop **100 LLM-driven UK citizens** into a network and have two committed minorities — one pro-climate, one anti — broadcast at them day after day, do opinions on **six climate policies** tip, polarise, or hold? Each citizen is a persona built from **real YouGov survey data**; each "day" is a round of broadcasts, peer chat, and a re-survey.

The entire codebase is one pipeline:

```
config  →  build the nation  →  Day 0 seed  →  [ day loop: phases → memory → survey ]×N  →  output CSVs
```

The code is layered, and each layer only leans on the ones beneath it:

```
CLI surface     __main__.py · presets.py            ← you run this
Orchestration   abm/sim.py                          ← decides when things happen
Domain          abm/agent.py · environment.py ·     ← the actual simulation
                networks.py · political_messages.py
Vocabulary      abm/attributes/* · abm/democracy/*  ← turns YouGov codes into persona text
Persistence     io/llm.py · results.py · ...        ← the model, the input CSV, the outputs
```

If you only have 90 seconds, that's the whole thing. Everything after this is detail.

---

## 2. Read these five first

Five files, ~30 minutes, and you have the skeleton. In this order:

1. [src/cag/__main__.py](src/cag/__main__.py) — how a `--flag` becomes a config dict.
2. [src/cag/presets.py](src/cag/presets.py) — what a named run-bundle actually is.
3. [src/cag/abm/sim.py](src/cag/abm/sim.py) — `SIM_CONFIG`, and the day loop in `_run_one_day` / `run_simulation`.
4. [src/cag/abm/agent.py](src/cag/abm/agent.py) — `assemble_context` (the six-section prompt), `manage_memory`, `administer_survey`.
5. [src/cag/io/results.py](src/cag/io/results.py) — `_RESULT_CSV_SCHEMAS` and `save_results`: everything a run produces.

But before you open any of them, read the next section. It's the part that makes the other four make sense.

---

## 3. One citizen, one day

This is the centre of the tour. Forget the directory tree for a moment and follow the code **in the order it actually fires** for a single run. Every function below is real; grep any of them.

**The run begins in the CLI.** [src/cag/__main__.py](src/cag/__main__.py) `main()` parses your flags, merges them into a config (`build_config`: defaults ← preset ← CLI), and loads the survey.

**The population is born from a spreadsheet.** `build_nation` hands the cleaned YouGov frame (from [io/survey.py](src/cag/io/survey.py) `load`) to `SurveyedNation` in [environment.py](src/cag/abm/environment.py). One row becomes one `SurveyedCitizen` ([agent.py](src/cag/abm/agent.py)) — its demographics, vote history, and Schwartz/SDO/RWA value scores all pulled in through the **vocabulary** maps in [attributes/](src/cag/abm/attributes/) and [democracy/](src/cag/abm/democracy/). At this point each citizen can already describe itself in the first person: that's `get_persona`.

**Control passes to the orchestrator.** `run_simulation` ([sim.py](src/cag/abm/sim.py)) does its one-time setup, in this exact order — worth knowing because it's all the deterministic structure:

1. `_resolve_runtime(cfg)` — load the API key or ping the local server, resolve survey-vs-broadcast model overrides, and **load + validate the offline message pool** ([political_messages.py](src/cag/abm/political_messages.py)). If any `(side, policy)` cell is empty, the run aborts here, before Day 0.
2. Create the two broadcasters: `PoliticalAgent("agent_a", "pro_climate")` and `("agent_b", "anti_climate")`.
3. `assign_political_exposure` — score every citizen on green- and reform-affinity and sort them into the four exposure cells (A-only / B-only / both / neither). This decides who hears whom.
4. `apply_audience_cap` then `apply_reach_subsample` — optional thinning of each broadcaster's audience.
5. `create_network` + `assign_network_blocks` ([networks.py](src/cag/abm/networks.py)) — build the peer graph (default: a 2-block stochastic block model), then the safety net in [network_repair.py](src/cag/abm/network_repair.py) bridges any islands so nobody is isolated.

**Day 0 seeds opinions.** `_run_day0` dispatches on `day0_anchor`. The research default is `ground_truth_with_rationale`: take the citizen's *real* YouGov answer as the numeric opinion, then make one LLM call asking it to write a rationale for that position. The rationale is stored in `survey_reasoning` — and it becomes §2 of every future prompt. (No persuasion has happened yet; this is just the starting line.)

**Then the day loop runs — this is the whole simulation.** For each day, `_run_one_day` does four things:

1. **Phases.** For each phase letter in the day's schedule, it calls into the nation: `run_package_broadcast` for P-A and P-B (the pro and anti broadcasts), `run_package_peer_messaging` for C. A broadcast lands as `receive_package_political_message` on each citizen in that broadcaster's audience → the citizen writes a private reflection. Peer messaging is **simultaneous**: every citizen generates its message first, *then* an inbox is built and everyone reflects — so there's no accidental within-phase ordering effect.
2. **Memory.** `agent.manage_memory(day, …)` runs on every citizen — *before* the survey, deliberately. If `day > 2` it compresses day `d−2` into a 4–5-sentence summary (`compress_daily_memory`). Days `d−1` and `d` stay verbatim in the "vivid window".
3. **The end-of-day survey.** `run_end_of_day_survey` re-asks each policy. In package mode the six policies are asked in a per-day deterministic shuffle (so no policy is always asked last). For each, `agent.administer_survey` builds the prompt via `assemble_context` and calls `send_chat` ([io/llm.py](src/cag/io/llm.py)). Under the default `debias=True` this is a **two-step** call: Step 1 elicits reasoning behind an anti-sycophancy preamble, Step 2 asks for the A–G letter with that reasoning appended. The letter is parsed by `parse_letter_response`, mapped to a number on the −3…+3 scale, and recorded. **No clamping** — the opinion is whatever the model answered.
4. **Checkpoint.** If enabled, the day's state is snapshotted ([io/checkpoint.py](src/cag/io/checkpoint.py)).

**The run ends back in I/O.** `_collect_results` ([io/results.py](src/cag/io/results.py)) reads every citizen's state dicts into DataFrames; `save_results` writes them as CSVs and `save_result_plots` ([io/plots.py](src/cag/io/plots.py)) draws the figures, all under `--outdir`.

That single walk — `load → build_nation → assign_political_exposure → _run_day0 → _run_one_day → broadcast → manage_memory → administer_survey → assemble_context → send_chat → _collect_results → save_results` — *is* the architecture. The rest of this doc just zooms in on each stop.

---

## 4. The map

Now the file-by-file detail, grouped by layer.

### 4.1 Orchestration

> **[src/cag/abm/sim.py](src/cag/abm/sim.py)** *(~853 ln)* — runs the show: validate config, build the world, seed Day 0, loop the days, return results.
>   **Staying?** Read `SIM_CONFIG` end to end once — it's the ~33-key default dict, and the comments next to each key are load-bearing (e.g. the literature citation for `p_inter`). Then read `_run_one_day`: phases → memory → survey, ~100 lines. The actual day loop in `run_simulation` is *three lines*. **Breadcrumb:** `SIM_CONFIG`, then `_run_one_day`, and sim.py stops being a black box. Note: a pile of names re-exported at the bottom (`_collect_results`, `save_results`, …) are imported back from `cag.io` so old notebooks still find them here — the implementations live in `io/`.

### 4.2 Domain — the simulation engine

> **[src/cag/abm/agent.py](src/cag/abm/agent.py)** *(~878 ln)* — one citizen: holds opinions, reflections and memory, and builds every prompt it sends.
>   **Staying?** The state lives in a handful of dicts: `opinion_history`, `survey_reasoning`, `reflections`, `daily_summaries`, and the diagnostic gold-mine `survey_assembled_context` (the exact prompt sent, per survey). The one method that matters is `assemble_context(day, policy_id, target_policy_id)` — the six-section prompt builder (see [§5.1](#51-policy_id-vs-target_policy_id)). `manage_memory` → `compress_daily_memory` does the compression; `administer_survey` does the debias two-step. `PoliticalAgent` lives at the bottom and is simple. **Breadcrumb:** read `assemble_context`, then open one row of `survey_assembled_context.csv` and find §1–§6 inside it.
>   *In the output:* `reflections.csv`, `survey_reasoning.csv`, `survey_assembled_context.csv`, `opinion_trajectories.csv`.

> **[src/cag/abm/environment.py](src/cag/abm/environment.py)** *(~1382 ln)* — the population: owns the network, runs the phases, and decides who hears whom.
>   **Staying?** This file quietly does **two jobs** (see [§5.5](#55-the-cruft-and-the-gotchas)). Job one is the nation: `create_network` / `assign_network_blocks`, the four phase entry points `run_package_broadcast` / `run_package_peer_messaging` (+ single-policy `run_political_broadcast` / `run_peer_messaging`), and `run_end_of_day_survey`. Job two is **political-exposure assignment**: `_green_affinity_score` / `_reform_affinity_score` score each citizen, and `assign_political_exposure` does a deterministic top-K sort into the four cells. **Breadcrumb:** read the comment block above the affinity weights — every weight has a literature anchor — then `assign_political_exposure`. The full mechanism is walked in [Appendix A](#appendix-a--political-exposure-assignment-the-affinity-rank-story).
>   *In the output:* `messages.csv`, `agent_attributes.csv` (exposure bucket per agent).

> **[src/cag/abm/networks.py](src/cag/abm/networks.py)** *(~508 ln)* — builds the peer network; 5 topologies, default stochastic-block, plus diagnostics.
>   **Staying?** `build_network(network_type, agents, params, seed)` returns a `networkx.Graph` keyed by agent ID; `compute_diagnostics` produces the edge/degree/component stats. **Breadcrumb:** if a network question ever comes up, find the `network: edges=… components=…` log line first.

> **[src/cag/abm/network_repair.py](src/cag/abm/network_repair.py)** *(~263 ln)* — the connectivity safety net.
>   **Staying?** Three layers: `_adjust_network_params_for_small_n` bumps the edge probabilities when N is small, `_auto_connect_components` adds the minimum bridges if the graph still fragments, and `_log_network_summary` reports it. After this runs, you're guaranteed one connected component.

> **[src/cag/abm/political_messages.py](src/cag/abm/political_messages.py)** *(~456 ln)* — loads the curated offline broadcast pool and serves one message per `(side, policy)`.
>   **Staying?** `load_message_pool` reads the CSV and validates it; `MessagePool` serves messages in a seeded rotation. The validation in `_resolve_runtime` is what aborts the run early if a `(side, policy)` cell is empty. **Breadcrumb:** read the header of `data/political_messages/v1/messages_v1.csv` — the `(side, policy_id)` cell convention is the whole API. This is the *default* message source; the `PoliticalAgent.generate_*` methods only fire if you switch to `political_message_source="llm"` (see [§5.4](#54-offline-vs-llm-messages)).

### 4.3 Vocabulary — persona building blocks

These are small, mostly-static, and you'll rarely touch them unless you add a policy or a demographic.

> **[src/cag/abm/attributes/opinion.py](src/cag/abm/attributes/opinion.py)** *(~190 ln)* — the six policies, the A–G (−3…+3) scale, the package index.
>   **Staying?** `ClimatePolicyID` is the six-value enum; `PACKAGE_SCOPE` is the sentinel string for "the bundle, not one policy"; `survey_to_numeric` converts YouGov's 1–7 to the centred scale; `compute_package_index` averages the six. `SURVEY_QUESTIONS` / `SURVEY_COLUMN_MAP` / `SURVEY_SHORT_LABELS` are the four add-points for a new policy. **Heads-up:** `clamp_opinion_shift` is defined here but **never called** anywhere — dead code (see [§5.5](#55-the-cruft-and-the-gotchas)).

> **[src/cag/abm/attributes/narratives.py](src/cag/abm/attributes/narratives.py)** *(~176 ln)* — value-scale maps (Schwartz, SDO, RWA) → the sentences describing a citizen's worldview. `get_narrative` is the lookup.

> **[src/cag/abm/attributes/](src/cag/abm/attributes/) — the demographic maps** — `politics.py`, `region.py`, `education.py`, `income.py`, `family.py`, `ethnicity.py`: one small ID→string table each, used to write persona text.

> **[src/cag/abm/democracy/elections/](src/cag/abm/democracy/elections/)** — `ukge2019.py` (`UKGE2019VoteMap`) and `brexit.py` (`BrexitVoteMap`): vote-choice maps used both in persona text and in affinity scoring.

### 4.4 Persistence — the model and the files

> **[src/cag/io/llm.py](src/cag/io/llm.py)** *(~740 ln)* — the only door to a model: one `send_chat()` for four providers, with self-healing retries.
>   **Staying?** `send_chat(system_prompt, user_prompt, …, provider)` is the single name the whole simulator uses to talk to an LLM (OpenAI / Anthropic / Google GenAI / local vLLM or mlx). `_resolve_model_profile` maps `thinking=True` to the right per-backend parameter; `_resilient_call` strips a rejected parameter and retries (which is why the same code survives gpt-5, Qwen3 and Apertus). `parse_letter_response` extracts the A–G; `ping_local` fails fast if the server is down. **Breadcrumb:** for junk survey numerics, the chain is `survey_raw_response.csv` → `parse_letter_response` → the `RESPONSE_SCALE` in opinion.py.

> **[src/cag/io/results.py](src/cag/io/results.py)** *(~512 ln)* — defines the CSV schemas and writes every artefact.
>   **Staying?** `_RESULT_CSV_SCHEMAS` is the canonical list of every output file — read it and you know what a run produces. `_collect_results` is the pure function that turns agent state into those DataFrames; `save_results` writes them atomically into a timestamped dir. **Footgun:** the default `output_dir` is *relative*, so a notebook that doesn't pass an absolute path writes into `notebooks/data/…`. `__main__.py` always passes `--outdir`, so real runs are fine.

> **[src/cag/io/aggregators.py](src/cag/io/aggregators.py)** *(~506 ln)* — turns raw state into summary tables.
>   **Staying?** `build_opinion_shares` (support/neutral/against %), `build_calibration_table` (Day-0 vs Day-N shift), `build_message_flow`, and the star, `build_agent_timeline` — one agent's whole experience interleaved in true execution order. The `*_by_bucket` variants stratify by exposure cell.

> **[src/cag/io/plots.py](src/cag/io/plots.py)** *(~555 ln)* — every figure, saved to disk (Agg backend, never shown). `save_result_plots` is the one entry point that fans out to all the `plot_*` functions.

> **[src/cag/io/checkpoint.py](src/cag/io/checkpoint.py)** *(~366 ln)* — per-day state snapshots + resume rules. `_write_checkpoint` / `_load_checkpoint`, and `_validate_resume_config` enforces which config keys may change on resume (the hard/soft key split).

> **[src/cag/io/survey.py](src/cag/io/survey.py)** *(~179 ln)* — loads and cleans the YouGov CSV the whole model is seeded from. `load` reads, validates required columns, and drops/filters bad rows.

### 4.5 CLI surface

> **[src/cag/__main__.py](src/cag/__main__.py)** *(~631 ln)* — `python -m cag`: flags → config → nation → run → outputs. The headless entry point AIRE calls.
>   **Staying?** `build_config` is the precedence rule in one place (defaults ← preset ← CLI); `build_nation` constructs the population; `build_days` expands an integer day-count into the alternating P-A/P-B/C schedule; `_ARG_TO_SIM` covers the few flags whose names don't match their config keys. **Breadcrumb:** read `build_config`, then trace one `--dry-run` to see the fully-resolved config without launching anything.

> **[src/cag/presets.py](src/cag/presets.py)** *(~73 ln)* — named flag-bundles. `RUN_BUNDLE_PRESETS` holds `smoke` (10×2) and `r14_canonical` (50×5). A preset is pure convenience — every knob is also a `--flag`, so new experiments never require a code change.

---

## 5. The five things that confuse everyone

These are the non-guessable invariants. If something in a run surprises you, the cause is almost always in here.

### 5.1 `policy_id` vs `target_policy_id`

`assemble_context` takes **two** policy scopes, and conflating them is the classic bug. `policy_id` is the **context scope** — "what has this agent been thinking about" — and filters the recent-reflections and summary sections. `target_policy_id` is the **question scope** — "the policy we're about to ask" — and scopes the Day-0 anchor, own-reasoning, and today's-other-answers sections. In single-policy mode they're equal. In **package mode** the survey passes `context_policy_id=PACKAGE_SCOPE` (so cross-policy reflections survive) but `target_policy_id=policy_id` (so the anchor stays pinned to the one policy being asked). They are independent dimensions, not one collapsed scope. [Appendix B](#appendix-b--a-worked-assemble_context-example) shows the resulting prompt, annotated.

### 5.2 Package mode vs single-policy

The default `communication_mode="package"` means all six policies are broadcast together each phase, and the end-of-day survey loops over all six in a deterministic per-day shuffle. This is why so many methods have a `package_` twin (`run_package_broadcast` vs `run_political_broadcast`, etc.). When you read the domain layer, assume the `package_` path is the live one unless you've deliberately switched to single-policy.

### 5.3 `debias` — the two-step survey

`debias=True` (the research default) makes every end-of-day survey a **two-call** exchange: Step 1 asks the model to reason behind an anti-sycophancy preamble; Step 2 asks for the A–G letter with that reasoning appended. It exists to cut the Day-0 pro-climate bias the cold LLM shows. One subtlety: `debias` is **ignored on Day 0** (Day 0 is just seeding), and only applies to end-of-day surveys.

### 5.4 Offline vs `llm` messages

`political_message_source="offline"` (the default) serves broadcasts from a curated, validated CSV pool via [political_messages.py](src/cag/abm/political_messages.py). The consequence that trips people up: under the default, **`PoliticalAgent.generate_message` / `generate_package_message` never fire** — those methods only run if you flip the source to `"llm"`. If you're hunting for where broadcast text comes from, it's the CSV, not the agent.

### 5.5 The cruft and the gotchas

The most valuable thing this doc can tell you is what to *ignore*:

- **`clamp_opinion_shift` is dead.** It's defined in [opinion.py](src/cag/abm/attributes/opinion.py) but called nowhere. Opinions shift freely — the model moves each citizen as far as its own answer implies. (The earlier design clamped to ±1/day; that's gone.)
- **`attributes/opinion_suggested_edit.py` is a scratch copy** of opinion.py — not imported, not used. Ignore it.
- **`environment.py` is secretly two files** — the nation *and* the affinity-scoring/exposure machinery. When it feels like two unrelated things, that's because it is.
- **`day0_anchor` (the SIM_CONFIG key) ≠ the §2 anchor section.** The config key chooses how Day 0 is *seeded* (`llm_survey` / `ground_truth` / `ground_truth_with_rationale`); §2 in `assemble_context` is the text that seeding produces. Same word, two jobs.
- **Peer messaging is simultaneous** — all messages are generated, *then* delivered — so don't look for a within-phase ordering effect; there isn't one.
- **`save_results`' default output dir is relative** — a notebook footgun, harmless for CLI runs (see [§4.4](#44-persistence--the-model-and-the-files)).

---

## 6. "I want to ___"

A reverse index for common tasks.

- **Add a 7th policy** → [opinion.py](src/cag/abm/attributes/opinion.py): four add-points (the `ClimatePolicyID` enum, `SURVEY_COLUMN_MAP`, `SURVEY_QUESTIONS`, `SURVEY_SHORT_LABELS`), then add at least one message per `(side, new-policy)` to the message CSV. Everything downstream picks it up via `ALL_CLIMATE_POLICIES`.
- **Swap LLM provider** → set `llm_provider` and `llm_model` (and `local_base_url` for `local`). Per-backend quirks live in `_resolve_model_profile` in [io/llm.py](src/cag/io/llm.py).
- **Change who hears whom** → tune the exposure targets/weights in [environment.py](src/cag/abm/environment.py), or pass `--exposure-targets` / `--affinity-weights` (a preset name or a literal JSON dict).
- **Trace one agent end to end** → find its ID in `agent_attributes.csv`, filter `agent_timeline.csv` to it (sorted by `sim_step` in true order), and cross-reference `survey_assembled_context.csv` for the exact prompt of any survey.
- **Debug a suspicious survey answer** → in order: `survey_assembled_context.csv` (did the prompt have the right anchor/reflections?), `survey_raw_response.csv` (did it answer with a letter or ramble?), `survey_reasoning.csv` (does the Step-1 reasoning contradict the final letter?). If the letter mismatches the reasoning, look at `parse_letter_response`; if the reasoning mismatches the context, look at `assemble_context`.

---

## 7. Running it on AIRE

The simulator is headless by design, which is exactly what Leeds's **AIRE** cluster needs. The shape of a run:

You submit one Slurm job from the login node: `sbatch aire/run.sh --preset r14_canonical --exposure-targets split50`. That job lands on a **GPU node** and does five things in order: (1) start a **vLLM server** in an Apptainer container serving the model (default Qwen3-8B), (2) wait until it answers `/v1/models` — up to 25 min on a cold model download, (3) `module load` conda and run `python -m cag --provider local --base-url localhost:8000 --outdir $SCRATCH/… "$@"`, forwarding all your flags, (4) write results under `$SCRATCH`, (5) shut the server down. The model server and the simulation run **side by side on the same node**, talking over localhost — so the LLM calls never leave the machine.

Two rules the cluster enforces: **all output goes to `$SCRATCH`** (never `$HOME` or the repo tree), and **modules/conda don't carry over** from the login node, so the job script re-loads them itself. The config still composes three ways — `SIM_CONFIG` defaults ← `--preset` ← individual `--flags` — so `aire/run.sh` stays thin and never hardcodes an experiment.

Pre-flight, once: an HF token file, `conda env create -f environment.yaml`, and `apptainer pull` the vLLM image. After that, every experiment is a new `sbatch` line. The full clone-to-results recipe is in [AIRE_Quickstart.md](AIRE_Quickstart.md); the cluster's own rules are in [AIRE_HPC_repo_primer.md](AIRE_HPC_repo_primer.md).

---

## 8. Keeping this doc honest

This file goes stale the moment the code moves, so a few habits keep it true:

- **Grep, don't cite line numbers.** Every reference here is a name you can `grep`. If you add one, make it a name too.
- **Regenerate the line counts** rather than trusting them:
  ```bash
  find src/cag -name '*.py' | sort | while read f; do printf "%5s  %s\n" "$(wc -l < "$f")" "$f"; done
  ```
- **Flag cruft on sight.** When you delete or abandon code, add a line to [§5.5](#55-the-cruft-and-the-gotchas). A tour that tells you what to ignore is worth more than one that pretends everything matters.
- **If the day loop changes, fix [§3](#3-one-citizen-one-day) first.** That trace is the spine of the doc; if it's right, the rest follows.

---

## Appendix A — Political-exposure assignment (the affinity-rank story)

This is the second-most-important mechanism in the codebase after the memory architecture, and the new map ([§4.2](#42-domain--the-simulation-engine)) only gestures at it. Here it is in full. It all lives in [environment.py](src/cag/abm/environment.py).

1. **Score every citizen twice.** `_green_affinity_score` (using the weights under key `"A"`) and `_reform_affinity_score` (key `"B"`) each compute a weighted sum over eleven signals:
   - **values:** Schwartz openness + self-transcendence, and SDO / RWA / conformity-tradition;
   - **demographics:** age band, education, region;
   - **politics:** left–right self-placement, Brexit referendum vote, and a signed vote-choice bonus from the UKGE2019 map.
   Missing or `UNKNOWN` attributes contribute 0 — they neither help nor hurt a side.
2. **Resolve the target distribution.** `political_exposure_targets=None` → the preset `committed_minority_symmetric` = `{A-only 0.11, B-only 0.11, both 0.33, neither 0.45}`. The other presets are `committed_minority_uk_2024`, `legacy_v05`, `split50` (`{0.5, 0.5, 0, 0}`), and `neither` (`{0, 0, 0, 1}`).
3. **Resolve the weights.** `affinity_weights=None` → the `balanced` preset (`DEFAULT_AFFINITY_WEIGHTS`), in which values and vote signals carry the most weight (openness/self-transcendence 1.5; Brexit/politics 1.5; vote-bonus 2.0) and demographics are secondary (age/education 1.0, region 0.75). `vote_dominant` and `values_dominant` are the sensitivity-sweep presets.
4. **Rank and fill** (default mode `rule_affinity_rank`): sort by descending score, fill the `A-only` and `B-only` quotas from the top, draw `both` from the cross-pressured remainder, and assign everyone left to `neither`.
5. **The cells drive everything downstream:** P-A reaches `A-only` + `both`; P-B reaches `B-only` + `both`; `neither` gets no broadcast at all; everyone is eligible in the peer-messaging phase.

One honesty note: these weights are **hand-picked, not fitted** — there's no UK individual-level ground truth for echo-chamber membership to fit against. The literature anchors for each weight are written in the comment block directly above `DEFAULT_AFFINITY_WEIGHTS`; read them once. The legacy modes `rule_priority_chain` / `rule_signal_count` still exist but are rarely used.

---

## Appendix B — A worked `assemble_context` example

The two-scope idea from [§5.1](#51-policy_id-vs-target_policy_id) lands faster with a concrete prompt. Here's a hypothetical Day-3 end-of-day survey context for one citizen on **Carbon Tax**, in package mode (P-A, P-B and C already happened today; day 1 is already compressed):

```
You are a 42-year-old British woman who works as a teacher and lives   ← §1 Persona
in London. You hold strongly pro-environmental values.                    (always)

Original prior position on "Carbon Tax":                               ← §2 Day-0 anchor
On Day 0 you said: "Polluters should pay. A carbon tax is the             (verbatim, scoped
fairest way to make climate damage visible in prices."                    to TARGET policy)

Summary of recent days:                                                ← §3 Summary
Day 1: engaged with a renewables broadcast and a peer message about        (gist; context
affordability — found it compelling but not enough to shift.               scope: policy_id)

Recent reflections following received messages:                        ← §4 Recent
- Day 2: the anti-climate export-competitiveness argument was new to        reflections
me; still think the benefits outweigh the costs.                          (vivid; context
- Day 3: a peer noted carbon-tax revenue can be recycled to               scope: policy_id)
lower-income households — reinforces my support.

Your considered position in recent days:                               ← §5 Own reasoning
- Day 2: slightly support — the export point introduces some doubt          (vivid, scoped
but doesn't override my values.                                           to TARGET policy)

Your answers so far in today's survey:                                 ← §6 Today so far
- Renewable Energy: Strongly support.                                     (package only,
- Ban Petrol Cars: Slightly support — with affordable alternatives.       scoped to TARGET)

[Then the user prompt asks for a single A–G letter on Carbon Tax.]
```

What to notice:

- **§2 and §5 are target-scoped** — they show only the *Carbon Tax* anchor and reasoning, not all six policies.
- **§3 and §4 are context-scoped** — filtered by `policy_id=PACKAGE_SCOPE`, so cross-policy reflections (renewables, petrol cars) survive.
- **§6 appears only in package mode**, and only once at least one *other* policy has been answered today — the first policy of the day's shuffle has an empty §6.

This exact string is captured per survey into `survey_assembled_context.csv`. When an answer surprises you, this is the file to open first — it's what the model actually saw.

---

## Appendix C — Glossary

| Term | Meaning |
|---|---|
| **`PACKAGE_SCOPE`** | The sentinel string used as a `policy_id` when a row represents the six-policy bundle, not one policy. Common in reflections, summaries, and messages. |
| **context scope vs question scope** | `policy_id` (what the agent has been thinking about — filters §3/§4) vs `target_policy_id` (the policy being asked — scopes §2/§5/§6). The central memory invariant; see [§5.1](#51-policy_id-vs-target_policy_id). |
| **`debias`** | The two-step end-of-day survey (default on): Step 1 elicits reasoning behind an anti-sycophancy preamble, Step 2 asks for the A–G letter. Cuts the cold LLM's pro-climate bias. Ignored on Day 0. |
| **`day0_anchor`** | How Day 0 is *seeded*: `llm_survey` (ask the LLM cold), `ground_truth` (take YouGov verbatim), or `ground_truth_with_rationale` (the default — YouGov number + an LLM-written rationale that becomes §2). Not to be confused with the §2 anchor section it produces. |
| **`reach_a` / `reach_b`** | Fraction of each broadcaster's audience actually reached per broadcast (1.0 = full audience). Used to study asymmetric reach. |
| **`audience_cap`** | Hard cap on each broadcaster's audience size, applied uniformly at random *before* the reach subsample. |
| **`political_exposure_mode`** | How citizens are sorted into the four cells. Default `rule_affinity_rank`; legacy `rule_priority_chain` / `rule_signal_count`. |
| **`affinity_weights`** | Per-signal weights inside the affinity scores. Presets: `balanced` (default), `vote_dominant`, `values_dominant`. |
| **`thinking`** | Enable the model's extended-reasoning mode; the parameter name is backend-specific (resolved in `_resolve_model_profile`). |
| **P-A / P-B / C** | The three daily phases: pro-climate broadcast, anti-climate broadcast, peer-to-peer messaging. Order is per-day configurable. |
| **package mode** | All six policies broadcast together each phase; the end-of-day survey loops all six in a deterministic per-day shuffle. The default `communication_mode`. |
| **vivid window** | Days `d−1` and `d` — reflections and own reasoning kept verbatim in the prompt. |
| **gist memory** | Days `≤ d−2` — compressed into one 4–5-sentence summary by `manage_memory` → `compress_daily_memory`. |

---

*For a second opinion on any subsystem, the tests are the most reliable source — they're all mocked, so no live LLM is needed.*
