# Climate-Action-GABM — Run Output Guide

A walk-through of the artefacts produced by a single simulation run, written so a reviewer can open the run directory cold and qualitatively check what the LLM agents said and did.

This guide is keyed to the run at:

```
data/output/experiments/20260623_140314/
```

…but the schema applies to every run produced by `save_results()` and `save_result_plots()` (defined in `cag.io.results` / `cag.io.plots`, with the per-table aggregators in `cag.io.aggregators`; all three are re-exported from `cag.abm.sim` for backwards compatibility).

---

## 1. Quick orientation

Every run directory holds five kinds of artefact:

| Kind | Files |
|---|---|
| Run config | `config.json` |
| **Generative text — the qualitative review surface** | `messages.csv`, `reflections.csv`, `survey_reasoning.csv`, `survey_raw_response.csv`, `survey_assembled_context.csv`, `daily_summaries.csv` |
| Per-agent ground truth (from YouGov survey) | `ground_truth.csv`, `package_ground_truth.csv` |
| Opinion time-series (numeric) | `opinion_trajectories.csv`, `package_index_trajectories.csv` |
| Aggregated diagnostic tables | `opinion_shares.csv`, `package_index_shares.csv`, `opinion_shares_by_bucket.csv`, `package_index_by_bucket.csv`, `day0_vs_dayN_shifts.csv`, `calibration.csv`, `message_flow.csv` |
| Per-agent audit trail | `agent_attributes.csv`, `agent_timeline.csv` |
| Network structure | `network_diagnostics.json`, `network_snapshot.json` |
| Plots (PNG) | one per trajectory / share / diagnostic table, plus `gap_widening.png`, `network_graph.png`, `calibration_by_policy.png` |

The files in **bold** are where the qualitative checking lives. Everything else is the numeric scaffolding that explains *why* those texts appeared when they did.

> **Changed in v0.7.0:** there is no longer a `timings.csv` or a `day0_anchors.csv`. Day-0 reasoning now lives directly in `survey_reasoning.csv`. The `survey_raw_response`, `survey_assembled_context`, `agent_attributes`, `agent_timeline`, `*_by_bucket`, `day0_vs_dayN_shifts`, `calibration`, `message_flow` and two `network_*.json` files are all new.

---

## 2. The simulation in one paragraph

Each simulated day has up to three phases, run in the order given by `config.json → days`:

- **P-A — Pro-climate political broadcast.** A `pro_climate` political agent emits a public message that all *exposed* citizens read; each exposed citizen produces a *reflection* (Phase A reflection) updating their stated opinion.
- **P-B — Anti-climate political broadcast.** Symmetric to P-A, with an `anti_climate` political agent and the agents exposed to that side.
- **C — Peer messaging.** Each citizen sends a short message to up to `k_peers_per_day` of their network neighbours; recipients read inbound peer messages and produce a Phase C reflection.

After the day's phases, every citizen takes an end-of-day climate survey. In this run **`communication_mode = "package"`**, so broadcasts, peer messages, reflections and surveys all cover the **whole 6-policy climate package** in a single LLM call rather than one call per policy.

Day 0 is special: **`day0_anchor = "ground_truth_with_rationale"`**. Day-0 opinion is *seeded directly from the YouGov survey response* (no LLM survey call), and the LLM is asked only to write a rationale for that pre-set opinion. From Day 1 onward, end-of-day surveys are real LLM calls that may move opinions.

---

## 3. The 6 climate policies & the opinion scale

Throughout the CSVs, policies appear as the string `ClimatePolicyID(N)` where `N` is 1–6. Mapping (from [`src/cag/abm/attributes/opinion.py`](src/cag/abm/attributes/opinion.py)):

| ID | Short name | Survey question (paraphrased) |
|---|---|---|
| `ClimatePolicyID(1)` | RENEWABLE_ENERGY | Accelerate roll-out of renewable energy (offshore/onshore wind, solar). |
| `ClimatePolicyID(2)` | BAN_FOSSIL_FUEL | Ban new oil / gas / coal licences. |
| `ClimatePolicyID(3)` | BAN_PETROL_CARS | Ban sale of new petrol cars by 2030. |
| `ClimatePolicyID(4)` | GREEN_HOUSING | Mandate non-fossil heating, rooftop solar, high insulation in new housing. |
| `ClimatePolicyID(5)` | CARBON_TAX | Carbon tax on fossil fuels with revenues returned to the public (fee-and-dividend). |
| `ClimatePolicyID(6)` | CLIMATE_COMPENSATION | Compensate people in other countries impacted by climate change. |

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

