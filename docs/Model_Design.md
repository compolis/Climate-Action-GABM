# Generative Agent-Based Model of Climate Policy Opinion Dynamics

## Full Design Specification — v1.0

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
