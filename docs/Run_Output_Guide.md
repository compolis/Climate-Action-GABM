# Climate-Action-GABM — Run Output Guide

A walk-through of the artefacts produced by a single simulation run, written so a reviewer can open the run directory cold and qualitatively check what the LLM agents said and did.

This guide is keyed to the run at:

```
data/output/experiments/20260423_223001/
```

…but the schema applies to every run produced by `cag.abm.sim.save_results()` and `save_result_plots()`.

---

## 1. Quick orientation

Every run directory contains:

| Kind | Files |
|---|---|
| Run config | `config.json` |
| Per-agent ground truth (from YouGov survey) | `ground_truth.csv`, `package_ground_truth.csv` |
| Time-series of agent opinions | `opinion_trajectories.csv`, `package_index_trajectories.csv` |
| Aggregated daily shares (support / neutral / against) | `opinion_shares.csv`, `package_index_shares.csv` |
| **Generative text — the qualitative review surface** | `messages.csv`, `reflections.csv`, `survey_reasoning.csv` |
| Optional per-agent end-of-day notes | `daily_summaries.csv` |
| Plots (PNG) | `*.png` corresponding to each trajectory / share file |
| Wall-time timing per notebook block | `timings.csv` |

The three files in **bold** are where all the qualitative checking lives. Everything else is the numeric scaffolding that explains *why* those texts appeared when they did.

---

## 2. The simulation in one paragraph

Each simulated day has up to three phases, run in order:

- **P-A — Pro-climate political broadcast.** A `pro_climate` political agent emits a public message that all *exposed* citizens read; each exposed citizen produces a *reflection* (Phase A reflection) updating their stated opinion.
- **P-B — Anti-climate political broadcast.** Symmetric to P-A, with an `anti_climate` political agent and the agents exposed to that side.
- **C — Peer messaging.** Each citizen sends a short message to up to `k_peers_per_day` of their network neighbours; recipients read inbound peer messages and produce a Phase C reflection.

After the day's phases, every citizen takes an end-of-day climate survey. In this run **`communication_mode = "package"`**, so broadcasts, peer messages, reflections and surveys all cover the **whole 6-policy climate package** in a single LLM call rather than one call per policy.

Day 0 is special: **`day0_anchor = "ground_truth_with_rationale"`**. Day-0 opinion is *seeded directly from the YouGov survey response* (no LLM survey call), and the LLM is asked only to write a rationale for that pre-set opinion. From Day 1 onward, end-of-day surveys are real LLM calls that may move opinions.

---

## 3. The 6 climate policies

Throughout the CSVs, policies appear as the string `ClimatePolicyID(N)` where `N` is 1–6. Mapping (from [`src/cag/abm/attributes/opinion.py`](src/cag/abm/attributes/opinion.py)):

| ID | Short name | Survey question (paraphrased) |
|---|---|---|
| `ClimatePolicyID(1)` | RENEWABLE_ENERGY | Accelerate roll-out of renewable energy (offshore/onshore wind, solar). |
| `ClimatePolicyID(2)` | BAN_FOSSIL_FUEL | Ban new oil / gas / coal licences. |
| `ClimatePolicyID(3)` | BAN_PETROL_CARS | Ban sale of new petrol cars by 2030. |
| `ClimatePolicyID(4)` | GREEN_HOUSING | Mandate non-fossil heating, rooftop solar, high insulation in new housing. |
| `ClimatePolicyID(5)` | CARBON_TAX | Carbon tax on fossil fuels with revenues returned to the public (fee-and-dividend). |
| `ClimatePolicyID(6)` | CLIMATE_COMPENSATION | Compensate people in other countries impacted by climate change. |

### The opinion scale

Internally opinions live on a centred 7-point scale **`-3 … +3`**:

| Numeric | Letter | Label |
|---|---|---|
| `-3` | A | Strongly oppose |
| `-2` | B | Somewhat oppose |
| `-1` | C | Slightly oppose |
| `0` | D | Neutral |
| `+1` | E | Slightly support |
| `+2` | F | Somewhat support |
| `+3` | G | Strongly support |

The YouGov survey itself is on a 1–7 scale; the conversion is simply `numeric = raw − 4`. The string `"ProClimatePolSupp"` (a column name in the YouGov dataset) is reused as the **package index name** — it is the simple arithmetic mean of the six policy responses on the same `-3 … +3` scale.

---

## 4. `config.json`

The exact config dict that produced the run. Most important keys for review:

