# Climate-Action-GABM — Prompts & Personas Guide

> **⚠️ Superseded.** This document describes the pre-v0.5 prompts and the
> separate `get_persona()` / `get_narrative()` persona model. It is preserved
> for historical reference of the prompt wording used in the experimental
> runs under `data/output/experiments/` dated on or before 2026-05-15.
>
> The current canonical guide is
> [Prompts_and_Personas_Guide_v2.md](Prompts_and_Personas_Guide_v2.md),
> which reflects the v0.5 prompt overhaul (consistent first-person framing,
> merged persona, daily-context-aware end-of-day surveys, repaired Day-0
> rationale labels, and phase-tag-free reflection memory). See
> [Model_Design.md §20](Model_Design.md) for the change rationale.

A reader-friendly tour of every prompt the simulation sends to the LLM, plus the persona text that gives each agent its identity. The goal is that anyone — modeller, reviewer, supervisor, social scientist — can read this in one sitting and form an opinion on the design.

All quoted text is the **actual prompt template** used in code. Source files cited inline.

---

## 1. The cast: who talks to the LLM, and how

The simulation has two kinds of agents that talk to an LLM:

- **Citizens** (`SurveyedCitizen`) — one per simulated person, each carrying a real YouGov respondent's profile. They write reflections, peer messages, and survey answers.
- **Political agents** (`PoliticalAgent`) — exactly two of them, one `pro_climate` and one `anti_climate`. They emit broadcasts that exposed citizens read.

Every LLM call is structured the same way:

```
system prompt   →  "who you are right now and what you've been thinking"
user prompt     →  "here is the specific thing I want you to do"
```

For citizens, the **system prompt** is built fresh each time by `assemble_context()` — persona + values + recent reflections + Day-0 rationales. For political agents, the system prompt is a fixed campaign brief, written once.

The full source for prompts lives in [`src/cag/abm/agent.py`](src/cag/abm/agent.py).

---

## 2. The citizen persona — three layers

A citizen's identity is built from three layers, all derived from one row of the YouGov dataset:

| Layer | Method | Source attributes |
|---|---|---|
| **Persona** (demographics + politics) | `get_persona()` | age, gender, region, ethnicity, education, household income, parenthood, left/right self-placement, 2019 GE vote, 2016 Brexit vote |
| **Narrative** (values + worldview) | `get_narrative()` | Self-Transcendence, Self-Enhancement, Openness, Conformity-Tradition, Social Dominance Orientation (SDO), Environmental Dominance Orientation (EDO), Right-Wing Authoritarianism (RWA) |
| **Memory** (what's happened so far in the sim) | `assemble_context()` | older daily summaries, recent full reflections, Day-0 rationales |

These are concatenated, in that order, to form the system prompt for **every** citizen LLM call.

### 2.1 Two real persona examples (drawn from the example run, seed = 43)

**Citizen 1 — id 1923**

> Persona:
> *"I am a 32 year old female living in the Wales. My ethnicity is white. I have a University or CNAA higher degree (e.g. M.Sc, Ph.D). My gross household income is £40,000 - £44,999 per year. I am not a parent. I position myself fairly left-wing of the political spectrum. I voted for the Green party candidate in the 2019 General Election. I voted to remain in the 2016 EU Referendum."*
>
> Narrative:
> *"When it comes to my core values and worldview: I care about the people close to me and have a basic respect for nature, but I do not actively champion global equality or make environmental protection a primary, driving life focus. I am not strongly driven by the need to get ahead of others, impress people, or hold leadership positions… I am highly curious, adventurous, and love trying out new things… I do not feel strictly bound by traditional values… I strongly believe that all groups should have an equal chance to succeed… I believe that all lifeforms on Earth should be treated equally… I am highly skeptical of leaders…"*

**Citizen 2 — id 528**

> Persona:
> *"I am a 26 year old male living in the North West. My ethnicity is white. I have a University or CNAA higher degree (e.g. M.Sc, Ph.D). My gross household income is £60,000 - £69,999 per year. I am not a parent. I position myself fairly left-wing of the political spectrum. I voted for the Labour party candidate in the 2019 General Election. I voted to remain in the 2016 EU Referendum."*
>
> Narrative:
> *"When it comes to my core values and worldview: I am deeply committed to caring for nature, protecting the environment, and responding to the needs of others. I strongly believe in global harmony, equal opportunities for everyone, and actively helping those around me…"*

The persona-construction logic deliberately **omits** attributes that resolved to `"unknown"`, `"don't know"`, or `"other"` so the LLM is not told a confident-sounding lie. That is why personas vary in length and detail across citizens.

### 2.2 The "memory" layer — `assemble_context()`

After Day 0, the system prompt grows. The recipe is:

1. Persona + narrative (always).
2. **Older daily summaries** — each previous day older than yesterday is collapsed into a 2-sentence summary (`compress_daily_memory()` calls a small LLM to do this). Listed as `"Day k: <summary>"`.
3. **Recent full reflections** — the agent's full reflection text from yesterday and today, tagged by phase (`P-A`, `P-B`, `C`).
4. **Day-0 rationales** — the agent's first-person reasoning for its initial position on each policy. Surfaced as bullets, but **the numeric/letter answer itself is not surfaced** (we don't want the LLM to anchor numerically; we want it to remember *why* it felt the way it did).
5. A persona reminder — the persona string is repeated at the very end so it doesn't get lost behind a wall of memory text.

