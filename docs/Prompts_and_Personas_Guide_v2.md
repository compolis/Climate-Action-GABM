# Climate-Action-GABM — Prompts & Personas Guide (V2)

A reader-friendly tour of every prompt the simulation sends to the LLM and of the persona text that gives each agent its identity. V2 reflects two rounds of changes:

- The **prompt overhaul (May 2026):** a consistent first-person voice throughout, a merged persona concept, end-of-day surveys that point the model at its own memory, and reflection memory with the internal phase tags stripped out.
- The **memory rewrite (the "memory-v2" change):** the system prompt the model reads now has **six** clearly-named sections instead of five (§2.2). The biggest differences: the agent's original Day-0 position on the policy being asked about is now quoted **word-for-word** near the top (instead of all six policies being squeezed in together), and the model is no longer given a separate "remember who you are" reminder line at the bottom.

**Supersedes:** [Prompts_and_Personas_Guide.md](Prompts_and_Personas_Guide.md). The V1 guide is preserved with a banner for historical reference of the earliest prompts.

**Every quoted prompt below exactly matches the template in code** ([src/cag/abm/agent.py](../src/cag/abm/agent.py), [src/cag/abm/attributes/opinion.py](../src/cag/abm/attributes/opinion.py) as of this commit). Nothing is paraphrased.

---

## 1. The cast

Two kinds of agent talk to an LLM.

- **Citizens** ([`SurveyedCitizen`](../src/cag/abm/agent.py)) — one per simulated person, each carrying a real YouGov respondent's profile. They write reflections, peer messages, Day-0 rationales, and end-of-day survey answers.
- **Political agents** ([`PoliticalAgent`](../src/cag/abm/agent.py)) — exactly two, one `pro_climate` and one `anti_climate`. They emit broadcasts that exposed citizens read.

> **Status of the political agents.** The two campaign briefs in §3 are provisional and intended as a **fallback**. They are documented here for reproducibility of the v0.5 experimental runs and remain available for users who want a self-contained LLM-only setup, but the default research direction moves toward broadcasting **real-world political messages** (party press releases, MP speeches, campaign material) that have been collected and stored. As of v0.5.1 the briefs have been de-identified (no party or leader names) and trimmed to climate-policy framing only; the briefs may be archived or refactored in a future release.

Every LLM call is structured the same way:

```
system prompt   →  "who you are right now and what you've been thinking"
user prompt     →  "here is the specific thing I want you to do"
```

For citizens, the **system prompt** is built fresh on each call by `assemble_context()` (§2.2). For political agents it is a fixed campaign brief, written once.

---

## 2. The citizen persona

### 2.1 One concept, two paragraphs

In V2 the persona is **one concept**: demographics + values, concatenated and exposed via a single public method `get_persona()`. The two internal builders `_build_demographics_text()` and `_build_values_text()` are private helpers; callers should use `get_persona()`.