## 4. Political exposure & affinity (read this once)

Several of the new tables are sliced by a citizen's **political-exposure bucket**, so it helps to understand it up front. Before Day 0, each citizen is assigned — by the rule named in `political_exposure_mode` — to exactly one of four buckets describing *which* political broadcasts they are eligible to receive:

| Bucket | Receives P-A (pro) | Receives P-B (anti) |
|---|---|---|
| `both` | ✓ | ✓ |
| `A-only` | ✓ | — |
| `B-only` | — | ✓ |
| `neither` | — | — |

The assignment is driven by two per-citizen **affinity scores** — `affinity_score_a` (pull toward the pro-climate side) and `affinity_score_b` (pull toward the anti-climate side) — computed from the citizen's demographics and values. Both scores and the resulting bucket are recorded per agent in `agent_attributes.csv`.

This bucket is the lens for the "gap-widening" question: do `A-only` and `B-only` citizens drift apart over the run because they only ever hear one side? That is exactly what `opinion_shares_by_bucket.csv`, `package_index_by_bucket.csv` and `gap_widening.png` are for. The science behind exposure modes lives in [Model_Design.md](Model_Design.md) and [result_report.md](result_report.md); this guide just tells you which column is which.

---

## 5. `config.json`

The exact config dict that produced the run (enums serialised to strings). Grouped by what they control:

**Population & schedule**

| Key | Meaning |
|---|---|
| `n_citizens` | Number of citizens in the run. |
| `days` | List of per-day phase orderings (e.g. `[{"phases": ["P-A","P-B","C"]}, …]`). Length = number of days simulated. |
| `random_seed` | Seed for sampling YouGov rows and SBM edges. |

**Communication**

| Key | Meaning |
|---|---|
| `communication_mode` | `"package"` (one call covers all 6 policies) or `"single_policy"` (one call per policy). |
| `package_policies` | The 6-policy set used in package mode. |
| `day0_anchor` | `"llm_survey"`, `"ground_truth"`, or `"ground_truth_with_rationale"`. Controls how Day-0 opinions are set. |
| `k_peers_per_day` | Max number of peer-message recipients per citizen per day in Phase C. |

**Network** — `network_type`, `network_params`, `p_intra`, `p_inter`, `block_sizes` are the stochastic-block-model parameters for the citizen network. `diagnostics_timeout_s` caps how long the graph-diagnostics pass may run before bailing out (recorded as `timed_out` in `network_diagnostics.json`).

**Political broadcast & exposure**

| Key | Meaning |
|---|---|
| `political_message_source` | `"offline"` (canned message bank) or `"llm"` (generated live). |
| `political_message_set` | Which canned set to draw from when source is offline (e.g. `"v1"`). |
| `political_exposure_mode` | Rule that assigns each citizen to a bucket (e.g. `"rule_affinity_rank"`). See §4. |
| `political_exposure_targets` / `affinity_weights` | Optional tuning for the exposure rule (`null` = built-in defaults). |
| `reach_a` / `reach_b` | Fraction of each side's eligible audience actually reached per broadcast (1.0 = everyone exposed). |
| `audience_cap` | Optional hard cap on broadcast recipients per side per day (`null` = uncapped). |

**LLMs**

| Key | Meaning |
|---|---|
| `llm_model` / `llm_provider` / `llm_temperature` | LLM used for **messaging** (broadcasts, peer messages, reflections). `llm_provider` is one of `"openai"`, `"genai"`, `"anthropic"`, `"local"`. |
| `survey_model` / `survey_provider` / `thinking` | LLM used for **end-of-day surveys**, plus whether extended-thinking is on. `null` survey_model/provider means "reuse the messaging LLM". (The Condition-B anti-sycophancy two-step survey is now always on and is no longer a config key.) |
| `local_base_url` / `local_extra_body` / `local_timeout_s` | Only used when a provider is `"local"`. See [Local_LLM_Setup_Guide.md](Local_LLM_Setup_Guide.md). All optional with env-var / built-in defaults. |

**Agent memory / prompt assembly**

