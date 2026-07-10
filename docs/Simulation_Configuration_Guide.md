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
| How widely each citizen passes messages on (scaled by how connected they are) | `peer_fanout_mode`, `peer_fanout_budget` |
| The shape of the social network | `network_type`, `network_params` |
| Who hears which politician, and in what proportions | `political_exposure_targets`, `affinity_weights`, `political_exposure_mode` |
| How far each politician's broadcasts reach | `reach_a`, `reach_b`, `audience_cap` |
| Which audience members a limited reach keeps | `reach_targeting_a`, `reach_targeting_b` |
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
| `political_message_source` | `offline` | Uses real political text from a curated file, which is the point of the study; AI-written political messages are only a fallback. |

The wording of the prompts the citizens see (in `agent.py`, documented in
[Prompts_and_Personas_Guide_v2.md](Prompts_and_Personas_Guide_v2.md)) is also part of this fixed
core.

---

## 4. Every setting explained

This section covers all 37 settings, grouped by what they control. Each entry says what the setting
does, its default, and whether it's something you'd normally change.

### Who is in the simulation

#### `n_citizens` — default `100`

The maximum number of citizens to create from the YouGov survey. The actual number can be slightly
lower if some survey rows can't be used. Smaller runs are faster and cheaper but noisier: below about
30 citizens the four exposure groups get so small that results swing wildly from run to run, so very
small sizes are best kept for quick tests. *Safe to change.*

#### `persona_mode` — default `"real"`

A **manipulation check** on whether the model actually conditions on each agent's assigned persona. It
never touches the scoring target (real opinions are always read from the survey), so all three modes
are scored against the same ground truth:

| `persona_mode` | What each agent is told it is |
|---|---|
| `"real"` | **Default.** Its own real persona — demographics, voting history, and values. No change; results are bit-for-bit identical to leaving this unset. |
| `"shuffled"` | *Another* agent's whole persona, verbatim (still a coherent real UK person). The reassignment is a derangement, so no agent keeps its own. |
| `"neutral"` | The generic `"I am an adult living in the United Kingdom."` — no age, region, politics, or values. |

If persona genuinely drives opinions, accuracy should be highest under `"real"`, collapse under
`"neutral"`, and land in between (mismatched but coherent) under `"shuffled"`. The persona each agent
ended up with is written to `persona_map.csv` for the audit trail. From the command line use
`--persona-mode {real,shuffled,neutral}`; vary `--seed` to change the shuffle permutation. The `tierP`
run preset (`--preset tierP`) bundles this with a Day-0-only, package-mode shape for the ablation.
*Safe to change.*

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

#### `k_peers_per_day` — default `2`

How many network neighbours each citizen sends a message to during a peer-chat (`C`) phase. Higher
numbers mean more AI calls (and more cost) per peer phase. If a citizen has fewer neighbours than this
number, they simply message all of them. *Safe to change.*

#### Peer fan-out — letting well-connected people spread messages further

By default every citizen passes their view to the *same* small number of neighbours each day
(`k_peers_per_day`, above), whether they are a lone voice with two friends or a hub with forty. That
keeps the peer step simple, but it also means a highly-connected "opinion leader" has no more sway in
conversation than anyone else. **Peer fan-out** lets you change that: a citizen's number of relay
partners can scale with how central they are in the network, so the well-connected spread their
messages further. This is the social-science idea of *influentials* and the *two-step flow* of
communication — a few well-placed connectors carry ideas out to the many.

It is controlled by three settings. The default (`peer_fanout_mode = "constant"`) reproduces the old
everyone-relays-equally behaviour exactly, so your runs do not change unless you opt in.