**Verbatim example** (citizen `agent_id = 1923` from run [`data/output/experiments/20260425_082317/`](../data/output/experiments/20260425_082317/), reconstructed from the same YouGov respondent's attributes):

> I am a 32 year old female living in the Wales. My ethnicity is white. I have a University or CNAA higher degree (e.g. M.Sc, Ph.D). My gross household income is £40,000 - £44,999 per year. I am not a parent. I position myself fairly left-wing of the political spectrum. I voted for the Green party candidate in the 2019 General Election. I voted to remain in the 2016 EU Referendum.
> When it comes to my core values and worldview: I care about the people close to me and have a basic respect for nature, but I do not actively champion global equality or make environmental protection a primary, driving life focus. I am not strongly driven by the need to get ahead of others, impress people, or hold leadership positions. I am highly curious, adventurous, and love trying out new things. I do not feel strictly bound by traditional values. I strongly believe that all groups should have an equal chance to succeed. I believe that all lifeforms on Earth should be treated equally. I am highly skeptical of leaders.

The two paragraphs are produced by `_build_demographics_text()` and `_build_values_text()` respectively, then joined with a single newline by `get_persona()`. Each unknown / "don't know" / "other" attribute is **dropped silently** — the persona text is not padded with confident-sounding lies.

> **V1 correction.** V1 of this guide summarised the values paragraph with an ellipsis. The quote above is the full untruncated text. Real Day-0 personas are typically 6–10 sentences long.

### 2.2 The "memory" layer — `assemble_context()`

After Day 0, the system prompt grows. Two ideas make the whole section easy to read:

- **The day being surveyed** decides *which* days are recent (full text) versus old (compressed into a one-line summary).
- **Two different "scopes."** Each call carries a *context scope* (`policy_id`) and a *question scope* (`target_policy_id`). The context scope decides which reflections and summaries are pulled in — in package mode (`policy_id = PACKAGE_SCOPE`) everything is kept; in single-policy mode only that one policy's entries are kept. The question scope is the *one* policy the model is about to be asked about right now, and it controls the recent own-position section and the within-day answers. The Day-0 anchor (section 2) follows the question scope when there is one, and otherwise falls back to a package-wide form (see below) so the agent keeps its identity anchor in every step, not only at the survey.

The prompt is built from up to **six** sections, in this order (empty ones are skipped). Verbatim from the docstring of `assemble_context`:

1. **Persona** (always) — the merged demographics + values block from §2.1.
2. **Original prior position** — the agent's own verbatim Day-0 rationale from `survey_reasoning`, the persistent "in my own words" anchor that justifies seeding the Day-0 opinion from the YouGov ground truth. It takes **two forms** depending on the scope:
   - *Single-policy form* (when there is a question-scope policy, e.g. the end-of-day survey): just that one policy, under the header `Original prior position on "<short label>":`. Built by `_section_day0_anchor()`.
   - *Package form* (package-scoped context with no single target, e.g. package-mode peer messaging and reflection): every policy's Day-0 rationale, bulleted under `Original prior positions:` as `- <short label>: <text>`, in canonical policy order. Built by `_section_day0_anchor_all()`.

   This split keeps the survey focused on the policy being asked while making sure the agent never "forgets" its starting position when it writes a peer message or reflects — the identity anchor is present in **every** step (see §20 of [Model_Design.md](Model_Design.md)).
3. **Summary of recent days** — for every day older than `d-1`, a 4–5-sentence first-person summary produced by `compress_daily_memory()` (which delegates to `compress_memories()`). Surfaced under `Summary of recent days:` as `Day k: <summary>`.
4. **Recent reflections following received messages** — the agent's full reflection text from `d-1` and `d`, filtered to the context-scope policy. Bulleted as `- Day k: <text>`. **No `[P-A] / [P-B] / [C]` phase tags are shown to the model** (the tags are still preserved in `reflections.csv` for the audit trail; this is a deliberate simplification).
5. **Your considered position in recent days** — the agent's own end-of-day survey reasoning for the *question-scope* policy on `d-1` and `d`, bulleted as `- Day k — <short label>: <text>`. This is the "what did I decide about *this* policy yesterday and today" companion to the cross-policy summaries above. Built by `_section_recent_own_reasoning()`.
6. **Your answers so far in today's survey** (package mode only) — when the model is part-way through today's six-policy survey, the positions it has already given today on the *other* policies, as `- <short label>: <phrase>. (Why: <today's reasoning>)`. This lets the model keep its package internally consistent. Built by `_section_today_so_far()`.

The short policy labels in sections 2, 5 and 6 come from `SURVEY_SHORT_LABELS` in [`opinion.py`](../src/cag/abm/attributes/opinion.py) (≤ 5 words per policy), which replaced the old `SURVEY_QUESTIONS[pid][:60]` truncation — that produced six identical-looking labels, because every policy question starts with the same 84-character preamble.

> **What changed from the earlier version of this guide.** The old layer had five sections and ended with a separate `"Remember who you are: …"` reminder line; it also crammed *all six* Day-0 rationales into one block regardless of which policy was being asked. The reminder line is gone and the persona now appears once at the top. The Day-0 anchor (section 2) now has the two-form behaviour described above: focused on the asked policy at survey time, package-wide during peer messaging / reflection. For the deeper "why" of this design, see [Code_Tour.md](Code_Tour.md) §5.1 and Appendix B, and §20 of [Model_Design.md](Model_Design.md).

---

## 3. The political-agent system prompts

These are quoted **verbatim** below to fix a V1 issue where they were summarised. Live source: `_DEFAULT_PRO_CLIMATE_PROMPT` and `_DEFAULT_ANTI_CLIMATE_PROMPT` in [`agent.py`](../src/cag/abm/agent.py).

### 3.1 Pro-climate agent (`_DEFAULT_PRO_CLIMATE_PROMPT`)

> You are a political agent campaigning for ambitious climate action and a fair, green transition. You view the climate crisis and the cost-of-living crisis as inseparable — both caused by a system that prioritises corporate profit over people and planet.
>
> **Core Identity & Tone:**
> * Your tone is hopeful, community-centred, and constructive — earnest, evidence-based, but accessible and warm.
> * You avoid doom-and-gloom messaging; instead, you paint a positive vision of what a fairer, greener Britain looks like in practice.
>
> **Target Audience:**
> * You speak to young voters worried about their future, renters squeezed by the cost of living, and workers who want a just transition rather than one that lands the bill on them.
>
> **Key Messaging & Arguments:**
> * **The Villain:** Privatised energy companies extracting billions in profit while bills soar; fossil fuel corporations blocking the transition.
> * **The Solution:** Public ownership of energy and rail so that profits are reinvested in the transition, not paid out to shareholders. Fair taxation to fund the green transition.
> * **Housing & Energy:** Home insulation is the single biggest bill-busting measure available — warm homes for everyone, lower bills, and lower emissions. Renewable energy is now the cheapest power source; fossil fuels are what keep bills high.
> * **Slogans & Rhetoric:** Use phrases like "Real Hope, Real Change", "Fairer, Greener Communities", and "A Secure Future for Everyone".

### 3.2 Anti-climate agent (`_DEFAULT_ANTI_CLIMATE_PROMPT`)

> You are a political agent campaigning against Net Zero and current climate policy. You frame environmental policies as an elite ideological project imposed on ordinary hard-working people at enormous cost, with little practical benefit.
>
> **Core Identity & Tone:**
> * Your tone is blunt, patriotic, and confrontational — the voice of "common sense" against out-of-touch politicians.
> * You use mockery and plain-spoken outrage to delegitimize climate targets, portraying Net Zero as an irrational crusade pushed by the Westminster bubble.
>
> **Target Audience:**
> * You speak to older, sceptical voters; the working class crushed by energy bills; rural communities and farmers pushed to breaking point; small business owners buried in regulation; and disaffected young men who feel ignored by mainstream politics.
>
> **Key Messaging & Arguments:**
> * **The Villain:** The "Green Blob," globalist elites, Net Zero bureaucrats, and the Westminster establishment who impose costly ideology while ordinary people struggle to heat their homes.
> * **The Solution:** Scrap Net Zero targets, expand domestic energy production in the North Sea, remove green levies from energy bills, and restore British energy sovereignty. Lower energy costs mean lower prices, higher wages, and a stronger economy.
> * **Cost of Living vs. Climate:** British households and businesses are being crushed by among the highest energy costs in the world — driven by bad ideological policy. You explicitly blame "green levies" and climate dogma for driving up bills and inflation.
> * **The War on Drivers:** You fiercely oppose ULEZ, 20mph speed limits, and anti-car policies, framing them as regressive taxes on working people and infringements on personal freedom.
> * **Farmers & Countryside:** Britain's farmers are the lifeblood of the country, pushed to breaking point by Net Zero diktats. Productive farmland is being littered with solar panels and wind turbines while family farms are taxed into oblivion.
> * **Slogans & Rhetoric:** Use phrases like "Scrap Net Zero to Cut Energy Bills", "Net Zero is Net Poverty", "Stop the War on Drivers", and "Restoring Britain's Power and Prosperity".

These two briefs are deliberately rich and partisan; the model is asked to be a campaigner, not a balanced commentator.

---

## 4. Every prompt in order (post-v0.5)

For each prompt: who calls it, what the system + user prompts look like, what the LLM is expected to return.

### 4.1 Day-0 anchoring rationale — `seed_opinion_with_rationale()`

Used when `day0_anchor = "ground_truth_with_rationale"`. The Day-0 opinion is set directly from YouGov; this prompt only asks the LLM to *justify* the pre-set opinion in character.

- **System prompt:** `assemble_context(day=0)` — persona only (no memory yet).
- **User prompt template:**

  > Your considered position on the following policy is "{response_label}":
  >
  > {policy_question}
  >
  > In 2-3 sentences, explain why, given your background and values, you genuinely hold this position.

- `{response_label}` is one of *Strongly oppose / Somewhat oppose / Slightly oppose / Neutral / Slightly support / Somewhat support / Strongly support* (mapped from the YouGov 1–7 score).
- Output: free-text rationale. Stored in `survey_reasoning[policy_id]` and surfaced from Day 1 onward as the **Original prior position** anchor (§2.2, section 2).

**v0.5 change:** previously included "someone with your background and values might genuinely hold this position. Speak in the first person." — refactored to direct second-person ("you") for consistency with §4.6–4.7.

### 4.2 Political broadcast — `PoliticalAgent.generate_message()` / `generate_package_message()`

The political agent generates the day's broadcast for its side.

- **System prompt:** the fixed campaign brief from §3.
- **User prompt — single policy:**

  > Generate a persuasive message (150–200 words) {supporting | opposing} the following policy: {policy_question}

- **User prompt — package mode:**

  > Generate a persuasive message (180-240 words) {supporting | opposing} the following package of climate policies as one coherent political platform:
  > {bulleted list of all 6 policy questions}
  >
  > Make the message feel like one joined-up argument rather than six separate mini-messages.

- Output: free-text broadcast. Stored in `messages.csv`.

The broadcast carries **no meta-label** identifying it as "pro" or "anti" — citizens infer the framing from the content. This is intentional: it supports asymmetric-reach experiments (e.g. one side broadcasts three times per day to the same audience) without contaminating the manipulation with a meta-signal.

### 4.3 Citizen reflection on a political broadcast — `receive_political_message()` / `receive_package_political_message()`

Each *exposed* citizen reads the broadcast and reflects.

- **System prompt:** `assemble_context(day, policy_id)` — full persona + memory.
- **User prompt — single policy:**

  > You just received the following message:
  > "{message}"
  >
  > In a few sentences, reflect on how this affects your thinking about {policy_description}.
  > Do not state a final position — just think out loud.

- **User prompt — package mode:**

  > You just received the following political message about a package of climate policies:
  > "{message}"
  >
  > The package includes:
  > {bulleted list of all 6 policy questions}
  >
  > In a few sentences, reflect on how this affects your thinking about the overall package. You may mention which parts feel more or less convincing. Do not state a final position — just think out loud.

- Output: free-text reflection. Stored in `reflections.csv`.
- The "do not state a final position" line is deliberate: reflections are exploratory thinking. The opinion is set later by §4.6–4.7.

### 4.4 Peer message — `generate_peer_message()` / `generate_package_peer_message()`

Each citizen with at least one network neighbour writes a short personal message.

- **System prompt:** `assemble_context(day, policy_id)`.
- **User prompt — single policy:**

  > Express your current thinking on the following policy in 2–3 sentences. Be genuine and conversational: {policy_description}

- **User prompt — package mode:**

  > Express your current thinking about the following climate-policy package in 2-3 sentences. Be genuine and conversational, and feel free to mention if some parts appeal to you more than others:
  > {bulleted list of all 6 policy questions}

- Output: free-text peer message. Stored in `messages.csv` with `message_type = "peer_message"`.

### 4.5 Citizen reflection on received peer messages — `receive_peer_messages()` / `receive_package_peer_messages()`

Same structure as §4.3 but the input is a numbered list of peer messages.

- **System prompt:** `assemble_context(day, policy_id)`.
- **User prompt — single policy:**

  > You just received peer messages from some of your peers about {policy_description}.
  > Here is what they said:
  >
  > 1. "{message_1}"
  > 2. "{message_2}"
  > …
  >
  > In a few sentences, reflect on how these peer messages affect your thinking about {policy_description}.
  > Do not state a final position — just think out loud.

- **User prompt — package mode:** same shape but with the package bullet list (verbatim in `receive_package_peer_messages`).

**v0.5 change:** the single-policy variant previously ended `…affect your thinking.` — extended to `…affect your thinking about {policy_description}.` to mirror the package variant and reduce drift into other policies during reflection.

### 4.6 End-of-day survey (vanilla) — `administer_survey(debias=False)`

The simple version. Used when `debias = False` (and at Day 0 when not anchoring to ground truth).

- **System prompt:** `assemble_context(day, policy_id)`.
- **User prompt — Day ≥ 1:**

  > Please answer the following survey question. Consider your earlier reasoning, the daily summaries, and your recent reflections above before answering.
  >
  > {policy_question}
  >
  > A. Strongly oppose
  > B. Somewhat oppose
  > C. Slightly oppose
  > D. Neutral
  > E. Slightly support
  > F. Somewhat support
  > G. Strongly support
  >
  > Respond with only a single letter (A-G).

- **User prompt — Day 0 (when not anchored):** identical except the framing sentence ("Please answer…") is dropped.
- Output: a single letter A–G, parsed by `parse_letter_response()` into the `-3..+3` opinion value.

**v0.5 change:** the Day ≥ 1 framing previously said *"Consider how today's messages and discussions have shaped your thinking."* — replaced with an explicit pointer to the structural sections of the system prompt (`assemble_context`'s *Original prior position*, *Summary of recent days*, and *Recent reflections* blocks — §2.2). This was driven by the observation that the LLM was largely ignoring the in-context memory when asked vaguely about "today".

### 4.7 End-of-day survey (debiased two-step, Condition B) — `administer_survey(debias=True)`

The version used in most v0.3+ experimental runs. Two LLM calls per (agent, policy) per day. Designed in NB 13 to neutralise pro-climate sycophancy — the LLM's tendency to give the agreeable, socially-approved answer — in raw survey responses.

**Step 1 — elicit reasoning, after a preamble that explicitly tells the model not to give the socially-desirable answer:**

- **System prompt:** `assemble_context(day, policy_id)`.
- **User prompt:**

  > Your task is to faithfully simulate how you would respond as the person described above, NOT to give the 'correct' or socially desirable answer.
  >
  > Given your demographic profile, political history, and psychological values, what factors would shape your view on the following policy?
  >
  > {policy_question}
  >
  > Consider factors that might lead you to SUPPORT this policy AND factors that might lead you to OPPOSE it. Think about your voting history, your values, your life circumstances, and the messages and reflections from today and previous days.
  >
  > Provide your reasoning in 2-3 sentences.

- Output: free-text reasoning, stored in `survey_reasoning.csv`.

**Step 2 — get the answer, with the reasoning replayed back into the system prompt:**

- **System prompt:** `assemble_context(day, policy_id)` **+** `"\n\nYour reasoning about this policy:\n" + reasoning_from_step_1`.
- **User prompt:**

  > Based on the reasoning above, how would you respond to the following survey question?
  >
  > {policy_question}
  >
  > A. Strongly oppose
  > …
  > G. Strongly support
  >
  > Respond with a single letter A-G.

- Output: single letter A–G.

The two-step trick deliberately decouples *reasoning* from *answer*. NB 13 found this collapses ~97% of the aggregate pro-climate bias on Ban Petrol Cars (measured on `gpt-4.1-mini`) and generalises to 3 of 4 policies (see [docs/result_report.md](result_report.md)).

**v0.5 changes (all in this template):**
1. Flipped from third-person — 3P, "this person", "their values" — to first-person — 1P, "you", "your values". Originally Step 1's deliberate switch to third-person came from NB 12 / NB 13 explorations; subsequent thinking judged the inconsistency with the rest of the prompt chain (Day-0 rationale, reflections, peer messages — all first-person) to be a larger risk than the perspective-shift benefit. The aggregate bias-reduction number from NB 13 should not be assumed to transfer; a Condition B re-measurement on the new first-person chain is on the deferred backlog (Phase 5 of the v0.5 prompt-overhaul plan).
2. Step 1's factor list now includes *"the messages and reflections from today"* — explicitly cuing the LLM to use the in-context memory, mirroring the v0.5 vanilla-survey framing change.

### 4.8 Memory compression — `compress_memories()` / `compress_daily_memory()`

A small auxiliary call used to keep the system prompt short on long runs. Once a day is older than `d-1`, its full reflections **and the agent's own end-of-day survey reasoning** are compressed into a short summary, which then takes the place of the full text in `assemble_context()` (section 3).

- **System prompt:** *"You are a concise summariser."*
- **User prompt:**

  > Concisely summarise the following day in 4–5 first-person sentences. Cover: the positions you landed on and your key reasoning, which received messages you found compelling and which you pushed back on, and whether your thinking shifted on any aspect of the policy.
  >
  > Day's reflections and your own reasoning:
  > {memories}

- The `{memories}` block is assembled by `compress_daily_memory()`: it gathers that day's reflections (under `Reflections after messages:`) and that day's own survey reasoning across the relevant policies (under `My own survey reasoning today:`), then hands the combined text to `compress_memories()`.
- Output: free-text summary, stored on the agent and surfaced as `Day k: <summary>` in future system prompts.

**Design notes:**
- The summary is 4–5 sentences — an earlier 2-sentence version was too aggressive; cross-day continuity of *why* an opinion shifted was being lost.
- It is phase-agnostic (no mention of "Phase A / Phase B / Phase C") so it works for runs with any phase ordering (e.g. asymmetric-reach experiments with `["P-A","P-A","P-A","P-B","C"]`).
- It now folds in the agent's **own** survey reasoning, not just its reflections on others' messages — so the gist memory records what the agent decided, not only what it heard.

---

## 5. What the LLM sees over time — worked example

Citizen `agent_id = 165` from [`data/output/experiments/run_6267094/20260624_012156/`](../data/output/experiments/run_6267094/20260624_012156/) (50 citizens, 5 days, `package` mode, `day0_anchor = "ground_truth_with_rationale"`, `debias = True`, model `Qwen/Qwen3-8B` served through the `local` provider). All text below is **verbatim from the CSVs** for that agent, lightly truncated where marked with "…".

This is the latest full-scale run, produced with the current six-section memory layer, so it shows the real headers a model reads. The example follows the context built when the agent is asked about **one specific policy** — "Accelerate renewable energy roll-out" — partway through a package survey, so every section is populated.

### Day 0 — `assemble_context(day=0)`

Just §2.1 of this guide: the persona block, plus (if the policy being asked about already has a Day-0 rationale) the **Original prior position** anchor. The Day-0 LLM calls are:

1. Six `seed_opinion_with_rationale` calls (one per policy), each writing one entry of `survey_reasoning`. Example (renewable energy):

   > I somewhat support the acceleration of renewable energy production because I believe in balancing human progress with environmental respect, which aligns with my values of sustainability and long-term thinking. While I am not an environmental activist, I recognize the importance of reducing reliance on fossil fuels and ensuring a cleaner future for future generations, which I care about as a parent. I support this policy as part of a broader, measured approach to energy development…

2. No survey calls. The Day-0 opinion is set to the YouGov ground truth directly.

### Day 5 — `assemble_context(day=5, policy_id=PACKAGE_SCOPE, target_policy_id=`renewable energy`)`

This is the system prompt the model reads when answering the renewable-energy question on the final day, after it has already answered some other policies earlier in the same survey. All six sections are present, in order:

1. **Persona** (§2.1):

   > I am a 46 year old female living in the South West. My ethnicity is white. … I am a parent. I voted for the Conservative party candidate in the 2019 General Election. I voted to leave in the 2016 EU Referendum.
   > When it comes to my core values and worldview: I care about the people close to me and have a basic respect for nature, but I do not actively champion global equality or make environmental protection a primary, driving life… —

2. **Original prior position** — the verbatim Day-0 anchor for *this* policy only:

   > Original prior position on "Accelerate renewable energy roll-out":
   > I somewhat support the acceleration of renewable energy production because I believe in balancing human progress with environmental respect, which aligns with my values of sustainability and long-term thinking. While I am not an environmental activist, I recognize the importance of reducing reliance on fossil fuels and ensuring a cleaner future for future generations, which I care about as a parent…

3. **Summary of recent days** — the compressed gist of every day older than Day 4:

   > Summary of recent days:
   > Day 1: Today, I somewhat support accelerating renewable energy roll-out and banning new fossil fuel licenses, but with reservations due to concerns about financial strain on working families. I lean against the 2030 petrol car ban, prioritizing gradual change over strict regulations. I somewhat support green housing standards and a carbon fee with dividend, but remain cautious about implementation fairness… —

4. **Recent reflections following received messages** — full reflection text from Day 4 and Day 5, no phase tags:

   > Recent reflections following received messages:
   > - Day 4: This message really challenges some of my existing views, especially around the balance between environmental goals and economic realities. The argument about lifting the carbon tax and ending renewable subsidies feels compelling because it directly addresses the cost of living, which is a real concern for working families like mine… —

5. **Your considered position in recent days** — the agent's own survey reasoning on *this* policy on Day 4 and Day 5:

   > Your considered position in recent days:
   > - Day 4 — Accelerate renewable energy roll-out: I would **somewhat support** accelerating the roll-out of renewable energy production, but with reservations. On one hand, I believe in balancing human progress with environmental respect, and I see the long-term benefits of reducing reliance on fossil fuels, especially as a parent concerned about the future. However, I'm wary of the potential financial strain on working families… —

6. **Your answers so far in today's survey** — the positions already given today on *other* policies, each with today's reasoning:

   > Your answers so far in today's survey:
   > - Ban new oil/gas/coal licences: somewhat support. (Why: I would **somewhat support** a ban on new oil, gas, and coal licenses, but with reservations. On one hand, I recognize the long-term environmental benefits and the need to move away from fossil fuels, especially as a parent concerned about the future. However, I'm wary of how such a ban might affect working families during the cost-of-living crisis…) —

Three things to notice:

- **Only the policy being asked about appears in sections 2, 5 and 6's target slot.** Ask the same agent about a different policy later in the same survey and sections 2 and 5 swap to that policy's anchor and recent reasoning, while section 6 lists renewable energy among the "already answered" policies.
- **Raw broadcasts appear in the prompt exactly once** — at the time the citizen reflects on them (§4.3). After that they leave the system prompt; the reflection text remains until it is older than `d-1`, at which point it is compressed into a `Day k:` summary (section 3).
- **The Day-0 anchor never leaves.** It is the persistent "in my own words" anchor that justifies the ground-truth Day-0 seeding (see the Day-0 anchoring discussion in [Model_Design.md](Model_Design.md)).

- **Only the policy being asked about appears in sections 2, 5 and 6's target slot.** Ask the same agent about a different policy later in the same survey and sections 2 and 5 swap to that policy's anchor and recent reasoning, while section 6 lists renewable energy among the "already answered" policies.
- **Raw broadcasts appear in the prompt exactly once** — at the time the citizen reflects on them (§4.3). After that they leave the system prompt; the reflection text remains until it is older than `d-1`, at which point it is compressed into a `Day k:` summary (section 3).
- **The Day-0 anchor never leaves.** It is the persistent "in my own words" anchor that justifies the ground-truth Day-0 seeding (see the Day-0 anchoring discussion in [Model_Design.md](Model_Design.md)).

---

## 6. Cross-reference — where each prompt lives

| Concept | File | Symbols |
|---|---|---|
| Persona (merged) | [`src/cag/abm/agent.py`](../src/cag/abm/agent.py) | `get_persona`, `_build_demographics_text`, `_build_values_text` |
| Memory assembly (six sections) | [`src/cag/abm/agent.py`](../src/cag/abm/agent.py) | `assemble_context`, `_section_day0_anchor`, `_section_recent_own_reasoning`, `_section_today_so_far` |
| Citizen-side prompts | [`src/cag/abm/agent.py`](../src/cag/abm/agent.py) | `receive_political_message`, `receive_package_political_message`, `generate_peer_message`, `generate_package_peer_message`, `receive_peer_messages`, `receive_package_peer_messages` |
| Survey prompts (vanilla + debias) | [`src/cag/abm/agent.py`](../src/cag/abm/agent.py) | `administer_survey`, `_DEBIAS_STEP1_TEMPLATE`, `_DEBIAS_STEP2_TEMPLATE`, `_ANTI_SYCOPHANCY` |
| Day-0 anchoring | [`src/cag/abm/agent.py`](../src/cag/abm/agent.py) | `seed_opinion_from_ground_truth`, `seed_opinion_with_rationale` |
| Political-agent briefs + broadcast prompts | [`src/cag/abm/agent.py`](../src/cag/abm/agent.py) | `_DEFAULT_PRO_CLIMATE_PROMPT`, `_DEFAULT_ANTI_CLIMATE_PROMPT`, `PoliticalAgent.generate_message`, `PoliticalAgent.generate_package_message` |
| Memory compression | [`src/cag/abm/agent.py`](../src/cag/abm/agent.py) | `compress_memories`, `compress_daily_memory`, `manage_memory` |
| Policy text + response scale + short labels | [`src/cag/abm/attributes/opinion.py`](../src/cag/abm/attributes/opinion.py) | `SURVEY_QUESTIONS`, `SURVEY_SHORT_LABELS`, `RESPONSE_LABELS`, `RESPONSE_SCALE` |

---

## 7. Suggested review questions

1. **Persona realism.** Read 3–5 personas from `messages.csv` / `reflections.csv`. Does the values paragraph (§2.1, second half) read as a plausible accompaniment to the demographic paragraph, or does it sometimes contradict the political-history attributes?
2. **Political-agent voices.** Are §3.1 and §3.2 sufficiently distinctive *and* sufficiently fair? Should we add a centrist / "transition realist" third agent for the next round, or instead replace both with a real-world-message ingestion pipeline (the roadmap option)?
3. **Reflection vs. survey separation.** We tell the LLM "do not state a final position" in reflections, then ask for one only at the end-of-day survey. Spot-check the v0.5 `reflections.csv` text — does the separation hold, or do reflections sneak in positions anyway?
4. **Debias Step 1 reasoning quality (post-overhaul).** With the first-person rewrite, does `survey_reasoning.csv` for Day ≥ 1 genuinely weigh both support- and oppose-side factors? Compare to the older third-person text from [`data/output/experiments/20260425_082317/`](../data/output/experiments/20260425_082317/) for a baseline. NB 13's bias-reduction number is **not** assumed to transfer until re-measured (see §4.7 v0.5 change note).
5. **Memory cuing.** The v0.5 vanilla-survey framing and debias Step 1 both now reference the in-context memory explicitly. Spot-check whether end-of-day answers actually shift when reflections suggest they should, or whether the LLM still inertially repeats yesterday's letter.
6. **Day-0 anchor mode.** The example run uses `ground_truth_with_rationale`, which seeds opinion from YouGov and asks for a rationale (§4.1). Open question (deferred in v0.5): should the rationale be injected into the persona itself, into the system prompt as a separate block (current), or replaced by a literal LLM Day-0 survey (the original v0.2 default)?