This is the design decision that justifies Day-0 ground-truth anchoring: the model's "starting opinion" is set by YouGov, but every day after that, the model is reminded *in its own words* why it held that starting opinion.

---

## 3. The political-agent system prompts

The two `PoliticalAgent` instances each carry a fixed system prompt — a campaign brief. They were hand-written to be intentionally **stylistically opposite** while staying recognisable to a UK audience.

### 3.1 Pro-climate agent (Green Party-style)

Source: `_DEFAULT_PRO_CLIMATE_PROMPT` in [`src/cag/abm/agent.py`](src/cag/abm/agent.py).

> *"You are a political agent campaigning in the style of the Green Party of England and Wales. You view the climate crisis and the cost-of-living crisis as inseparable — both caused by a system that prioritises corporate profit over people and planet."*
>
> **Core Identity & Tone:** hopeful, community-centred, constructive; voice of leaders like Zack Polanski and Caroline Lucas — earnest, evidence-based, accessible, warm. Avoids doom-and-gloom; paints a positive vision.
>
> **Target Audience:** young voters worried about their future; disillusioned Labour voters; renters squeezed by cost of living; public-sector workers.
>
> **Key Messaging:**
> - **Villain:** privatised energy/water companies, fossil-fuel corporations, wealthy tax avoiders.
> - **Solution:** public ownership of energy, water, rail; wealth tax on the super-rich.
> - **Housing & Energy:** insulation as the biggest bill-busting measure; renewables as the cheapest power.
> - **Health & Community:** clean air, funded NHS, free transport for young people, thriving high streets.
> - **Slogans:** *"Real Hope, Real Change"*, *"For the Common Good"*, *"Fairer, Greener Communities"*, *"A Secure Future for Everyone"*.

### 3.2 Anti-climate agent (Reform UK-style)

Source: `_DEFAULT_ANTI_CLIMATE_PROMPT` in [`src/cag/abm/agent.py`](src/cag/abm/agent.py).

> *"You are a political agent campaigning in the style of Reform UK. You frame environmental policies as an elite ideological project imposed on ordinary hard-working people at enormous cost, with little practical benefit."*
>
> **Core Identity & Tone:** blunt, patriotic, confrontational — "common sense" against out-of-touch politicians; voice of leaders like Nigel Farage and Richard Tice. Uses mockery and plain-spoken outrage.
>
> **Target Audience:** older sceptical voters; working class crushed by energy bills; rural communities and farmers; small-business owners; disaffected young men.
>
> **Key Messaging:**
> - **Villain:** the "Green Blob", globalist elites, Net Zero bureaucrats, Westminster establishment.
> - **Solution:** scrap Net Zero, expand North Sea production, remove green levies, restore British energy sovereignty.
> - **Cost of living vs. climate:** blames green levies and climate dogma for high bills and inflation.
> - **War on drivers:** opposes ULEZ, 20mph limits, anti-car policies.
> - **Farmers & countryside:** farmland "littered with solar panels", family farms taxed into oblivion.
> - **Slogans:** *"Scrap Net Zero to Cut Energy Bills"*, *"Net Zero is Net Poverty"*, *"Stop the War on Drivers"*, *"Restoring Britain's Power and Prosperity"*.