| Setting | Default | What it does |
|---|---|---|
| `peer_fanout_mode` | `"constant"` | `"constant"` = everyone relays to the same `k_peers_per_day` (the original behaviour). `"degree"` = a citizen's relay count grows with how many neighbours they have. `"betweenness"` = it grows with how much of a *bridge* they are between otherwise-separate groups. |
| `peer_fanout_budget` | `"additive"` | Only used for `"degree"` / `"betweenness"`. `"additive"` (the default) lets the well-connected simply relay to more people, so the *total* amount of peer talk grows — the realistic picture of a posting network, where better-connected accounts reach more followers. `"preserve"` instead keeps the total the same as a constant run and just redistributes it (hubs relay more, isolated people fewer, the average stays at `k_peers_per_day`), which is useful when you want to change *who* talks without changing *how much*. |
| `peer_fanout_kmax` | `10` | A safety cap on the most anyone relays to, even a huge hub. Without it, a very well-connected agent in a large network could message dozens of neighbours a day and run up AI cost and time. |

(Two further internal knobs — a `scale` multiplier and a floor of `1` — are baked to sensible values so
nobody is ever silenced; they are not run settings.)

**When to use it.** Reach for the default `"additive"` when you want the realistic reading, where
better-connected people simply reach more others (like followers on a social platform). Switch to
`"preserve"` when you instead want to ask *whether it matters who does the talking* without also
changing *how much* talking happens — for example, re-testing whether aiming a campaign at network hubs
pays off once those hubs can pass their shifted views on to more people. Leave `peer_fanout_mode` at
`"constant"` for the standard, comparable runs.

A quick example — a standard run, then the same run with well-connected citizens relaying wider:

```bash
# Standard run: everyone relays to the same 2 neighbours (this is the default).
python -m cag --preset r14_canonical --exposure-targets split50 --k-peers 2

# Influentials: well-connected citizens relay to more people (total peer talk grows),
# capped so no single hub messages more than 10 neighbours a day.
python -m cag --preset r14_canonical --exposure-targets split50 \
    --k-peers 2 --peer-fanout-mode degree --peer-fanout-budget additive --peer-fanout-kmax 10
```

From the command line the three flags are `--peer-fanout-mode {constant,degree,betweenness}`,
`--peer-fanout-budget {additive,preserve}`, and `--peer-fanout-kmax`. They have no effect when
`--k-peers 0` (peer chat is switched off entirely). *Safe to change.*

#### Broadcast-frequency asymmetry from the command line

The shorthand above lets one side broadcast more often than the other *within a day*. When you run
from the command line ([src/cag/__main__.py](../src/cag/__main__.py)) and give `--days` a plain
number, three flags apply that same asymmetry to **every** day of the run without you having to write
out a `days` list:

| Flag | Default | What it does |
|---|---|---|
| `--broadcasts-a N` | `1` | The pro-climate politician broadcasts `N` times each day. |
| `--broadcasts-b M` | `1` | The anti-climate politician broadcasts `M` times each day. |
| `--interleave` / `--no-interleave` | on | With `--interleave` the broadcasts alternate (`A,B,A,…`); with `--no-interleave` they run in blocks (`A,A,…,B`). Only matters when the two counts differ. |

For example, `--days 5 --broadcasts-a 3 --broadcasts-b 1 --no-interleave` builds five identical days
of `["P-A", "P-A", "P-A", "P-B", "C"]`; adding `--interleave` instead gives
`["P-A", "P-B", "P-A", "P-A", "C"]`. Peer chat (`C`) is always appended — switch it off with
`--k-peers 0`. The default `1`-vs-`1` is exactly the classic schedule, so leaving these flags off
changes nothing.