| Key | Meaning |
|---|---|
| `n_citizens` | Number of citizens in the run. |
| `days` | List of per-day phase orderings (e.g. `[{"phases": ["P-A","P-B","C"]}, …]`). Length = number of days simulated. |
| `communication_mode` | `"package"` (one call covers all 6 policies) or `"single_policy"` (one call per policy). |
| `package_policies` | The 6-policy set used in package mode. |
| `day0_anchor` | `"llm_survey"`, `"ground_truth"`, or `"ground_truth_with_rationale"`. Controls how Day-0 opinions are set. |
| `k_peers_per_day` | Max number of peer-message recipients per citizen per day in Phase C. |
| `network_type`, `p_intra`, `p_inter`, `block_sizes` | Stochastic-block-model parameters for the citizen network. |
| `llm_model` / `llm_provider` / `llm_temperature` | LLM used for **messaging** (broadcasts, peer messages, reflections). |
| `survey_model` / `survey_provider` / `thinking` / `debias` | LLM used for **end-of-day surveys**, plus whether extended-thinking and the Condition-B anti-sycophancy two-step survey are on. |
| `random_seed` | Seed for sampling YouGov rows and SBM edges. |

The two-LLM split lets us message with a cheap fast model and survey with a careful, less-biased model.

---

## 5. Ground-truth files

### `ground_truth.csv` — per-policy, per-agent

| Column | Meaning |
|---|---|
| `agent_id` | YouGov respondent ID (also the citizen ID inside the sim). |
| `policy_id` | `ClimatePolicyID(N)`. |
| `ground_truth` | YouGov-derived opinion on the `-3 … +3` scale. |

Rows = `n_citizens × 6`. This is the YouGov "truth" for each (agent, policy) pair.

### `package_ground_truth.csv` — per-agent

| Column | Meaning |
|---|---|
| `agent_id` | YouGov respondent ID. |
| `index_name` | Always `ProClimatePolSupp`. |
| `ground_truth` | Mean of the agent's six policy GT values, on `-3 … +3`. |

Rows = `n_citizens`.

When `day0_anchor = "ground_truth_with_rationale"`, the Day-0 rows in `opinion_trajectories.csv` should equal `ground_truth` exactly for every (agent, policy) — that invariant is asserted in [notebooks/17_day0_anchoring_smoke_test.ipynb](notebooks/17_day0_anchoring_smoke_test.ipynb).

---

## 6. Trajectory files (numeric)

### `opinion_trajectories.csv`

The per-policy time series. One row per (agent, day, policy).

| Column | Meaning |
|---|---|
| `agent_id` | Citizen ID. |
| `day` | `0` is Day-0 anchor; `1..N` are end-of-day-survey results. |
| `policy_id` | `ClimatePolicyID(N)`. |
| `numeric` | Opinion on `-3 … +3`. |

Rows = `n_citizens × (1 + n_days) × 6`.

### `package_index_trajectories.csv`

Same time series collapsed to one number per (agent, day) — the package index.

| Column | Meaning |
|---|---|
| `agent_id` | Citizen ID. |
| `day` | `0..N`. |
| `index_name` | `ProClimatePolSupp`. |
| `package_scope` | `climate_policy_package`. |
| `package_index` | Mean of the agent's six policy opinions on that day, `-3 … +3`. |

Rows = `n_citizens × (1 + n_days)`.

Plotted in `opinion_trajectories.png` and `package_index_trajectories.png`.

---

## 7. Daily share files (aggregated)

These bin the `-3 … +3` opinion into three buckets — **support (`> 0`)**, **neutral (`= 0`)**, **against (`< 0`)** — and report counts and percentages of the population in each bucket per day.

### `opinion_shares.csv`

| Column | Meaning |
|---|---|
| `policy_id` | `ClimatePolicyID(N)`. |
| `day` | `0..N`. |
| `n_agents` | Population size for that (policy, day). |
| `n_support` / `support_pct` | Count and % with `numeric > 0`. |
| `n_neutral` / `neutral_pct` | Count and % with `numeric == 0`. |
| `n_against` / `against_pct` | Count and % with `numeric < 0`. |

Rows = `6 × (1 + n_days)`. Plotted as `opinion_shares.png`.

### `package_index_shares.csv`

Same schema with `policy_id` replaced by `index_name` + `package_scope`, applied to the package index. Plotted as `package_index_shares.png`.

---

## 8. The qualitative-review files (the important ones)

### 8.1 `messages.csv` — every message produced by anyone

One row per LLM-generated message. This is the social discourse layer.

