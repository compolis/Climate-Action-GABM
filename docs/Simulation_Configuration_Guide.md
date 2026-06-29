# Climate-Action-GABM — Simulation Configuration Guide

This guide explains the **configuration** of a simulation run: the small dictionary of settings
you hand to `run_simulation(config, nation)` to control who is in the model, how many days it runs,
which AI model speaks for the citizens, and who hears which politician.

You almost never set every option by hand. The model ships with a complete set of defaults
(`SIM_CONFIG`), and your `config` only needs to list the things you want to change. Anything you
leave out keeps its default. So a perfectly valid run is `config = {}` — that just uses the defaults
described in the next section.

The guide is organised so you can stop reading as soon as you have what you need:

- **Section 1** — what a default run actually does, in plain language.
- **Section 2** — the handful of settings most people change.
- **Section 3** — the settings to leave alone unless you have a specific reason.
- **Section 4** — a full plain-language reference for every one of the 33 settings.
- **Sections 5–7** — ready-to-copy examples, what the model rejects, and how resuming works.
- **Section 8** — companion guides and a short note for developers (code locations).

> **Companion guides.** The exact wording of every prompt and persona is in
> [Prompts_and_Personas_Guide_v2.md](Prompts_and_Personas_Guide_v2.md). What each output file
> contains is in [Run_Output_Guide.md](Run_Output_Guide.md). Setting up a local AI model is in
> [Local_LLM_Setup_Guide.md](Local_LLM_Setup_Guide.md). The reasoning behind the design choices is
> in [Model_Design.md](Model_Design.md), and a tour of the code is in [Code_Tour.md](Code_Tour.md).

---

## 1. What a default run does

If you run the model with no changes at all, here is what happens.

1. **The citizens.** The model creates **100 citizens**, each built from a real person's answers in
   the YouGov April 2024 climate survey. Their demographics, voting history, and values all come
   from that survey.

2. **The AI model.** Every time a citizen needs to think, write a message, or answer a survey, the
   model asks a **local AI model** (`Qwen3-8B`) running on your own machine. You can switch to a
   cloud model from OpenAI, Anthropic, or Google instead — that is fully supported — but the default
   keeps everything local so runs are reproducible and cost nothing in API fees.

3. **The topic.** Each day, citizens hear about and are surveyed on **all six climate policies at
   once** (renewable energy, banning new fossil-fuel licences, banning new petrol cars, greener
   housing, a carbon tax, and climate compensation). This is called **package mode**.

4. **The politicians.** Two political voices broadcast at the citizens each day: a **pro-climate**
   one and an **anti-climate** one. Their messages are drawn from a curated file of real-world
   political text, not made up by the AI. If any required message is missing, the run stops
   immediately rather than quietly carrying on.

5. **The starting point (Day 0).** Each citizen's opinions on Day 0 are set **directly from their
   real survey answers**, and the AI is only asked to write a short reason for that position. This
   avoids a known problem where the AI, asked cold, leans more pro-climate than real people do.

6. **The end-of-day surveys.** At the end of each day every citizen is re-surveyed. The survey uses
   a **two-step bias-correction process** (it first asks the AI to reason, then to commit to an
   answer) to keep the AI from drifting pro-climate.

7. **The social network.** Citizens are connected in a friendship-style network, with people who
   share a political leaning more likely to be linked than people who don't.

8. **Who hears whom.** Citizens are sorted into four groups: those who hear only the pro-climate
   side, only the anti-climate side, both, or neither. By default this is a **committed-minority**
   split — small, equal pro and anti minorities (11% each), a third who hear both sides, and a
   disengaged 45% who hear no political broadcasts.

9. **Broadcast reach.** By default every citizen in a politician's audience hears every one of that
   politician's broadcasts (no one is dropped).

10. **Peer chat.** Each day, every citizen sends a short message to **3 of their network
    neighbours**.

11. **Day plan.** A default run is **2 days long**, and the two politicians take turns going first
    (to avoid one side always having the last word before the survey).

That is the canonical research setup. Everything below tells you how to change parts of it.

---

## 2. The settings you'll most likely change

These are the knobs designed for experiments. Changing them is normal and expected.

