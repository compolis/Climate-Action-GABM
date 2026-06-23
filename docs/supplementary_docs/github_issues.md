# Climate-Action-GABM — Planned GitHub Issues

## About This Document

This file contains the full implementation plan for the Climate-Action-GABM MVP, broken into 10 GitHub issues across 5 dependency phases. Each issue is self-contained with enough context for any developer to pick up and implement independently.

**Source:** All issues are derived from the design specification in [Model_Design.md](Model_Design.md).

---

## Project Context (Read This First)

### What Is This Project?

Climate-Action-GABM is a **Generative Agent-Based Model** (GABM) that simulates how citizen opinions on climate-related policies evolve under the influence of competing political messaging and peer-to-peer messaging. It is a research tool, not a product.

**How it works at a high level:**

1. **200 citizen agents** are created from real YouGov survey data (UK, January 2024). Each agent has a detailed demographic profile, political history, and psychological value scores.
2. Each agent is given a **natural-language persona prompt** derived from their survey data, which an LLM adopts as its identity.
3. Two **political group agents** (pro-climate and anti-climate) broadcast persuasive messages to subsets of citizens.
4. Citizens **exchange messages with network neighbors** (peer messaging).
5. After each simulated day, citizens are **re-surveyed** on 6 climate policies using the original survey instrument (A–G scale, mapped to -3 to +3).
6. Opinion shifts are **clamped** to enforce realistic change limits (max ±1 per day).
7. A **tiered memory system** compresses older reflections into summaries to manage LLM context windows.
8. Output: CSV trajectories of opinions over time + panel plots.

### Codebase Structure

```
src/cag/
├── __init__.py              # Package version
├── __main__.py              # Entry point: loads data, creates agents, runs simulation
├── abm/
│   ├── __init__.py
│   ├── agent.py             # SurveyedCitizen class (inherits gabm.Citizen)
│   ├── environment.py       # SurveyedNation class (inherits gabm.Nation)
│   ├── attributes/          # Attribute maps (education, ethnicity, income, politics, narratives, etc.)
│   │   ├── education.py     # SurveyEducationMap (18 levels)
│   │   ├── ethnicity.py     # SurveyEthnicityMap (6 categories)
│   │   ├── family.py        # SurveyFamilyMap (parent/not)
│   │   ├── income.py        # SurveyIncomeMap (15 brackets)
│   │   ├── narratives.py    # Value/orientation scales (Schwartz values, SDO, EDO, RWA)
│   │   ├── opinion.py       # Re-exports gabm opinion classes (currently minimal)
│   │   ├── politics.py      # SurveyPoliticsMap (7-point left-right scale)
│   │   └── region.py        # UKRegionMap (13 UK regions)
│   └── democracy/
│       └── elections/
│           ├── brexit.py    # Brexit referendum vote classes
│           └── ukge2019.py  # 2019 UK General Election vote classes
├── io/
│   └── survey.py            # load() function for YouGov CSV data with validation
tests/
├── test_agent.py            # SurveyedCitizen persona and vote tests (passing)
├── test_brexit_vote.py      # Brexit vote mapping tests (passing)
└── test_ukge2019_vote.py    # UKGE2019 vote mapping tests (passing)
```

### Key Dependencies

| Dependency | Version | What It Provides |
|------------|---------|------------------|
| `gabm` | 0.2.18 | Base classes (`Citizen`, `Nation`, `Group`), attribute system (`GABMAttributeMap`, `GABMID`), opinion model (`OpinionTopicID`, `Opinion`), election framework, API key reader (`gabm.io.read_api_keys`). The `gabm` library is a separate repository where the project lead is also a developer. |
| `pandas` | 3.0.1 | Data loading and manipulation |
| `networkx` | 3.6.1 | Network/graph operations for citizen social networks |

**Important:** gabm's `LLMService.send()` is an **abstract base class** that accepts only a single string prompt. It does **not** support chat-style system/user message roles. gabm's `SurveyConversation` is an empty placeholder. Therefore, this project builds its own LLM chat wrapper (`src/cag/io/llm.py`).

### What Already Exists and Works

- `SurveyedCitizen` — agent class with demographic attributes, persona generation (`get_persona()`), and narrative generation (`get_narrative()`)
- `SurveyedNation` — environment class with all attribute maps loaded
- Survey data loader (`survey.py`) with column validation and filtering rules
- All attribute maps (education, ethnicity, income, politics, family, region, narratives)
- Election vote classes (Brexit, UKGE2019)
- `__main__.py` — loads survey data, creates 200+ agents, logs sample personas
- 8 passing tests

### What We Need to Build (This Issue Set)

- Climate policy definitions and survey question constants
- LLM chat wrapper (system + user message roles)
- Baseline survey administration + persona fidelity validation
- Political agent message generation
- Social network creation + political exposure assignment
- Political broadcast → citizen reflection cycle
- Peer messaging with simultaneous update
- End-of-day survey with opinion shift clamping
- Tiered memory architecture (full → daily → weekly summaries)
- Simulation loop with configurable phase ordering + CSV/plot output

### Architecture Decisions

