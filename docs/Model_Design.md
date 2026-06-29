# Generative Agent-Based Model of Climate Policy Opinion Dynamics

## Full Design Specification — v1.0

> **Append-only document.** This file is treated as an append-only design log.
> Existing sections are not edited or rewritten; new design decisions are
> added as new numbered sections at the end of the document so that the
> historical record of decisions remains intact and reviewable.

---

## 1. Overview

This simulation models how citizen opinions on climate-related policies evolve under the influence of competing political messaging and peer-to-peer deliberation. LLM-powered citizen agents — initialized from real survey data — are placed in a networked social environment where two opposing political group agents broadcast persuasive messages and citizens converse with one another. Opinion is measured periodically using the original survey instrument, enabling direct validation against empirical data.

### Core Research Questions

- How do competing political messages shape citizen opinions on climate policy over time?
- Does peer deliberation amplify, moderate, or redirect the effects of political persuasion?
- How does the order of exposure (political messaging vs. peer messaging) affect opinion trajectories?
- What role does network structure (echo chambers vs. cross-cutting ties) play in opinion dynamics?

---

## 2. Agent Types

### 2.1 Citizen Agents

Each citizen agent represents a real survey respondent from the **YouGov survey commissioned by the University of Leeds (January 2024)**. The data file used is `data/yougov_survey_data/YouGovProcessedData.csv` (train/validation splits available). Rows with missing values or flagged responses (e.g., "Don't know" on political identity) are excluded before simulation.

The agent is constructed from the following individual-level variables:

| Variable | Description | Type |
|---|---|---|
| `age` | Respondent age in years | Numeric |
| `male_dummy` | Gender (1 = Male, 0 = Female) | Binary |
| `tprofile_GOR` | UK Government Office Region (1–13) | Categorical |
| `profile_education_level` | Highest qualification (1–18) | Categorical |
| `tprofile_gross_household` | Annual gross household income band (1–15) | Categorical |
| `ethnicity_R` | Ethnicity (White / Asian / Black / Mixed) | Categorical |
| `parent_dummy` | Parental status (1 = parent, 0 = not) | Binary |
| `Vote2019R` | 2019 General Election vote (1–7) | Categorical |
| `pastvote_EURef` | EU Referendum vote (Remain / Leave / Did not vote) | Categorical |
| `Political_Left_Right` | Self-reported political position (1 = Very left-wing … 7 = Very right-wing) | Ordinal |
| `Selftransc_Val` | Self-transcendence values score (Schwartz) | Continuous |
| `Selfenh_Values` | Self-enhancement values score (Schwartz) | Continuous |
| `Openness` | Openness to change values score (Schwartz) | Continuous |
| `ConformTrad` | Conformity/tradition values score (Schwartz) | Continuous |
| `SDO` | Social Dominance Orientation score | Continuous |
| `EDO` | Environmental Dominance Orientation score | Continuous |
| `RWA` | Right-Wing Authoritarianism score | Continuous |

The coded values are decoded using `PROFILE_DICT` (from `sandbox/ajay_sandbox/survey_dict.py`), and the seven continuous scores are converted to low/moderate/high narrative descriptors via `get_narrative()`. All attributes are then assembled into a first-person **natural-language persona prompt** using `format_persona_from_row()` (from `sandbox/ajay_sandbox/gabm_basic_v1.py`), which the LLM adopts as its identity for the duration of the simulation.

**Persona template (`format_persona_from_row`):**

```python
def format_persona_from_row(row):
    base_persona = (
        f"Demographically, I am a {row['age']}-year-old {row['male_dummy']} living in the "
        f"{row['tprofile_GOR']}, United Kingdom. "
        f"My ethnic background is {row['ethnicity_R']}, and I hold a {row['profile_education_level']}. "
        f"Financially, my gross household income falls into the {row['tprofile_gross_household']} bracket. "
        f"Regarding my family status, I {row['parent_dummy']} a parent. "
        f"Politically, I position myself on the {row['Political_Left_Right']} of the spectrum. "
        f"In the 2019 General Election, I cast my vote for the {row['Vote2019R']}. "
        f"Looking back at the EU Referendum, {row['pastvote_EURef']}."
    )
    full_persona = (
        f"{base_persona}\n\n"
        f"When it comes to my core values and worldview: {selftransc_narrative} {selfenh_narrative} "
        f"{openness_narrative} {conform_narrative} {sdo_narrative} {edo_narrative} {rwa_narrative}"
    )
    return full_persona
```

**Example persona prompt (from real YouGov respondent):**

```
Demographically, I am a 52-year-old Male living in the South East, United Kingdom.
My ethnic background is White, and I hold a GCE A level or Higher Certificate.
Financially, my gross household income falls into the £35,000 to £39,999 per year bracket.
Regarding my family status, I am a parent.
Politically, I position myself on the Slightly right-of-centre of the spectrum.
In the 2019 General Election, I cast my vote for the Conservative Party.
Looking back at the EU Referendum, I voted to Leave.

When it comes to my core values and worldview: I care about the people close to me and
have a basic respect for nature, but I do not actively champion global equality or make
environmental protection a primary, driving life focus. I appreciate personal success and
am capable of taking charge when necessary, but I do not feel a constant need to dominate
decisions or impress others to feel fulfilled. I prefer routine and the familiar, showing
little interest in taking risks or seeking out new adventures. I place a high value on
obedience and maintaining traditional ways of thinking. I generally support fairness but
might implicitly accept that some mild social hierarchies are a natural part of society.
I believe human progress is important but should generally be balanced with environmental
respect. I have a healthy respect for leaders and traditions but maintain some skepticism.
```

### 2.2 Political Group Agents

Two political group agents represent opposing elite voices in the climate policy debate:

- **Political Agent A (Pro-Climate Action):** Generates persuasive messages advocating for climate policies.
- **Political Agent B (Anti-Climate Action):** Generates persuasive counter-messages opposing climate policies.

These agents do not update their opinions — they are fixed message sources. Their messages may be pre-authored or LLM-generated per policy per day, depending on experimental design.

---

## 3. Baseline Measurement (Validation Step)

Before any simulation begins, each citizen agent is administered the **original survey questions** for all 6 target climate policies. The question wording and response scale are identical to the real survey.

**Response scale:** A through G (7-point), mapped numerically:

| Response | Label              | Numeric |
|----------|--------------------|---------|
| A        | Strongly oppose    | -3      |
| B        | Somewhat oppose    | -2      |
| C        | Slightly oppose    | -1      |
| D        | Neutral            |  0      |
| E        | Slightly support   | +1      |
| F        | Somewhat support   | +2      |
| G        | Strongly support   | +3      |

**Target survey questions (from `SURVEY_QUESTIONS` in `sandbox/ajay_sandbox/survey_dict.py`):**

| ID | Column | Policy question |
|----|--------|----------------|
| Q1 | `page5posttreatment6_1` | Please say how much you support or oppose government policies that do the following: **Accelerate the roll-out of renewable energy production** (e.g. more offshore and onshore wind parks) |
| Q2 | `page5posttreatment6_4` | Please say how much you support or oppose government policies that do the following: **Ban new oil/gas/coal licenses** |
| Q3 | `page5posttreatment6_5` | Please say how much you support or oppose government policies that do the following: **Ban the sale of new petrol cars by no later than 2030** |
| Q4 | `page5posttreatment6_7` | Please say how much you support or oppose government policies that do the following: **Mandate that all new housing developments should have non-fossil fuel heating systems, roof-top solar panels, high-level of insulation** |
| Q5 | `page5posttreatment6_9` | Please say how much you support or oppose government policies that do the following: **Impose a carbon tax on fossil fuel sale and distribute the tax revenues to the public** (i.e. carbon fee and dividend) |
| Q6 | `page5posttreatment6_11` | Please say how much you support or oppose government policies that do the following: **Compensate people in other countries who are impacted by climate change** |

Baseline responses are compared against the real respondent's survey answers to assess **persona fidelity** — a calibration check on how well the LLM reproduces the attitudes of the person it represents. Agents with poor fidelity may be flagged or excluded.

---

## 4. Simulation Loop (One "Day" per Iteration)

Each iteration represents a single simulated day. A day consists of **three interaction phases** executed in a configurable order, followed by an **end-of-day survey**.

### 4.1 Interaction Phases

#### Phase P-A: Political Agent A Broadcast

Political Agent A sends a persuasive message about a **target policy** (one of 6) to its connected subset of citizen agents (determined by the network; see Section 6). Upon receiving the message, each exposed citizen agent produces a **private reflection** — a short natural-language paragraph (~100–150 words) describing how the message affected their thinking. The agent does **not** commit to a scale position at this stage.

**Reflection prompt:**

```
You just received the following message: [MESSAGE]

In a few sentences, reflect on how this affects your thinking about [POLICY X].
Do not state a final position — just think out loud.
```

#### Phase P-B: Political Agent B Broadcast

Identical to Phase P-A, but Political Agent B sends a counter-message on the same target policy to its connected subset. Exposed citizens again produce a private reflection.

#### Phase C: Peer Messaging (Citizen-to-Citizen)

Citizens exchange messages with a random subset of their network neighbors (controlled by `k_peers_per_day`). Citizens share their current thinking on the target policy through natural-language messages.

**Update mode: Simultaneous (synchronous).**

All citizen messages are generated based on their **current state** before any reflections occur. This ensures no citizen's updated thinking influences another citizen's message within the same phase, preventing cascade effects.

**Procedure:**

1. **Message generation:** Each citizen generates a message for each selected neighbor, expressing their current thinking on the target policy.
2. **Message delivery:** All messages are collected.
3. **Reflection:** Each citizen who received peer messages produces a private reflection summarizing how the messages affected their thinking.

### 4.2 Phase Ordering

The three phases (P-A, P-B, C) are executed in a **configurable order**, specified as a simulation parameter.

```
phase_order: list[str]  # e.g., ["P-A", "P-B", "C"]
```

All 6 permutations are valid:

| Ordering | Interpretation |
|----------|----------------|
| P-A → P-B → C | Media first, then deliberation (processing model) |
| P-A → C → P-B | A gets peer amplification; B gets recency |
| P-B → P-A → C | B sets the frame; A responds; peers process |
| P-B → C → P-A | B gets peer amplification; A gets recency |
| C → P-A → P-B | Peers prime; political messages are last word |
| C → P-B → P-A | Peers prime; A gets recency advantage |

Phase ordering is treated as an **experimental condition** — the simulation is run multiple times with different fixed orderings, and outcomes are compared across runs. This directly tests whether the sequence of exposure matters for opinion dynamics.

Note: One PA has more resource than the other. More messages from one than other. 

### 4.3 End-of-Day Survey

At the close of each simulated day, every citizen agent is re-administered the **original survey instrument** for the target policy. The question wording and response options (A–G) are identical to the real survey.

The agent's response is recorded as the **official opinion** for that day.

### 4.4 Opinion Shift Calibration (Post-Hoc Clamping)

Real-world evidence (Coppock, *Persuasion in Parallel*) shows that persuasive effects are small — typically a fraction of a scale point, and directionally consistent with the message. To enforce this empirical regularity, a **post-hoc clamping function** limits the maximum opinion shift per day:

```python
def clamp_opinion_shift(previous: int, new: int, max_shift: int = 1) -> int:
    """
    Clamp the opinion shift to a maximum magnitude per day.

    Args:
        previous: Previous day's opinion (-3 to +3)
        new: LLM's raw survey response (-3 to +3)
        max_shift: Maximum allowed shift magnitude (default: 1 scale point)

    Returns:
        Clamped opinion value (-3 to +3)
    """
    shift = new - previous
    clamped_shift = max(min(shift, max_shift), -max_shift)
    return previous + clamped_shift
```

**Design choice:** Shift magnitude is **uniform** — it does not depend on how extreme the agent's prior position is. This keeps the model simple and can be revisited in later iterations.

**Parameter:** `max_shift` is configurable (default: 1). Sensitivity analysis can test values from 0.5 to 2.


Note by AJ:  Quantify reflection in sub-scale of the survey (e.g., 0.1, 0.3) and takes survey every few days.

### 4.5 Day Iteration

The simulation repeats for a defined number of days (`n_days`). Each day may target the same policy or rotate through policies, depending on experimental design.

---

## 5. Opinion Update Mechanism: Hybrid (Reflections + End-of-Day Survey)

### 5.1 Summary

The simulation uses a **hybrid** opinion update mechanism that separates internal reasoning from formal measurement:

- **After each interaction phase** (P-A, P-B, or C): The agent produces a **private reflection** — a natural-language paragraph describing how the interaction affected their thinking. No scale position is committed.
- **At end-of-day only:** The agent receives the formal survey instrument and commits to a response on the A–G scale.

### 5.2 Rationale

- Reflections provide **qualitative micro-data** for understanding mechanisms of influence without forcing premature crystallization.
- The formal opinion is recorded once per day, preserving **ecological validity** and clean comparability with real survey data.
- Reflections serve as **chain-of-thought reasoning**, improving LLM consistency.
- Avoids the **anchoring problem** — the agent hasn't committed to a number mid-day, so it integrates all information holistically.

### 5.3 Persistent Reflections Across Days

All reflections and survey responses **persist across days** in the agent's context, creating agents that accumulate experience over time. This means each agent carries an evolving autobiographical narrative of how its thinking developed.

---

## 6. Memory Architecture: Tiered Memory (Architecture 3)

### 6.1 Overview

To manage context window limits while preserving experiential continuity, the simulation uses a **tiered memory** architecture inspired by cognitive science:

| Time Horizon | Memory Format | Detail Level |
|-------------|---------------|-------------|
| Current day | Full reflections | Maximum — complete text of all reflections |
| Last 2 days | Full reflections | Maximum — retained verbatim |
| Days 3–7 | Daily summaries | Medium — 2–3 sentence LLM-generated summary per day |
| Days 8+ | Weekly summaries | Low — 2–3 sentence summary covering ~5–7 days |

### 6.2 Context Assembly

On any given day, the agent's full context is assembled as:

```
[PERSONA BLOCK]                          ← fixed, from survey data
[WEEKLY SUMMARIES]                       ← days 8+ (heavily compressed)
[DAILY SUMMARIES for days 3–7]           ← medium compression
[FULL REFLECTIONS for last 2 days]       ← retained verbatim
[CURRENT DAY interactions]               ← being generated
[END-OF-DAY SURVEY PROMPT]               ← when measuring opinion
```

All past end-of-day survey scores are also included as a compact list (e.g., "Day 1: C, Day 2: C, Day 3: D, ...") to provide a numerical trajectory alongside the qualitative narrative.

### 6.3 Summarization Process

- **Daily summary:** At the end of each day, an LLM call compresses that day's reflections into a 2–3 sentence summary capturing key attitudinal shifts and reasoning.
- **Weekly summary:** Once daily summaries age past 7 days, they are further compressed into weekly summaries via an additional LLM call.

### 6.4 Persona Drift Mitigation

With persistent memory, there is a risk that accumulated reflections gradually dominate the context, causing the agent to drift from its original persona. Mitigation strategies:

- **Persona reinforcement:** The persona block is placed at both the **beginning and end** of the system prompt to leverage recency and primacy effects in LLM attention.
- **Periodic re-injection:** Every 5 days, key persona attributes are re-stated within the context.
- **Drift monitoring:** Periodically re-administer a neutral baseline question and compare responses to day-0 to quantify drift.

### 6.5 Resource Implications

| Operation | Extra LLM Calls |
|-----------|-----------------|
| Daily summary | 1 per agent per day |
| Weekly summary | 1 per agent per week |

For 200 agents over 30 days: ~6,000 daily summary calls + ~800 weekly summary calls = ~6,800 additional calls (lightweight, short-output calls using a cheaper model if desired).

---

## 7. Network Structure

### 7.1 Design Principles

The network is implemented as a **pluggable component** — the simulation accepts any NetworkX graph object. The network factory takes a type identifier and parameters, returning a configured graph. This allows easy swapping of topologies without modifying simulation logic.

```python
def create_network(network_type: str, params: dict) -> nx.Graph:
    """
    Factory function for creating citizen networks.

    Args:
        network_type: One of "stochastic_block", "erdos_renyi",
                      "watts_strogatz", "barabasi_albert", "custom"
        params: Type-specific parameters (see below)

    Returns:
        A NetworkX Graph with node attributes assigned
    """
```

### 7.2 Default Topology: Stochastic Block Model

The default network is a **Stochastic Block Model** with two blocks representing political clusters. This directly models the echo chamber / cross-cutting exposure phenomenon central to the research question.

**Parameters:**

| Parameter | Description | Default |
|-----------|-------------|---------|
| `n_citizens` | Total population size | 200 |
| `n_blocks` | Number of political clusters | 2 |
| `block_sizes` | Citizens per block | [100, 100] |
| `p_intra` | Connection probability within same block | 0.15 |
| `p_inter` | Connection probability across blocks | 0.02 |

**Polarization knob:** The ratio `p_intra / p_inter` controls the degree of network polarization:

- `p_inter ≈ p_intra` → well-mixed society
- `p_inter ≈ 0` → fully polarized echo chambers
- Intermediate values → realistic partial segregation

### 7.3 Peer Messages Per Day

On each day during Phase C, each citizen does **not** message all network neighbors. Instead, they exchange messages with a random subset of `k` neighbors.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `k_peers_per_day` | Number of peers each citizen exchanges messages with per day | 2–3 |

### 7.4 Alternative Topologies (Future Iterations)