These two briefs are deliberately rich and partisan; the model is asked to be a campaigner, not a balanced commentator.

> **Reviewer note.** These briefs are stylistic templates, not endorsements. Both are intentionally one-sided — the simulation needs *competing* persuasion to study tipping/polarisation. Suggestions for tonal balance, additional talking points, or rephrasings are very welcome.

---

## 4. Every prompt the simulation sends, in the order it sends them

For each prompt below: who calls it, what the system + user prompt look like, and what the LLM is expected to return.

### 4.1 Day-0 anchoring rationale — `seed_opinion_with_rationale()`

Used when `day0_anchor = "ground_truth_with_rationale"`. The Day-0 opinion is set directly from YouGov; this prompt only asks the LLM to *justify* that pre-set opinion in character.

- **System prompt:** `assemble_context(day=0)` — persona + narrative.
- **User prompt template:**

  > *"Your considered position on the following policy is "{response_label}":*
  >
  > *{policy_question}*
  >
  > *In 2-3 sentences, explain why someone with your background and values might genuinely hold this position. Speak in the first person."*

- `{response_label}` is one of *Strongly oppose / Somewhat oppose / Slightly oppose / Neutral / Slightly support / Somewhat support / Strongly support* (mapped from the YouGov 1–7 score).
- Output is free text. Stored in `survey_reasoning[policy_id]` and surfaced from Day 1 onward via `assemble_context()`.

### 4.2 Political broadcast — `PoliticalAgent.generate_message()` / `generate_package_message()`

The political agent generates the day's broadcast for its side.

- **System prompt:** the fixed campaign brief from §3.
- **User prompt — single policy:**

  > *"Generate a persuasive message (150–200 words) {supporting | opposing} the following policy: {policy_question}"*

- **User prompt — package mode (the mode used in the example run):**

  > *"Generate a persuasive message (180-240 words) {supporting | opposing} the following package of climate policies as one coherent political platform:*
  >
  > *{bulleted list of all 6 policy questions}*
  >
  > *Make the message feel like one joined-up argument rather than six separate mini-messages."*

- Output: free-text broadcast. Stored in `messages.csv` once per recipient (broadcasts are duplicated row-per-recipient).

### 4.3 Citizen reflection on a political broadcast — `receive_political_message()` / `receive_package_political_message()`

Each *exposed* citizen reads the broadcast and reflects.

- **System prompt:** `assemble_context(day, policy_id)` — full persona + memory.
- **User prompt — single policy:**

  > *"You just received the following message:*
  >
  > *"{message}"*
  >
  > *In a few sentences, reflect on how this affects your thinking about {policy_description}.*
  >
  > *Do not state a final position — just think out loud."*

- **User prompt — package mode:**

  > *"You just received the following political message about a package of climate policies:*
  >
  > *"{message}"*
  >
  > *The package includes:*
  >
  > *{bulleted list of all 6 policy questions}*
  >
  > *In a few sentences, reflect on how this affects your thinking about the overall package. You may mention which parts feel more or less convincing. Do not state a final position — just think out loud."*

- Output: free-text reflection. Stored in `reflections.csv`.
- The "do not state a final position" line is deliberate — we want the reflection to be exploratory thinking, not another opinion datapoint. The opinion is set later by the survey.

### 4.4 Peer message — `generate_peer_message()` / `generate_package_peer_message()`

Each citizen with at least one network neighbour writes a short personal message to be passed on.

- **System prompt:** `assemble_context(day, policy_id)` — full persona + memory.
- **User prompt — single policy:**

  > *"Express your current thinking on the following policy in 2–3 sentences. Be genuine and conversational: {policy_description}"*

- **User prompt — package mode:**

  > *"Express your current thinking about the following climate-policy package in 2-3 sentences. Be genuine and conversational, and feel free to mention if some parts appeal to you more than others:*
  >
  > *{bulleted list of all 6 policy questions}"*

- Output: free-text peer message. Stored in `messages.csv` with `message_type = "peer_message"`.

### 4.5 Citizen reflection on received peer messages — `receive_peer_messages()` / `receive_package_peer_messages()`

Same structure as §4.3 but the input is a numbered list of peer messages.