| Key | Meaning |
|---|---|
| `memory` | What the agent "remembers" and sees in each prompt. A preset name (e.g. `"default"`, `"short_memory"`, `"no_anchor"`), a partial-override dict, or `null` (= `"default"`). Presets and the full schema are documented in [Simulation_Configuration_Guide.md](Simulation_Configuration_Guide.md). |
| `memory_resolved` | The fully-expanded, validated memory config the run actually used — every section toggle, the `verbatim_window_days` window, and any per-stage overrides. This is *derived* from `memory` and always written, so you can audit the exact prompt-assembly behaviour even when `memory` is just a preset name. |

**Audit-trail sampling** — `timeline_sample_size` (default 3) and `timeline_sample_agent_ids` (explicit list, or `null` to auto-pick) control which agents get a detailed `agent_timeline.csv`. See §10.

The two-LLM split lets us message with a cheap fast model and survey with a careful, less-biased model.

---

## 6. Ground-truth files

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

## 7. Trajectory files (numeric)

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

## 8. Aggregated diagnostic tables

These collapse the per-agent numbers into population-level summaries. The first two existed before; the rest are new in v0.7.0 and are sliced by political-exposure bucket (§4) so you can watch the two sides diverge.

All "share" tables bin the `-3 … +3` opinion into three bands — **support (`> 0`)**, **neutral (`= 0`)**, **against (`< 0`)** — and report counts and percentages.

### `opinion_shares.csv` — per policy, whole population

| Column | Meaning |
|---|---|
| `policy_id` | `ClimatePolicyID(N)`. |
| `day` | `0..N`. |
| `n_agents` | Population size for that (policy, day). |
| `n_support` / `support_pct` | Count and % with `numeric > 0`. |
| `n_neutral` / `neutral_pct` | Count and % with `numeric == 0`. |
| `n_against` / `against_pct` | Count and % with `numeric < 0`. |

Rows = `6 × (1 + n_days)`. Plotted as `opinion_shares.png`.

### `package_index_shares.csv` — package index, whole population

Same schema with `policy_id` replaced by `index_name` + `package_scope`, applied to the package index. Rows = `1 + n_days`. Plotted as `package_index_shares.png`.

### `opinion_shares_by_bucket.csv` — per policy, split by exposure bucket

The `opinion_shares` breakdown, additionally grouped by `political_exposure`.

| Column | Meaning |
|---|---|
| `policy_id` | `ClimatePolicyID(N)`. |
| `day` | `0..N`. |
| `political_exposure` | `A-only`, `B-only`, `both`, or `neither`. |
| `n_agents` | Bucket size for that (policy, day). |
| `n_support` / `n_neutral` / `n_against` | Counts in each opinion band. |
| `support_pct` / `neutral_pct` / `against_pct` | The same as percentages of the bucket. |

Plotted as `opinion_shares_by_bucket.png`.

### `package_index_by_bucket.csv` — package index distribution per bucket

The headline "are A-only and B-only drifting apart?" table: the package index within each exposure bucket per day.

| Column | Meaning |
|---|---|
| `day` | `0..N`. |
| `political_exposure` | `A-only`, `B-only`, `both`, `neither`. |
| `n_agents` | Bucket size (std/quartiles are blank when this is 1). |
| `mean` / `std` | Mean and standard deviation of the bucket's package index. |
| `q25` / `q50` / `q75` | Quartiles of the package index. |

Plotted as `package_index_by_bucket.png`; the A-only-vs-B-only mean gap over time is plotted separately as `gap_widening.png`.

### `day0_vs_dayN_shifts.csv` — net opinion movement per agent × policy

How far each citizen moved from their first surveyed day to their last.

| Column | Meaning |
|---|---|
| `agent_id` | Citizen ID. |
| `policy_id` | `ClimatePolicyID(N)`. |
| `political_exposure` | The agent's bucket. |
| `day0` / `dayN` | The two day numbers compared. |
| `day0_numeric` / `dayN_numeric` | Opinion on `-3 … +3` at each end. |
| `signed_shift` | `dayN_numeric − day0_numeric` (direction of movement). |
| `abs_shift` | `|signed_shift|` (magnitude of movement). |

Rows = `n_citizens × 6`.

### `calibration.csv` — agent opinions vs. YouGov ground truth

How well agent opinions track the real survey, per policy per day. Day 0 should be near-perfect when the GT anchor is on; later days show whether the LLM dynamics preserve or erode that calibration.