The pluggable design supports future experimentation with:

- **Erdős–Rényi (random):** Equal connection probability for all pairs.
- **Watts-Strogatz (small-world):** Clustered with random long-range ties.
- **Barabási-Albert (scale-free):** Power-law degree distribution with influencer nodes.
- **Empirically derived:** Constructed from survey social network data if available.
- **Custom degree distribution:** User passes a target degree sequence.

---

## 8. Political Exposure (Attribute-Based)

### 8.1 Mechanism

Political agents' broadcast reach is determined by **citizen attributes from the survey data**. This models the empirical reality that media exposure is correlated with political identity.

Assignment logic (configurable, example):

```
Citizens with left-leaning attributes  → connected to Political Agent A (pro-climate)
Citizens with right-leaning attributes → connected to Political Agent B (anti-climate)
Citizens with moderate attributes      → connected to both (or neither)
```

Note by AJ: We should rely on voting history rather than just political leaning.
### 8.2 Exposure Categories

Each citizen is assigned an **exposure category** based on their survey data:

| Category | Receives from A | Receives from B | Typical Profile |
|----------|----------------|----------------|-----------------|
| A-only | Yes | No | Left-leaning, pro-environment media consumer |
| B-only | No | Yes | Right-leaning, skeptical of climate regulation |
| Both | Yes | Yes | Moderate, mixed media diet |
| Neither | No | No | Politically disengaged |

### 8.3 Assignment Function

The specific mapping from survey attributes to exposure category is a configurable function. The default implementation uses political identity and media consumption variables from the survey, but this can be customized per dataset.

```python
def assign_political_exposure(agent_attributes: dict) -> str:
    """
    Determine which political agents' messages this citizen receives.

    Args:
        agent_attributes: Dictionary of survey responses

    Returns:
        One of: "A-only", "B-only", "both", "neither"
    """
```

---

## 9. Simulation Configuration

### 9.1 Master Parameter Table

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `n_citizens` | int | 200 | Number of citizen agents |
| `n_days` | int | 30 | Number of simulated days |
| `target_policies` | list[str] | 6 policies | Which policies are targeted each day |
| `phase_order` | list[str] | ["P-A", "P-B", "C"] | Order of interaction phases per day |
| `max_shift` | int | 1 | Maximum opinion shift per day (clamping) |
| `k_peers_per_day` | int | 3 | Peers each citizen exchanges messages with per day |
| `network_type` | str | "stochastic_block" | Network topology type |
| `p_intra` | float | 0.15 | Within-block connection probability |
| `p_inter` | float | 0.02 | Across-block connection probability |
| `block_sizes` | list[int] | [100, 100] | Citizens per political cluster |
| `memory_architecture` | str | "tiered" | Memory type (tiered / rolling / full) |
| `persona_reinforcement_interval` | int | 5 | Re-inject persona every N days |
| `llm_model` | str | configurable | LLM model identifier (API or local) |
| `llm_temperature` | float | 0.7 | Temperature for LLM generation |
| `random_seed` | int | 42 | For reproducibility |

---

## 10. Data Collection and Output

### 10.1 Primary Output: Opinion Trajectories

For each citizen agent, for each target policy, for each day:

| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | int | Unique citizen identifier |
| `day` | int | Simulation day (0 = baseline) |
| `policy` | str | Target policy identifier |
| `opinion_raw` | str | Raw A–G response from LLM |
| `opinion_numeric` | int | Mapped value (-3 to +3) |
| `opinion_clamped` | int | After post-hoc clamping |

### 10.2 Secondary Output: Reflections

For each citizen agent, for each interaction phase, for each day:

| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | int | Unique citizen identifier |
| `day` | int | Simulation day |
| `phase` | str | "P-A", "P-B", or "C" |
| `reflection_text` | str | Full text of private reflection |
| `messages_received` | list[str] | Messages the agent received in this phase |

### 10.3 Tertiary Output: Network and Configuration Metadata

- Full network graph (edge list + node attributes)
- Simulation configuration (all parameters)
- Political agent messages per day
- Memory summaries generated

### 10.4 Primary Visualization

The main output visualization is a **panel plot** of opinion trajectories:

- **X-axis:** Simulation day (0 to `n_days`)
- **Y-axis:** Opinion score (-3 to +3)
- **Lines:** Individual agent trajectories (semi-transparent) with group-level means overlaid
- **Facets:** By policy, by political exposure group, or by network block
- **Annotations:** Phase ordering condition, key parameter values

---

## 11. Simulation Pseudocode

```
INITIALIZE:
    Load survey data
    For each respondent:
        Create citizen agent with persona prompt
        Assign political exposure (attribute-based)
    Create network (pluggable topology, default: stochastic block model)
    Create Political Agent A (pro-climate)
    Create Political Agent B (anti-climate)

BASELINE (Day 0):
    For each citizen agent:
        Administer original survey (6 policies)
        Record baseline opinions
        Compare to real survey responses (validation)

SIMULATION LOOP (Day 1 to n_days):
    Determine target policy for today
    Determine phase order (from config)

    For each phase in phase_order:
        If phase == "P-A":
            Political Agent A generates message for target policy
            For each citizen connected to A:
                Deliver message
                Citizen produces private reflection
                Store reflection in agent context

        If phase == "P-B":
            Political Agent B generates message for target policy
            For each citizen connected to B:
                Deliver message
                Citizen produces private reflection
                Store reflection in agent context

        If phase == "C":
            For each citizen:
                Select k random neighbors from network
            For each citizen (simultaneous - generate all messages first):
                Generate peer message expressing current thinking
            For each citizen (simultaneous - then deliver and reflect):
                Receive all peer messages
                Produce private reflection on peer messages
                Store reflection in agent context

    END-OF-DAY SURVEY:
        For each citizen agent:
            Administer original survey for target policy
            Record raw LLM response (A–G → -3 to +3)
            Apply clamping: opinion = clamp(raw, previous, max_shift)
            Store clamped opinion as official day-end position

    MEMORY MANAGEMENT:
        For each citizen agent:
            If day > 2: compress day (day - 2) reflections into daily summary
            If day > 7 and day % 7 == 0: compress oldest daily summaries into weekly summary
            If day % persona_reinforcement_interval == 0: re-inject persona attributes

    LOGGING:
        Record all opinions, reflections, messages, and summaries

OUTPUT:
    Save opinion trajectory panel data (agent × day × policy)
    Save reflection corpus
    Save network structure and configuration
    Generate opinion trajectory visualizations
```

---

## 12. Experimental Design (Using This Framework)

The configurable parameters enable several experimental conditions:

### 12.1 Phase Ordering Experiment

Run the simulation 6 times (once per permutation of [P-A, P-B, C]) with all other parameters held constant. Compare opinion trajectories across conditions to test whether exposure order matters.

### 12.2 Network Polarization Experiment

Vary `p_inter` from 0.0 (total echo chambers) to `p_intra` (well-mixed) across runs. Test whether cross-cutting ties moderate or amplify polarization.

### 12.3 Message Strength Experiment

Vary the persuasiveness of political agent messages (e.g., emotional vs. factual framing) and measure differential impact on opinion change.

### 12.4 Calibration Sensitivity

Vary `max_shift` (0.5, 1, 1.5, 2) and compare results to empirical benchmarks from Coppock and other persuasion studies.

---

## 13. Validation Strategy

1. **Persona fidelity (Day 0):** Compare LLM baseline survey responses to real respondent answers. Report accuracy rates and systematic biases.
2. **Aggregate plausibility:** Compare simulated opinion distributions to known population-level distributions from survey data.
3. **Shift magnitude realism:** Verify that clamped opinion shifts fall within empirically observed ranges.
4. **Qualitative validation:** Sample reflections and assess whether reasoning is consistent with the agent's persona and received information.
5. **Robustness checks:** Test sensitivity to LLM temperature, random seed, and model choice.

---

## 14. Future Extensions

- **Hybrid calibration (Approach 3):** Replace post-hoc clamping with the hybrid reasoning + calibrated mapping approach, where the LLM characterizes shift direction/intensity qualitatively and a calibration function maps this to bounded numerical shifts.
- **Prior-dependent shift magnitude:** Make shift limits depend on how extreme the agent's prior position is (empirically motivated by Bayesian updating).
- **Sequential peer updating:** Explore asynchronous Phase C updating to study cascade effects.
- **Multi-policy interaction:** Model how opinions on one policy spill over to related policies.
- **Influencer nodes:** Introduce scale-free network elements or designated opinion leaders.
- **Dynamic networks:** Allow network ties to form and dissolve based on opinion similarity (homophily-driven rewiring).

---

## 15. Implementation Plan

The implementation of this design spec is broken into 10 GitHub issues organised across 5 dependency phases. See [github_issues.md](github_issues.md) for the full issue breakdown, dependency graph, and acceptance criteria.

### v0.2 — MVP Complete

All 10 issues have been implemented and tested (226 tests across 14 test files). Notebooks 01–08 demonstrate each component. The core model architecture described in this specification is fully operational.

### v0.3 — Bias Calibration & Validation

Post-MVP work added the following capabilities without changing the model architecture:

- **Condition B debias** — two-step reasoning + anti-sycophancy preamble in `administer_survey()`, activated via `debias=True`
- **Survey model override** — `survey_model` / `survey_provider` config keys for dual-model runs
- **Anthropic provider** — Claude models in `send_chat()` with extended thinking support
- **Ground truth utility** — `collect_ground_truth()` extracts real YouGov responses for calibration
- **Experiment Runs 1–4** — documented in [result_report.md](result_report.md)

The design spec remains v1.0 — the model architecture is unchanged; v0.3 adds calibration tooling and validation infrastructure.

### v0.4 — Package Communication Mode, Day-0 Anchoring, Memory Refactor

v0.4 adds three changes that extend (and in one place, supersede) the v1.0 design above. Earlier sections of this document have **not** been edited; this entry is the authoritative description of what changed in v0.4.

**1. Package communication mode (extends §4.1).** A new `communication_mode` config key supports `"per_policy"` (the original v1.0 behaviour, default) and `"package"`. In package mode each phase fires once per day rather than once per (day × policy): a single Phase P-A broadcast, single Phase P-B broadcast, and single Phase C peer-message pass each cover all six policies in the package together. Citizen reflections and end-of-day surveys still operate per-policy. New helpers: `compute_package_index()` averages the six policy responses into a single −3..+3 index; `package_index_trajectories` is a new output DataFrame; `collect_package_ground_truth()` mirrors `collect_ground_truth()` at the package level; `PACKAGE_SCOPE` is a sentinel used by `assemble_context()` and the survey path to signal package-level prompts. Package mode is the recommended setting when the research question is the climate-policy package as a whole rather than any individual policy.

**2. Day-0 ground-truth anchoring (extends §3 and §4.3).** A new `day0_anchor` config key selects how Day-0 opinion is initialised, with three modes:

- `"llm_survey"` — original v1.0 behaviour: Day 0 opinion is the LLM's response to the baseline survey.
- `"ground_truth"` — Day 0 opinion is set to the agent's real YouGov response; no LLM call.
- `"ground_truth_with_rationale"` — Day 0 opinion is set to the real YouGov response **and** the LLM is asked to rationalise that position; the rationale text is stored in `survey_reasoning` keyed by `(policy_id, day=0)`.

The dispatcher `_run_day0()` in `sim.py` selects the path. New `SurveyedCitizen` methods `seed_opinion_from_ground_truth()` and `seed_opinion_with_rationale()` implement the two non-`llm_survey` modes. The `debias` flag is silently ignored on Day 0 when an anchor mode is chosen (it still applies to end-of-day surveys). Anchoring lets a Day-0 cohort mean equal the YouGov mean exactly, so any subsequent drift is unambiguously attributable to the simulation dynamics rather than to LLM baseline bias.

**3. Memory anchor refactor (supersedes §6.2).** §6.2 above states that past end-of-day survey scores are concatenated into the prompt as a numeric trajectory (e.g. `"Day 1: C, Day 2: C, Day 3: D, …"`). **In v0.4 this block is removed from `assemble_context()`.** It was the strongest LLM self-consistency cue in the prompt and was anchoring the model on its own prior survey answers rather than letting it integrate the day's reflections. In its place, when `day0_anchor="ground_truth_with_rationale"`, a new block is injected:

```
Your earlier reasoning on these policies:
- {policy short name}: {Day-0 rationale text}
…
```

It is built by `_build_day0_rationales()` and uses only the Day-0 entries from `survey_reasoning`. Later-day rationales are intentionally not surfaced (they would re-introduce a self-consistency cue). When `day0_anchor="llm_survey"` (no rationale generated), the new block is silently empty — equivalent to v1.0 behaviour minus the numeric trajectory. `opinion_history` itself is unchanged on the agent and still drives the data layer / output CSVs / package-index computation; only the prompt-side surfacing is removed.

**Notebooks added.** `notebooks/16_package_mode_sanity_checks.ipynb` exercises package mode at small scale; `notebooks/17_day0_anchoring_smoke_test.ipynb` is the full-stack smoke test combining package mode, `ground_truth_with_rationale` anchoring, debias, extended thinking, and dual-model surveys, with a per-block timing harness used to estimate scaling cost before the headline run.

**Tests.** 315 passing (up from 276) across the new package-mode, anchoring, and memory-refactor test classes.

### v0.4 — Checkpoint and Resume (Operational Addendum)

This addendum is purely operational — it does not change agent behaviour, prompts, or any quantity recorded in the result CSVs. It adds crash-recovery and pause/resume capability to `run_simulation()` so that long, costly runs can survive kernel interrupts, network failures, or schema-compatible config changes without re-spending tokens on already-completed days.

**Two new keyword arguments on `run_simulation(config, nation, ...)`:**

- `checkpoint_dir: Path | None` — directory where per-day snapshots are written. When `None` (default), no checkpointing happens and behaviour is identical to v0.4.
- `checkpoint_every_day: bool = False` — when `True` and `checkpoint_dir` is set, a full snapshot is written after each day completes (after `manage_memory`, before the loop advances).
- `resume: bool = False` — when `True`, `run_simulation` hydrates the supplied `nation` from the checkpoint at `checkpoint_dir` instead of starting from Day 0, and continues the daily loop from `last_completed_day + 1`.

**Checkpoint contents.** A checkpoint is the same set of CSVs that `save_results()` writes (`opinion_trajectories.csv`, `reflections.csv`, `messages.csv`, `daily_summaries.csv`, `survey_reasoning.csv`, `ground_truth.csv`, `package_ground_truth.csv`, `opinion_shares.csv`, plus `package_index_*` in package mode), accompanied by a `checkpoint_meta.json` recording `schema_version`, `last_completed_day`, the `agent_ids` list (sorted by string form via `sorted(..., key=str)` so the on-disk fingerprint is stable across runs whose IDs may be a mix of ints, floats, and strings), the full normalised `config`, a `config_hash` (sha256 of the serialised config), and `written_at`. Note that the derived share CSVs (`opinion_shares.csv`, `package_index_shares.csv`) are written into every per-day checkpoint as well as the final result directory — they are cheap to recompute and are not consumed by `_load_checkpoint`, but writing them on every day means the checkpoint directory is drop-in usable as a result directory if the run is abandoned mid-way. Plot images are not regenerated per day; they are produced once via `save_result_plots()` after the run finishes.

**Atomicity.** Every CSV/JSON write goes through `_atomic_write_csv()` / `_atomic_write_json()`, which writes to `<name>.tmp` in the same directory and then `os.replace()`s into place. A crash mid-write therefore either leaves the previous valid checkpoint intact or the fresh complete one — never a partial file. The smoke test in `notebooks/18_checkpoint_resume_smoke_test.ipynb` asserts there are no `.tmp` files left in the checkpoint directory after either a clean run or an interrupt.

**Resume semantics.** On `resume=True`, `_load_checkpoint()` rebuilds four agent state fields (`opinion_history`, `reflections`, `daily_summaries`, `survey_reasoning`) from CSVs and rebuilds `nation.message_log` from `messages.csv`. A reverse lookup `{str(pid): pid for pid in ALL_CLIMATE_POLICIES}` converts the string-form `policy_id` column back into `ClimatePolicyID` enum members so the rehydrated dictionary keys match the in-memory keys produced by a fresh run (this round-trip equality is what the unit tests verify). Each `pd.read_csv` result is normalised with `df.where(pd.notna(df), None)` before iteration, and `_to_policy()` early-returns `""` for NaN/None/empty cells; without this guard, `str(np.nan)` would propagate as the literal string `'nan'` through `messages.csv` (where `policy_id` is empty in package mode) and poison both `nation.message_log` keys and any downstream resume cycle. **Day 0 is then skipped** — no `_run_day0()` call, no Day-0 LLM token spend — and the loop advances from `last_completed_day + 1` through the configured `n_days`.

**Compatibility checks (`_validate_resume_config`).**

- *Hard-fail keys* (`ValueError` on mismatch): `n_citizens`, `random_seed`, `p_intra`, `p_inter`, `network_type`, `communication_mode`, `package_policies`, `day0_anchor`, plus the agent-ID set itself. These define the world; mixing them across a resume would silently corrupt the trajectory.
- *Days-schedule prefix check*: `cfg["days"][0:last_completed_day]` must equal the same slice of the checkpoint's saved `days` (compared after `_serialise_config` normalisation so policy enums round-trip cleanly). Past days are immutable; future entries may be added or modified, but `len(cfg["days"]) >= last_completed_day` is required.
- *Soft-warn keys*: `llm_model`, `llm_provider`, `survey_model`, `survey_provider`, `debias`, `thinking`, `llm_temperature`. Changes here are logged as warnings and allowed — they support legitimate workflows like swapping in a cheaper model after a baseline day, or upgrading the survey model mid-experiment, while making the change visible in logs.

