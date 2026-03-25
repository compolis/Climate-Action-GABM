# Generative Agent-Based Model of Climate Policy Opinion Dynamics

## Full Design Specification — v1.0

---

## 1. Overview

This simulation models how citizen opinions on climate-related policies evolve under the influence of competing political messaging and peer-to-peer deliberation. LLM-powered citizen agents — initialized from real survey data — are placed in a networked social environment where two opposing political group agents broadcast persuasive messages and citizens converse with one another. Opinion is measured periodically using the original survey instrument, enabling direct validation against empirical data.

### Core Research Questions

- How do competing political messages shape citizen opinions on climate policy over time?
- Does peer deliberation amplify, moderate, or redirect the effects of political persuasion?
- How does the order of exposure (political messaging vs. peer conversation) affect opinion trajectories?
- What role does network structure (echo chambers vs. cross-cutting ties) play in opinion dynamics?

---

## 2. Agent Types

### 2.1 Citizen Agents

Each citizen agent represents a real survey respondent. The agent is constructed from individual-level survey data including:

- **Socio-demographics:** Age, gender, education, income, region, etc.
- **Political identity:** Party affiliation, ideology, political engagement.
- **Prior voting behavior:** Past election choices.
- **Core value indicators:** Multiple indicators capturing underlying value orientations.
- **Baseline policy opinions:** Support/opposition on 6–12 climate-related policies.

This data is converted into a **natural-language persona prompt**, which the LLM (via API or local instance) adopts as its identity for the duration of the simulation.

**Example persona prompt (illustrative):**

```
You are a 54-year-old man living in a rural area. You have a high school education
and work in manufacturing. You identify as politically conservative and voted
Republican in the last two elections. You value economic stability and personal
freedom highly, and are skeptical of government regulation. You attend church
regularly and are active in your local community. You are somewhat concerned about
the environment but believe economic growth should not be sacrificed for
environmental protection.
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
| A        | Strongly Against   | -3      |
| B        | Against            | -2      |
| C        | Somewhat Against   | -1      |
| D        | Neutral            |  0      |
| E        | Somewhat Support   | +1      |
| F        | Support            | +2      |
| G        | Strongly Support   | +3      |

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

#### Phase C: Peer Conversation (Citizen-to-Citizen)

Citizens converse with a random subset of their network neighbors (controlled by `k_conversations_per_day`). Citizens exchange their current thinking on the target policy through natural-language messages.

**Update mode: Simultaneous (synchronous).**

All citizen messages are generated based on their **current state** before any reflections occur. This ensures no citizen's updated thinking influences another citizen's message within the same phase, preventing cascade effects.

**Procedure:**

1. **Message generation:** Each citizen generates a message for each selected neighbor, expressing their current thinking on the target policy.
2. **Message delivery:** All messages are collected.
3. **Reflection:** Each citizen who received peer messages produces a private reflection summarizing how the conversation affected their thinking.

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

### 7.3 Peer Conversations Per Day

On each day during Phase C, each citizen does **not** talk to all network neighbors. Instead, they converse with a random subset of `k` neighbors.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `k_conversations_per_day` | Number of peer conversations per citizen per day | 2–3 |

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
| `k_conversations_per_day` | int | 3 | Peer conversations per citizen per day |
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
                Produce private reflection on peer conversation
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

*Specification version 1.0 — produced during iterative design session.*
*All design decisions are documented and configurable for experimental variation.*