| Column | Meaning |
|---|---|
| `day` | Day the message was emitted. |
| `phase` | `P-A`, `P-B`, or `C`. |
| `message_type` | `political_broadcast` (P-A / P-B) or `peer_message` (C). |
| `sender_type` | `political_agent` or `citizen`. |
| `sender_id` | `agent_a`, `agent_b`, or a citizen ID. |
| `sender_side` | `pro_climate` or `anti_climate` for political agents; empty for citizens. |
| `recipient_id` | The citizen ID that received the message. (Broadcasts are duplicated one row per recipient.) |
| `recipient_scope` | `broadcast` (sent to all exposed citizens of that side) or `direct` (peer-to-peer). |
| `policy_id` | The single policy the message is about — only populated in `single_policy` mode. **Empty in package mode.** |
| `package_scope` | `climate_policy_package` in package mode; empty in single-policy mode. |
| `policy_ids_json` | JSON array of the policies covered by the message. In package mode this is the full 6-policy list. |
| `message_text` | The full LLM output. **This is what to read.** |

In **package mode** every row has `policy_id` empty, `package_scope = "climate_policy_package"`, and `policy_ids_json` listing all six policies. A single message therefore covers the entire climate package.

**For qualitative review:** filter by `phase` to read political broadcasts vs. peer messages; filter by `sender_side` to compare pro- vs. anti-climate framing; filter by `sender_id` to follow one citizen's voice across days.

### 8.2 `reflections.csv` — what each citizen privately concluded

After receiving messages in any phase, the citizen writes an internal *reflection* — a per-policy or per-package summary of how they now see things. This is the "interior monologue" produced by the messaging LLM.

| Column | Meaning |
|---|---|
| `agent_id` | Citizen ID. |
| `day` | Day the reflection was written. |
| `phase` | Which phase triggered the reflection (`P-A`, `P-B`, `C`). |
| `policy_id` | `climate_policy_package` in package mode, or a `ClimatePolicyID(N)` in single-policy mode. |
| `package_scope` | `climate_policy_package` in package mode; empty otherwise. |
| `policy_ids_json` | JSON array of policies the reflection covers. |
| `messages_received_json` | JSON array of the messages the citizen had in front of them when reflecting. |
| `messages_received_count` | Length of that array (typically `1` for political broadcasts; up to `k_peers_per_day` for Phase C). |
| `text` | The reflection itself. **This is what to read.** |

A reflection only fires for citizens who actually *received at least one message* in that phase. In a small-N run with sparse `p_intra` / `p_inter`, many citizens have no peer neighbours, so Phase C reflections will be sparse — that is expected, not a bug. For political broadcasts, only citizens marked as *exposed* to that side receive a message (controlled by `assign_political_exposure()`), so P-A and P-B reflection counts will not equal `n_citizens` either.

### 8.3 `survey_reasoning.csv` — why each survey response was given

End-of-day surveys ask the citizen to (1) reason briefly and (2) pick a letter A–G. The reasoning is captured here, the chosen letter is reflected in `opinion_trajectories.csv`.

| Column | Meaning |
|---|---|
| `agent_id` | Citizen ID. |
| `day` | `0` for Day-0 rationales, `1..N` for end-of-day surveys. |
| `policy_id` | `ClimatePolicyID(N)`. |
| `reasoning` | The free-text reasoning that produced that day's opinion. **This is what to read.** |

Day 0 is special: when `day0_anchor = "ground_truth_with_rationale"`, the *opinion* came from YouGov but the *reasoning* is an LLM rationalisation of that pre-set opinion. There will be exactly `n_citizens × 6` Day-0 rows.

When `debias = True`, Day ≥ 1 reasoning entries are the Step-1 anti-sycophancy reasoning from the two-step Condition-B survey.

### 8.4 `daily_summaries.csv` — optional end-of-day note (may be empty)

Reserved for an optional end-of-day per-(agent, policy) summary. It can be empty in runs that don't enable that step (as in the example run).

| Column | Meaning |
|---|---|
| `agent_id` | Citizen ID. |
| `day` | Day. |
| `policy_id` | `ClimatePolicyID(N)` or `climate_policy_package`. |
| `summary` | Free-text end-of-day note. |

---

## 9. Plots

Each `*.png` is generated from the corresponding `*.csv` of the same name and is purely a visual aid. They are deterministic given the CSVs, so reviewers can regenerate them via `cag.abm.sim.save_result_plots(results, out_path)` if needed.

| File | What it shows |
|---|---|
| `opinion_trajectories.png` | Per-policy mean and per-agent lines over days, with YouGov GT mean as a dashed reference. |
| `opinion_shares.png` | Stacked support / neutral / against percentages per policy per day. |
| `package_index_trajectories.png` | Same as opinion_trajectories but for the package index. |
| `package_index_shares.png` | Same as opinion_shares but for the package index. |