**Caveat for stochastic models.** Resume restores world state but not the LLM's internal RNG. With `llm_temperature > 0` the post-resume daily trajectory will not be bitwise identical to a from-scratch run with the same seed; it is a statistically equivalent continuation, not a deterministic replay. For exact reproducibility, run end-to-end without checkpointing.

**Validation.** Thirteen unit tests in `tests/test_checkpoint.py` cover round-trip equality, day-numbering continuation, Day-0 skip on resume, hard-fail and warn-only config diffs, missing-checkpoint errors, agent-set mismatch rejection, no `.tmp` leftovers, parameter-validation error paths (e.g. `resume=True` without `checkpoint_dir`), days-schedule prefix-mismatch and shorter-than-checkpoint rejection, and a two-cycle package-mode resume that asserts no literal `'nan'` strings appear in any string column of `messages.csv` after the second checkpoint. `notebooks/18_checkpoint_resume_smoke_test.ipynb` is the end-to-end smoke test: it runs with `checkpoint_every_day=True`, supports a manual kernel interrupt, inspects the partial checkpoint, exercises the negative-test path, then resumes from a fresh nation and asserts full day coverage `0..N_DAYS`.

**Tests.** 328 passing (up from 315).

---

### v0.5 — Local LLM Provider (Operational Addendum)

Like v0.4's checkpoint addendum, v0.5 is purely operational — agent behaviour, prompts, and CSV semantics are unchanged. v0.5 promotes NB 24's in-notebook monkey-patch into a first-class fourth provider in [src/cag/io/llm.py](../src/cag/io/llm.py) so that any locally-hosted, OpenAI-compatible model (mlx-lm, Ollama, vLLM, sglang, llama.cpp) can be used as a drop-in replacement for the cloud `openai` / `genai` / `anthropic` providers without modifying any call site.

**`provider="local"` dispatcher branch.** `send_chat(..., provider="local")` routes through a new `_send_local()` that uses the `openai` SDK with a configurable `base_url` (any OpenAI-compatible server). The dispatcher reads its base URL, timeout, and per-model defaults from a module-level `_LOCAL_CONFIG` populated once per run by `configure_local(base_url=..., extra_body=..., timeout_s=...)`. This avoids touching the dozens of `send_chat` call sites in `agent.py` / `environment.py` — they keep passing `provider="local"` with no other change. Resolution order for the base URL is: `configure_local()` argument → `CAG_LOCAL_BASE_URL` environment variable → the built-in default `http://localhost:8080/v1`. Timeout follows the same chain via `CAG_LOCAL_TIMEOUT_S`.

**No-API-key short-circuit.** `load_api_key("local")` returns the sentinel string `"not-needed"` without consulting `data/api_key.csv` or any environment variable. Local servers reject `Authorization` headers from some clients if absent, so the OpenAI SDK still receives a non-empty key, but no real credential is read or stored.

**`_MODEL_REGISTRY` — substring-keyed per-family defaults.** A list-of-dicts registry maps model-name substrings to recommended sampling, `max_tokens`, and (for Qwen3) the `enable_thinking` chat-template kwarg. Currently registered families: Qwen3 (4B / 8B / 14B / 32B), Llama 3.1/3.2, Apertus, Mistral, DeepSeek-R1-Distill. Unknown models log an INFO line on first use and fall back to caller-supplied or library-default sampling. User-supplied `extra_body` always overrides the registry, so workflow-specific overrides remain possible.

**Empty-thinking-truncation guard.** Some local backends return an empty `content` field when a thinking-mode response is truncated at `max_tokens` while the model is still inside `<think>…</think>`. `_send_local()` detects this and retries once with `enable_thinking=False` plus the non-thinking sampling preset and `max_tokens` budget. Non-thinking empties are not retried (they indicate a real generation failure to surface). This is generic across any registered model with a `thinking_extra_body` lambda; today only Qwen3 has one.

**`ping_local()` startup health-check.** `_resolve_runtime` in [src/cag/abm/sim.py](../src/cag/abm/sim.py) calls `ping_local()` once at simulation start when `llm_provider=="local"` (or `survey_provider=="local"`). It issues a GET to `<base_url>/models` and raises a remediation-tagged exception if the server is unreachable, so a misconfigured run fails in the first second instead of after the first agent call.

**Three new SIM_CONFIG keys.**

- `local_base_url: str | None = None` — passed to `configure_local()` at start; falls back to env var, then default.
- `local_extra_body: dict | None = None` — global override applied to every local call (e.g. force a specific sampler).
- `local_timeout_s: float | None = None` — per-call HTTP timeout for the local server.