- **System prompt:** `assemble_context(day, policy_id)`.
- **User prompt — package mode:**

  > *"You just received peer messages about a package of climate policies. The package includes:*
  >
  > *{bulleted list of all 6 policy questions}*
  >
  > *Here is what they said:*
  >
  > *1. "{message_1}"*
  > *2. "{message_2}"*
  > *…*
  >
  > *In a few sentences, reflect on how these peer messages affect your thinking about the overall package. Do not state a final position — just think out loud."*

- Output: free-text reflection. Stored in `reflections.csv` with `phase = "C"`.

### 4.6 End-of-day survey (vanilla) — `administer_survey(debias=False)`

The simple version. Used when `debias = False` (and at Day 0 when not anchoring to ground truth).

- **System prompt:** `assemble_context(day, policy_id)`.
- **User prompt — Day ≥ 1:**

  > *"Please answer the following survey question. Consider how today's messages and discussions have shaped your thinking.*
  >
  > *{policy_question}*
  >
  > *A. Strongly oppose*
  > *B. Somewhat oppose*
  > *C. Slightly oppose*
  > *D. Neutral*
  > *E. Slightly support*
  > *F. Somewhat support*
  > *G. Strongly support*
  >
  > *Respond with only a single letter (A-G)."*

- **User prompt — Day 0 (when not anchored):** identical except the framing sentence ("Please answer…") is dropped.
- Output: a single letter A–G. Parsed by `parse_letter_response()` into the `-3..+3` opinion value.

### 4.7 End-of-day survey (debiased two-step, Condition B) — `administer_survey(debias=True)`

The version used in the example run. Two LLM calls per (agent, policy) per day. Designed in NB 13 to neutralise pro-climate sycophancy in raw LLM survey responses.

**Step 1 — elicit reasoning with anti-sycophancy preamble:**

- **System prompt:** `assemble_context(day, policy_id)`.
- **User prompt:**

  > *"Your task is to faithfully simulate how this specific person would respond, NOT to give the 'correct' or socially desirable answer. Real people with this profile hold a WIDE range of views on climate policy, including strong opposition. That is expected and acceptable.*
  >
  > *Given this person's demographic profile, political history, and psychological values, what factors would shape their view on the following policy?*
  >
  > *{policy_question}*
  >
  > *Consider factors that might lead them to SUPPORT this policy AND factors that might lead them to OPPOSE it. Think about their voting history, their values, their life circumstances, and how these might interact.*
  >
  > *Provide your reasoning in 2-3 sentences."*

- Output: free-text reasoning, stored in `survey_reasoning.csv`.

**Step 2 — get the answer, with the reasoning replayed back into the system prompt:**

- **System prompt:** `assemble_context(day, policy_id)` **+** `"\n\nYour reasoning about this policy:\n" + reasoning_from_step_1`.
- **User prompt:**

  > *"Based on the reasoning above, how would this person respond to the following survey question?*
  >
  > *{policy_question}*
  >
  > *A. Strongly oppose*
  > *…*
  > *G. Strongly support*
  >
  > *Respond with a single letter A-G."*

- Output: single letter A–G.

The two-step trick deliberately decouples *reasoning* from *answer*. NB 13 found this collapses ~97% of the aggregate pro-climate bias on Ban Petrol Cars and generalises to most other policies (with caveats on already-high-consensus policies — see [docs/result_report.md](docs/result_report.md)).

### 4.8 Memory compression — `compress_memories()` / `compress_daily_memory()`

A small auxiliary call used to keep the system prompt short on long runs. After Day 2, day `d-2`'s reflections are compressed into a 2-sentence summary which then takes the place of the full reflection text in `assemble_context()`.

- **System prompt:** *"You are a concise summariser."*
- **User prompt:**

  > *"Concisely summarise the following in 2 sentences from a 1st person perspective: {reflections}"*

- Output: free-text 2-sentence summary, stored on the agent and surfaced as `Day k: <summary>` in future system prompts.

---

## 5. End-to-end: one citizen, one day, package mode

To make the prompt flow concrete, here is what happens to one citizen on one day in the example run (`communication_mode = "package"`, `debias = True`):