- **Medium-strict approach:** Core logic in `agent.py` and `environment.py`, with 3 justified new files:
  - `src/cag/io/llm.py` — LLM chat wrapper (I/O concern, analogous to existing `survey.py`)
  - `src/cag/abm/simulation.py` — Simulation config + orchestration (doesn't belong to a single agent or environment)
  - `src/cag/io/output.py` — CSV export + visualization (I/O concern)
- **No changes to gabm library** — we only extend its base classes
- **Voting history over political leaning** — exposure assignment uses Brexit + UKGE2019 votes as the primary signal (per research lead's specification)

---

## Dependency Graph

```
Phase 1 (Foundation):      Issue 1 ──┬── Issue 3
                           Issue 2 ──┤
Phase 2 (Agents+Network):  Issue 4 ──┼── Issue 5
                                     │
Phase 3 (Sim Phases):      Issue 6 ──┤
                           Issue 7 ──┼── Issue 8
                                     │
Phase 4 (Memory):          Issue 9 ──┤
                                     │
Phase 5 (Loop+Output):     Issue 10 ─┘
```

**Parallelisation opportunities:**
- Issues 1 and 2 are fully independent (can be done simultaneously).
- Issues 3 and 4 are independent of each other (both depend on 1+2).
- Issues 6 and 7 have independent agent-side methods but both need Issue 5 done first.
- Issues 9 and 10 can be partially parallelised (output can be stubbed while memory is built).

---

## Phase 1: Foundation

---

### Issue 1: Climate Policy Opinion System

**Labels:** `enhancement`, `phase-1`, `foundation`

#### Description

Define the 6 climate policy survey questions, A–G response scale, numeric mapping, and opinion shift clamping function as reusable constants. These are the core data definitions that every other issue depends on.

**Background:** The simulation tracks citizen opinions on 6 specific UK climate policies from the YouGov survey. Opinions are measured on a 7-point scale (A = Strongly oppose through G = Strongly support), mapped to integers -3 to +3. A clamping function limits how much an agent's opinion can change per simulated day, based on empirical evidence that persuasion effects are small (Coppock, *Persuasion in Parallel*).

#### What to build

1. Add to `src/cag/abm/attributes/opinion.py`:
   - `ClimatePolicyID` — an enum or `GABMID` subclass with 6 members:
     - `RENEWABLE_ENERGY` → CSV column `page5posttreatment6_1`
     - `BAN_FOSSIL_FUEL` → CSV column `page5posttreatment6_4`
     - `BAN_PETROL_CARS` → CSV column `page5posttreatment6_5`
     - `GREEN_HOUSING` → CSV column `page5posttreatment6_7`
     - `CARBON_TAX` → CSV column `page5posttreatment6_9`
     - `CLIMATE_COMPENSATION` → CSV column `page5posttreatment6_11`
   - `SURVEY_QUESTIONS: dict[ClimatePolicyID, str]` — full question text for each policy. The exact wording is in [Model_Design.md Section 3](Model_Design.md#3-baseline-measurement-validation-step). Each question starts with "Please say how much you support or oppose government policies that do the following:" followed by the specific policy.
   - `RESPONSE_SCALE: dict[str, int]` — `{"A": -3, "B": -2, "C": -1, "D": 0, "E": 1, "F": 2, "G": 3}`
   - `RESPONSE_LABELS: dict[str, str]` — `{"A": "Strongly oppose", "B": "Somewhat oppose", "C": "Slightly oppose", "D": "Neutral", "E": "Slightly support", "F": "Somewhat support", "G": "Strongly support"}`
   - `SURVEY_COLUMN_MAP: dict[ClimatePolicyID, str]` — maps each policy ID to its CSV column name (for looking up real survey responses)
   - `clamp_opinion_shift(previous: int, new: int, max_shift: int = 1) -> int`:
     ```python
     def clamp_opinion_shift(previous: int, new: int, max_shift: int = 1) -> int:
         shift = new - previous
         clamped_shift = max(min(shift, max_shift), -max_shift)
         return previous + clamped_shift
     ```

2. Add to `src/cag/io/survey.py`:
   - Add the 6 policy column names (`page5posttreatment6_1`, `_4`, `_5`, `_7`, `_9`, `_11`) to the `REQUIRED_COLUMNS` list if not already present, so the data loader validates they exist.

#### Reference

- [Model_Design.md Section 3](Model_Design.md#3-baseline-measurement-validation-step) — survey questions table, response scale table
- [Model_Design.md Section 4.4](Model_Design.md#44-opinion-shift-calibration-post-hoc-clamping) — `clamp_opinion_shift()` spec with code
- `sandbox/ajay_sandbox/survey_dict.py` — original `SURVEY_QUESTIONS` dict (for reference only; implement fresh in `opinion.py`)

#### Acceptance Criteria

- [ ] All 6 policies importable as `ClimatePolicyID` members
- [ ] `SURVEY_QUESTIONS[ClimatePolicyID.RENEWABLE_ENERGY]` returns exact question text
- [ ] `RESPONSE_SCALE["A"] == -3`, `RESPONSE_SCALE["G"] == 3`
- [ ] `clamp_opinion_shift(-1, 2, max_shift=1) == 0` (raw shift of +3, clamped to +1 → -1+1 = 0)
- [ ] `clamp_opinion_shift(2, 2, max_shift=1) == 2` (no shift, no change)
- [ ] `clamp_opinion_shift(1, -2, max_shift=1) == 0` (raw shift of -3, clamped to -1 → 1-1 = 0)
- [ ] `make test` passes (all existing tests still pass)
- [ ] New test file: `tests/test_opinion.py` with tests for scale mapping, clamping edge cases, and `ClimatePolicyID` enumeration

---

### Issue 2: LLM Chat Integration

**Labels:** `enhancement`, `phase-1`, `foundation`

#### Description

Create a thin wrapper for sending chat-style prompts (system message + user message) to LLM providers. This is the foundation for all LLM interactions in the simulation — every agent method that talks to an LLM will call through this module.

**Background:** The simulation requires **chat-style prompting** where a system message establishes the agent's persona and a user message provides the task (e.g., "answer this survey question" or "reflect on this message"). The gabm library's `LLMService.send()` is an abstract base that accepts only a single string — it does not support system/user message separation. gabm's `SurveyConversation` is an empty placeholder. Therefore we build a simple utility module with functions (no class hierarchy).

#### What to build

1. Create `src/cag/io/llm.py` with three functions:

   **`send_chat(system_prompt, user_prompt, api_key, model, provider="openai", temperature=0.7) -> str`**
   - Sends a chat completion request using the provider's API with two messages: a system message (persona/context) and a user message (task/question).
   - Returns the assistant's text response as a string.
   - Minimum supported providers for MVP:
     - `"openai"` — uses the `openai` Python package's chat completions API. The `openai` package is already installed as a transitive dependency of gabm.
     - `"genai"` — uses the `google-genai` Python package for Gemini models. The `google-genai` package is already installed as a transitive dependency of gabm.
   - Raises `ValueError` for unsupported provider names.
   - Raises clear errors for missing/invalid API keys and API failures.

   **`load_api_key(provider, csv_path="data/api_key.csv") -> str`**
   - Reads the API key from the project's CSV file (`data/api_key.csv` has columns `api` and `key`). Can use `gabm.io.read_api_keys()` or a direct pandas/csv read.
   - Falls back to environment variables if CSV is not found: `OPENAI_API_KEY` for openai, `GENAI_API_KEY` for genai.
   - Raises `ValueError` if no key found from either source.

   **`parse_letter_response(response) -> str`**
   - Extracts a single letter A–G from a free-text LLM response.
   - Must handle common LLM response patterns:
     - Just the letter: `"B"`
     - Letter with punctuation: `"B."`, `"B,"`
     - Letter with explanation: `"My answer is B - Somewhat oppose"`, `"Based on my values, E."`
     - Letter at start: `"E. I slightly support..."`, `"G\n\nI strongly support..."`
   - Returns the uppercase letter as a single character string.
   - Raises `ValueError` if no valid letter A–G can be extracted.

2. Keep the interface simple — plain functions, no class hierarchy.

#### Reference

- gabm's `LLMService` base class in `gabm.io.llm` — understanding the existing abstract interface we are supplementing
- `data/api_key.csv` — CSV with columns `api` and `key` (one row per provider)
- OpenAI Python client docs: chat completions API
- Google GenAI Python client docs: `google.genai` module

#### Acceptance Criteria

- [ ] `send_chat("You are a helpful assistant", "Say hello", api_key, model="gpt-4o-mini")` returns a non-empty string
- [ ] Works with at least one provider end-to-end (OpenAI or Gemini)
- [ ] `parse_letter_response("I would choose B - Somewhat oppose")` returns `"B"`
- [ ] `parse_letter_response("Based on my values, E.")` returns `"E"`
- [ ] `parse_letter_response("G")` returns `"G"`
- [ ] `parse_letter_response("I'm not sure")` raises `ValueError`
- [ ] `load_api_key("openai")` returns a key string (from CSV or env var)
- [ ] `make test` passes

#### Notes

- Do **not** build response caching for MVP — gabm's cache system can be integrated later.
- Temperature is a parameter (default 0.7) as specified in [Model_Design.md Section 9](Model_Design.md#9-simulation-configuration).
- This module will be imported by `agent.py` for all LLM interactions throughout the simulation.

---

## Phase 2: Political Agents + Network

---

### Issue 3: Baseline Survey Administration (Day 0)

**Labels:** `enhancement`, `phase-2`, `core`
**Depends on:** Issue 1, Issue 2

#### Description

Before the simulation begins, each citizen agent answers the 6 climate policy survey questions via LLM, using their persona prompt as the system message. These baseline responses are compared to the real human respondent's survey answers to assess **persona fidelity** — how well the LLM reproduces the attitudes of the person it represents.

**Background:** This is the validation step described in [Model_Design.md Section 3](Model_Design.md#3-baseline-measurement-validation-step). The existing `SurveyedCitizen` class already has `get_persona()` and `get_narrative()` methods that produce a natural-language description of the agent's demographics and psychological profile. What's missing is the ability to use these as LLM prompts, administer the survey, and compare results to ground truth.

#### What to build

1. Add to `SurveyedCitizen` in `src/cag/abm/agent.py`:

   - **`opinion_history`** — a dict tracking each policy's opinion over time:
     ```python
     # Structure: {policy_id: [(day, raw_numeric, clamped_numeric), ...]}
     self.opinion_history: dict[ClimatePolicyID, list[tuple[int, int, int]]] = {}
     ```
     Initialized as empty dict in `__init__`.

   - **`administer_survey(policy_id, day, api_key, model, provider="openai", temperature=0.7) -> tuple[str, int]`**
     - Builds system prompt: concatenation of `self.get_persona()` and `self.get_narrative()` (these already exist and return natural-language persona text).
     - Builds user prompt with the survey question from `SURVEY_QUESTIONS[policy_id]` plus instructions to respond with a single letter A–G.
     - Calls `send_chat()` from `cag.io.llm`.
     - Parses the LLM response using `parse_letter_response()`.
     - Maps the letter to a numeric value using `RESPONSE_SCALE` (from Issue 1).
     - Returns `(letter, numeric_value)`.

   - **`run_baseline(api_key, model, provider="openai") -> dict`**
     - Calls `administer_survey()` for all 6 policies with `day=0`.
     - Stores each result in `opinion_history` as `(0, numeric, numeric)` (no clamping for baseline).
     - Returns a dict: `{policy_id: (letter, numeric)}`.

   - **`get_real_survey_response(policy_id) -> int`**
     - Returns the real respondent's numeric answer from the original survey data.
     - This requires storing the original survey row on the agent at init time (see modification to `__main__.py` below).
     - Looks up the CSV column name from `SURVEY_COLUMN_MAP[policy_id]`, reads the value from the stored row, maps it to the -3 to +3 scale.

2. Add to `SurveyedNation` in `src/cag/abm/environment.py`:

   - **`run_baseline(api_key, model, provider="openai") -> pd.DataFrame`**
     - Iterates all agents in `self.agents_active`.
     - Calls each agent's `run_baseline()`.
     - Also calls each agent's `get_real_survey_response()` for each policy.
     - Builds a comparison DataFrame:
       | Column | Type | Description |
       |--------|------|-------------|
       | `agent_id` | int | Citizen ID |
       | `policy_id` | str | Policy name |
       | `llm_letter` | str | LLM's A–G response |
       | `llm_numeric` | int | LLM's numeric score (-3 to +3) |
       | `real_numeric` | int | Real survey respondent's score |
       | `match` | bool | Whether llm_numeric == real_numeric |
     - Logs summary: accuracy per policy, overall accuracy.
     - Returns the DataFrame.

3. Modify `src/cag/__main__.py`:
   - When creating each `SurveyedCitizen` from a survey row, store the full row (or at least the 6 policy columns) on the agent object so `get_real_survey_response()` can access it.

#### Reference

- [Model_Design.md Section 3](Model_Design.md#3-baseline-measurement-validation-step) — baseline measurement procedure, survey questions, response scale
- [Model_Design.md Section 13](Model_Design.md#13-validation-strategy) — validation strategy, persona fidelity (point 1)
- Existing methods: `SurveyedCitizen.get_persona()`, `SurveyedCitizen.get_narrative()` in `src/cag/abm/agent.py`

#### Acceptance Criteria

- [ ] Single agent baseline returns 6 letter responses (A–G), all valid
- [ ] `opinion_history` has 6 entries (one per policy), each with a single day-0 tuple
- [ ] Comparison DataFrame has correct schema and no null values
- [ ] `get_real_survey_response()` returns the correct value from the original CSV data
- [ ] Works end-to-end with 5 agents (this is a slow/integration test — can be marked as such)
- [ ] `make test` passes

---

### Issue 4: Political Agent Class

**Labels:** `enhancement`, `phase-2`, `core`
**Depends on:** Issue 1, Issue 2

#### Description

Create a `PoliticalAgent` class representing a fixed-stance political communicator that generates persuasive messages about climate policies via LLM. Two instances will be created: one pro-climate (Agent A) and one anti-climate (Agent B). These agents **do not update their opinions** — they are fixed message sources that broadcast to connected citizens.

**Background:** The design models two opposing elite voices (see [Model_Design.md Section 2.2](Model_Design.md#22-political-group-agents)). Each day, a political agent generates a persuasive message about the target policy, which is then delivered to its connected subset of citizens. This is a separate class from `SurveyedCitizen` because it has fundamentally different behaviour (message generation vs. opinion formation). We do not use gabm's `OpinionatedGroup` because political agents are message generators, not opinion holders.

#### What to build

1. Add `PoliticalAgent` class to `src/cag/abm/agent.py`:

   ```python
   class PoliticalAgent:
       def __init__(self, agent_id: str, side: str, system_prompt: str = None):
           # agent_id: unique identifier, e.g., "political_agent_a"
           # side: "pro_climate" or "anti_climate"
           # system_prompt: fixed persona text (defaults provided below)
           # connected_citizens: list of SurveyedCitizen references (set during exposure assignment)
   ```

   - **`generate_message(policy_id, api_key, model, provider="openai", temperature=0.7) -> str`**
     - Determines verb based on `self.side`: "supporting" (pro_climate) or "opposing" (anti_climate).
     - Builds user prompt: `"Generate a persuasive message (150–200 words) {verb} the following policy: {SURVEY_QUESTIONS[policy_id]}"`
     - Calls `send_chat()` with `self.system_prompt` as system message.
     - Returns the generated message text.

   - **`connected_citizens: list`** — list of `SurveyedCitizen` references that this agent broadcasts to. Populated during network/exposure setup (Issue 5). Initialized as empty list.

2. Default system prompts (used when `system_prompt=None`):

   - **Pro-climate (Agent A):**
     > "You are a political communicator who strongly supports climate action. You believe urgent government intervention is needed to address climate change. Your goal is to persuade citizens to support climate policies. Use evidence-based arguments, appeal to shared values, and emphasize the urgency and benefits of climate action."

   - **Anti-climate (Agent B):**
     > "You are a political communicator who opposes aggressive climate regulation. You believe current climate policies are economically harmful and overly restrictive. Your goal is to persuade citizens to oppose climate policies. Use economic arguments, appeal to personal freedom, and emphasize costs and unintended consequences of climate regulation."

3. System prompts are configurable — pass a custom string at init to override the defaults.

#### Reference

- [Model_Design.md Section 2.2](Model_Design.md#22-political-group-agents) — political group agent description
- [Model_Design.md Section 4.1](Model_Design.md#41-interaction-phases) — how political agents broadcast in phases P-A and P-B

#### Acceptance Criteria

- [ ] Can create pro and anti political agents with default system prompts
- [ ] `generate_message(ClimatePolicyID.CARBON_TAX, ...)` returns persuasive text (roughly 150–200 words)
- [ ] Pro-climate messages advocate FOR the policy; anti-climate messages argue AGAINST
- [ ] Custom system prompts work when passed at init
- [ ] `connected_citizens` is an assignable list (starts empty)
- [ ] `make test` passes

---

### Issue 5: Network + Political Exposure

**Labels:** `enhancement`, `phase-2`, `core`
**Depends on:** Issue 4

#### Description

Build a stochastic block model network connecting citizens and assign political exposure categories that determine which political agent's messages each citizen receives.

**Background:** The social network determines who exchanges messages during peer messaging (Phase C). It is implemented as a [NetworkX](https://networkx.org/) graph. The default topology is a **Stochastic Block Model** with two blocks representing political clusters — this models echo chambers vs. cross-cutting exposure, which is central to the research questions. See [Model_Design.md Section 7](Model_Design.md#7-network-structure).

Political exposure determines which political agent's broadcasts a citizen receives. Assignment is based on the citizen's **voting history** (Brexit referendum vote + 2019 General Election vote) as the primary signal, with political self-placement as secondary. This is documented in [Model_Design.md Section 8](Model_Design.md#8-political-exposure-attribute-based). The research lead specifically noted that voting history should be prioritised over self-reported political leaning.

#### What to build

1. Add to `SurveyedNation` in `src/cag/abm/environment.py`:

   - **Attributes:**
     - `network: nx.Graph` — the citizen interaction network (default: `None`)
     - `political_agent_a: PoliticalAgent` — pro-climate agent (default: `None`)
     - `political_agent_b: PoliticalAgent` — anti-climate agent (default: `None`)

   - **`create_network(network_type="stochastic_block", n_blocks=2, block_sizes=None, p_intra=0.15, p_inter=0.02, seed=42) -> nx.Graph`**
     - Creates a NetworkX graph using `nx.stochastic_block_model()`.
     - `block_sizes` defaults to an equal split of `len(self.agents_active)` (e.g., `[100, 100]` for 200 agents).
     - Each node is a citizen agent ID. Node attributes include `block` membership.
     - Stores the graph as `self.network` and returns it.
     - The `seed` parameter ensures reproducibility.

   - **`assign_political_exposure()`**
     - Iterates all citizens in `self.agents_active`.
     - For each citizen, determines exposure category using these rules (in priority order):
       | Brexit Vote | UKGE2019 Vote | Political Leaning | → Exposure |
       |-------------|---------------|-------------------|------------|
       | Leave | Conservative or Brexit Party | Any | `"B-only"` |
       | Remain | Labour, Green, or Lib Dem | Any | `"A-only"` |
       | Any | Any | Moderate (centrist) | `"both"` |
       | Leave | Labour/Green/Lib Dem (mixed) | Any | `"both"` |
       | Remain | Conservative (mixed) | Any | `"both"` |
       | Unknown/Don't Know | Unknown/Don't Know | Any | `"neither"` |
     - Sets `citizen.political_exposure` for each citizen.
     - Populates `self.political_agent_a.connected_citizens` (agents with `"A-only"` or `"both"`) and `self.political_agent_b.connected_citizens` (agents with `"B-only"` or `"both"`).

   - **`assign_network_blocks()`**
     - Maps citizens to network blocks based on exposure:
       - `"A-only"` → block 0
       - `"B-only"` → block 1
       - `"both"` and `"neither"` → distributed across blocks
     - Populates each citizen's `network_neighbors` from the graph adjacency.

2. Add to `SurveyedCitizen` in `src/cag/abm/agent.py`:
   - `political_exposure: str = "neither"` — one of `"A-only"`, `"B-only"`, `"both"`, `"neither"`
   - `network_neighbors: list = []` — list of neighboring `SurveyedCitizen` references (populated from graph)

#### Existing attributes available for exposure assignment

These are already on `SurveyedCitizen` from the current codebase:
- `self.brexit_vote_id` — `BrexitVoteID` enum: `UNKNOWN`, `REMAIN`, `LEAVE`, `DONT_KNOW`
- `self.ukge2019_vote_id` — `UKGE2019VoteID` enum: `UNKNOWN`, `CONSERVATIVE`, `LABOUR`, `LIBERAL_DEMOCRATS`, `BREXIT`, `GREEN`, `OTHER`, `DONT_KNOW`
- `self.politics_id` — `SurveyPoliticsID` enum: maps to 7-point left–right scale

#### Reference

- [Model_Design.md Section 7](Model_Design.md#7-network-structure) — stochastic block model, default parameters (p_intra=0.15, p_inter=0.02)
- [Model_Design.md Section 8](Model_Design.md#8-political-exposure-attribute-based) — exposure categories, assignment logic
- [Model_Design.md Section 8](Model_Design.md#8-political-exposure-attribute-based) note: "We should rely on voting history rather than just political leaning"
- NetworkX docs: [`nx.stochastic_block_model()`](https://networkx.org/documentation/stable/reference/generated/networkx.generators.community.stochastic_block_model.html)

#### Acceptance Criteria

- [ ] `create_network()` produces a graph with correct number of nodes (equal to number of agents)
- [ ] Edge density is approximately correct (within ±20% of expected for given p_intra, p_inter)
- [ ] Exposure assignment uses voting history (Brexit + UKGE2019) as primary signal
- [ ] All 4 exposure categories (`"A-only"`, `"B-only"`, `"both"`, `"neither"`) are represented in a realistic population
- [ ] `political_agent_a.connected_citizens` contains only agents with exposure `"A-only"` or `"both"`
- [ ] `political_agent_b.connected_citizens` contains only agents with exposure `"B-only"` or `"both"`
- [ ] Generating the same network with the same seed produces identical results
- [ ] `make test` passes
- [ ] New test file: `tests/test_network.py` — node count, exposure distribution, seed reproducibility

---

## Phase 3: Simulation Phases

---

### Issue 6: Political Broadcast Phases (P-A, P-B)

**Labels:** `enhancement`, `phase-3`, `simulation`
**Depends on:** Issue 3, Issue 4, Issue 5

#### Description

Implement the political agent broadcast → citizen reflection cycle. In each political broadcast phase, a political agent generates a persuasive message about the target policy and delivers it to its connected citizens. Each receiving citizen produces a **private reflection** — a short natural-language paragraph describing how the message affected their thinking. The citizen does NOT commit to a scale position at this stage.

**Background:** This is described in [Model_Design.md Section 4.1](Model_Design.md#41-interaction-phases) (Phases P-A and P-B). Reflections serve as chain-of-thought reasoning that feeds into the end-of-day survey. They also provide qualitative micro-data for understanding influence mechanisms. The hybrid opinion update model ([Section 5](Model_Design.md#5-opinion-update-mechanism-hybrid-reflections--end-of-day-survey)) separates internal reasoning (reflections) from formal measurement (survey).

#### What to build

1. Add to `SurveyedCitizen` in `src/cag/abm/agent.py`:

   - **`reflections: list[dict]`** — initialized as empty list in `__init__`.
     Each entry is a dict:
     ```python
     {"day": int, "phase": str, "text": str, "messages_received": list[str]}
     ```

   - **`receive_political_message(message, policy_id, phase, day, api_key, model, provider="openai") -> str`**
     - Builds system prompt from persona (initially just `get_persona()` + `get_narrative()`; will switch to `assemble_context()` in Issue 9).
     - Builds user prompt using the reflection prompt template from the design spec:
       ```
       You just received the following message:
       "{message}"

       In a few sentences, reflect on how this affects your thinking about {policy description}.
       Do not state a final position — just think out loud.
       ```
     - Calls `send_chat()`.
     - Appends a reflection dict to `self.reflections`.
     - Returns the reflection text.

2. Add to `SurveyedNation` in `src/cag/abm/environment.py`:

   - **`run_political_broadcast(phase, policy_id, day, api_key, model, provider="openai")`**
     - Determines which political agent: `self.political_agent_a` for phase `"P-A"`, `self.political_agent_b` for `"P-B"`.
     - Agent generates a message via `generate_message(policy_id, ...)`.
     - Delivers the message to each citizen in that agent's `connected_citizens` list.
     - Each connected citizen calls `receive_political_message(message, ...)`.
     - Logs: the political message text, number of citizens reached, 1–2 sample reflections.

#### Reference

- [Model_Design.md Section 4.1](Model_Design.md#41-interaction-phases) — Phase P-A and P-B procedure, reflection prompt template
- [Model_Design.md Section 5.1](Model_Design.md#51-summary) — hybrid opinion update: reflections are private, no scale commitment

#### Acceptance Criteria

- [ ] Political agent generates a message for a given policy
- [ ] Only connected citizens receive the message (based on their exposure category)
- [ ] Each receiving citizen produces a non-empty reflection (~100–150 words)
- [ ] Reflection is stored in `citizen.reflections` with correct `day`, `phase`, and `messages_received` metadata
- [ ] Citizens NOT connected to the broadcasting agent produce NO reflection for that phase
- [ ] `make test` passes
- [ ] Test: run one P-A broadcast for 5 agents, verify the reflection count matches the number of connected agents

---

### Issue 7: Peer Messaging Phase (C)

**Labels:** `enhancement`, `phase-3`, `simulation`
**Depends on:** Issue 5, Issue 6

#### Description

Implement simultaneous peer-to-peer messaging. During Phase C, citizens exchange views on the target policy with a random subset of their network neighbors. The update is **synchronous (simultaneous)** — ALL citizen messages are generated based on their current state BEFORE any reflections occur. This prevents cascade effects where one citizen's updated thinking influences another's message within the same phase.

**Background:** This is the peer messaging mechanism from [Model_Design.md Section 4.1 (Phase C)](Model_Design.md#41-interaction-phases). The simultaneous update ensures that the order in which agents are processed doesn't affect outcomes. Each citizen exchanges messages with at most `k` neighbors per day (default: 2–3), controlled by the `k_peers_per_day` parameter ([Section 7.3](Model_Design.md#73-peer-messages-per-day)).

#### What to build

1. Add to `SurveyedCitizen` in `src/cag/abm/agent.py`:

   - **`generate_peer_message(policy_id, api_key, model, provider="openai") -> str`**
     - System prompt: persona + context (initially just persona; will use `assemble_context()` after Issue 9).
     - User prompt: `"Express your current thinking on the following policy in 2–3 sentences. Be genuine and conversational: {policy description}"`
     - Calls `send_chat()`, returns the message text.

   - **`receive_peer_messages(messages, policy_id, day, api_key, model, provider="openai") -> str`**
     - `messages` is a list of strings (the peer messages this citizen received).
     - Builds reflection prompt:
       ```
       You just had conversations with some of your peers about {policy description}.
       Here is what they said:

       1. "{message_1}"
       2. "{message_2}"
       ...

       In a few sentences, reflect on how these conversations affect your thinking.
       Do not state a final position — just think out loud.
       ```
     - Calls `send_chat()`, returns reflection text.
     - Stores in `self.reflections` with `phase="C"` and all peer messages in `messages_received`.

2. Add to `SurveyedNation` in `src/cag/abm/environment.py`:

   - **`run_peer_messaging(policy_id, day, k_peers=3, api_key="", model="", provider="openai")`**
     - **Step 1 — Select neighbors:** For each citizen, randomly select `min(k_peers, len(citizen.network_neighbors))` neighbors.
     - **Step 2 — Generate messages (SIMULTANEOUS):** Loop through ALL citizens and have each generate their peer message FIRST, collecting all messages before any reflections happen.
     - **Step 3 — Deliver + Reflect:** Build a mapping of which messages each citizen received. Each citizen who received messages calls `receive_peer_messages()`.
     - Logs: number of messages exchanged, sample messages and reflections.

#### Reference

- [Model_Design.md Section 4.1 (Phase C)](Model_Design.md#41-interaction-phases) — simultaneous update procedure
- [Model_Design.md Section 7.3](Model_Design.md#73-peer-messages-per-day) — `k_peers_per_day` (default: 2–3)

#### Acceptance Criteria

- [ ] Messages are generated for ALL citizens BEFORE any reflections occur (simultaneous update verified)
- [ ] Each citizen talks to at most `k` random network neighbors
- [ ] Reflections reference the actual peer messages received
- [ ] Citizens with no network neighbors produce no reflection (no error, just skip)
- [ ] Reflection stored with `phase="C"` and all peer messages in `messages_received` metadata
- [ ] `make test` passes
- [ ] Test: run one C phase for 10 agents, verify total message count ≤ k × 10

---

### Issue 8: End-of-Day Survey + Clamping

**Labels:** `enhancement`, `phase-3`, `simulation`
**Depends on:** Issue 3, Issue 6, Issue 7

#### Description

At the end of each simulated day, every citizen agent is re-administered the original survey for the target policy. The key difference from the baseline survey (Issue 3) is that the survey prompt now includes all reflections accumulated during that day's interaction phases (P-A, P-B, C), providing the agent with the full record of that day's experiences to inform its response. Raw LLM responses are then clamped to enforce realistic opinion shift limits.

**Background:** This implements the end-of-day survey from [Model_Design.md Section 4.3](Model_Design.md#43-end-of-day-survey) and the clamping from [Section 4.4](Model_Design.md#44-opinion-shift-calibration-post-hoc-clamping). The hybrid update model ([Section 5](Model_Design.md#5-opinion-update-mechanism-hybrid-reflections--end-of-day-survey)) means reflections feed into the survey response, but the formal opinion is only recorded at end-of-day.

#### What to build

1. Modify `SurveyedCitizen.administer_survey()` in `src/cag/abm/agent.py`:

   - **Context-aware system prompt:** Instead of just persona, include persona + all reflections from the current day in chronological order. (Before Issue 9 is implemented, this is a simple concatenation. After Issue 9, this will use `assemble_context()`.)
   - **Enhanced user prompt** that includes the previous day's response as a reference:
     ```
     Based on everything you've experienced today, please answer the following survey question.

     {SURVEY_QUESTION_TEXT}

     Respond with a single letter from A to G:
     A = Strongly oppose, B = Somewhat oppose, C = Slightly oppose,
     D = Neutral, E = Slightly support, F = Somewhat support, G = Strongly support

     Your previous response was: {LETTER} ({LABEL})

     Respond with only a single letter (A-G).
     ```
   - After getting the raw LLM response and parsing to numeric, apply `clamp_opinion_shift(previous_clamped, raw_numeric, max_shift)` from Issue 1.
   - Store BOTH raw and clamped values in `opinion_history`: `(day, raw_numeric, clamped_numeric)`.
   - For day 0 (baseline), no clamping is applied (there is no previous value).

2. Add to `SurveyedNation` in `src/cag/abm/environment.py`:

   - **`run_end_of_day_survey(policy_id, day, max_shift=1, api_key="", model="", provider="openai") -> pd.DataFrame`**
     - Iterates all agents, calls `administer_survey()` for each with the target policy.
     - Returns a DataFrame:
       | Column | Type | Description |
       |--------|------|-------------|
       | `agent_id` | int | Citizen ID |
       | `day` | int | Simulation day |
       | `policy_id` | str | Policy name |
       | `raw_letter` | str | Raw A–G response |
       | `raw_numeric` | int | Raw numeric (-3 to +3) |
       | `clamped_numeric` | int | After clamping |
       | `shift` | int | clamped - previous |
     - Logs: mean shift, shift distribution, number of agents clamped.

#### Reference

- [Model_Design.md Section 4.3](Model_Design.md#43-end-of-day-survey)
- [Model_Design.md Section 4.4](Model_Design.md#44-opinion-shift-calibration-post-hoc-clamping) — clamping function
- [Model_Design.md Section 5.1](Model_Design.md#51-summary) — hybrid update model

#### Acceptance Criteria

- [ ] Survey context includes all reflections from the current day (in chronological order)
- [ ] Previous response is referenced in prompt (provides anchoring)
- [ ] `opinion_history` stores both raw and clamped values as `(day, raw, clamped)`
- [ ] Clamped opinion never shifts more than ±max_shift from previous clamped value
- [ ] Day 0 (baseline) has no clamping applied (raw == clamped)
- [ ] DataFrame output has correct schema and reasonable values
- [ ] `make test` passes
- [ ] Test: verify clamping with known inputs (e.g., previous_clamped=1, raw=3, max_shift=1 → clamped=2)

---

## Phase 4: Memory

---

### Issue 9: Tiered Memory Architecture

**Labels:** `enhancement`, `phase-4`, `memory`
**Depends on:** Issue 6

#### Description

Implement a tiered memory system that manages each agent's LLM context across simulation days. As the simulation progresses, older reflections are compressed into daily summaries (medium detail) and then further into weekly summaries (low detail). This prevents the LLM context window from overflowing while preserving experiential continuity.

**Background:** Without memory management, an agent running for 30 days would accumulate hundreds of reflections, easily exceeding LLM context limits. The tiered approach (inspired by cognitive science) balances detail and compression. See [Model_Design.md Section 6](Model_Design.md#6-memory-architecture-tiered-memory-architecture-3) for the full design. The persona drift mitigation strategy (placing persona at both start and end of context, periodic re-injection) is also part of this issue.

#### Context assembly structure

On any given day `d`, the agent's full context is assembled as (in order):

```
[PERSONA BLOCK]                    ← get_persona() + get_narrative() — fixed
[WEEKLY SUMMARIES]                 ← for days 8+ (2–3 sentences covering ~7 days)
[DAILY SUMMARIES for days d-7…d-2] ← 2–3 sentence LLM-generated summary per day
[FULL REFLECTIONS for days d-1, d] ← retained verbatim (current + yesterday)
[OPINION TRAJECTORY]               ← "Day 0: C, Day 1: D, Day 2: D, ..."
[PERSONA REINFORCEMENT]            ← key persona attributes repeated (every N days)
```

#### What to build

1. Add to `SurveyedCitizen` in `src/cag/abm/agent.py`:

   - **`daily_summaries: dict[int, str]`** — `{day_number: summary_text}`. Initialized empty.
   - **`weekly_summaries: dict[int, str]`** — `{week_number: summary_text}`. Initialized empty.

   - **`compress_daily_memory(day, api_key, model, provider="openai") -> str`**
     - Collects all reflections from `self.reflections` where `r["day"] == day`.
     - Sends to LLM: `"Summarize the following reflections from day {day} in 2–3 sentences. Capture key attitudinal shifts and reasoning: {reflection_texts}"`
     - Stores result in `self.daily_summaries[day]`.
     - Returns the summary text.

   - **`compress_weekly_memory(week, api_key, model, provider="openai") -> str`**
     - Collects daily summaries for the days in that week (e.g., week 1 = days 1–7).
     - Sends to LLM: `"Summarize the following daily summaries from week {week} in 2–3 sentences: {daily_summary_texts}"`
     - Stores result in `self.weekly_summaries[week]`.
     - Returns the summary text.

   - **`assemble_context(day) -> str`**
     - Builds the full context string following the structure above.
     - Rules:
       - **Current day & yesterday (d and d-1):** Include full reflection texts.
       - **Days d-2 through d-7:** Include daily summaries (if they exist).
       - **Days older than d-7:** Include weekly summaries (if they exist).
       - **Opinion trajectory:** Compact list of all past survey responses: `"Day 0: C, Day 1: D, Day 2: D, ..."` (using letter codes from `opinion_history`).
       - **Persona reinforcement:** If `day % persona_reinforcement_interval == 0`, append key persona attributes at the end of the context.

   - **`manage_memory(day, persona_reinforcement_interval=5, api_key="", model="", provider="openai")`**
     - Called at end of each simulation day.
     - If `day > 2`: compress reflections from `day - 2` into a daily summary.
     - If `day > 7` and `day % 7 == 0`: compress the oldest batch of daily summaries into a weekly summary.

2. **Update all LLM-calling methods** to use `assemble_context(day)` as the system prompt instead of just persona:
   - `administer_survey()` — use `assemble_context(day)` as system prompt
   - `receive_political_message()` — use `assemble_context(day)` as system prompt
   - `generate_peer_message()` — use `assemble_context(day)` as system prompt
   - `receive_peer_messages()` — use `assemble_context(day)` as system prompt

#### Reference

- [Model_Design.md Section 6](Model_Design.md#6-memory-architecture-tiered-memory-architecture-3) — tiered memory overview
- [Model_Design.md Section 6.2](Model_Design.md#62-context-assembly) — context assembly order
- [Model_Design.md Section 6.3](Model_Design.md#63-summarization-process) — summarization process
- [Model_Design.md Section 6.4](Model_Design.md#64-persona-drift-mitigation) — persona reinforcement strategy

#### Acceptance Criteria

- [ ] Day 1: context contains only persona + current day reflections
- [ ] Day 3: context contains persona + full reflections (days 2–3) + current day
- [ ] Day 5: context contains persona + daily summary (day 3) + full reflections (days 4–5) + current day
- [ ] Day 10: context contains persona + weekly summary (week 1) + daily summaries + recent reflections
- [ ] Opinion trajectory string is included in context
- [ ] Persona reinforcement appears at end every N days
- [ ] Daily summaries are 2–3 sentences each
- [ ] Weekly summaries are 2–3 sentences each
- [ ] `make test` passes

---

## Phase 5: Simulation Loop + Output

---

### Issue 10: Simulation Loop + Phase Ordering + Output

**Labels:** `enhancement`, `phase-5`, `simulation`, `output`
**Depends on:** All previous issues (blocking: Issues 8 and 9)

#### Description

Create the end-to-end simulation runner that wires all components together. This is the capstone issue. It includes a `SimulationConfig` dataclass (all configurable parameters), a `run_simulation()` function (the main loop), CSV output, and basic matplotlib visualization.

**Background:** The simulation loop follows the pseudocode in [Model_Design.md Section 11](Model_Design.md#11-simulation-pseudocode). Each day: execute interaction phases in configurable order → end-of-day survey → memory management. The phase ordering is a key experimental variable — all 6 permutations of [P-A, P-B, C] are valid conditions ([Section 4.2](Model_Design.md#42-phase-ordering)). Output format follows [Section 10](Model_Design.md#10-data-collection-and-output).

#### What to build

1. **Create `src/cag/abm/simulation.py`:**

   - **`SimulationConfig`** dataclass with all parameters from [Model_Design.md Section 9](Model_Design.md#91-master-parameter-table):
     ```python
     @dataclass
     class SimulationConfig:
         n_citizens: int = 200
         n_days: int = 30
         target_policies: list = None    # ClimatePolicyIDs; defaults to all 6, rotated
         phase_order: list = None        # e.g., ["P-A", "P-B", "C"]; defaults to this order
         max_shift: int = 1
         k_peers_per_day: int = 3
         network_type: str = "stochastic_block"
         p_intra: float = 0.15
         p_inter: float = 0.02
         block_sizes: list = None        # defaults to equal split
         persona_reinforcement_interval: int = 5
         llm_model: str = "gpt-4o-mini"
         llm_provider: str = "openai"
         llm_temperature: float = 0.7
         random_seed: int = 42
         output_dir: str = "data/output/experiments"
     ```

   - **`SimulationResults`** dataclass:
     ```python
     @dataclass
     class SimulationResults:
         opinion_trajectories: pd.DataFrame   # (agent_id, day, policy_id, raw_letter, raw_numeric, clamped_numeric)
         reflections: pd.DataFrame             # (agent_id, day, phase, reflection_text)
         baseline_validation: pd.DataFrame     # (agent_id, policy_id, llm_numeric, real_numeric, match)
         config: SimulationConfig
     ```

   - **`run_simulation(config, surveyed_nation) -> SimulationResults`**
     ```
     INITIALIZE:
         Load API key for config.llm_provider
         Create PoliticalAgent A (pro-climate) and B (anti-climate)
         Create network: surveyed_nation.create_network(...)
         Assign exposure: surveyed_nation.assign_political_exposure()
         Assign blocks: surveyed_nation.assign_network_blocks()

     BASELINE (Day 0):
         surveyed_nation.run_baseline(api_key, model, provider)

     DAILY LOOP (Day 1 to config.n_days):
         Determine target policy for today (rotate through config.target_policies)

         For each phase in config.phase_order:
             if phase == "P-A":
                 surveyed_nation.run_political_broadcast("P-A", policy, day, ...)
             elif phase == "P-B":
                 surveyed_nation.run_political_broadcast("P-B", policy, day, ...)
             elif phase == "C":
                 surveyed_nation.run_peer_messaging(policy, day, k_peers=config.k_peers_per_day, ...)

         End-of-day survey:
             surveyed_nation.run_end_of_day_survey(policy, day, config.max_shift, ...)

         Memory management:
             For each agent: agent.manage_memory(day, config.persona_reinforcement_interval, ...)

         Log progress (day number, mean opinion, shift stats)

     COLLECT AND RETURN:
         Build opinion_trajectories DataFrame from all agents' opinion_history
         Build reflections DataFrame from all agents' reflections
         Return SimulationResults
     ```

2. **Create `src/cag/io/output.py`:**

   - **`save_results(results, output_dir)`**
     - Creates a timestamped subdirectory under `output_dir` (e.g., `data/output/experiments/20260402_143000/`).
     - Saves:
       - `opinion_trajectories.csv`
       - `reflections.csv`
       - `baseline_validation.csv`
       - `config.json` (serialized `SimulationConfig` for reproducibility)

   - **`plot_opinion_trajectories(results, output_dir)`**
     - Creates a matplotlib panel plot per [Model_Design.md Section 10.4](Model_Design.md#104-primary-visualization):
       - X-axis: simulation day (0 to n_days)
       - Y-axis: opinion score (-3 to +3)
       - Individual agent trajectory lines (semi-transparent, alpha ~0.2)
       - Bold group-mean lines overlaid
       - Faceted by policy (1 subplot per policy, 2×3 or 3×2 grid)
       - Title includes phase ordering and key parameter values
     - Saves as PNG in the output directory.

3. **Update `src/cag/__main__.py`:**
   - Create `SimulationConfig` (defaults or from command-line arguments).
   - Existing code already loads survey data + creates `SurveyedNation` and citizens.
   - After citizen creation: call `run_simulation(config, surveyed_nation)`.
   - After simulation: call `save_results()` and `plot_opinion_trajectories()`.

#### Reference

- [Model_Design.md Section 9](Model_Design.md#91-master-parameter-table) — full parameter table with defaults
- [Model_Design.md Section 10](Model_Design.md#10-data-collection-and-output) — output schemas (primary, secondary, tertiary)
- [Model_Design.md Section 10.4](Model_Design.md#104-primary-visualization) — panel plot specification
- [Model_Design.md Section 11](Model_Design.md#11-simulation-pseudocode) — simulation pseudocode
- [Model_Design.md Section 4.2](Model_Design.md#42-phase-ordering) — all 6 valid phase orderings

#### Acceptance Criteria

- [ ] `SimulationConfig` has all parameters from the design spec with sensible defaults
- [ ] Can run a 3-day simulation with 10 agents end-to-end (smoke test)
- [ ] All 6 phase orderings (`["P-A", "P-B", "C"]`, `["P-A", "C", "P-B"]`, `["P-B", "P-A", "C"]`, `["P-B", "C", "P-A"]`, `["C", "P-A", "P-B"]`, `["C", "P-B", "P-A"]`) are accepted and produce results
- [ ] Different phase orderings with the same seed produce different opinion trajectories
- [ ] CSV files are produced with correct schema in a timestamped directory
- [ ] `config.json` captures all parameters for reproducibility
- [ ] Panel plot renders and saves as PNG
- [ ] `make test` passes
- [ ] `make run-local` runs a small simulation end-to-end

---

## Summary

| Issue | Title | Phase | Files Modified/Created | Depends On | Can Parallel With |
|-------|-------|-------|----------------------|------------|-------------------|
| 1 | Climate Policy Opinion System | 1 | `attributes/opinion.py`, `io/survey.py`, `tests/test_opinion.py` | — | Issue 2 |
| 2 | LLM Chat Integration | 1 | **NEW:** `io/llm.py` | — | Issue 1 |
| 3 | Baseline Survey Administration | 2 | `agent.py`, `environment.py`, `__main__.py` | 1, 2 | Issue 4 |
| 4 | Political Agent Class | 2 | `agent.py` | 1, 2 | Issue 3 |
| 5 | Network + Political Exposure | 2 | `environment.py`, `agent.py`, `tests/test_network.py` | 4 | — |
| 6 | Political Broadcast Phases | 3 | `agent.py`, `environment.py` | 3, 4, 5 | Issue 7 (agent methods) |
| 7 | Peer Messaging Phase | 3 | `agent.py`, `environment.py` | 5, 6 | Issue 6 (agent methods) |
| 8 | End-of-Day Survey + Clamping | 3 | `agent.py`, `environment.py` | 3, 6, 7 | — |
| 9 | Tiered Memory Architecture | 4 | `agent.py` | 6 | Issue 10 (partially) |
| 10 | Simulation Loop + Output | 5 | **NEW:** `abm/simulation.py`, **NEW:** `io/output.py`, `__main__.py` | All | — |

All file paths are relative to `src/cag/`.