| Column | Meaning |
|---|---|
| `policy_id` | `ClimatePolicyID(N)`. |
| `day` | `0..N`. |
| `n` | Number of agents compared. |
| `pearson_r` / `spearman_rho` | Linear / rank correlation between agent opinion and ground truth. |
| `mae` | Mean absolute error vs. ground truth. |
| `mean_signed_bias` | Mean (agent − ground truth); positive = agents more pro-climate than reality. |

Plotted as `calibration_by_policy.png`.

### `message_flow.csv` — message volume diagnostics

Who talked to whom, and how much. Useful for confirming broadcasts reached the right buckets and that peer messaging actually fired.

| Column | Meaning |
|---|---|
| `day` | Day. |
| `phase` | `P-A`, `P-B`, or `C`. |
| `sender_side` | `pro_climate` / `anti_climate` for broadcasts; empty for peer messages. |
| `recipient_bucket` | Exposure bucket of the recipients counted in this row. |
| `n_messages` | Number of messages in that (day, phase, side, bucket) cell. |
| `mean_chars` | Mean character length of those messages. |

---

## 9. The qualitative-review files (the important ones)

### 9.1 `messages.csv` — every message produced by anyone

One row per LLM-generated message. This is the social discourse layer.

| Column | Meaning |
|---|---|
| `sim_step` | Global monotonic step counter — sort by it to replay events in true execution order across phases and days. |
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
| `political_message_id` | ID of the canned message used when `political_message_source = "offline"`; empty for peer messages and live-generated broadcasts. |

In **package mode** every row has `policy_id` empty, `package_scope = "climate_policy_package"`, and `policy_ids_json` listing all six policies. A single message therefore covers the entire climate package.

**For qualitative review:** filter by `phase` to read political broadcasts vs. peer messages; filter by `sender_side` to compare pro- vs. anti-climate framing; filter by `sender_id` to follow one citizen's voice across days.

### 9.2 `reflections.csv` — what each citizen privately concluded

After receiving messages in any phase, the citizen writes an internal *reflection* — a per-policy or per-package summary of how they now see things. This is the "interior monologue" produced by the messaging LLM.

| Column | Meaning |
|---|---|
| `agent_id` | Citizen ID. |
| `sim_step` | Global step counter for ordering against `messages.csv`. |
| `day` | Day the reflection was written. |
| `phase` | Which phase triggered the reflection (`P-A`, `P-B`, `C`). |
| `policy_id` | `climate_policy_package` in package mode, or a `ClimatePolicyID(N)` in single-policy mode. |
| `package_scope` | `climate_policy_package` in package mode; empty otherwise. |
| `policy_ids_json` | JSON array of policies the reflection covers. |
| `messages_received_json` | JSON array of the messages the citizen had in front of them when reflecting. |
| `messages_received_count` | Length of that array (typically `1` for political broadcasts; up to `k_peers_per_day` for Phase C). |
| `text` | The reflection itself. **This is what to read.** |

A reflection only fires for citizens who actually *received at least one message* in that phase. In a small-N run with sparse `p_intra` / `p_inter`, many citizens have no peer neighbours, so Phase C reflections will be sparse — that is expected, not a bug. For political broadcasts, only citizens whose exposure bucket (§4) includes that side receive a message, so P-A and P-B reflection counts will not equal `n_citizens` either.

### 9.3 `survey_reasoning.csv` — why each survey response was given

End-of-day surveys ask the citizen to (1) reason briefly and (2) pick a letter A–G. The reasoning is captured here; the chosen letter ends up in `opinion_trajectories.csv`.

| Column | Meaning |
|---|---|
| `agent_id` | Citizen ID. |
| `sim_step` | Global step counter. |
| `day` | `0` for Day-0 rationales, `1..N` for end-of-day surveys. |
| `policy_id` | `ClimatePolicyID(N)`. |
| `reasoning` | The free-text reasoning that produced that day's opinion. **This is what to read.** |

Day 0 is special: when `day0_anchor = "ground_truth_with_rationale"`, the *opinion* came from YouGov but the *reasoning* is an LLM rationalisation of that pre-set opinion. There will be exactly `n_citizens × 6` Day-0 rows. (There is no longer a separate `day0_anchors.csv`; this is where Day-0 reasoning lives.)

When `debias = True`, Day ≥ 1 reasoning entries are the Step-1 anti-sycophancy reasoning from the two-step Condition-B survey.