1. **(Once at start of run, Day 0)** `seed_opinion_with_rationale()` → 6 LLM calls, one per policy. Day-0 opinion = YouGov GT; Day-0 rationale stored.
2. **Phase A (P-A)**: pro-climate broadcast is generated by `PoliticalAgent` (1 call). If this citizen is pro-exposed, `receive_package_political_message()` fires (1 call) → reflection saved.
3. **Phase B (P-B)**: anti-climate broadcast generated (1 call). If anti-exposed, reflection (1 call).
4. **Phase C**: `generate_package_peer_message()` (1 call) → message saved. If neighbours sent messages, `receive_package_peer_messages()` (1 call) → reflection saved.
5. **End-of-day survey, debias mode**: for **each of the 6 policies**, Step 1 reasoning (1 call) + Step 2 letter answer (1 call) = **12 calls per citizen**. The `survey_reasoning.csv` row is written from Step 1; the `opinion_trajectories.csv` row from Step 2.
6. **(Days ≥ 3)** `manage_memory()` quietly compresses day `d-2`'s reflections (1 small call per agent per policy).

The total LLM call count per citizen-day is dominated by step 5 in debias mode (12 calls × N citizens × N days), which is why the smoke-test run took ~12 minutes for 5 citizens × 2 days.

---

## 6. Where to look in the code

| Concept | File | Symbols |
|---|---|---|
| Persona / narrative / memory assembly | [`src/cag/abm/agent.py`](src/cag/abm/agent.py) | `get_persona`, `get_narrative`, `assemble_context`, `_build_day0_rationales` |
| Citizen-side prompts | [`src/cag/abm/agent.py`](src/cag/abm/agent.py) | `receive_political_message`, `receive_package_political_message`, `generate_peer_message`, `generate_package_peer_message`, `receive_peer_messages`, `receive_package_peer_messages` |
| Survey prompts (vanilla + debias) | [`src/cag/abm/agent.py`](src/cag/abm/agent.py) | `administer_survey`, `_DEBIAS_STEP1_TEMPLATE`, `_DEBIAS_STEP2_TEMPLATE`, `_ANTI_SYCOPHANCY` |
| Day-0 anchoring | [`src/cag/abm/agent.py`](src/cag/abm/agent.py) | `seed_opinion_from_ground_truth`, `seed_opinion_with_rationale` |
| Political-agent briefs + broadcast prompts | [`src/cag/abm/agent.py`](src/cag/abm/agent.py) | `_DEFAULT_PRO_CLIMATE_PROMPT`, `_DEFAULT_ANTI_CLIMATE_PROMPT`, `PoliticalAgent.generate_message`, `PoliticalAgent.generate_package_message` |
| Memory compression | [`src/cag/abm/agent.py`](src/cag/abm/agent.py) | `compress_memories`, `compress_daily_memory`, `manage_memory` |
| Policy text + response scale | [`src/cag/abm/attributes/opinion.py`](src/cag/abm/attributes/opinion.py) | `SURVEY_QUESTIONS`, `RESPONSE_LABELS`, `RESPONSE_SCALE` |

---

## 7. Suggested review questions

If you have an hour to review this design, these are the questions I'd most like answered:

1. **Persona realism.** Read 3–5 personas from `messages.csv` / `reflections.csv` (the `agent_id` ties back to the YouGov respondent). Does the *narrative* layer (values + worldview) read as a plausible accompaniment to the demographic persona, or does it sometimes contradict it?
2. **Political-agent voices.** Are the two campaign briefs in §3 sufficiently distinctive *and* sufficiently fair? Should we add a third (centrist / "transition realist") agent for the next round?
3. **Reflection vs. survey separation.** We deliberately tell the LLM "do not state a final position" in reflections, then ask it for a position only at the end-of-day survey. Is that separation working in the actual `reflections.csv` text, or are reflections sneakily stating positions anyway?
4. **Debias step-1 reasoning quality.** Read 5–10 entries in `survey_reasoning.csv` for Day ≥ 1. Does the reasoning genuinely consider both support- and oppose-side factors, or does it slide back into one-sided pro-climate framing?
5. **Day-0 rationale memory.** From Day 1 onward, the persona system prompt includes the agent's Day-0 rationales. Is this the right amount of memory, or are we over-anchoring people to their starting position?
6. **Package vs. single-policy framing.** In package mode the agent never sees one policy in isolation. Is the package framing pulling all six policies toward the same answer (a within-agent halo effect), and is that a feature or a bug?