This is a **frequency** lever: how *often* each side speaks. It is distinct from `reach_a` / `reach_b`
(see [Who hears the politicians](#who-hears-the-politicians)), which controls what *fraction of the
audience* a single broadcast reaches. The two combine — you can have one side speak more often *and*
to a wider slice. The flags only apply when `--days` is a number; if you pass an explicit `days` list
(where each day already names its own phases) they are ignored, with a warning.

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

#### `reach_targeting_a` — default `"random"`, and `reach_targeting_b` — default `"random"`

When a side's `reach` is below `1.0`, this chooses *which* of its audience the limited reach keeps (it has
no effect at `reach = 1.0`, where everyone is kept). Per side, one of:

- `"random"` — a uniform random slice (the classic behaviour).
- `"persuadable"` — the most undecided members (closest to the neutral midpoint of their real opinion),
  modelling a campaign that spends its reach on swing citizens.
- `"degree"` — the most-connected members of the peer network (the "influencers").
- `"betweenness"` — the members that bridge otherwise-separate clusters (the "brokers").

`reach_targeting_a` is the pro-climate side, `reach_targeting_b` the anti-climate side. The two centrality
modes need the peer network, which the simulation now builds before applying reach. *Safe to change.*

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

**How affinity ranking works.** The rule turns each citizen into two numbers and then sorts. There
are two separate pieces:

*Piece 1 — the scorecard.* Every citizen gets a **side-A score** (pull toward the pro-climate side)
and a **side-B score** (pull toward the anti-climate side). Each score is a weighted sum of signals:
their values (openness, self-transcendence, RWA, …), their demographics (age, education, region), and
their politics (Brexit vote, left–right placement, party vote). The `affinity_weights` below set how
much each signal counts. A citizen who is open, self-transcendent, Remain-voting and Labour/Green
scores high on side A; someone authoritarian, Leave-voting and Reform/Conservative scores high on
side B.

*Piece 2 — sort and slice.* The scores are used **only for ranking** — their absolute size is
meaningless, only who-outranks-whom matters. The rule then fills the four groups top-down to hit your
target proportions exactly:

1. **B-only** first — take the citizens with the highest side-B scores until that group is full.
2. **A-only** next — from those left, take the highest side-A scores until full.
3. **both** — from those still left, take the highest of *either* score until full.
4. **neither** — everyone remaining (the citizens with the weakest political signal on both sides)
   hears no politician.

Because the group sizes come from `political_exposure_targets` and the slicing always fills them, **the
target proportions are hit regardless of the weights** — the weights only change *which individuals*
land near each group's boundary. That is why the weights are safe to tune.

*A quick example (targets = 5% / 5% / 60% / 30%, 100 citizens):* the 5 most anti-leaning citizens
become `B-only`, the 5 most pro-leaning of the rest become `A-only`, the next 60 most
politically-engaged become `both`, and the 30 least-engaged fall into `neither`.

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

How strongly each piece of a citizen's profile counts when scoring their pull toward each side (see
"How affinity ranking works" above). `None` uses the **balanced** preset.

Each preset is a simple **three-tier ladder**: a dominant signal family, the next at a quarter or half,
then demographics weakest. The three signal families are **vote/politics** (Brexit vote, left–right
placement, party vote), **values** (openness, self-transcendence, conformity-tradition, SDO, RWA), and
**demographics** (age, education, region):

| Preset | vote / politics | values | demographics | Idea |
|---|---:|---:|---:|---|
| `balanced` *(default)* | 2.0 | 1.0 | 0.5 | Vote is the best proxy for media diet, so it leads — but only 2× values. |
| `vote_dominant` | 4.0 | 1.0 | 0.5 | "Is it really all just vote choice?" — push vote to 4× values. |
| `values_dominant` | 1.0 | 4.0 | 0.5 | "Can values alone reproduce the groups?" — flip the top two rungs. |

Because only the *ordering* of scores matters, these ladders are easy to reason about: they change
*which citizens sit near each group's edge*, never the group sizes. `vote_dominant` and
`values_dominant` are deliberate distortions of `balanced` used to check how sensitive the results are
to the choice of weights.

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

### What each citizen remembers

#### `memory` — default `"default"`

Controls the citizen's **memory and prompt assembly** — what each citizen is reminded of before it
writes a message, reflects, or answers a survey. Every prompt is built from the same set of building
blocks; this setting decides which blocks are switched on and how far back the citizen remembers
things word-for-word.