### 9.4 `survey_raw_response.csv` — the LLM's raw chosen answer

The literal answer string the survey LLM returned, before it was parsed into a numeric opinion. Pair it with `survey_reasoning.csv` to check the parser never silently misread a response.

| Column | Meaning |
|---|---|
| `agent_id` | Citizen ID. |
| `sim_step` | Global step counter. |
| `day` | `0..N`. |
| `policy_id` | `ClimatePolicyID(N)`. |
| `raw_response` | The raw answer the LLM gave (e.g. a letter `E`), pre-parse. |

### 9.5 `survey_assembled_context.csv` — exactly what the survey LLM saw

The full context block handed to the survey LLM for each (agent, day, policy) — persona, memory, and the messages the agent had been exposed to. This is the audit surface for "why did the model answer that?".

| Column | Meaning |
|---|---|
| `agent_id` | Citizen ID. |
| `sim_step` | Global step counter. |
| `day` | `0..N`. |
| `policy_id` | `ClimatePolicyID(N)`. |
| `assembled_context` | The full prompt-context string produced by `assemble_context()`. |

### 9.6 `daily_summaries.csv` — optional end-of-day note (often empty)

Reserved for an optional end-of-day per-(agent, policy) summary that some memory configurations write (typically only from Day ≥ 2). It is header-only in runs that don't enable that step (as in the example run).

| Column | Meaning |
|---|---|
| `agent_id` | Citizen ID. |
| `sim_step` | Global step counter. |
| `day` | Day. |
| `policy_id` | `ClimatePolicyID(N)` or `climate_policy_package`. |
| `summary` | Free-text end-of-day note. |

---

## 10. Per-agent audit trail

### 10.1 `agent_attributes.csv` — who each citizen is

A one-row-per-citizen snapshot of demographics, the assigned exposure bucket, and the affinity scores that produced it (§4).

| Column | Meaning |
|---|---|
| `agent_id` | Citizen ID. |
| `political_exposure` | Assigned bucket: `A-only`, `B-only`, `both`, `neither`. |
| `affinity_score_a` / `affinity_score_b` | Pull toward the pro- / anti-climate side, used to assign the bucket. |
| `year_of_birth`, `gender_id`, `region_id`, `education_id`, `ukge2019_vote_id`, `brexit_vote_id` | YouGov demographic codes for the sampled respondent. |
| `persona_text` | The natural-language persona built from those demographics and shown to the LLM. |

Rows = `n_citizens`.

### 10.2 `agent_timeline.csv` — a sampled per-event replay

A long-format, fully ordered event log for a small **sample** of agents (default 3, set by `timeline_sample_size` / `timeline_sample_agent_ids`). It is the single best file for following one citizen's full experience — every message received, reflection written, and survey answered — in execution order, without joining five other CSVs. It is sampled because writing it for every agent would be huge.

| Column | Meaning |
|---|---|
| `agent_id` | Citizen ID. |
| `political_exposure` | The agent's bucket. |
| `sim_step` | Global step counter — sort by this. |
| `day` | Day. |
| `phase` | `P-A`, `P-B`, `C`, or empty for surveys. |
| `event_type` | What happened, e.g. `survey_numeric`, message received, reflection written. |
| `policy_id` | Policy or `climate_policy_package` the event concerns. |
| `counterparty_id` / `counterparty_role` | The other party in the event (e.g. a political agent or peer), where applicable. |
| `content` | The event payload (message text, reasoning, chosen opinion, …). |
| `metadata_json` | Any extra structured fields for the event. |

---

## 11. Network files (JSON)

### 11.1 `network_diagnostics.json` — summary statistics of the peer graph

A compact health check of the citizen network the SBM produced.

| Field | Meaning |
|---|---|
| `n_nodes` / `n_edges` / `density` | Size and overall connectedness. |
| `mean_degree` / `median_degree` / `max_degree` / `degree_histogram` | Degree distribution. |
| `n_connected_components` / `largest_component_size` | Fragmentation of the graph. |
| `average_clustering` / `diameter` | Local clustering and longest shortest-path. |
| `assortativity_political_exposure` | Whether citizens preferentially connect to their own exposure bucket (homophily). |
| `timed_out` | `true` if the diagnostics pass hit `diagnostics_timeout_s` and returned partial stats. |

### 11.2 `network_snapshot.json` — the graph itself