| What you want to change | Setting(s) |
|---|---|
| How many citizens are in the run | `n_citizens` |
| How many days, and what happens each day | `days` |
| How many peers each citizen messages per day | `k_peers_per_day` |
| The shape of the social network | `network_type`, `network_params` |
| Who hears which politician, and in what proportions | `political_exposure_targets`, `affinity_weights`, `political_exposure_mode` |
| How far each politician's broadcasts reach | `reach_a`, `reach_b`, `audience_cap` |
| Which climate policies are in the package | `package_policies` |
| Using a cloud AI model instead of the local one | `llm_provider`, `llm_model` |
| Using a stronger model just for the surveys | `survey_provider`, `survey_model`, `thinking` |
| Reproducing or varying randomness | `random_seed` |

Full explanations of each are in [Section 4](#4-every-setting-explained).

---

## 3. The settings to leave as-is (unless you know why)

Six settings define the research design. They have been chosen and validated deliberately, and
changing them means your run is no longer comparable to the standard ones. Change them only on
purpose, and note it when you report results.

| Setting | Default | Why it's set this way |
|---|---|---|
| `llm_provider` | `local` | Keeps runs reproducible and free of API costs and rate limits. |
| `llm_model` | `Qwen3-8B-4bit` | The local model that was checked against cloud models and behaved comparably. |
| `communication_mode` | `package` | The research question is about how the six policies move *together*; doing them one at a time hides that. |
| `day0_anchor` | `ground_truth_with_rationale` | Starts everyone from their real survey answer, removing the AI's pro-climate lean on Day 0. |
| `debias` | `True` | The two-step survey removes most of the AI's residual pro-climate lean on later days. |
| `political_message_source` | `offline` | Uses real political text from a curated file, which is the point of the study; AI-written political messages are only a fallback. |

The wording of the prompts the citizens see (in `agent.py`, documented in
[Prompts_and_Personas_Guide_v2.md](Prompts_and_Personas_Guide_v2.md)) is also part of this fixed
core.

---

## 4. Every setting explained

This section covers all 33 settings, grouped by what they control. Each entry says what the setting
does, its default, and whether it's something you'd normally change.

### Who is in the simulation

#### `n_citizens` — default `100`

The maximum number of citizens to create from the YouGov survey. The actual number can be slightly
lower if some survey rows can't be used. Smaller runs are faster and cheaper but noisier: below about
30 citizens the four exposure groups get so small that results swing wildly from run to run, so very
small sizes are best kept for quick tests. *Safe to change.*

### The daily schedule

#### `days` — default: two days, politicians alternating who goes first

A list where each entry is one day. The default is:

```python
[{"phases": ["P-A", "P-B", "C"]},
 {"phases": ["P-B", "P-A", "C"]}]
```

Each day is a list of **phases**, run in order:

- **`P-A`** — the pro-climate politician broadcasts.
- **`P-B`** — the anti-climate politician broadcasts.
- **`C`** — peer chat: citizens message their neighbours.

You can repeat phases (`["P-A", "P-A", "P-B", "C"]` makes the pro side broadcast twice that day) and
you can reorder them. The default alternates which politician speaks first across days so neither side
always gets the last word before the evening survey.

There is also a **shorthand** for describing a day when you want lots of broadcasts and don't want to
type them out. Instead of a `phases` list, you can write, for example:

```python
{"broadcasts_a": 3, "broadcasts_b": 1, "peer": True, "interleave": False, "a_first": True}
```

which means "three pro broadcasts, one anti broadcast, then peer chat." Use either the explicit
`phases` list **or** the shorthand keys for a given day — mixing both in the same day is rejected.

> **One-policy runs need a policy named per day.** If you switch off package mode (see
> `communication_mode`), every day must also say which policy it covers, e.g.
> `{"phases": ["P-A", "P-B", "C"], "policy": ClimatePolicyID.CARBON_TAX}`. In the default package
> mode, any `policy` you add is simply ignored. *Safe to change.*

#### `k_peers_per_day` — default `3`

How many network neighbours each citizen sends a message to during a peer-chat (`C`) phase. Higher
numbers mean more AI calls (and more cost) per peer phase. If a citizen has fewer neighbours than this
number, they simply message all of them. *Safe to change.*

### The peer (social) network

#### `network_type` — default `"stochastic_block"`

The shape of the citizen friendship network. There are five options:

| `network_type` | What it is |
|---|---|
| `"stochastic_block"` | **Default.** Two communities (roughly, the pro-leaning and anti-leaning citizens), densely linked inside each community and sparsely between them. |
| `"erdos_renyi"` | A plain random network — everyone equally likely to be linked to everyone. A neutral baseline. |
| `"watts_strogatz"` | A "small-world" network: mostly local links plus a few long-range shortcuts. |
| `"barabasi_albert"` | A network with a few highly-connected hubs (like real social media followings). |
| `"homophily_weighted"` | Links are more likely between citizens who are similar on attributes you choose (vote, region, and so on). |

*Safe to change.*

#### `network_params` — default `None`

A small dictionary of settings specific to the chosen `network_type`. Leaving it `None` uses sensible
built-in values. Examples:

```python
# A small-world network
{"network_type": "watts_strogatz", "network_params": {"k": 8, "beta": 0.2}}

# A similarity-based network on chosen attributes
{"network_type": "homophily_weighted",
 "network_params": {"attributes": ["ukge2019_vote_id", "selftransc_id", "openness_id"],
                    "weights": [2.0, 1.0, 1.0]}}
```

*Safe to change.*

#### `p_intra` — default `0.15`, and `p_inter` — default `0.05`

These two apply only to the default `stochastic_block` network. `p_intra` is how likely two citizens
in the **same** community are to be linked; `p_inter` is how likely two citizens in **different**
communities are. The defaults give roughly three within-community links for every cross-community
link — about a quarter of links cross the political divide, which matches what social-media studies
report (Bakshy et al. 2015; Halberstam & Knight 2016). (Earlier versions used a much lower
cross-community rate, which left small networks broken into disconnected islands.) *Safe to change.*

#### `block_sizes` — default `None`

For the `stochastic_block` network, the sizes of the two communities. `None` splits the citizens
evenly. *Safe to change.*

#### `diagnostics_timeout_s` — default `30.0`

After building the network the model measures some properties of it (clustering, path lengths). On a
large network a few of these measurements can be slow, so this is a time limit in seconds for the slow
ones; the quick measurements always run. Set it to `0` or `None` to skip the slow ones entirely. This
only affects diagnostics, not the simulation itself. *Safe to change for performance reasons.*

### The AI model

#### `llm_model` — default `"mlx-community/Qwen3-8B-4bit"`

Which AI model writes the citizens' reflections, messages, and survey answers. For the local model,
the name is matched against a small built-in list to pick good sampling settings automatically. *Part
of the fixed research core — see [Section 3](#3-the-settings-to-leave-as-is-unless-you-know-why).*

#### `llm_provider` — default `"local"`

Where the AI model runs. One of `"local"`, `"openai"`, `"anthropic"`, or `"google"`. With `"local"`,
the model checks that your local AI server is running at the start and stops the run if it isn't.
*Part of the fixed research core, but switching to a cloud provider is a documented, supported option
(see the examples in [Section 5](#5-ready-to-copy-examples)).*

#### `llm_temperature` — default `0.5`

How much randomness the AI uses when generating text (higher = more varied wording). Note: for the
local model this is usually overridden by the model's own recommended setting, so to change it for a
local run you generally pass it through `local_extra_body` instead (see below). *Safe to change.*

#### `survey_model` — default `None`

Lets you use a **different** AI model for the end-of-day surveys than for everything else. `None`
means "use the same model as `llm_model`." This is handy for messaging with a cheap, fast model but
surveying with a stronger, more careful one. *Safe to change.*

#### `survey_provider` — default `None`

The provider that goes with `survey_model` (for example, message locally but survey with Anthropic).
`None` means "use the same provider as `llm_provider`." *Safe to change.*

#### `thinking` — default `False`

Turns on the AI's extended "show your working" reasoning mode **for surveys only**. Reflections and
messages never use it, because they are meant to be short. Survey answers tend to benefit most from
the extra reasoning. *Safe to change.*

#### `debias` — default `True`

Turns on the two-step bias-correction process for end-of-day surveys: the AI first reasons about the
range of views a real person might hold, then commits to an answer. This removes most of the AI's
tendency to answer more pro-climate than real survey respondents. It does not apply on Day 0 (Day 0 is
just the seeded starting point). *Part of the fixed research core.*

### What gets talked about

#### `communication_mode` — default `"package"`

Either `"package"` (all six policies discussed and surveyed together each day) or `"single_policy"`
(one policy at a time). Package mode is the default because the research is about how opinions on the
policies move as a set. If you choose `single_policy`, remember every entry in `days` must name its
policy. *Part of the fixed research core.*

#### `package_policies` — default: all six climate policies

The set of policies covered in package mode. You can narrow it to a subset, for example:

```python
{"package_policies": (ClimatePolicyID.CARBON_TAX, ClimatePolicyID.RENEWABLE_ENERGY)}
```

*Safe to change.*

### The politicians' messages

#### `political_message_source` — default `"offline"`

Where the politicians' broadcast text comes from. `"offline"` uses a curated file of real-world
political text; `"llm"` has the AI write the political messages live. With `"offline"`, the run checks
that every needed message exists before it starts and stops immediately if any is missing — there is
no silent fallback. *Part of the fixed research core.*

#### `political_message_set` — default `"v1"`

Which curated message file to use. This points at
`data/political_messages/messages_v1.csv` (and its companion sources file). `v1` is the set that ships
with the project. *Safe to change if you have other message sets.*

### Where Day 0 opinions come from

#### `day0_anchor` — default `"ground_truth_with_rationale"`

How each citizen's starting opinion is set on Day 0. Three options:

- **`"ground_truth_with_rationale"`** (default) — use the citizen's real survey answer as the
  opinion, and ask the AI to write a short reason for it. Removes the AI's Day-0 pro-climate lean
  while keeping a written rationale for review.
- **`"ground_truth"`** — use the real survey answer with **no** AI call at all on Day 0. Cheapest;
  loses the rationale text.
- **`"llm_survey"`** — ask the AI to answer the survey cold on Day 0, with no real-world anchor. Use
  this only when you specifically want to *measure* the AI's built-in lean.

*Part of the fixed research core.*

### Who hears the politicians

#### `reach_a` — default `1.0`, and `reach_b` — default `1.0`

The fraction of a politician's audience that actually receives each broadcast (`1.0` = everyone in the
audience). `reach_a` is for the pro-climate side, `reach_b` for the anti-climate side. Lowering one
side models a politician with weaker media presence. Values must be between 0 and 1. *Safe to change.*

#### `audience_cap` — default `None`

An optional hard limit on how many citizens each politician can reach, applied (at random) before
`reach` is taken into account. `None` means no limit. This is useful at small population sizes, where
the survey sample can give one side a structurally bigger audience than the other; capping both to the
same size makes a fair "equal reach" comparison possible. *Safe to change.*

#### `political_exposure_mode` — default `"rule_affinity_rank"`

The rule used to sort citizens into the four exposure groups (pro-only, anti-only, both, neither).

- **`"rule_affinity_rank"`** (default) — score each citizen's pull toward each side, then fill the
  groups to hit the target proportions you set exactly.
- **`"rule_priority_chain"`** — an older vote-based rule; the group sizes fall out of the data rather
  than being targeted. Kept for reproducing older runs.
- **`"rule_signal_count"`** — currently behaves the same as `rule_priority_chain` (reserved for
  future use).

*Safe to change.*

#### `political_exposure_targets` — default `None`

The proportions of citizens in each of the four groups. `None` uses the **committed-minority
symmetric** preset. You can name a preset or pass your own four numbers (they must add up to 1).

| Preset | Pro-only | Anti-only | Both | Neither | Notes |
|---|---|---|---|---|---|
| `committed_minority_symmetric` *(default)* | 0.11 | 0.11 | 0.33 | 0.45 | Equal small pro/anti minorities; 45% hear no politics. |
| `committed_minority_uk_2024` | 0.08 | 0.14 | 0.33 | 0.45 | An anti-leaning version (more anti-only than pro-only). |
| `legacy_v05` | 0.225 | 0.225 | 0.20 | 0.35 | The older default, before committed-minority. |
| `split50` | 0.50 | 0.50 | 0.00 | 0.00 | Half hear only the pro side, half only the anti side. A clean polarisation test. |
| `neither` | 0.00 | 0.00 | 0.00 | 1.00 | No one hears any politician — peer effects only. |

A custom example: `{"A-only": 0.2, "B-only": 0.2, "both": 0.3, "neither": 0.3}`. *Safe to change.*

#### `affinity_weights` — default `None`

How strongly each piece of a citizen's profile counts when scoring their pull toward each side.
`None` uses the **balanced** preset. Three presets:

| Preset | Idea |
|---|---|
| `balanced` *(default)* | All three kinds of signal — values, demographics, and vote/politics — contribute, with values and vote choice weighted most. |
| `vote_dominant` | "Is it really all just vote choice?" — boosts vote/Brexit/politics, shrinks the rest. |
| `values_dominant` | "Can values alone reproduce the groups?" — boosts values, shrinks vote-related signals. |

You can also pass your own weights as `{"A": {...}, "B": {...}}` using the same signal names as the
presets. The weights are deliberately hand-chosen and anchored to published correlations rather than
fitted to data, because there is no UK individual-level "truth" about who lives in which echo chamber
to fit against. *Safe to change.*

### Reproducibility

#### `random_seed` — default `42`

The seed for every random choice in the run — which survey rows are sampled, how the network is wired,
how audiences are thinned, which messages are picked. Keep it fixed to reproduce a run; change it to
get a different random draw. (AI models are not perfectly deterministic, so text may still vary
slightly run to run.) *Safe to change.*

> **Where results are saved** is not part of this configuration dictionary. The output location is
> chosen when results are written (the command-line runner uses `--outdir`; see
> [Run_Output_Guide.md](Run_Output_Guide.md)).

### Running a local AI model

These three apply only when `llm_provider="local"`. All are optional; left as `None` they fall back to
environment variables and then to built-in defaults.

#### `local_base_url` — default `None`

The web address of your local AI server. `None` falls back to the `CAG_LOCAL_BASE_URL` environment
variable, then to `http://localhost:8080/v1`. *Safe to change to match your setup.*

#### `local_extra_body` — default `None`

Extra options sent with every request to the local server — for example to override the sampling
temperature (`{"temperature": 0.3}`) or to turn the model's thinking mode on or off. This is the
reliable way to change the temperature on a local run. *Safe to change.*

#### `local_timeout_s` — default `None`

How long (in seconds) to wait for the local server to answer before giving up. `None` falls back to
the `CAG_LOCAL_TIMEOUT_S` environment variable, then to 600 seconds. It is set high because local
models in thinking mode can take a while. *Safe to change.*

### The detailed audit trail

#### `timeline_sample_size` — default `3`

The model can write a minute-by-minute log for a few sampled citizens — every broadcast they heard,
every reflection they wrote, every message sent and received, and the exact survey prompt they saw —
in true order, to `agent_timeline.csv`. This setting is how many citizens get that detailed log. Set
it to `0` to switch the log off. *Safe to change.*

#### `timeline_sample_agent_ids` — default `None`

Which specific citizens get the detailed log. `None` picks a spread automatically; otherwise pass a
list of citizen IDs. *Safe to change.*

---

## 5. Ready-to-copy examples

### 5.1 The standard research run

```python
config = {}  # use all the defaults from Section 1
results = run_simulation(config, nation)
```

### 5.2 A quick test run

```python
config = {
    "n_citizens": 10,
    "days": [
        {"phases": ["P-A", "P-B", "C"]},
        {"phases": ["P-B", "P-A", "C"]},
    ],
    "k_peers_per_day": 2,
    # everything else stays on the defaults from Section 1
}
```

### 5.3 Using a cloud AI model

```python
config = {
    "llm_provider": "openai",
    "llm_model": "gpt-4.1-mini",
    # optional: survey with a stronger model
    "survey_provider": "anthropic",
    "survey_model": "claude-sonnet-4-5",
    "thinking": True,            # extended reasoning, surveys only
}
```

This needs API keys in `data/api_key.csv` (see [API_KEYS.md](../API_KEYS.md)).

### 5.4 An unequal-reach experiment

```python
config = {
    "reach_a": 1.0,             # pro side reaches all of its audience
    "reach_b": 0.5,             # anti side reaches only half of its audience
    "political_exposure_targets": "committed_minority_uk_2024",
}
```

### 5.5 A clean polarisation test (two echo chambers)

```python
config = {
    "political_exposure_targets": "split50",   # half hear only pro, half only anti
}
```

---

## 6. What the model rejects at the start

To fail fast rather than waste time, a run checks the configuration before doing anything and stops
with a clear error if something is wrong:

| If… | …the run stops because |
|---|---|
| `day0_anchor` isn't one of the three valid options | the value is invalid |
| `reach_a` or `reach_b` isn't a number between 0 and 1 | the value is out of range |
| `audience_cap` is negative, a boolean, or not a whole number (and not `None`) | the value is invalid |
| `political_message_source` isn't `"offline"` or `"llm"` | the value is invalid |
| the message source is `"offline"` but a needed message is missing | the message file is incomplete |
| `political_exposure_mode` isn't one of the valid rules | the value is invalid |
| custom exposure proportions don't add up to 1 | the targets are invalid |
| `network_type` isn't one of the five known types | the network type is unknown |
| a network setting is invalid for its type | the network can't be built |
| a day mixes the explicit `phases` list with the shorthand keys | the day is ambiguous |
| `llm_provider="local"` but the local server isn't reachable | the model can't be contacted |
| you ask to resume or checkpoint without giving a checkpoint folder | there's nowhere to read/write the checkpoint |

---

## 7. Pausing and resuming a run

A run can save its state after each day (when checkpointing is turned on) and pick up later from where
it stopped. When you resume, the model compares your new configuration against the saved one:

- **Settings that must not change** — changing any of these cancels the resume, because it would make
  the second half incompatible with the first: `n_citizens`, `random_seed`, the network type and its
  resolved settings, `communication_mode`, `package_policies`, `day0_anchor`, `reach_a`, `reach_b`,
  `audience_cap`, the three exposure settings, and the two political-message settings. The set of
  citizens and the days already completed must also match (you may *add* future days).

- **Settings you may change** — these only produce a warning and the run continues: the AI model and
  provider (including the survey ones), `debias`, `thinking`, `llm_temperature`, and the three local-
  model settings.

---

## 8. For developers, and where to look next

### Companion guides

- [Model_Design.md](Model_Design.md) — why the design is the way it is.
- [Prompts_and_Personas_Guide_v2.md](Prompts_and_Personas_Guide_v2.md) — every prompt, word for word.
- [Local_LLM_Setup_Guide.md](Local_LLM_Setup_Guide.md) — running a local AI server.
- [Run_Output_Guide.md](Run_Output_Guide.md) — what each output file contains.
- [Code_Tour.md](Code_Tour.md) — a guided walk through the source code.
- [Literature_Political_Exposure.md](Literature_Political_Exposure.md) — the evidence behind the
  exposure proportions and affinity weights.
- [`notebooks/29_canonical_full_smoke.ipynb`](../notebooks/29_canonical_full_smoke.ipynb) — a working
  end-to-end run you can copy as a starting template.

### Where things live in the code

The settings dictionary and the run loop are in [src/cag/abm/sim.py](../src/cag/abm/sim.py). Rather
than line numbers (which drift as the file changes), here are names you can search for:

- `SIM_CONFIG` — the full default dictionary, with an explanatory comment beside each setting.
- `run_simulation`, `_run_one_day` — the top-level run and the per-day loop.
- `_resolve_runtime` — start-up checks: AI provider, message-file validation, model overrides.
- `_resolve_day_phases`, `make_phases` — how a day entry (or its shorthand) becomes a phase list;
  `_PHASE_SUGAR_KEYS` is the set of shorthand keys.
- `VALID_DAY0_ANCHORS` — the three valid Day-0 options.
- `_resolve_network_params` — how the network settings are assembled.

Exposure and affinity scoring are in
[src/cag/abm/environment.py](../src/cag/abm/environment.py): `assign_political_exposure`,
`_green_affinity_score`, `_reform_affinity_score`, `TARGET_PRESETS`, `AFFINITY_WEIGHT_PRESETS`, and
`VALID_EXPOSURE_MODES`.

Other key locations: network building in
[src/cag/abm/networks.py](../src/cag/abm/networks.py) (`build_network`, `compute_diagnostics`); the
political-message file loader in
[src/cag/abm/political_messages.py](../src/cag/abm/political_messages.py) (`load_message_pool`,
`MessagePool`); the single door to every AI model in [src/cag/io/llm.py](../src/cag/io/llm.py)
(`send_chat`, `configure_local`, `ping_local`); and the per-citizen timeline in
[src/cag/io/aggregators.py](../src/cag/io/aggregators.py) (`build_agent_timeline`).