You can give it three kinds of value:

- **a preset name** (a string), e.g. `"short_memory"`;
- **your own partial settings** (a dictionary) that override just the pieces you name; or
- **`None`**, which is the same as `"default"`.

The building blocks are: the citizen's **persona**, its **Day-0 anchor** (a reminder of where it
started), the **daily summaries** of earlier days, its **recent reflections**, its **own past survey
reasoning**, **what has happened so far today**, and an optional **opinion trajectory**. A shared
**verbatim window** (`verbatim_window_days`, default `2`) decides how many recent days are replayed
word-for-word before older days are compressed into short summaries.

The default reproduces the model's long-standing behaviour exactly, so leaving it alone changes
nothing. The named presets are for **ablation experiments** — turning one piece off to see whether it
mattered:

| Preset | What it changes |
|---|---|
| `default` | The standard memory (all the usual blocks on, 2-day verbatim window). |
| `short_memory` | Verbatim window shrinks to 1 day (older days compressed sooner). |
| `wide_memory` | Verbatim window grows to 4 days. |
| `no_compression` | Never compress — every day is remembered word-for-word. |
| `no_anchor` | Drop the Day-0 anchor (test how much the starting point pins opinions). |
| `anchor_ttl2` | Keep the Day-0 anchor for only the first 2 days, then drop it. |
| `no_own_reasoning` | Stop reminding the citizen of its own earlier survey reasoning. |
| `reflections_only` | Keep persona + reflections; drop anchor, own-reasoning, and today-so-far. |
| `persona_only` | Strip everything back to just the persona. |

To hand-tune, pass a dictionary with only the parts you want to change — for example
`{"verbatim_window_days": 3, "day0_anchor": {"enabled": False}}`. You can also override a single
**stage** (`survey`, `reflection`, or `peer_message`) so, say, the anchor is hidden at survey time
but shown when writing peer messages. The full schema and every preset live in
`src/cag/abm/config/memory.py`; the demo notebook
[`notebooks/35_memory_ablation_demo.ipynb`](../notebooks/35_memory_ablation_demo.ipynb) shows each
preset changing the assembled prompt.

The run records exactly what it used: the startup log prints a `[memory]` line, and `config.json`
stores both the raw `memory` value and a fully-expanded `memory_resolved` block (see
[Run_Output_Guide.md](Run_Output_Guide.md)). *Safe to change.*

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

### 5.6 A memory-ablation experiment

```python
# Preset: does the Day-0 anchor pin opinions? Turn it off and compare.
config = {"memory": "no_anchor"}

# Hand-tuned: widen the verbatim window and drop the anchor at survey time only.
config = {
    "memory": {
        "verbatim_window_days": 3,
        "stages": {"survey": {"day0_anchor": {"enabled": False}}},
    },
}
```

Run each variant against `{"memory": "default"}` and compare the trajectories. The exact memory
config used is recorded in `config.json → memory_resolved` and printed on the startup `[memory]` line.

---

## 6. What the model rejects at the start

To fail fast rather than waste time, a run checks the configuration before doing anything and stops
with a clear error if something is wrong:

| If… | …the run stops because |
|---|---|
| `day0_anchor` isn't one of the three valid options | the value is invalid |
| `reach_a` or `reach_b` isn't a number between 0 and 1 | the value is out of range |
| `reach_targeting_a` or `reach_targeting_b` isn't one of `random` / `persuadable` / `degree` / `betweenness` | unknown targeting mode |
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
  `audience_cap`, `persona_mode`, the three exposure settings, and the two political-message settings.
  The set of citizens and the days already completed must also match (you may *add* future days).

- **Settings you may change** — these only produce a warning and the run continues: the AI model and
  provider (including the survey ones), `thinking`, `llm_temperature`, and the three local-
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