The raw structure, for re-drawing or custom analysis. `nodes` is a list of `{id, bucket, degree}`; `edges` is a list of `[u, v]` ID pairs. This is what `network_graph.png` is rendered from.

---

## 12. Plots

Each `*.png` is generated from the matching `*.csv` by `save_result_plots(results, out_path)` (in `cag.io.plots`, re-exported from `cag.abm.sim`). They are deterministic given the CSVs and are written only when the underlying data is present, so a given run may have fewer than the nine below.

| File | What it shows | When written |
|---|---|---|
| `opinion_trajectories.png` | Per-policy mean and per-agent lines over days, with YouGov GT mean as a dashed reference. | always |
| `opinion_shares.png` | Stacked support / neutral / against percentages per policy per day. | always |
| `package_index_trajectories.png` | Same as opinion_trajectories but for the package index. | package mode |
| `package_index_shares.png` | Same as opinion_shares but for the package index. | package mode |
| `package_index_by_bucket.png` | Package-index mean per exposure bucket over days. | package mode + buckets present |
| `opinion_shares_by_bucket.png` | Per-policy shares split by exposure bucket. | buckets present |
| `gap_widening.png` | A-only vs B-only mean package index over days — the polarisation headline. | both A-only and B-only present |
| `network_graph.png` | The peer network drawn with nodes coloured by exposure bucket. | networkx installed + network exists |
| `calibration_by_policy.png` | Agent-vs-ground-truth correlation / MAE per policy over days. | opinion + ground truth present |

---

## 13. A suggested qualitative-review workflow

1. Open `config.json` and skim it — note `n_citizens`, `days`, `communication_mode`, `day0_anchor`, `political_exposure_mode`, the messaging vs. survey LLM, whether `thinking` is on, and the `memory` preset (with `memory_resolved` for the exact section toggles).
2. Open `messages.csv`. Filter `message_type == "political_broadcast"` and `sender_side == "pro_climate"` — read those, then the `anti_climate` ones. Are they on-message, distinct, and persuasive in the way you'd expect?
3. Filter `message_type == "peer_message"` and read a handful per day. Do they sound like a real person passing a thought to a friend, or do they read like another political broadcast?
4. Pick a sampled agent and open `agent_timeline.csv` for them — it replays every message, reflection, and survey in `sim_step` order in one place. (For agents outside the sample, join `reflections.csv` and `survey_reasoning.csv` on `agent_id`.)
5. Cross-reference `survey_reasoning.csv` against the reflections for the same agent: does the end-of-day rationale match, or does the survey LLM (a different model in dual-model runs) drift? Use `survey_assembled_context.csv` to see exactly what it was shown, and `survey_raw_response.csv` to confirm the parse.
6. Spot-check `opinion_trajectories.csv` Day-0 rows against `ground_truth.csv` for that agent — they must match exactly when the GT anchor is on. `calibration.csv` Day 0 should show `pearson_r ≈ 1`, `mae ≈ 0`.
7. Look at `gap_widening.png` / `package_index_by_bucket.csv` to see whether A-only and B-only citizens diverged, and `opinion_shares.png` for any policy where a tipping pattern (support/against share crossing) appeared.

---

## 14. Checkpointing & Resume

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
  survey_raw_response.csv
  survey_assembled_context.csv
  messages.csv
  package_index_trajectories.csv  # if package mode
  ground_truth.csv
  package_ground_truth.csv
```

A per-day checkpoint deliberately omits the derived diagnostic tables (the `*_shares`, `*_by_bucket`, `day0_vs_dayN_shifts`, `calibration`, `message_flow` files), `agent_timeline.csv`, and `network_snapshot.json` — they are too expensive to recompute every day and are rebuilt from the raw CSVs when the finished run is saved. Writes are atomic (temp file + `os.replace`) so a crash mid-write cannot leave a half-written CSV.

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

- `llm_model`, `llm_provider`, `survey_model`, `survey_provider`, `debias`, `thinking`, `llm_temperature`, `local_base_url`, `local_extra_body`, `local_timeout_s`

### Caveat

With `temperature > 0`, a "ran cleanly in one shot" execution and a "crashed and resumed" execution are not byte-identical even with the same config. The checkpoint records when it was written; for paper-headline results, disclose whether a run was resumed.

That's enough to form a qualitative judgement on whether the generative-text layer is behaving sensibly before any quantitative analysis is layered on top.
