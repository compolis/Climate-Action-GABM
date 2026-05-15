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

---

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