---

## 10. `timings.csv`

Wall-time per notebook block (seconds). Used to spot bottlenecks before scaling up.

| Column | Meaning |
|---|---|
| `section` | Label of the block (`build_nation`, `collect_ground_truth`, `run_simulation (TOTAL)`, …). |
| `seconds` | Wall-time. |

---

## 11. A suggested qualitative-review workflow

1. Open `config.json` and skim it — note `n_citizens`, `days`, `communication_mode`, `day0_anchor`, the messaging vs. survey LLM, and whether `debias` / `thinking` are on.
2. Open `messages.csv`. Filter `message_type == "political_broadcast"` and `sender_side == "pro_climate"` — read those, then the `anti_climate` ones. Are they on-message, distinct, and persuasive in the way you'd expect?
3. Filter `message_type == "peer_message"` and read a handful per day. Do they sound like a real person passing a thought to a friend, or do they read like another political broadcast?
4. Open `reflections.csv`. Pick one `agent_id` and read all of their reflections in `day` / `phase` order — does the citizen's stance evolve coherently in response to what `messages.csv` shows they were exposed to?
5. Cross-reference with `survey_reasoning.csv` for the same agent: does the end-of-day rationale match the reflections, or does the survey LLM (a different model in dual-model runs) drift?
6. Spot-check `opinion_trajectories.csv` Day-0 rows against `ground_truth.csv` for that agent — they must match exactly when the GT anchor is on.
7. Look at `package_index_trajectories.png` to see whether the population mean drifted away from the GT package mean over the run, and `opinion_shares.png` for any policy where a tipping pattern (support/against share crossing) appeared.

---

## 12. Checkpointing & Resume

Long runs (50+ agents × 10+ days) can make hundreds of LLM calls. To make them crash-resilient and forkable, `run_simulation()` accepts three optional parameters:

| Parameter | Type | Purpose |
|---|---|---|
| `checkpoint_dir` | `Path` | Directory to write/read per-day snapshots. Required when `resume=True` or `checkpoint_every_day=True`. |
| `checkpoint_every_day` | `bool` | If `True`, write a full CSV snapshot to `checkpoint_dir` after each day's `manage_memory` step (and once after Day 0). |
| `resume` | `bool` | If `True`, hydrate agent + nation state from `checkpoint_dir`, skip Day 0, and continue day numbering from `last_completed_day + 1`. |

### Checkpoint contents

A checkpoint directory contains the same CSVs `save_results()` writes for a finished run, plus a metadata file:

```
<checkpoint_dir>/
  checkpoint_meta.json         # last_completed_day, agent_ids, config, hash, schema_version
  opinion_trajectories.csv     # full history through last_completed_day
  reflections.csv
  daily_summaries.csv
  survey_reasoning.csv
  messages.csv
  package_index_trajectories.csv  # if package mode
  ground_truth.csv
  package_ground_truth.csv
```

Writes are atomic (temp file + `os.replace`) so a crash mid-write cannot leave a half-written CSV.

### Crash recovery

If a 10-day run crashes during Day 7's peer-messaging phase, the checkpoint at `last_completed_day=6` is intact. Restart with the same `checkpoint_dir` and `resume=True`; Days 7–10 are re-run from scratch. The Day 7 LLM calls that fired before the crash are lost — checkpoint granularity is end-of-day, not mid-day.

### Branching from a finished run

To fork a finished run with a different policy or extra days:

1. Build a `nation` with the same `n_citizens` and `random_seed` as the original.
2. Call `run_simulation(new_cfg, nation, checkpoint_dir=<original_checkpoint>, resume=True, ...)`.
3. The original checkpoint dir is read-only unless `checkpoint_every_day=True` is also passed (in which case it will be overwritten as the new branch progresses — point `checkpoint_dir` at a fresh path if you want to preserve the original).

### Compatibility rules on resume

Hard-fail (raises `ValueError`):

- `n_citizens`, `random_seed`, `p_intra`, `p_inter`, `network_type`, `communication_mode`, `package_policies`
- Active agent ID set differs from the checkpoint

Warn-only (proceeds, but logs at `WARNING` level):

- `llm_model`, `llm_provider`, `survey_model`, `survey_provider`, `debias`, `thinking`, `llm_temperature`

### Caveat

With `temperature > 0`, a "ran cleanly in one shot" execution and a "crashed and resumed" execution are not byte-identical even with the same config. The checkpoint records when it was written; for paper-headline results, disclose whether a run was resumed.

That's enough to form a qualitative judgement on whether the generative-text layer is behaving sensibly before any quantitative analysis is layered on top.