All three are added to `_RESUME_SOFT_KEYS`: changing them mid-experiment (e.g. swapping the local server's port between days) is allowed and logged.

**Mixed providers.** Because `survey_provider` / `survey_model` are independent of `llm_provider` / `llm_model`, a run can use, for example, a local Qwen3 for messaging and reflections while routing surveys to GPT-4o-mini in the cloud, or vice versa. `configure_local()` is invoked when either provider is `"local"`.

**Validation.** [tests/test_llm_local.py](../tests/test_llm_local.py) adds 26 unit tests (mocked `openai.OpenAI`, no live server required) covering: dispatcher routing, base-URL / timeout resolution priority chain, registry substring matching across all five registered families, registry sampling and `max_tokens` injection (with caller and user-`extra_body` precedence rules), Qwen3 thinking on/off behaviour, empty-thinking retry trigger and non-trigger, `load_api_key("local")` short-circuit, and unsupported-provider error message coverage. The full suite is **365 passing, 1 skipped, 0 failures** (up from 339).

**End-to-end parity.** [notebooks/25_local_llm_integrated_smoke.ipynb](../notebooks/25_local_llm_integrated_smoke.ipynb) re-runs NB 24's exact configuration (10 agents × 1 day Ban Petrol Cars, Qwen3 8B 4-bit, `debias=True`, `thinking=True`, seed 42) through the integrated provider. Headline metrics match NB 24 bit-for-bit (Day-0 bias +0.50, Day-1 ρ +0.76, reflections median 135.5 tokens, 59 % mention rate, 0 errors, 0 thinking-empty retries) — see [result_report.md](result_report.md) for the full comparison table.

**Documentation.** A V3 quickstart-first rewrite of [docs/Local_LLM_Setup_Guide.md](Local_LLM_Setup_Guide.md) covers mlx-lm, Ollama, vLLM, sglang, and llama.cpp; a model gallery lists licenses, RAM footprints, and registered status; a registry-extension recipe shows how to add a new model family without code changes outside `_MODEL_REGISTRY`; troubleshooting covers server-unreachable, empty-thinking, OOM, and HPC scenarios. The legacy V2 (mlx-only) and V1 (Qwen 2.5) sections are retained below the V3 section as historical reference. Optional dependencies are pinned in [requirements-local.txt](../requirements-local.txt).

---

## 16. Parallelization Plan (Backlog)

Status: **planning only — not yet implemented.** This section is a working note to seed a future GitHub issue. Append-only; revise via additions below rather than edits in place.

### 16.1 Motivation

Wall-time is dominated by blocking LLM HTTP calls made one agent at a time. For a single day with `N` agents and the default `["P-A", "P-B", "C"]` phase order, the runner issues roughly `N × (1 + 1 + 2 + 1 + 1)` sequential calls (P-A reflect, P-B reflect, peer message gen + receive-reflect, end-of-day survey, manage_memory). With `debias=True` the survey doubles. At `N=30` and ~3 s/call this is ~10 minutes/day; at `N=200` it is over an hour/day. The work is I/O-bound, not CPU-bound.

### 16.2 Where parallelism is safe

The model already uses **phase barriers** as the synchronisation primitive. Within a single phase, every per-agent operation reads a frozen snapshot and writes only to its own state, so the operations commute. Parallelism is therefore safe **inside a phase**, never across phases or days.

| Site | Per-agent op | Parallelisable | Notes |
|---|---|---|---|
| Day-0 baseline survey | `administer_survey(day=0)` or `seed_opinion_with_rationale` | yes | fully independent |
| Day-0 ground-truth seeding | `seed_opinion_from_ground_truth` | n/a | no LLM calls |
| Phase P-A | `receive_political_message` | yes | broadcast is shared input |
| Phase P-B | `receive_political_message` | yes | as P-A |
| Phase C step 1 | `generate_peer_message` | yes | reads pre-phase state |
| Phase C step 2 | `receive_peer_messages` (reflection) | yes | requires step 1 barrier |
| End-of-day survey | `administer_survey(day=N)` | yes | independent |
| `manage_memory` | summarisation calls | yes | independent |

What is **not** safe: parallelising across days (causal dependency), or collapsing the three sub-steps of `run_peer_messaging` (they are an explicit barrier).

### 16.3 Recommended first cut — `ThreadPoolExecutor` over agents

Because the bottleneck is HTTP wait, a thread pool gives near-linear speedup up to the provider rate-limit ceiling. Plan:

- Add a config key `max_concurrent_agents: int = 1` (default preserves current sequential behaviour).
- Wrap the per-agent loops in [src/cag/abm/environment.py](src/cag/abm/environment.py) (`administer_survey`, `run_broadcast`, the two non-barrier sub-steps of `run_peer_messaging`) and the `manage_memory` loop in [src/cag/abm/sim.py](src/cag/abm/sim.py) with a single shared `ThreadPoolExecutor(max_workers=cfg["max_concurrent_agents"])`.
- Provider SDKs (`openai`, `anthropic`, `google-genai`) are thread-safe per client.
- Keep the phase barriers explicit: each `executor.map(...)` call must complete before the next phase begins.

Expected speedup: roughly `min(N_agents, max_workers, rate_limit_ceiling)`. A starting point of 8–16 workers is reasonable for OpenAI tier-1.

### 16.4 Caveats and mitigations

- **Rate limits.** The existing `_resilient_call` in [src/cag/io/llm.py](src/cag/io/llm.py) handles 400-class param errors; it does not yet do 429 backoff with jitter. Add bounded exponential backoff before turning concurrency on in production.
- **Determinism.** Order of completion will vary; logging will interleave. Any per-agent RNG must be seeded at agent construction (already the case). For exact reproducibility, use `max_concurrent_agents=1`.
- **Logging volume.** The per-agent `INFO` lines in the survey loop will interleave. Consider buffering per-agent log lines and flushing at the phase barrier.
- **Checkpoint interaction.** The atomic write in `_atomic_write_csv` happens once per day, after the `manage_memory` barrier — concurrency inside a phase does not affect checkpoint integrity.
- **Cost.** Concurrency reduces wall-time, not token spend. Pair with the OpenAI Batch API (see 16.5) for cost reduction.

### 16.5 Stretch options (larger refactors)

1. **Async clients.** `openai.AsyncOpenAI` / `anthropic.AsyncAnthropic` give the same throughput as threads with lower overhead and cleaner cancellation. Requires converting `send_chat` and the per-agent methods to `async def` and replacing per-phase loops with `asyncio.gather`. Worth it past ~100 agents.
2. **Batch API for end-of-day survey.** Phase C survey calls are independent and have no dependent follow-up that day — ideal for OpenAI / Anthropic Batch APIs. ~50 % cheaper, very high throughput, at the cost of minutes of submission latency. Suitable for offline runs.
3. **Pre-fetched political messages.** P-A and P-B broadcast generation can run once at the top of each day in parallel (two calls, independent), removing them from the critical path.

### 16.6 Explicitly out of scope

- **Multiprocessing.** Pickling `SurveyedNation` and the agent graph dwarfs any benefit; the workload is I/O-bound. Threads win.
- **Cross-day parallelism.** Breaks causality.
- **Distributed runners.** Unjustified for current N; revisit if `N_citizens` exceeds 1 000.

### 16.7 Suggested issue scope (MVP for the team)

A single PR-sized first step:

1. Add `max_concurrent_agents` to `SIM_CONFIG`; default 1.
2. Introduce one helper `_parallel_for_agents(executor, agents, fn)` in `sim.py` and route the four phase loops through it.
3. Add 429 backoff with jitter to `_resilient_call`.
4. Add a smoke notebook that runs the same config at `max_concurrent_agents ∈ {1, 4, 8}` and reports wall-time + cost + Day-N opinion-mean drift (should be statistically indistinguishable across settings).

Acceptance: existing 325 tests pass at `max_concurrent_agents=1`; new wall-time test asserts ≥3× speedup at `max_workers=8` for a 30-agent / 3-day run; opinion trajectory means agree within Monte-Carlo noise.

---

*Specification version 1.0 — produced during iterative design session.*
*All design decisions are documented and configurable for experimental variation.*



## 17. Pluggable Peer-Network Factory (v0.5, 2026-05-14)

### 17.1 Motivation

Through v0.4 the peer network was a single hard-coded 2-block stochastic block
model (SBM) driven entirely by `political_exposure`, exposing only `p_intra`
and `p_inter` as knobs. That bakes in three structural assumptions: (i)
exposure category is the only homophily axis, (ii) the degree distribution
is approximately Poisson, and (iii) there are no hubs and no clustering
beyond what the block structure produces. These assumptions silently constrain
exactly the dynamics the project wants to study (echo chambers, tipping,
asymmetric reach by hubs), so the network model is promoted to a **first-class
configurable component** with a registry of alternative topologies and a
shared structural-diagnostics report.

This is **not** a change to the broadcast contact structure (Priority 2 in the
current planning cycle); only the peer-messaging graph.

### 17.2 Design decisions (locked-in this cycle)

1. **Five network types ship in v0.5**: `stochastic_block` (default,
   back-compat), `erdos_renyi`, `watts_strogatz`, `barabasi_albert`,
   `homophily_weighted`. Barabási–Albert is included from the start because
   hub effects are central to upcoming reach-asymmetry experiments.
2. **Raw parameters are exposed**, no auto-tuning of density. The
   experimenter chooses the knobs per type; comparability across types is
   reported via the diagnostics block, not enforced at construction time.
3. **Homophily-weighted similarity** uses a config-controlled subset of
   citizen attributes (default `["ukge2019_vote_id", "brexit_vote_id",
   "region_id"]`). The day-0 climate-opinion vector is **excluded by default**
   to avoid conflating with day-0 anchoring; experimenters may add it.
4. **Diagnostics are always on** but bounded. Cheap structural metrics
   always run; clustering / shortest-path / diameter run under per-metric
   size caps **and** a single wall-clock cap (`diagnostics_timeout_s`,
   default 30 s). On timeout, partial results are saved with
   `"timed_out": true` rather than aborting the run.
5. **Back-compat is preserved.** Legacy flat keys `p_intra`, `p_inter`
   continue to work for `stochastic_block`; legacy
   `nation.create_network(p_intra=..., p_inter=...)` calls continue to work
   with a `DeprecationWarning` in the log.

### 17.3 Network types (as built)

| `network_type` | Builder | Parameters (raw, no tuning) | Notes |
|---|---|---|---|
| `stochastic_block` | `nx.stochastic_block_model` | `p_intra` (def 0.15), `p_inter` (def 0.02) | 2 blocks driven by `political_exposure`; swing round-robin. Identical to the v0.4 implementation. |
| `erdos_renyi` | `nx.erdos_renyi_graph` | `p` (def 0.05) | Null model: no homophily, no clustering, no hubs. |
| `watts_strogatz` | `nx.watts_strogatz_graph` | `k` (even int, def 6), `beta` (def 0.10) | Small-world: high clustering + short paths. Probes echo-chamber strength. |
| `barabasi_albert` | `nx.barabasi_albert_graph` | `m` (def 3) | Scale-free / preferential attachment; hubs. Important for asymmetric-reach experiments. |
| `homophily_weighted` | custom | `attributes` (list, default above), `weights` (list, default uniform), `scale` (def 6.0), `threshold` (def 3.0) | Edge prob = `sigmoid(scale·sim − threshold)`; per-attribute similarity is 1/0 for categorical and `1 − normalised distance` for numeric. Larger threshold ⇒ sparser graph. |

All builders return an `nx.Graph` whose nodes are agent IDs, so
`assign_network_blocks()` is unchanged and topology-agnostic.

### 17.4 Diagnostics

A single `compute_diagnostics(G, agents, timeout_s)` entry point produces
one JSON record saved as `<run_dir>/network_diagnostics.json`.

**Always reported** (cheap, O(n + m)):
- `n_nodes`, `n_edges`, `density`
- `mean_degree`, `median_degree`, `max_degree`, `degree_histogram` (20 bins)
- `n_connected_components`, `largest_component_size`
- `assortativity_political_exposure` (categorical)

**Conditional, capped:**
- `average_clustering` — skipped if `n > 5000`.
- `average_shortest_path_length` — skipped if `n > 2000`; on disconnected
  graphs computed on the largest CC; if the CC has > 500 nodes, estimated
  from 500 sampled source nodes (recorded in the `_note` field).
- `diameter` — skipped if `n > 2000` or largest-CC `n > 2000`.
- A single wall-clock guard (`diagnostics_timeout_s`, default 30 s,
  POSIX `SIGALRM`) wraps the whole conditional block; on expiry, the
  record carries `"timed_out": true` and partial fields are kept.
- Skipped metrics carry `<name>_skipped_reason`.

The trailing `elapsed_s` field records wall time so anomalies are
auditable.

### 17.5 Configuration surface

New / changed `SIM_CONFIG` keys:

| Key | Type | Default | Meaning |
|---|---|---|---|
| `network_type` | str | `"stochastic_block"` | One of the five registered types. |
| `network_params` | dict \| None | `None` | Per-type parameters; defaults applied if `None`. |
| `diagnostics_timeout_s` | float | `30.0` | Wall-clock cap for the conditional metrics block. `0` / `None` disables the wall-clock guard; per-metric size caps still apply. |

**Back-compat:** `p_intra`, `p_inter`, and `block_sizes` remain in
`SIM_CONFIG` and are folded into `network_params` when
`network_type == "stochastic_block"` and the new dict does not already
specify them.

**Resume contract:** `network_params` is added to `_RESUME_HARD_KEYS`
alongside the existing `network_type`, `p_intra`, `p_inter`. Changing it
across a resume aborts.

### 17.6 Code structure

- **New module** `src/cag/abm/networks.py`
  - `NETWORK_TYPES`, `DEFAULT_HOMOPHILY_ATTRIBUTES`
  - `build_network(network_type, agents, params, seed) -> nx.Graph`
  - `compute_diagnostics(G, agents, timeout_s) -> dict`
- **Refactored** `SurveyedNation.create_network()` is a thin dispatcher
  delegating to `build_network`; legacy `p_intra` / `p_inter` / `n_blocks`
  kwargs trigger `DeprecationWarning`. Stores `self.network_type` and
  `self.network_params` for diagnostics.
- **`sim.py`** adds `_resolve_network_params()` and
  `_safe_network_diagnostics()`; `_collect_results` attaches the
  diagnostics dict to the results, and `save_results` writes
  `network_diagnostics.json` next to `config.json`.
- **`tests/test_networks.py`** — 17 new tests covering every builder,
  invalid-parameter paths, seed reproducibility, perfect-homophily
  separation, dispatch through `SurveyedNation`, legacy-kwargs
  back-compat, and the diagnostics surface (basic keys, assortativity,
  disconnected graphs, timeout disabled).
- **Demo notebook** `notebooks/26_network_factory_demo.ipynb` — builds
  all five types on the same 80-agent synthetic set, prints diagnostics
  side-by-side, and renders graph layouts + degree histograms.

### 17.7 Test status

- 382 passed, 1 skipped (was 365 / 1) — 17 new tests, no regressions.
- All five builders produce reproducible graphs at fixed `seed`.
- Demo notebook executes end-to-end; visuals confirm expected structural
  signatures (two communities for SBM and homophily, hubs for BA,
  ring + shortcuts for WS, noise for ER).

### 17.8 Out of scope (deferred)

- **Degree-corrected SBM, multiplex / two-layer graphs, configuration
  model, latent-space embeddings.** All flagged in the planning thread;
  not required for the current research questions and easy to add later
  via the same factory.
- **Auto-tuned density / mean-degree calibration** so different topologies
  share a target degree. Decided against this cycle (raw parameters were
  preferred); the diagnostics report makes mismatches explicit instead.
- **Broadcast contact structure** (Priority 2). Still uses
  `political_agent.connected_citizens` filtered by `audience_cap` and
  `reach_a` / `reach_b`; the network factory does **not** touch it.

---

## 18. Broadcast-Audience Assignment: Multi-Mode Rule + Calibration (v0.5, 2026-05-14)

### 18.1 Purpose and scope

This section specifies an upgrade to how each citizen is sorted into
one of four political-exposure cells — `A-only`, `B-only`, `both`,
`neither` — that decide who receives each political agent's broadcast
messages.

The upgrade has two independent parts:

- **Phase A — three named assignment rules behind a `mode` switch.**
  The existing 10-priority chain (kept frozen for back-compat) plus a
  new signal-counting rule (the new default) plus a truly-random
  baseline rule.
- **Phase B — optional resampling-calibration layer.** Sub-samples the
  YouGov pool so the realised four-cell marginals match a target
  distribution. Applies on top of `rule_priority_chain` or
  `rule_signal_count`; ignored under `rule_random` (which hits any
  marginals directly).

The function `assign_political_exposure()` in
[`src/cag/abm/environment.py`](../src/cag/abm/environment.py) **keeps
its name** (so existing notebooks continue to work). It becomes a
dispatcher that takes a `mode` argument and delegates to one of three
implementations.

Nothing about the political agents, broadcast prompt, message-delivery
loop, end-of-day survey, peer messaging, or the peer-network factory
in §17 changes — only **which citizens land in which cell**.

The supporting empirical evidence sits in
[`docs/Literature_Political_Exposure.md`](Literature_Political_Exposure.md).

> **Status (2026-05-14):** design only. No code, tests, or notebooks
> in this section yet. The `rule_random` mode in §18.6 is flagged for
> a team-discussion review before implementation; see §18.12.

### 18.2 Why the current rule needs to change

The current `assign_political_exposure()` is a 10-step priority chain
over `(brexit_vote_id, ukge2019_vote_id, politics_id)`. It conflates
three conceptually distinct questions under one routing logic:

1. **Engagement** — does this person attend to political messaging at all?
2. **Identity** — if engaged, which side?
3. **Topic relevance** — does this person attend to *climate*
   messaging specifically?

Two consequences are visible in the data. Measured on the full YouGov
pool (`YouGovProcessedData.csv`, N = 1483) on 2026-05-14:

| Cell      | Count | Share  |
|-----------|------:|-------:|
| `A-only`  |   405 | 27.31% |
| `B-only`  |   285 | 19.22% |
| `both`    |   725 | **48.89%** |
| `neither` |    68 |  **4.59%** |

A-audience (`A-only ∪ both`) = 76.2 %; B-audience (`B-only ∪ both`)
= 68.1 %; structural asymmetry ≈ +8 pp in agent A's favour.

Two structural problems:

1. **`both` is a residual catch-all (~49 %).** Rules 5–9 of the chain
   route any citizen with a *single-direction* signal (e.g. Leave +
   "don't know" GE2019; or "don't know" Brexit + Conservative GE2019)
   into `both`, even though that signal points unambiguously one way.
   The cell stops meaning "engaged with cross-cutting content" and
   starts meaning "anything we couldn't cleanly classify".
2. **`neither` is implausibly small (~5 %).** UK survey evidence
   (Reuters Institute *Digital News Report*, Hansard *Audit*, climate
   audience-segmentation work) puts the genuinely depoliticised /
   news-avoidant share at ~35–50 % — see lit doc §2–§4. Almost every
   YouGov respondent has *some* political signal in *some* dimension
   because YouGov recruits politically engaged panellists by design;
   the rule's catch-all then absorbs them into `both`.

Problem (1) is a **rule-design** problem and is fixed by Phase A
(`rule_signal_count`). Problem (2) is a **panel-selection** problem
that no rule can fix on its own — it needs Phase B's resampling
calibration to drop politically-engaged respondents in proportion.

### 18.3 Locked design decisions

The decisions below were taken in the planning thread of 2026-05-14
and are fixed for the v0.5 implementation cycle.

1. **Three named rules, default `rule_signal_count`.** No "legacy"
   label — all three are first-class, documented modes. The renaming
   is deliberate: in six months "legacy" will mean nothing to a new
   reader, but `rule_priority_chain` describes how the rule actually
   works.
2. **`rule_priority_chain` is frozen.** Kept identical to the current
   2026-04 implementation, byte-for-byte. Used for reproducing
   pre-v0.5 results. Any future rule changes go into a new mode, not
   into `priority_chain`.
3. **Symmetric political reach is the *target* default for Phase B.**
   When Phase B is enabled with no explicit `targets`, the dict used
   is `{A-only: 0.225, B-only: 0.225, both: 0.20, neither: 0.35}` —
   symmetric A vs B, lit-grounded `neither`. Asymmetric scenarios
   (e.g. UK-realistic `B-only > A-only`) are explicit overrides, not
   the default.
4. **Phase B is opt-in on rule modes.** With `political_exposure_targets
   = None` (the default), Phase B does nothing and the rule's natural
   marginals stand. With a target dict supplied, the resampling layer
   runs after Phase A.
5. **`rule_random` is mutually exclusive with Phase B resampling.**
   It hits any marginals directly in one shot; there is nothing to
   resample. `political_exposure_targets` is *required* under
   `rule_random`.
6. **Replication regime defaults to "fixed counts, individuals vary".**
   Each of K replications draws fresh individuals while keeping the
   four cell *counts* equal to their targets. A "multinomial counts"
   regime where counts also jitter is available as opt-in for
   uncertainty audits. Applies to both `rule_random` label-assignment
   and Phase B resampling.

### 18.4 Mode `rule_priority_chain` (frozen)

The existing 10-rule priority chain documented in §6. Implementation
is moved out of `SurveyedNation.assign_political_exposure()` into a
private helper `_assign_priority_chain()` in
`src/cag/abm/exposure.py` but remains byte-equivalent. Used to
reproduce all pre-v0.5 results.

Realised marginals on full YouGov pool (measured 2026-05-14):
A-only 27.3 %, B-only 19.2 %, both 48.9 %, neither 4.6 %.

### 18.5 Mode `rule_signal_count` (new default)

The new rule replaces the priority chain with a symmetric
signal-counting procedure. For each citizen:

```text
LEFT_SIGNALS  = (Brexit == REMAIN)
              + (GE2019 in {Labour, Green, LibDem})
              + (politics_id in {very-left, fairly-left, slightly-left})

RIGHT_SIGNALS = (Brexit == LEAVE)
              + (GE2019 in {Conservative, Brexit Party})
              + (politics_id in {slightly-right, fairly-right, very-right})

ENGAGED       = (Brexit not in {DK, Unknown})
             OR (GE2019 not in {DK, Unknown, Other})
             OR (politics_id not in {DK, Unknown})
              # politics_id == CENTRE (4) counts as engaged

cell = "neither"               if not ENGAGED
     = "A-only"                if LEFT_SIGNALS > 0 and RIGHT_SIGNALS == 0
     = "B-only"                if RIGHT_SIGNALS > 0 and LEFT_SIGNALS == 0
     = "both"                  otherwise
                               # cross-pressured (Leave+Lab, Remain+Con, ...)
                               # OR engaged-with-no-direction (centre, Other)
```

> **Provisional CENTRE routing (pending §18.12 Q2).** Citizens with
> `politics_id == CENTRE` and no resolvable Brexit / GE2019 vote contribute
> zero to both `LEFT_SIGNALS` and `RIGHT_SIGNALS`, so the `otherwise` branch
> routes them to `both`. This is the working resolution of §18.12 Q2; the
> alternative is to route them to `neither` (treat "engaged-but-centred"
> as a non-audience). The team review of §18.12 will confirm or revise this
> before the implementation lands.

#### 18.5.1 Defensibility (the conceptual case)

- **`A-only` and `B-only` aggregate strong-and-weak directional
  signals into one cell.** A "Remain + Labour + politics=2" citizen
  and a "Remain + DK + DK" citizen both end up in `A-only`. Both
  legitimately lean left; the strength difference is real and
  recoverable downstream as a covariate, but does not justify a cell
  boundary. (The current chain instead routes the second citizen into
  `both`, which is what makes `both` a dustbin.)
- **`both` is reserved for genuine cross-pressure or engaged-no-direction.**
  Cross-pressured = signals point *both* ways (Leave + Labour, Remain
  + Conservative). Engaged-no-direction = explicit centrist
  (`politics_id == CENTRE`) with no resolvable vote, or "Other" GE2019
  voter with no other signal. The lit (Dubois & Blank 2018; Eady
  et al. 2019) supports treating these as the cross-cutting-content
  audience.
- **Engagement uses revealed behaviour, not ideological extremity.**
  We considered an "engagement = distance from centre" axis and
  rejected it: a passionate centrist Lib Dem activist is engaged but
  central, and a disaffected partisan can be politically marginal.
  Engagement and extremity are independent dimensions in every UK
  survey series we trust. The boundary that *does* work is "did this
  person give us any non-DK signal at all?" — which is identical to
  the existing rule's `neither` boundary, deliberately.

#### 18.5.2 Realised marginals on YouGov (measured 2026-05-14)

| Cell      | `priority_chain` | `signal_count` |
|-----------|----------------:|---------------:|
| `A-only`  | 27.3 %          | **41.9 %**     |
| `B-only`  | 19.2 %          | **28.2 %**     |
| `both`    | **48.9 %**      | **25.3 %**     |
| `neither` | 4.6 %           | 4.6 %          |
| A-audience| 76.2 %          | 67.2 %         |
| B-audience| 68.1 %          | 53.5 %         |
| A − B asymmetry | +8.1 pp   | **+13.8 pp**   |

Three honest observations:

1. **`both` drops from 49 % → 25 %**, exactly as designed. This is
   the headline win of `rule_signal_count`.
2. **`neither` is unchanged at 4.6 %.** The engagement boundary is
   unchanged by design, so YouGov's panel-selection bias still binds.
   This is a Phase B problem, not a rule problem.
3. **A-vs-B asymmetry *increases* from +8 pp to +14 pp.** The
   priority chain was hiding single-direction Remainers in `both`;
   the new rule places them correctly in `A-only`, which makes the
   YouGov panel's underlying Remain skew newly visible. Phase B is
   needed to re-symmetrise if a symmetric baseline is wanted.

#### 18.5.3 Per-replication variability at N = 100 (`signal_count`)

Sub-sampling N = 100 from the 1483-row pool, five seeds:

| seed  | A-only | B-only | both | neither |
|------:|-------:|-------:|-----:|--------:|
| 42    | 38     | 26     | 34   | 2       |
| 7     | 44     | 32     | 20   | 4       |
| 123   | 50     | 26     | 21   | 3       |
| 2024  | 37     | 29     | 28   | 6       |
| 9999  | 47     | 19     | 31   | 3       |

Cell counts swing by ±5 across seeds, which is the binomial sampling
noise we expect at N = 100. `neither` remains tiny in every replication.

### 18.6 Mode `rule_random` (truly random; baseline / null model)

> **Status:** scoped here for documentation; flagged for team review
> before implementation (§18.12 Q3).

> **Reading note on `neither` (applies to all three rules).** The
> `neither` cell means "receives no direct *broadcast* from either
> political agent on a given day" — it does **not** mean "receives no
> political or climate information at all". `neither` citizens still
> participate in peer messaging, the end-of-day survey, memory
> updates and everything else. The lit-supported 35–45 % share is for
> this *no-broadcast-receipt* reading; the genuinely
> information-isolated share is ~2–9 %. See
> [`Literature_Political_Exposure.md`](Literature_Political_Exposure.md)
> §6.2 for the distinction and §18.14 below for why YouGov-`neither`
> respondents are an imperfect proxy for the genuinely disengaged.

A pure stratified-label assignment rule. Cell labels are assigned to
citizens by RNG, conditional on a target proportions dict and a
count-regime. The per-citizen `(brexit, ge2019, politics_id)` triple
is **not consulted**.

```text
inputs:
  citizens         : list of agents (length n_agents)
  targets          : dict[cell -> proportion]  (sums to 1.0)
  count_regime     : "fixed" | "multinomial"
  seed             : int

steps:
  1. Compute cell counts:
       if count_regime == "fixed":
         n_c = round(targets[c] * n_agents)
         (largest-remainder rounding so sum(n_c) == n_agents)
       else:
         (n_A, n_B, n_both, n_neither) ~ Multinomial(n_agents, targets)
  2. Build a label vector of length n_agents:
       [A-only] * n_A + [B-only] * n_B + [both] * n_both + [neither] * n_n
  3. RNG-shuffle the label vector with the given seed.
  4. Assign labels to citizens in agent_id-sorted order so the mapping
     is reproducible across replications that share a seed.
```

#### 18.6.1 What `rule_random` is for

A **null-model control** for the rule itself. If a research finding
survives swapping `rule_signal_count` → `rule_random` *at matched
marginals*, the result is driven by the **population mix** (cell
counts) and not by *which specific individuals were where*. If it
doesn't survive, the per-individual signal mattered — also
publishable. This control is methodologically valuable and difficult
to construct any other way.

#### 18.6.2 What `rule_random` is *not* for

`rule_random` cannot support per-individual claims. A citizen whose
voting record screams "left" can land in `B-only` purely by RNG. Do
not use this mode to claim "Reform's natural audience"; do not
interpret cell membership as anything other than a randomly-assigned
treatment label.

#### 18.6.3 Open variants (deferred to team discussion)

Two restricted-random variants are flagged for §18.12 review and
**not** implemented in the first pass:

- *Random-conditional-on-engagement*: assign `neither` strictly to
  citizens with no political signal (so the engagement boundary is
  preserved); randomly distribute the engaged remainder across A-only
  / B-only / both at the requested proportions.
- *Random-conditional-on-Brexit*: RNG-assign within Leavers and
  Remainers separately so the Brexit-vote signal is preserved while
  GE2019 and politics_id are ignored.

Both are softer middle grounds between full `rule_random` and full
`rule_signal_count`. The first-pass implementation ships only the
fully-random version; variants are added if the team discussion
endorses them.

### 18.7 Phase B: Optional resampling-calibration layer

When `political_exposure_targets` is supplied under
`rule_priority_chain` or `rule_signal_count`, Phase B sub-samples the
YouGov pool so the realised four-cell marginals match the target
distribution. Algorithm:

```text
inputs:
  nation                : SurveyedNation, agents_active fully populated
  rule                  : the chosen Phase A rule
  targets               : dict[cell -> proportion]  (sums to 1.0)
  n_agents              : desired post-calibration agent count
  count_regime          : "fixed" | "multinomial"
  seed                  : int

steps:
  1. Run the Phase A rule on the full pool.
  2. Group citizens by realised cell -> pools[cell].
  3. Compute target counts per §18.5 / §18.6 rounding.
  4. For each cell c:
       if n_c <= len(pools[c]):
         draw n_c citizens uniformly without replacement
       else:
         raise ValueError (pool exhaustion — see §18.9)
  5. Replace nation.agents_active with the union of the four draws.
  6. Re-run the Phase A rule on the reduced set so connected_citizens
     lists reflect the calibrated population.
  7. Emit exposure_diagnostics: requested vs realised proportions,
     RNG seed, pool-exhaustion warnings, rule used.
```

Rationale: the Phase A rule labels each individual based on their own
data; Phase B controls the *population mix* without changing those
labels. Every retained citizen still carries a meaningful cell tag.

### 18.8 Configuration surface

```python
# Additions to src/cag/abm/sim.py SIM_CONFIG. Defaults preserve
# current behaviour exactly *except* for the rule itself: a v0.5 run
# without specifying these keys uses rule_signal_count, not
# priority_chain. Set political_exposure_rule="rule_priority_chain"
# to reproduce pre-v0.5 results byte-for-byte.

"political_exposure_rule": "rule_signal_count",
    # "rule_priority_chain"  -> frozen 10-rule chain (§18.4)
    # "rule_signal_count"    -> new symmetric signal counter (§18.5; default)
    # "rule_random"          -> truly random label assignment (§18.6)

"political_exposure_targets": None,
    # Required when rule == "rule_random"; dict that sums to 1.0 and
    # contains all four cells {"A-only","B-only","both","neither"}.
    # Optional under rule_priority_chain / rule_signal_count: triggers
    # Phase B resampling-calibration on top of that rule.
    # None  -> use rule's natural marginals, no resampling.

"exposure_count_regime": "fixed",
    # "fixed"        -> cell counts deterministic per replication
    # "multinomial"  -> cell counts drawn from Multinomial each replication
    # Ignored when rule != "rule_random" and targets is None.

"exposure_seed_offset": 0,
    # Added to random_seed when drawing rule_random labels and Phase B
    # resampling. Independent of network and broadcast RNG streams.
```

`political_exposure_rule` and `political_exposure_targets` go in
`_RESUME_HARD_KEYS` (changing either invalidates the agent set);
`exposure_count_regime` and `exposure_seed_offset` go in
`_RESUME_SOFT_KEYS`.

#### 18.8.1 Configuration cheat-sheet

| Goal | `rule` | `targets` |
|---|---|---|
| Reproduce pre-v0.5 results byte-for-byte | `rule_priority_chain` | `None` |
| New default research workflow | `rule_signal_count` | `None` |
| Symmetric baseline with rule-grounded cells | `rule_signal_count` | `{0.225, 0.225, 0.20, 0.35}` |
| UK-realistic asymmetric scenario | `rule_signal_count` | `{0.15, 0.30, 0.20, 0.35}` |
| Maximum-control synthetic baseline | `rule_random` | any dict |
| "Does the rule itself matter?" sensitivity | matched `rule_signal_count` vs `rule_random` | matched targets |

### 18.9 Edge cases and gotchas

- **Pool exhaustion (Phase B only).** If a target cell count exceeds
  the matching YouGov rows, raise `ValueError`. No silent
  with-replacement fallback — that would create duplicate personas
  and break the one-citizen-per-respondent invariant the rest of the
  codebase assumes. With the §18.3 default targets at `n_agents = 100`,
  the binding cell under `rule_signal_count` is `neither` (35 needed
  vs 68 available — 1.9× headroom; cf. §18.5.2).
- **`rule_random` has no pool exhaustion.** Labels are assigned, not
  resampled. The 1483-row pool supports any cell mix at any agent
  count up to 1483.
- **`neither` cells skip broadcasts.** They are absent from both
  political agents' `connected_citizens` lists, so increasing
  `neither` from 5 % to 35 % reduces the per-day political-message
  volume by ≈ 30 % at fixed `reach_a` / `reach_b`. This is the
  *intended* effect; experimenters should size `reach` knobs with
  this in mind.
- **`audience_cap` and `reach_a`/`reach_b` compose downstream.**
  Phase A → Phase B → `audience_cap` → reach subsample → broadcast.
  No interaction with peer messaging or end-of-day survey.
- **`day0_anchor` interaction: none.** Both phases change only the
  agent set, not what happens to those agents on Day 0.
- **Strict targets validation.** Targets must sum to 1.0 ± 1e-6 and
  contain all four canonical cell keys. We raise on typos rather than
  silently renormalising — caught a typo costs less than discovering
  a 0.95-summing dict ran an experiment with `neither` at 5 % when
  35 % was meant.
- **Largest-remainder rounding tie-break.** When two or more cells tie
  on fractional remainder (e.g. targets `0.225 / 0.225 / 0.20 / 0.35`
  at `n_agents = 100` produce two cells with remainder `.5`), ties are
  broken by canonical cell order: `A-only`, `B-only`, `both`, `neither`.
  This makes the integer cell counts deterministic across replications
  regardless of dict iteration order or platform sort stability, and
  fixes the §18.10 worked example (`A-only` rounds up to 23, `B-only`
  rounds down to 22).

### 18.10 Replication-variance interpretation

For the user's intended use case "100 agents, 100 replications" with
the §18.3 default targets, per-replication cell counts under the two
regimes are:

| Cell      | Target | Regime "fixed" | Regime "multinomial", ±1 SD |
|-----------|-------:|---------------:|----------------------------:|
| `A-only`  |  0.225 |             23 | 23 ± 4.2 |
| `B-only`  |  0.225 |             22 | 22 ± 4.2 |
| `both`    |  0.20  |             20 | 20 ± 4.0 |
| `neither` |  0.35  |             35 | 35 ± 4.8 |

(Largest-remainder rounding: 23+22+20+35 = 100. Standard deviations
from the binomial marginals of the multinomial.)

Implications for the headline 100-replication run:

1. **Per-replication SE on a within-cell mean opinion** (scale −3..+3,
   per-agent SD ≈ 1.5): SE ≈ 1.5 / √20 ≈ 0.34 for the smallest cell.
   Across 100 replications the *mean of cell means* has SE
   ≈ 0.34 / √100 ≈ 0.034. Cell-level mean differences of ~0.05 are
   resolvable; ~0.10 is comfortable.
2. **Condition-level mean** (pooling agents and replications, fixed
   regime): SE ≈ 1.5 / √(100 × 100) ≈ 0.015 — much smaller than any
   plausible LLM-driven effect (Run-4 condition contrasts in
   `result_report.md` are ~0.3–0.9 scale points).
3. **Multinomial regime widens condition-level CIs modestly.** Use as
   an *audit*: report headline under "fixed" and a robustness CI
   under "multinomial".
4. **Pool exhaustion is not the bottleneck.** Smallest cell pool
   (`neither`, 68 respondents under either rule) supports any
   single-replication draw up to 68 agents in that cell.
5. **Across-replication independence.** With `n_agents = 100` against
   1483 rows, no two of 100 replications can be fully disjoint (only
   ~14 disjoint 100-samples exist). For *bootstrap-of-the-pool*
   uncertainty (how much would the headline change if we had a
   different YouGov panel?), wrap the 100-replication run in an outer
   loop that resamples 1483 rows *with replacement* before each inner
   replication. That outer CI is the right number to report when
   making external-validity claims.

### 18.11 Code structure (planned)

| Location | Purpose |
|---|---|
| `src/cag/abm/exposure.py` (NEW) | All three rule implementations + Phase B helper. Pure functions, no LLM calls. Public entry: `assign_exposure(nation, rule, targets, n_agents, count_regime, seed) -> exposure_diagnostics`. |
| `src/cag/abm/environment.py` | `SurveyedNation.assign_political_exposure(rule="rule_signal_count", targets=None, ...)` becomes a thin dispatcher to `cag.abm.exposure.assign_exposure`. Existing call sites that pass no arguments default to `rule_signal_count`. |
| `src/cag/abm/sim.py` | Four new SIM_CONFIG keys (§18.8); `_resolve_runtime` reads them and dispatches. `_collect_results()` writes `exposure_diagnostics` into the results dict; `save_results()` persists it as `exposure_diagnostics.json`. |
| `tests/test_exposure.py` (NEW) | Per rule: byte-for-byte equivalence of `rule_priority_chain` against the current implementation; cell-count accuracy of `rule_signal_count` on a synthetic fixture; statistical validity of `rule_random` (targets hit in expectation); largest-remainder rounding sums to `n_agents`; pool-exhaustion raises under Phase B; Phase B invariance — every retained citizen's cell label is unchanged by resampling. |
| `notebooks/27_exposure_assignment_demo.ipynb` (NEW) | Side-by-side demo of all three rules on the YouGov pool; Phase B calibration before/after; cell-count distribution across 100 replications under fixed vs multinomial regimes. |

### 18.12 Open questions for team discussion

Carried forward from the planning thread; these are questions the
team should weigh in on before or shortly after implementation lands.

1. **Default rule: hard flip or one-cycle deprecation?** Current plan
   defaults to `rule_signal_count` from day one. Alternative: keep
   `rule_priority_chain` as default for one cycle, then flip. Cleaner
   migration vs less faff.
2. **Centre treatment in `rule_signal_count`.** Currently
   `politics_id == CENTRE` with no resolvable vote → `both`
   (engaged-but-cross-cutting). Alternative: → `neither`. Defensible
   either way; ours leans on Dubois & Blank's framing.
3. **`rule_random` — fully random vs conditional variants?** First
   pass ships fully random only. §18.6.3 lists two restricted
   variants (random-conditional-on-engagement;
   random-conditional-on-Brexit) as candidates. Need team view on
   whether either is worth implementing.
4. **Per-citizen reproducibility under `rule_random`.** Should a given
   `agent_id` always receive the same label given a fixed
   `random_seed`, or should labels re-shuffle per replication? Current
   plan: reproducible per agent_id given seed (§18.6 step 4). Affects
   whether replications trace different *populations* or different
   *labellings of the same population* — material for the methodology
   section of any paper using this mode.
5. **Phase B + `rule_random` mutual exclusivity.** Current plan: hard
   error if both `rule_random` and `political_exposure_targets` are
   supplied (since random already hits any targets directly). Should
   we instead allow `targets` under `rule_random` as the *required*
   input that makes the assignment work? Cleaner semantically but
   asymmetric with how `targets` works under the rule modes.
6. **Asymmetric default for the calibration target.** §18.3 locks a
   symmetric default. Alternative: lit-realistic asymmetric default
   (`B-only > A-only`) with symmetric available as an explicit
   override. Trade-off: defensibility vs cleanliness for null-condition
   experiments.
7. **Pool source for the `neither` cell.** §18.14 documents that our
   68 YouGov `neither` rows are demographically not the same people
   as the UK disengaged population (lit doc §6.2.1). v0.5 ships with
   the YouGov-only Phase B resample anyway (Option A in §18.14),
   accepting this as a documented limitation. Two near-term options
   are essentially closed (Option D — within-YouGov reweighting —
   blocked by the 68-row pool size; Option C — augmenting from UKHLS /
   BSA / ONS OLS — blocked by our restriction to the YouGov panel for
   ground-truth comparability). Option B (synthetic disengaged
   personas) is open but tensions with the broader
   real-data + ground-truth design philosophy and needs explicit team
   discussion before any work begins.

### 18.13 Out of scope (deferred to a future cycle)

- **Per-cell joint calibration with demographics.** Phase B controls
  the marginal four-cell distribution but lets YouGov's intra-cell
  demographic composition flow through unchanged. Stratifying further
  (age × cell × region) is possible but adds many rounding constraints.
- **Continuous exposure-probability** `(p_A, p_B) ∈ [0,1]²` per
  citizen drawn per-day. Cleaner conceptually; breaks every
  cell-comparison experiment in NB 20 / 21. Defer.
- **Joint calibration of broadcast targets and peer-network targets.**
  Peer-network rule design is owned by the user's team this cycle.
- **Climate-relevant psychometric rule** using EDO / Selftransc /
  Openness etc. Discussed and rejected this cycle: it would confound
  the dependent variable (climate-receptive citizens disproportionately
  in `A-only` makes the broadcast trivially "succeed" by selection).
  Documented as a possible robustness mode for a future cycle.
- **Hooking Phase B into the controller / multi-policy setup.**
  Single-policy and package modes both work unchanged because Phase B
  runs once at simulation start, before any per-policy branching.

### 18.14 Pool source for the `neither` cell — documented limitation and options

This subsection records a known limitation of the v0.5 design and
the options considered for addressing it. **The decision for v0.5 is
Option A (ship as planned).** Options B–D are documented for a future
cycle; Options C and D are essentially closed under our current
constraints and are kept here as understanding-the-disengaged context,
not as actionable next steps.

#### 18.14.1 The limitation

The lit (see [`Literature_Political_Exposure.md`](Literature_Political_Exposure.md)
§6.2) supports a 35–45 % `neither` share when `neither` is read as
"no direct broadcast receipt". Our Phase B resampling layer (§18.7)
can hit that target. **However**, the 68 YouGov rows that the rule
classifies as `neither` are not demographically representative of the
UK disengaged population. YouGov recruits politically-engaged
panellists by design, so its `neither` rows are best characterised as
*engaged respondents who happened to give DK on the three
political-signal variables*, not as the Hansard / Reuters / CAST
disengaged cluster (lit doc §6.2.1). Resampling 35 % of agents from
those 68 rows inflates a demographically-narrow subset.

This matters for any analysis that interprets `neither`-cell agents as
"the disengaged public". It does **not** affect analyses that interpret
`neither` purely structurally as "agents who don't receive a broadcast
on a given day".

#### 18.14.2 Options considered

| Option | Description | Status |
|---|---|---|
| **A** | Phase B resamples within YouGov, accepting the demographic skew. | **Selected for v0.5.** |
| **B** | Synthetic disengaged personas — strip political signals from selected YouGov rows and reweight psychometric / demographic fields toward the disengaged profile. | **Open but unresolved.** Tensions with the project's real-data + ground-truth philosophy; needs team discussion before any work. |
| **C** | Augment the `neither` slot with respondents from UKHLS (Understanding Society), British Social Attitudes, or ONS Opinions and Lifestyle Survey — surveys that probability-sample the disengaged. | **Closed for now.** We are restricted to the YouGov panel for ground-truth comparability with the current v0.5 result chain. |
| **D** | Reweight the existing 68-row YouGov `neither` pool by age × education × non-voter targets so its internal composition matches the UK disengaged profile, even though the count stays small. | **Closed.** 68 rows is too thin to reweight on more than one or two demographic axes without producing extreme weights and effective-sample-size collapse. |

#### 18.14.3 Why Options C and D are still documented

Even though neither is actionable in the current cycle, both clarify
*who* is missing from our `neither` cell. The candidate external pools
in Option C (UKHLS Wave 12 + political-engagement and environment
modules; BSA annual climate items; ONS OLS environment waves) are
useful **as readings, not as data**: they describe the demographic
signature of the disengaged that any future Option B work would need
to target. Option D similarly fails on *count*, not on *concept* — the
concept (post-stratify the disengaged subset to UK marginals) is
sound, and would be the right move if the YouGov pool were 10× larger.

#### 18.14.4 Option B — what would need resolving before implementing

Synthetic personas conflict with the existing design choice that every
simulated citizen corresponds to one real YouGov respondent (which is
what makes the per-agent ground-truth comparison in `result_report.md`
possible). Outstanding questions, none answered:

1. **What does ground truth mean for a synthetic `neither` agent?**
   Their Day-0 survey ground-truth values would have to be imputed,
   which weakens the central calibration claim of the project.
2. **Which fields can be safely synthesised?** Psychometric scales
   (EDO, Self-transcendence, Openness) carry a lot of behavioural
   weight in the prompts. Their joint distribution conditional on
   "disengaged" is not well-characterised in any UK source we have.
3. **How do we audit that synthetic `neither` agents behave
   *differently* from engaged-but-DK YouGov `neither` agents?** If
   the LLM treats them identically, the synthetic effort buys
   nothing; if it treats them very differently, we need to show those
   differences are realistic.

These are research-design questions for the team, not implementation
choices, and are flagged as §18.12 Q7.

### 18.15 Sanity-check execution and post-implementation revisions (2026-05-20)

NB 27 (`notebooks/27_affinity_exposure_demo.ipynb`) is the structural
sanity check for the §18 reframe, run end-to-end on the full YouGov
pool (N = 1483). It validated three of the four pre-registered design
claims — exact target marginals, interpretable cell-level demographic
profile (A-only youngest / highest openness / 96 % Remain;
B-only oldest / highest RWA / 98 % Leave; all four validation gates
passed), and a non-trivial weight-knob (66 % cell-level agreement
between `vote_dominant` and `values_dominant` at fixed target). Full
numbers are in [result_report.md](result_report.md) §"Affinity-based
political exposure: NB 27".

Two changes to the §18 design were made as a direct result of running
this notebook. Both are documented here for traceability rather than
back-edited into the earlier subsections, so the v0.5 design history
remains an honest record of what was tried, what failed, and why.

#### 18.15.1 `rule_affinity_logistic` removed (was §18.3, option C)

The originally-shipped third mode — independent Bernoulli draws on
z-scored affinity, calibrated so per-side marginals match the target —
**systematically missed cell-share targets by ±18 pp on real data** and
has been removed entirely (from `VALID_EXPOSURE_MODES`, the dispatcher,
the `_assign_affinity_logistic` method, the
`affinity_logistic_temperature` SIM_CONFIG key, the `_RESUME_HARD_KEYS`
list, and the corresponding test class). The failure mode is purely
structural and is *guaranteed* by the §18.3 design choice that both
scorers reuse the same demographic + vote signals with opposite signs:
`corr(score_A, score_B) = −0.975` on the YouGov pool, and two
independent Bernoullis on strongly anti-correlated scores collapse the
joint `both` cell and inflate the singleton cells, even though each
side's individual marginal is correct. The unit-test suite missed it
because the original `TestAffinityLogistic` only checked per-side
marginals on a synthetic n=400 fixture with uncorrelated scores.

The lesson is design-level, not implementation-level: any future
sampling-based mode for this audience layer must validate the **joint
cell distribution**, not the side marginals, on a fixture that
preserves the empirical `corr(A, B)`. The `rule_affinity_rank` mode
sidesteps the issue entirely by allocating the joint cells directly
via deterministic top-K. v0.5 therefore ships with two modes only:
`rule_priority_chain` (legacy) and `rule_affinity_rank` (new default).

#### 18.15.2 `_safe_int` bugfix (silent zeroing of psych-scale signals)

The first pass of NB 27 surfaced a silent bug in `environment._safe_int`
that affected **every affinity score computed on `build_nation`-built
citizens**. The four psychometric IDs (`openness_id`, `rwa_id`,
`sdo_id`, `selftransc_id`) are `GABMAttributeID` enum subclasses that
expose their ordinal via `.id` only — `int()` raises `TypeError` on
them. The previous `_safe_int` body was a bare `int(attr_id)` inside
`try/except`, so every psych-scale contribution was silently zeroed
and the entire `psych_scales` weight bucket multiplied zero. The
visible symptom in NB 27 was that the three weight presets
(`balanced`, `vote_dominant`, `values_dominant`) produced **bit-identical
cell shares** on the first pass, which is structurally impossible if
the weight knob is doing anything.

The fix is small (`getattr(attr_id, "id", None)` first, then `.value`,
then `int()`, then `0`) but the **unit-test gap was the real lesson**:
the existing `tests/test_exposure.py` fixtures passed raw `int`
ordinals via a synthetic `_make_citizen` helper, so `int(v)` worked
inside the helper and the bug never reached the assertions. The new
`TestSafeInt` regression class in `tests/test_exposure.py` closes the
gap with both unit-level tests on real `PoliticsID` instances and an
integration-level guard (`test_psych_scales_contribute_to_score`) that
builds two otherwise-identical citizens differing only on
`openness_id` and asserts their green-affinity scores differ. Any
future bug of the same shape — silently treating a GABM enum as a raw
int — will now be caught by the regression test rather than producing
plausible-looking but signal-free affinity scores.

After both fixes the suite is **432 passed, 1 skipped** (430 → 432:
−2 logistic tests, +4 `TestSafeInt` tests).

#### 18.15.3 Status of §18 as a whole

The §18 reframe is structurally validated on real data: rank-mode
targets are hit exactly, cells are demographically interpretable in
the direction the literature predicts (§18.7 / §18.8), and the
weight knob is non-trivial. The audience layer is therefore ready to
be exercised end-to-end inside a simulation run; that integration
experiment (Run 9) is the next planned step and is **not** covered by
NB 27.

---

## 19. Per-Day Broadcast-Frequency Sugar (v0.5, 2026-05-15)

### 19.1 Motivation

The "competing committed minorities" research question naturally calls
for varying the **resources** of each political agent — in particular,
how many broadcasts per day each side can afford. The simulation loop
already supports this: the per-day `phases` list is iterated literally,
so `["P-A", "P-A", "P-A", "P-B", "C"]` already fires three P-A
broadcasts and one P-B broadcast, with no deduplication. This section
documents that contract and adds an ergonomic config surface around it.

### 19.2 Public API

New helper `cag.abm.sim.make_phases(broadcasts_a=1, broadcasts_b=1,
peer=True, interleave=False, a_first=True) -> list[str]` builds a phases
list from per-side broadcast counts. Examples:

```python
make_phases()                            # ['P-A', 'P-B', 'C']
make_phases(broadcasts_a=3)              # ['P-A', 'P-A', 'P-A', 'P-B', 'C']
make_phases(2, 1, interleave=True)       # ['P-A', 'P-B', 'P-A', 'C']
make_phases(broadcasts_b=0, peer=False)  # ['P-A']
```

The same five arguments are accepted as **per-day sugar keys** in
`SIM_CONFIG["days"]`:

```python
{"policy": ClimatePolicyID.CARBON_TAX,
 "broadcasts_a": 3, "broadcasts_b": 1}
# expanded internally to phases=['P-A','P-A','P-A','P-B','C']
```

Resolution is handled by the new `_resolve_day_phases(day_config)`
helper, called at the top of `_run_one_day`. Precedence rules:

1. If `"phases"` is present in the day entry, it is used verbatim
   (full backward compatibility).
2. Otherwise, any of the sugar keys are forwarded to `make_phases`.
3. Mixing `"phases"` with any sugar key in the same day entry raises
   `ValueError` — there is one canonical source of truth per day.

Validation in `make_phases` rejects negative integers, non-int counts,
and `bool` values for the count arguments (the latter to avoid the
implicit `True == 1` foot-gun).

### 19.3 Behavioural contract under repetition

Three behaviours are intentional and fixed in tests:

- **Same audience on repeats.** `apply_reach_subsample()` shrinks each
  political agent's `connected_citizens` once at sim setup. Repeated
  broadcasts therefore reach the **same** subsample on every call —
  semantically "repeated TV ads to the same viewers," not a fresh
  sample. A future variant could add a per-broadcast resample mode; the
  current API leaves room for it without breaking existing configs.
- **Stateless message generation.** Each `run_political_broadcast` call
  invokes `political_agent.generate_message(...)` afresh, with no
  awareness of earlier messages from the same agent on the same day.
  Citizens, by contrast, *do* see their own prior reflections via the
  `recent_reflections` block in `assemble_context()`, so message-level
  variation accumulates on the receiver side.
- **No deduplication.** `["P-A","P-A","P-B","C"]` calls
  `run_political_broadcast` three times. This is locked in by
  `TestPerDayPhaseSugarInRunSimulation.test_explicit_phases_duplicates_not_deduped`.

### 19.4 Tests

21 new unit tests in `tests/test_sim.py` across three classes:
`TestMakePhases` (helper output and validation), `TestResolveDayPhases`
(precedence and error paths), `TestPerDayPhaseSugarInRunSimulation`
(end-to-end through `run_simulation`). Full suite: 403 passing,
1 skipped.

### 19.5 Out of scope (deferred)

- Per-broadcast audience resampling under `reach < 1.0`.
- Per-broadcast cost/budget accounting (the natural follow-on if
  resource asymmetry becomes a primary research lens).
- Cross-day broadcast budgets (`budget_a` / `budget_b` global caps).
- A dedicated experiment notebook sweeping `broadcasts_a` ×
  `broadcasts_b` (left for the next analysis pass).

## 20. v0.5 Prompt audit and unification (post local-LLM)

### 20.1 Motivation

A full audit of every LLM-facing prompt in `agent.py` surfaced three
chronic issues:

1. **Perspective inconsistency.** The debias chain
   (`_ANTI_SYCOPHANCY` / `_DEBIAS_STEP1_TEMPLATE` /
   `_DEBIAS_STEP2_TEMPLATE`) and the Day-0 rationale prompt mixed
   second- and third-person framings ("this person… their values…")
   while every other citizen-side prompt was first-person ("you…
   your values…"). The 3P framings were inherited from NB 12 / NB 13
   experiments and never reconciled with the rest of the chain after
   NB 13's Condition B was promoted to the default.
2. **End-of-day surveys did not reference the in-context memory.**
   The vanilla Day ≥ 1 framing said *"Consider how today's messages
   and discussions have shaped your thinking."*; debias Step 1's
   factor list named voting history, values, and life circumstances
   but not the day's messages and reflections. Spot-checks showed
   the LLM largely ignoring `assemble_context()`'s daily-summary and
   recent-reflection blocks at survey time.
3. **`get_persona()` and `get_narrative()` were two different things
   in code but one concept ("the persona") in every doc and review.**
   Plus a Day-0 rationale bullet bug: every label was
   `SURVEY_QUESTIONS[pid][:60]`, which truncates inside the
   84-character shared preamble of all six policy questions —
   producing six identical-looking bullets.

### 20.2 Changes

All changes are confined to `src/cag/abm/agent.py` and a small
addition to `src/cag/abm/attributes/opinion.py`. No changes to
network construction, simulation loop, output, or LLM provider.

- **Perspective flipped to consistent 1P** across `_ANTI_SYCOPHANCY`,
  `_DEBIAS_STEP1_TEMPLATE`, `_DEBIAS_STEP2_TEMPLATE`, and
  `seed_opinion_with_rationale`'s user prompt. NB 13's Condition B
  bias-reduction number (~97% on Ban Petrol Cars, `gpt-4.1-mini`)
  should **not** be assumed to transfer to the 1P chain; a
  Condition B re-measurement is on the deferred backlog (Phase 5 of
  the v0.5 prompt-overhaul plan).
- **End-of-day surveys reference the memory explicitly.** Vanilla
  framing rewritten to *"Consider your earlier reasoning, the daily
  summaries, and your recent reflections above before answering."*
  Debias Step 1's factor list extended with *"the messages and
  reflections from today"*.
- **Persona merge.** `get_persona()` is now the canonical public
  method, returning demographics + values joined by a single
  newline. The two old builders are now private:
  `_build_demographics_text()` (rename of old `get_persona`) and
  `_build_values_text()` (rename of old `get_narrative`). The
  end-of-context "Remember your persona: …" line is renamed
  *"Remember who you are: …"* and continues to use the
  demographics-only block (intentionally — values text in the
  reminder slot tends to dilute the focus signal).
- **Day-0 rationale labels fixed.** New `SURVEY_SHORT_LABELS` dict
  in `opinion.py` (≤ 5 words per policy). `_build_day0_rationales`
  switched from `SURVEY_QUESTIONS[pid][:60]` to
  `SURVEY_SHORT_LABELS[pid]`. Every bullet is now uniquely labelled.
- **Phase tags stripped from in-context reflections.** Bullets in
  `assemble_context`'s recent-reflections block are now `- <text>`
  rather than `- [P-A] <text>`. The `phase` field is unchanged in
  `self.reflections[i]["phase"]` and `reflections.csv` (full audit
  trail preserved). Rationale: the broadcast source is intentionally
  unlabelled (see §19.3 / §3 of [V2 Prompts Guide](Prompts_and_Personas_Guide_v2.md)),
  and the LLM doesn't need a meta-tag it can't act on.
- **Memory compression: more depth, phase-agnostic.**
  `compress_memories`'s user prompt rewritten from
  *"Concisely summarise the following in 2 sentences from a 1st
  person perspective: {memories}"* to a 4–5-sentence first-person
  brief that specifically asks about which received messages were
  compelling vs. pushed back on, and whether thinking shifted. Two
  sentences was too aggressive — cross-day continuity of *why*
  opinions moved was being lost.
- **Peer-message reflection symmetry.** The single-policy variant of
  `receive_peer_messages` previously ended *"affect your thinking."*
  while the package variant ended *"affect your thinking about the
  overall package."* — extended the single-policy version to
  *"affect your thinking about {policy_description}."* to mirror.

### 20.3 Tests

Five existing assertions in `tests/test_agent.py`,
`tests/test_baseline.py`, `tests/test_endofday.py`, and
`tests/test_memory.py` updated to track the new wording and the
merged-persona semantics. No new tests added (changes are
text-level; existing structural coverage is sufficient). Full suite:
**403 passing, 1 skipped** (unchanged from §19.4).

### 20.4 Documentation

- New canonical guide:
  [docs/Prompts_and_Personas_Guide_v2.md](Prompts_and_Personas_Guide_v2.md).
  Verbatim prompt quotes from current code, worked example over
  Day 0 / Day 2 / Day 5 using real data from
  `data/output/experiments/20260425_082317/` (with a caveat that
  that run pre-dates the overhaul — structure is unchanged, wording
  inside each section differs).
- The V1 guide
  [docs/Prompts_and_Personas_Guide.md](Prompts_and_Personas_Guide.md)
  is preserved as historical reference of pre-v0.5 prompts.

### 20.5 Out of scope (deferred)

- Condition B bias-reduction re-measurement on the new 1P debias
  chain (NB 13 partial re-run, ~120 API calls).
- USER_GUIDE.md rewrite.
- `__version__` bump across the 12 source modules.
- Day-0 anchoring discussion — see "DAY 0 ANCHORING DISCUSSION" in
  the user's progress notes; orthogonal to this overhaul.

### 20.6 Political-agent prompt de-identification (2026-05-20)

Follow-up to §20.2 covering the political-agent side (citizen-side
prompts were already audited in §20.2). The two campaign briefs
`_DEFAULT_PRO_CLIMATE_PROMPT` and `_DEFAULT_ANTI_CLIMATE_PROMPT` in
[`src/cag/abm/agent.py`](../src/cag/abm/agent.py) previously read
"campaigning in the style of the Green Party of England and Wales /
Reform UK" and named real politicians (Zack Polanski, Caroline Lucas,
Nigel Farage, Richard Tice). For the v0.5 paper this is reframed as a
*fallback* path:

- **Why.** The next research step is to broadcast real-world political
  messages (party press releases, MP speeches, campaign material) that
  have been collected and stored, not LLM-generated party-style
  messages. The provisional briefs remain available for users who want
  a self-contained LLM-only setup but should not advertise themselves
  as faithful renderings of named UK parties — both because the
  briefs are not validated against the parties' own messaging and
  because the model is exemplar-of-a-pair, not Reform-vs-Green
  specifically (see [Literature_Political_Exposure.md](Literature_Political_Exposure.md)
  §5.3).
- **What was removed.** All party and politician names. From the
  pro-climate brief: water companies, NHS, free public transport,
  the "For the Common Good" slogan, the wealth-tax-on-the-super-rich
  content, and the "disillusioned Labour voters / public sector
  workers" audience segments. Parallel cuts to the anti-climate brief.
  Result: both briefs are now tighter and climate-policy-focused
  rather than generic UK-political-spectrum.
- **Other prompt tightening done in the same pass.** `_ANTI_SYCOPHANCY`
  drops the trailing "Real people like you hold a WIDE range of
  views, including strong opposition. That is expected and
  acceptable." sentence; the prior wording was over-leading and could
  legitimise extreme positions the underlying persona would not
  endorse. `_DEBIAS_STEP1_TEMPLATE` updated from "the messages and
  reflections from today, and how these might interact" to "the
  messages and reflections from today and previous days" so the
  factor list matches the v0.5.1 multi-day daily-context surveys
  (§20.2 (b)).
- **Documentation.** [Prompts_and_Personas_Guide_v2.md](Prompts_and_Personas_Guide_v2.md)
  status banner rewritten as fallback framing with an explicit note
  about the de-identification and the real-message-ingestion direction;
  §3.1, §3.2, and the debias step-1 verbatim quotes regenerated to
  match the trimmed source. The worked example in §6 is unchanged —
  it pre-dates this pass and the structural section markers it cites
  are unaffected by wording changes.
- **Out of scope.** Re-running NB 13 (Condition B bias measurement)
  against the trimmed prompts. The trimming removes leading content
  and is expected to *reduce* baseline sycophancy slightly, but this
  is not measured.

### 20.7 Day-0 anchor: cross-step memory consistency (2026-06-28)

Bug-fix to the v0.8 memory-v2 layer (§ assemble_context six-section
design). In **package mode**, the system prompt the agent reads
depended on *which step* it was performing:

- The end-of-day **survey** calls
  `get_system_prompt(day, policy_id=PACKAGE_SCOPE, target_policy_id=<one policy>)`,
  so the three target-scoped sections (Day-0 anchor, recent considered
  position, answers-so-far) were populated.
- **Peer-message generation and reflection** call
  `get_system_prompt(day, policy_id=PACKAGE_SCOPE)` with no target, so
  those three sections were all empty.

Net effect: an agent "forgot" its verbatim Day-0 identity anchor while
writing a peer message or reflecting, then "remembered" it again at
survey time. This is poor cognitive modelling and an experimental-
validity concern (peer messages were generated from a thinner
self-model than survey answers). Single-policy mode was unaffected —
every step there passes the same `policy_id`, so the sections are
already consistent.

**Decision (consistency vs relevance).** Only the **Day-0 anchor**
(section 2) is propagated across steps, because it is identity-level,
anti-drift memory that is relevant whenever the agent forms or
expresses an opinion. The other two target-scoped sections are
deliberately **not** propagated:

- *Recent considered position* (section 5, verbatim own survey
  reasoning) is largely redundant during a holistic package step — the
  daily summaries (section 3) and recent reflections (section 4)
  already carry that recent thinking — and its anti-drift value is
  specific to answering a single policy's survey question. Kept
  survey- and target-scoped, unchanged.
- *Answers so far in today's survey* (section 6) is chronologically
  transient: the agent has not taken today's survey when it writes a
  morning peer message, so its absence there is correct. Unchanged.

**Implementation.** New `_section_day0_anchor_all()` emits every
policy's Day-0 rationale (canonical `SURVEY_QUESTIONS` order) under the
header `Original prior positions:` as `- <short label>: <text>`
bullets. `assemble_context` now branches: a real `target_policy_id`
uses the focused single-policy `_section_day0_anchor()` (survey,
unchanged — option (a): the survey stays focused on the policy being
asked); otherwise, package-scoped context with no single target uses
the all-policy form (peer messaging / reflection). Nothing is ever
"forgotten" going peer→survey — the survey's single anchor is a subset
of the package form the agent saw earlier in the day. The
peer/reflection call sites are unchanged; they simply start receiving
the anchor.

**Tests.** `tests/test_memory.py::TestDay0AnchorSection` — the former
`test_anchor_omitted_when_target_is_package_scope` is replaced by
`test_package_anchor_lists_all_policies_when_no_single_target` and
`test_package_anchor_present_on_peer_reflection_path` (the
`target_policy_id=None` path). Single-target anchor tests and all
`TestRecentOwnReasoning` (section 5) tests are unchanged. Full suite:
557 passed, 1 skipped.

**Out of scope.** Dumping peer/reflection assembled contexts to a CSV
for auditability (only `survey_assembled_context.csv` exists today);
`__version__` bumps.

  ---

## 21. v0.6 Canonical Runtime Consolidation (2026-05-24)

### 21.1 Scope

v0.6 is a consolidation release for runtime truth and documentation consistency.
It does not introduce a new opinion-dynamics mechanism; it promotes an
operationally-complete path to canonical status and makes that path explicit in
code defaults, smoke notebooks, and user-facing documentation.

Core v0.6 surfaces:

1. Canonical `SIM_CONFIG` defaults moved to the research path currently used in
  production-style runs.
2. Offline political-message ingestion promoted to a first-class default mode.
3. Strict startup validation for offline political-message availability.
4. Message-level provenance surfaced in outputs (`political_message_id`).
5. Resume compatibility contract extended for message-source consistency.
6. Canonical smoke/docs workflow established via NB28 + NB29 and
  `docs/Simulation_Configuration_Guide.md`.

### 21.2 Canonical defaults (authoritative for v0.6)

In v0.6, the canonical defaults in `src/cag/abm/sim.py` are:

| Key | v0.6 canonical default | Rationale |
|---|---|---|
| `n_citizens` | `100` | practical default balancing cost and trajectory stability |
| `days` | alternating package-mode phases: `[{"phases":["P-A","P-B","C"]}, {"phases":["P-B","P-A","C"]}]` | mitigates fixed first-speaker recency |
| `llm_provider` | `"local"` | reproducible local runtime, no API spend |
| `llm_model` | `"mlx-community/Qwen3-8B-4bit"` | validated local baseline |
| `communication_mode` | `"package"` | package-level dynamics are the active research direction |
| `debias` | `True` | retain Condition-B mitigation by default |
| `day0_anchor` | `"ground_truth_with_rationale"` | zero Day-0 numeric drift from survey mean, keep rationale trace |
| `political_message_source` | `"offline"` | curated political-message corpus as default broadcast source |
| `political_message_set` | `"v1"` | pinned versioned corpus |

### 21.3 Offline political-message runtime flow

`run_simulation()` now resolves political-broadcast source mode in
`_resolve_runtime()`:

1. Validate `political_message_source ∈ {"offline", "llm"}`.
2. When source is `"offline"`, load a versioned message pool from
  `data/political_messages/`.
3. Validate required cells (side × policy or side × package scope depending on
  communication mode) before the day loop begins.
4. Abort early if required cells are missing; do not silently fallback to LLM.

Broadcast methods receive `message_pool=` and select messages from the pool when
offline mode is active. LLM-generated political messages remain available as an
explicit opt-in path (`political_message_source="llm"`).

### 21.4 Output schema delta (v0.6)

`messages.csv` now includes a `political_message_id` column for political
broadcast events. This enables row-level provenance from runtime logs back to
the exact curated corpus record used for that broadcast.

### 21.5 Resume contract delta (v0.6)

Resume hard-fail compatibility keys now include:

- `political_message_source`
- `political_message_set`

This prevents checkpoint continuation across incompatible broadcast-message
regimes (e.g., switching from curated offline corpus to live generated
political messages mid-run).

### 21.6 Validation notebooks and roles

- **NB28** (`notebooks/28_offline_political_messages_smoke.ipynb`): verifies
  offline political-message plumbing and message-pool round-trip checks.
- **NB29** (`notebooks/29_canonical_full_smoke.ipynb`): validates canonical
  full-stack configuration and outputs under smoke-scale run settings.

NB29 is a canonical run-path smoke test, not a resume/checkpoint regression.
Resume/checkpoint behavior remains primarily validated by NB18.

### 21.7 Corrections to stale defaults in earlier sections

This document is append-only, so earlier default tables are preserved as
historical records. For current runtime behavior, this addendum supersedes those
older defaults where they conflict.

Specifically, if an earlier table states `n_citizens = 200` as a current
default, treat it as historical context; the v0.6 active default is
`n_citizens = 100`.

### 21.8 Dataset timing wording

For runtime-cohort references in v0.6 docs, use **YouGov April 2024** wording.
Literature citations that include 2022 publication years are unchanged and not
part of this correction.

---


## 22. AIRE / HPC infrastructure (v0.7, 2026-06-21)

v0.7 ships a production-ready HPC integration layer for the University of Leeds AIRE cluster (SLURM). The intent is *thin, composable, and edit-free*: launching a new experiment is one entry in a Python preset dict plus one line in a sweep file. No per-experiment shell-script edits.

### 22.1 Thin sbatch launcher

[scripts/aire/run.sh](../scripts/aire/run.sh) is a single sbatch script that delegates every research knob to the Python CLI via environment variables. It defines the SLURM `#SBATCH` directives (partition, gres, mem, time), auto-starts a vLLM server on the GPU node with `$HF_MODEL` (overrideable), waits for the model endpoint to come up, then invokes `python -m cag` with every variable forwarded as a `--flag`. Adding a new experiment never requires editing this script.

### 22.2 Sweep submitter

[scripts/aire/sweep.sh](../scripts/aire/sweep.sh) reads a sweep file (one line per condition, each line a list of CLI overrides) and submits one `sbatch` per condition. Sweep files live under [scripts/aire/sweeps/](../scripts/aire/sweeps/). The v0.7 canonical sweep is [scripts/aire/sweeps/r14_v2.txt](../scripts/aire/sweeps/r14_v2.txt) — 3 split50 conditions for the first AIRE production run.

### 22.3 Preset bundle registry

New [src/cag/presets.py](../src/cag/presets.py) defines `RUN_BUNDLE_PRESETS`, a dict of named SIM_CONFIG bundles. v0.7 ships two: `"smoke"` (10-agent × 2-day fast smoke, used by NB 32) and `"r14_canonical"` (the canonical 50-agent × 5-day Run-14 v2 baseline). Presets are loaded by the CLI via `--preset NAME`; individual `--flag` overrides layer on top.

### 22.4 Walkthrough docs

- [docs/AIRE_HPC_repo_primer.md](AIRE_HPC_repo_primer.md) — cluster fundamentals, storage rules, hard constraints, troubleshooting.
- [docs/AIRE_Quickstart.md](AIRE_Quickstart.md) — copy-pasteable zero-to-Run-14 walkthrough.


## 23. NB-31 package-mode survey-context fix (v0.7, 2026-06-21)

### 23.1 The bug

In v0.4–v0.6, package-mode end-of-day surveys (`administer_survey()` in `src/cag/abm/agent.py` and `run_end_of_day_survey()` in `src/cag/abm/environment.py`) called `assemble_context(policy_id=...)` with a single per-policy `policy_id`. The in-context memory slice retrieved for that policy was effectively empty: in package mode every reflection, peer message, and broadcast lives under `PACKAGE_SCOPE` (the union over all six climate policies), not under any single per-policy key. Result: every package-mode survey was reading an effectively unchanging system prompt — broadcasts and peer messages had nothing to influence at the survey step.

The bug was silent. Per-day inertia metrics looked plausible (the LLM is anchored heavily by Day-0 rationale and persona); only a cross-bucket gap-widening probe could expose it.

### 23.2 Discovery

[notebooks/30_surgical_survey_replay.ipynb](../notebooks/30_surgical_survey_replay.ipynb) replays a single agent's package-mode survey under frozen state across models. With the buggy code the assembled context was structurally empty after the persona prefix; with `PACKAGE_SCOPE` plumbed in, the same agent's context expanded by ~10–18 KB and the survey response shifted.

### 23.3 Fix

Both `administer_survey()` and `run_end_of_day_survey()` now branch on `communication_mode`. In package mode they pass `PACKAGE_SCOPE` (the canonical union key from [src/cag/abm/attributes/opinion.py](../src/cag/abm/attributes/opinion.py)) to `assemble_context()`. In single-policy mode the call is unchanged.

### 23.4 Validation

[notebooks/31_package_mode_fix_validation.ipynb](../notebooks/31_package_mode_fix_validation.ipynb) confirms the predicted amplification on the surgical-replay pool. Production confirmation: **Run-14 v2 measured +0.667 Day-5 cross-bucket package-index gap-widening vs +0.053 pre-fix — a 12.6× amplification** matching the GPT-5.4-mini surgical-replay prediction within noise. Full write-up in [docs/result_report.md](result_report.md).


## 24. Outputs and instrumentation expansion (v0.7, 2026-06-22)

The saved run bundle in v0.7 expands from 17 → 29 artefacts so that every diagnostic question previously requiring a notebook to derive from raw CSVs is answered by the bundle itself.

### 24.1 Phase 1 — Agent-attribute persistence

`_assign_affinity_rank` in [src/cag/abm/environment.py](../src/cag/abm/environment.py) now caches `_affinity_score_a` and `_affinity_score_b` on every citizen (mirrors the existing in-place `political_exposure` write).

New `collect_agent_attributes(nation)` in [src/cag/abm/sim.py](../src/cag/abm/sim.py) returns a per-agent DataFrame keyed on `agent_id` with `bucket`, both affinity scores, the demographic IDs that drive the persona, and the **full `get_persona()` text** (no truncation). Written as `agent_attributes.csv` to checkpoints + final.

### 24.2 Phase 2 — Bucket-stratified CSVs

Three pure-function builders join `agent_attributes` to the per-day signals:
- `build_package_index_by_bucket` — per `(bucket × day)` mean / SD / N of the per-agent package index (mean of the six per-policy `pro_climate_index` values).
- `build_opinion_shares_by_bucket` — per `(policy × bucket × day)` support / against / neutral share.
- `build_day0_vs_dayN_shifts` — per-bucket Day-0 → Day-N shift in package index plus per-policy shifts.

The Run-14 v2 "+0.667 Day-5 gap-widening" headline is now derivable from `package_index_by_bucket.csv` alone.

### 24.3 Phase 3 — Bucket plots

- `plot_package_index_by_bucket` (one panel per bucket, mean ± SE band)
- `plot_opinion_shares_by_bucket` (`policy × bucket` mega-grid)
- `plot_gap_widening` (bold package-index gap + thin per-policy gap traces)

All wired through the single `save_result_plots(results, out_path)` entry point in [src/cag/abm/output.py](../src/cag/abm/output.py).

### 24.4 Phase 4 — Calibration, message flow, network snapshot

- `build_calibration_table` — per `(policy_id, day)` `pearson_r / spearman_rho / mae / mean_signed_bias` of LLM survey vs `ground_truth`.
- `plot_calibration_by_policy` — per-policy GT-vs-LLM scatter with diagonal reference.
- `build_message_flow` — joins `messages × agent_attributes` to a `(day × phase × sender_side × recipient_bucket)` aggregation. Would have flagged the `k_peers=0` waste in one glance.
- `_safe_network_snapshot` — writes a JSON-safe `{nodes:[{id,bucket,degree}], edges:[[u,v],...]}` to `network_snapshot.json`. Defensive `isinstance(G, nx.Graph)` guard so MagicMock unit tests don't crash.
- `plot_network_graph` — node colour by bucket, size by degree.

### 24.5 Phase 5 — Survey assembled-context + agent timeline

New `self.survey_assembled_context = {}` on `SurveyedCitizen` in [src/cag/abm/agent.py](../src/cag/abm/agent.py). `administer_survey()` appends `(day, ctx_str)` immediately after `assemble_context()`. Captures the **exact ~1–18 KB system prompt** each agent saw at every survey call — the diagnostic affordance that would have caught NB-31 in week one.

Two new `SIM_CONFIG` keys:
- `timeline_sample_size = 3` — number of agents to include in `agent_timeline`.
- `timeline_sample_agent_ids = None` — auto-stratify one agent per top-3-by-size exposure bucket; ties broken by sorted `agent_id`; if fewer than 3 buckets, evenly-spaced sampling along `agent_id`.

`build_agent_timeline` returns a long-format DataFrame with **9 event types** (`broadcast_received`, `broadcast_reflection`, `peer_message_received`, `peer_message_sent`, `peer_reflection`, `survey_assembled_context`, `survey_raw_response`, `survey_reasoning`, `survey_numeric`) sorted by `(agent_id, sim_step)`.

Final-output only — `_CHECKPOINT_SKIP_KEYS = frozenset({"agent_timeline"})` ensures the timeline (which can be GB-scale on long runs) is not duplicated into every per-day checkpoint.

### 24.6 Cross-cutting — `sim_step` instrumentation

Monotonic `nation._sim_step` counter (lazy-init, restored to `max(sim_step)` across all loaded sources on resume) is incremented at every event-logging site. New `sim_step` column on `messages`, `reflections`, `survey_reasoning`, `survey_raw_response`, `survey_assembled_context`, and `daily_summaries`. The canonical sort key for any interleaved replay is now `(agent_id, sim_step)` — the schema makes zero assumption about phase count, order, or repetition.

### 24.7 CLI ergonomics carried in

- `k_peers=0` short-circuit in `run_peer_messaging` and `run_package_peer_messaging`: early-return when peer count is zero, skipping the ~240 wasted `generate_peer_message` LLM calls per r14-style 5-day broadcast-only run.
- Per-day checkpointing default-on in CLI: `--checkpoint-every-day` is `argparse.BooleanOptionalAction, default=True`; `--no-checkpoint-every-day` opts out. The Python-side `run_simulation(..., checkpoint_every_day=False)` default is intentionally unchanged — interactive notebooks don't accumulate per-day artefacts unless asked.


## 25. Network connectivity 3-layer defence (v0.7, 2026-06-22)

### 25.1 Motivation

v0.6 shipped with SBM `p_inter = 0.02` and ER `p = 0.05` as defaults. Empirical sweep in [scripts/estimate_connectivity_threshold.py](../scripts/estimate_connectivity_threshold.py) showed that at n=10 these are hopeless at any `p ≤ 0.15`, and at n=50 SBM needs `p_inter ≥ 0.06` for 90% connectivity. The failure mode is silent: disjoint components produce uneven cross-bucket exposure with no warning to the operator.

### 25.2 New defaults

Updated in [src/cag/abm/networks.py](../src/cag/abm/networks.py) and [src/cag/abm/sim.py](../src/cag/abm/sim.py):
- SBM `p_inter` default 0.02 → **0.05** (within-to-between ratio drops from 7.5:1 to 3:1, yielding ~25% cross-cutting exposure — within the Facebook ~24% of Bakshy et al. 2015 *Science* and the Twitter 18–26% of Halberstam & Knight 2016).
- ER `p` default 0.05 → **0.10** (above the n=50 classical threshold ln(50)/50 ≈ 0.078).
- Watts–Strogatz, Barabási–Albert, and `homophily_weighted` defaults unchanged (always connected by construction).

### 25.3 Layer 1 — Adaptive small-N bump

`_adjust_network_params_for_small_n(cfg, n_agents)` is called before `nation.create_network`:
- SBM `n < 30` → bump `p_inter` to `max(p_inter, 0.10)` and log WARNING.
- SBM `30 ≤ n < 100` → bump to `max(p_inter, 0.06)` and log INFO.
- ER analogues.
- `n ≥ 100` → untouched.

Layer 1 only ever raises values, never lowers — explicit higher overrides survive untouched.

### 25.4 Layer 2 — Deterministic auto-repair

`_auto_connect_components(nation, seed)` is called after `nation.assign_network_blocks`. If `nx.is_connected(G)` is False:
1. Sort components by `(-len, sorted_node_ids[0])` for determinism.
2. Seed an `np.random.default_rng(seed)` to pick endpoints.
3. Add exactly `(k − 1)` bridging edges — one from each smaller component to the largest.
4. Re-run `assign_network_blocks()` to refresh agent `network_neighbors`.
5. Log a WARNING with component count, sizes, n_added, and seed.

Records `nation._auto_connected_edges` (count).

### 25.5 Layer 3 — Visibility log + diagnostic field

`_log_network_summary(nation)` emits a single INFO line `n_nodes / n_edges / n_components / mean_degree / auto_connected_edges`. `_safe_network_diagnostics` adds a new `auto_connected_edges` field in `network_diagnostics.json`. Defensive `isinstance(G, nx.Graph)` guards on Layer 2/3 helpers so MagicMock-based unit tests pass cleanly.

### 25.6 Validation

NB 32 ([notebooks/32_v06_outputs_smoke.ipynb](../notebooks/32_v06_outputs_smoke.ipynb)) doubles as the live demo: at n=10, Layer 1 fires (`p_inter` 0.05 → 0.10) and Layer 2 fires (5 components → 1 with 4 bridging edges). `network_snapshot.json` and `network_diagnostics.json` both reflect the auto-repaired graph. 13 new tests in [tests/test_networks.py](../tests/test_networks.py) cover Layer 1 (`TestAdjustNetworkParamsForSmallN`, 7 tests), Layer 2 (`TestAutoConnectComponents`, 4 tests), and Layer 3 (`TestNetworkDiagnosticsAutoConnectedField`, 2 tests).


## 26. v0.7 operational defaults (2026-06-22)

| Area | v0.7 default | Notes |
|---|---|---|
| `__version__` across source modules | `0.7.0` (18 modules) | Retires 0.2.0 / 0.3.0 / 0.5.0 / 0.6.0 / 1.0.0 inconsistency. |
| SBM `p_inter` | `0.05` | Bakshy 2015, Halberstam-Knight 2016 grounded. |
| ER `p` | `0.10` | Above n=50 classical threshold. |
| `timeline_sample_size` | `3` | Top-3-bucket stratified. |
| `timeline_sample_agent_ids` | `None` | Auto-stratify. |
| `--checkpoint-every-day` (CLI) | `True` (default-on) | `--no-checkpoint-every-day` opts out. |
| `checkpoint_every_day=` (Python) | `False` (unchanged) | Interactive notebooks unaffected. |
| Connectivity defence Layer 1 / 2 / 3 | Active | Operator-visible auto-repair on small-N or disconnected configs. |
| Test suite baseline | **538 passed, 1 skipped** | Was 432 at end of v0.5 / start of in-progress v0.6. |
| Saved-artefact count | **29** | Was 17. |

---

## 27. v0.8 `sim.py` modular refactor (2026-06-23)

### 27.1 Motivation

`src/cag/abm/sim.py` had grown to **2755 lines** by end of v0.7, accumulating responsibilities far outside its orchestration mandate: network connectivity repair, every plot generator, all result post-processing builders, CSV schema and IO, JSON serialisation, and checkpoint mechanics. The v0.7 outputs-expansion (29 saved artefacts, full prompt capture, agent timeline) made the file's diagnostic surface very rich but also made its structural responsibilities increasingly conflated. Reading `sim.py` no longer revealed the simulation loop; it required scrolling past hundreds of lines of matplotlib code and JSON-writing helpers.

The refactor is the first item on the v0.8 **refactor track** — a label that will hold all subsequent pure structural splits this cycle. Behaviour-track work (memory architecture v2, target-policy scoping, blind-spot fix in `_run_one_day`) is deliberately gated on this refactor landing first, so that the next round of changes to `_run_one_day` does not also touch plot code or CSV schemas.

### 27.2 What moved where

| New module | Lines | Responsibility |
|---|---:|---|
| [src/cag/abm/sim.py](../src/cag/abm/sim.py) | **838** | Orchestration only: `run_simulation`, `_run_one_day`, `_resolve_runtime`, `SIM_CONFIG`. |
| [src/cag/abm/network_repair.py](../src/cag/abm/network_repair.py) | 263 | v0.7 3-layer connectivity defence: `_adjust_network_params_for_small_n`, `_auto_connect_components`, `_log_network_summary`, `_safe_network_diagnostics`. |
| [src/cag/io/aggregators.py](../src/cag/io/aggregators.py) | 506 | `_collect_results` post-processing: `collect_agent_attributes`, `build_package_index_by_bucket`, `build_opinion_shares_by_bucket`, `build_day0_vs_dayN_shifts`, `build_calibration_table`, `build_message_flow`, `build_agent_timeline`. |
| [src/cag/io/plots.py](../src/cag/io/plots.py) | 555 | `save_result_plots` + every per-figure plotter (`plot_package_index_by_bucket`, `plot_opinion_shares_by_bucket`, `plot_gap_widening`, `plot_calibration_by_policy`, `plot_network_graph`, plus the legacy single-policy plotters). |
| [src/cag/io/results.py](../src/cag/io/results.py) | 512 | `save_results`, `_RESULT_CSV_SCHEMAS`, `_write_all_csvs`, `_safe_network_snapshot`, JSON config/diagnostics serialisation. |
| [src/cag/io/checkpoint.py](../src/cag/io/checkpoint.py) | 366 | `_write_checkpoint`, `_load_checkpoint`, `_CHECKPOINT_SKIP_KEYS`, resume-key validation, `sim_step` rehydration logic. |

Total: ~3040 lines across 6 focused modules vs. one 2755-line file. The +285-line overhead is import boilerplate and module-level docstrings in each new file.

### 27.3 Validation

End-to-end NB 32 smoke ([notebooks/32_v06_outputs_smoke.ipynb](../notebooks/32_v06_outputs_smoke.ipynb), 10 agents × 2 alternating package-mode days, `gpt-5-mini`, `debias=True`, `random_seed=42`) re-run against the pre-refactor baseline. See [docs/result_report.md](result_report.md) v0.8 entry for the full regression-validation matrix. Headline:

- **Deterministic outputs bit-identical:** `config.json`, `ground_truth.csv`, `package_ground_truth.csv`, `agent_attributes.csv`, `network_snapshot.json` (10 nodes, 9 edges, bucket distribution `{A-only:1, B-only:1, both:3, neither:5}`).
- **All 22 LLM-driven CSVs match in schema and row count.**
- **Numeric distributional stats** (mean abs_shift, calibration MAE per bucket, signed shifts) within `gpt-5-mini @ T=0.5` stochastic noise.
- **Test suite:** 538 passed, 1 skipped, 21 subtests passed (unchanged from end of v0.7). No test rewrites required; imports updated to the new module paths where symbols moved.

### 27.4 What this refactor preserves (contracts)

- **Determinism path** through `_resolve_runtime` → network construction → ground-truth collection → `agent_attributes` serialisation.
- **CSV schema contract** on all 22 result CSVs (column names, dtypes, sort order).
- **JSON contract** on `config.json`, `network_diagnostics.json`, `network_snapshot.json`.
- **Call-count contract**: number of LLM invocations per `(agent, day, policy)` is unchanged.
- **Resume contract**: `_RESUME_HARD_KEYS`, `_RESUME_SOFT_KEYS`, and `sim_step` max-restore logic preserved.

### 27.5 What this refactor explicitly does NOT cover

- Long-horizon (>2 day) behaviour — validation horizon matches the v0.7 NB 32 smoke.
- The memory-architecture v2 changes (Day-0 anchor compression, target-policy scoping in `assemble_context`, blind-spot fix in `_run_one_day` reordering, within-day previous-policy answers, unified daily summaries). Those are the behaviour track, gated on this refactor.

### 27.6 No `__version__` bump

v0.8 is a refactor-only label. The version bump is held until the next behaviour-bearing change. This avoids the v0.5/v0.6/v0.7 pattern where versions advanced ahead of `__version__` strings across modules and then needed a coordinated bulk-bump catch-up.

---

## 28. v0.8 v2 tiered memory architecture (2026-06-23)

### 28.1 Motivation

The v0.7 stack stitched four memory mechanisms together: (a) full reflections kept verbatim until compressed; (b) a `daily_summaries` dict written once per agent per day by `manage_memory()`; (c) a one-shot `compress_day0_anchor()` LLM call that re-summarised each agent's Day-0 rationale into a compact anchor block; (d) the per-policy slice of `assemble_context()`. The v0.7 NB-31 fix surfaced two underlying issues with this composition. First, the Day-0 anchor was being summarised *away* from the original rationale via a separate LLM call, introducing a drift surface for an LLM-driven write that always conveyed the same numeric position. Second, package-mode surveys needed to see cross-policy reflections (which `assemble_context()` filtered out by per-policy `policy_id`) while still anchoring the prompt to *the specific policy being asked* — a split the v0.7 single-`policy_id` API could not express.

### 28.2 The v2 six-section context order

`assemble_context(day, policy_id, target_policy_id)` in [src/cag/abm/agent.py](../src/cag/abm/agent.py) now builds the system prompt as the following ordered concatenation, skipping any section that is empty:

```
§1 Persona + values             always (get_persona())
§2 Day-0 anchor                 verbatim Day-0 rationale for target_policy_id
§3 Summary of recent days       daily_summaries for days < d-1
§4 Recent reflections           reflections from days d-1 and d
§5 Own reasoning d-1, d         survey_reasoning for target_policy_id (recent)
§6 Today's other answers        package mode only: prior answers in day d
                                for OTHER policies (target_policy_id excluded)
```

The split between `policy_id` (context scope) and `target_policy_id` (question scope) is the central v2 invariant. In single-policy mode the two are equal. In **package mode**, the EOD survey passes `context_policy_id=PACKAGE_SCOPE` (so cross-policy reflections survive §4's `policy_id` filter) but `target_policy_id=policy_id` (so §2, §5, §6 are narrowed to the specific policy being asked). The §3 + §4 filter and the §2 + §5 + §6 target scope are *independent dimensions*, not one collapsed scope.

### 28.3 Day-0 anchor compression removed

The pre-v2 architecture had `compress_day0_anchor()` re-summarise the Day-0 rationale (a verbose first-person paragraph from the LLM) into a 1–2-sentence "anchor block" that was then injected into every subsequent day's context. The new architecture reads the verbatim Day-0 rationale **directly from `survey_reasoning[target_policy_id]`**. Specifically:

- `agent.day0_anchors = {}` dict initialisation removed from `SurveyedCitizen.__init__`.
- `compress_day0_anchor()` method removed.
- Post-`_run_day0` compression loop removed from [src/cag/abm/sim.py](../src/cag/abm/sim.py).
- `day0_anchors.csv` removed from `_RESULT_CSV_SCHEMAS` in [src/cag/io/results.py](../src/cag/io/results.py).
- `day0_anchors.csv` hydration block and the `agent.day0_anchors = {}` reset line removed from [src/cag/io/checkpoint.py](../src/cag/io/checkpoint.py).
- `_section_day0_anchor()` simplified to read `survey_reasoning.get(target_policy_id, [])` directly.

**Effect:** one fewer LLM call per agent at Day 0 (n=100 agents × 6 policies → ~600 calls saved per run); the §2 text is now provably the same string the agent wrote during the Day-0 rationale step.

### 28.4 Unified manage_memory cadence

`manage_memory(day, policy_id, …)` is now called once per agent per day, **before** the EOD survey. If `day > 2`, it compresses day `d-2` into a single `daily_summaries[(d-2, policy_id)]` entry via `compress_daily_memory()` (and via `compress_memories()` underneath). Days `d-1` and `d` remain as full verbatim reflections in the "vivid window" (§4 and §5 above). This is the same compression policy as v0.7, but now with no `compress_day0_anchor()` side-call.

### 28.5 Test coverage and ordering invariants

[tests/test_memory.py](../tests/test_memory.py) covers:

- `TestSectionOrder` — every legal combination of populated sections renders the six in the canonical order; missing sections are skipped (no blank lines, no orphan headers).
- `TestDay0AnchorSection` — §2 is always sourced from `survey_reasoning[target_policy_id][0]` (the Day-0 entry), is target-scoped (one policy's anchor, not all six), and is verbatim.
- `TestSectionOrder.test_full_package_mode_section_order` — package-mode survey path renders §1 + §2 (target-scoped) + §3 + §4 + §5 (target-scoped) + §6 (target-scoped, excludes the policy being asked), in that order.
- `TestCompressDay0Anchor` removed (the method no longer exists).

Test suite: **556 passed, 1 skipped** (was 538 at end of v0.7; +18 from new section-order tests).

### 28.6 Backwards compatibility

- Existing checkpoints written under v0.7 do not contain `day0_anchors.csv` consumers in the new code path; the file is silently ignored if present. Old runs in `data/output/experiments/` are unaffected.
- `_RESUME_HARD_KEYS` and `_RESUME_SOFT_KEYS` are unchanged. A resume from a v0.7 checkpoint into v0.8 succeeds; the §2 anchor is rebuilt from `survey_reasoning` at the first `assemble_context()` call.
- The `day0_anchor` SIM_CONFIG key (singular, the *anchor-mode* selector with values `llm_survey` / `ground_truth` / `ground_truth_with_rationale`) is **unchanged** and still in `SIM_CONFIG`. It controls how Day-0 is *seeded*, not how it is *compressed* — the latter no longer exists.

---

## 29. v0.8 operational fixes and researcher-onboarding doc (2026-06-23)

A small cluster of operational cleanups landed in the same v0.8 cycle as the refactor and v2 memory work.

### 29.1 Dead `SIM_CONFIG["output_dir"]` removed

The key was never consumed. [src/cag/__main__.py](../src/cag/__main__.py) reads `--outdir` (default `data/output/experiments`) and passes it directly to `save_results(output_dir=…)`. Removed from `SIM_CONFIG` in [src/cag/abm/sim.py](../src/cag/abm/sim.py), from `_base_config()` in [tests/test_checkpoint.py](../tests/test_checkpoint.py), and from [notebooks/32_v06_outputs_smoke.ipynb](../notebooks/32_v06_outputs_smoke.ipynb) (which has a `set(config) == set(SIM_CONFIG)` parity assertion). `SIM_CONFIG` now has 33 keys (was 34). Not in `_RESUME_HARD_KEYS` or `_RESUME_SOFT_KEYS`, so resume contracts are unaffected.

### 29.2 Network-type-aware `[peer]` config-log line

`_log_experiment_config()` in [src/cag/abm/sim.py](../src/cag/abm/sim.py) previously printed `[peer] k_peers_per_day=K  network_type=T  p_intra=X  p_inter=Y` — but `p_intra` / `p_inter` are SBM-only legacy flat keys, misleading for `watts_strogatz` (`k`, `beta`), `barabasi_albert` (`m`), `erdos_renyi` (`p`), or `homophily_weighted` (`scale`, `threshold`, `attributes`). The line now renders the resolved params dict via `_resolve_network_params(cfg)`:

```
[peer] k_peers_per_day=K  network_type=stochastic_block  params={p_intra=0.15, p_inter=0.05}
[peer] k_peers_per_day=K  network_type=watts_strogatz     params={k=8, beta=0.2}
[peer] k_peers_per_day=K  network_type=barabasi_albert    params={m=3}
[peer] k_peers_per_day=K  network_type=erdos_renyi        params={p=0.10}
[peer] k_peers_per_day=K  network_type=homophily_weighted params={} (builder defaults)
```

Future network types added to `NETWORK_TYPES` automatically render correctly — no log-code change needed.

### 29.3 AIRE Quickstart §6 first-time-model-download callout

[docs/AIRE_Quickstart.md](../docs/AIRE_Quickstart.md) §6 ("First real experiment — split50 Run-14") gained a `> **Important — first-time model download.**` blockquote between the wall-clock estimate and the `sbatch --time=06:00:00` example. Explains that the first submission with a model not yet in the Hugging Face cache can exceed the **1500 s** vLLM-readiness wait baked into `scripts/aire/run.sh`, and recommends `--time=06:00:00` on that first submission. Subsequent runs warm from cache in <2 min and the standard wall-clock is fine.

### 29.4 Code Tour — researcher onboarding doc

[docs/Code_Tour.md](../docs/Code_Tour.md) is a new ~25-page walkthrough of `src/cag/` aimed at a newcomer who knows the science but has not opened the source code. Structure:

- **A. Audience + conventions.**
- **B. 30-minute skim sequence** — five files in order (`__main__.py` → `presets.py` → `sim.py` → `agent.py` → `io/results.py`).
- **C. 15 file-by-file walkthroughs** — one-sentence summary + 2–5 key names + a single concrete breadcrumb per file. Medium depth on `sim.py` and `agent.py` with annotated excerpts; lighter elsewhere.
- **D. Two side-trips** — the political-exposure affinity-rank mechanism (5-step explanation with the literature-anchoring rationale); the v2 memory architecture with a fully annotated example `survey_assembled_context.csv` row.
- **E. Cookbook** — 6 recipes (add a 7th policy, swap LLM provider, new exposure preset, new message set, trace one agent, debug a survey response).
- **F. Glossary** — 11 terms (PACKAGE_SCOPE, debias, day0_anchor modes, reach_*, audience_cap, political_exposure_mode, affinity_weights, thinking, P-A/P-B/C, package mode, vivid window / gist memory).
- **G. AIRE pre-flight checklist** — 10 copy-pasteable steps plus 4 common pitfalls.

The doc is model-agnostic; it does not assume the reader will use any particular provider. It pairs with [docs/AIRE_Quickstart.md](../docs/AIRE_Quickstart.md) for HPC submission and [docs/USER_GUIDE.md](../USER_GUIDE.md) for the canonical research config.

### 29.5 NB 34 v2-memory smoke

[notebooks/34_memory_v2_smoke.ipynb](../notebooks/34_memory_v2_smoke.ipynb) is a paired smoke for v0.8 §28: end-to-end run with the v2 6-section context order, asserting that §2 reads verbatim from `survey_reasoning`, §3 + §4 respect the `policy_id` filter, and §5 + §6 are target-scoped. The notebook is configured for local Qwen3-8B-4bit (`provider="local"`). Local Apple-Silicon throughput proved too low on this laptop for a Day-0 survey on n=10 agents in a reasonable time; AIRE re-run is the planned path. The notebook's diagnostic cells are valid regardless of LLM backend.

---
