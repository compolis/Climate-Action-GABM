# Research Notes

Append-only log of research-direction thinking, framing decisions, and
strategic questions that don't belong in code comments or a CHANGE_LOG.
Topics here are intentionally broader than any single PR: prompt-design
philosophy, what the model *is and isn't* measuring, where the next
production sweep is pointed, lessons that span multiple runs.

---

## Research aim

This is a generative-AI agent-based model (GABM) of **UK climate-policy
opinion dynamics under competing committed-minority broadcasts**. Each
citizen agent is anchored to a real respondent in a representative
**YouGov survey (April 2024)** — the simulation starts from observed
opinions, not synthetic priors. Two **committed-minority political
agents** broadcast persuasive messages drawn from real online communication
by Reform UK and the Green Party of England and Wales (loosely modelled on
those parties; the model is institution-agnostic and party names are not
hard-coded in agent prompts). Citizens sit on a stochastic-block social
network and exchange peer messages alongside the political broadcasts.

**Ultimate research question.** How do opinion dynamics shift when the two
committed minorities have **different resources** — that is, when one side
can reach a larger share of citizens and/or release persuasive messages
more frequently than the other? Two planned asymmetry tests:

1. **Reach asymmetry.** Vary `reach_a` / `reach_b` (the fraction of each
   committed minority's dedicated audience that a single broadcast actually
   reaches) holding broadcast frequency constant.
2. **Frequency asymmetry.** Vary the number of broadcast phases per day
   per side, holding reach constant.

Both tests sweep over the same six climate policies in package mode and
read out the resulting bucket-level opinion trajectories.

**Exposure structure (canonical `committed_minority_symmetric` preset).**

| Bucket | Share | Sees |
|---|---:|---|
| A-only | **5%** | Pro-climate broadcasts only (Green-style) |
| B-only | **5%** | Anti-climate broadcasts only (Reform-style) |
| both | **50%** | Both broadcast streams |
| neither | **40%** | No political broadcasts (peers only) |

The small A-only and B-only cells are the **dedicated audiences** of each
minority party — the citizens whose values align strongly enough with one
side that they'd opt into that broadcast stream. The 5% figure reflects
real-world political-attention research: dedicated minority-party audiences
are small. The `both` cell at 50% reflects the cross-cutting broadcast
exposure most citizens get in a mass-media environment. The `neither` cell
at 40% is the matched no-broadcast baseline used for persuasion-subtraction
analysis. The asymmetric `committed_minority_uk_2024` preset and the
`split50` / `neither` / `legacy_v05` presets are also available — see
[USER_GUIDE.md](../USER_GUIDE.md).

**What is measured.** Per-citizen, per-policy, per-day support score on
the YouGov 7-point scale (-3 strongly oppose → +3 strongly support), plus
the aggregated 6-policy package index. Calibration against ground truth
(the citizen's actual Day-0 YouGov response) is tracked per `(policy, day)`.
Cross-bucket gap-widening on the package index is the primary persuasion
signal (see [result_report.md](result_report.md) for the +0.667 Day-5 v0.7
post-fix headline).

**What is NOT measured (current scope).** Long-term attitude change beyond
the simulated horizon, behavioural intentions beyond stated policy support,
real-world political mobilisation, second-order network effects beyond the
direct peer messaging captured in the simulation.

**Where this is going.** The production sweep target is **n=100 citizens,
30 days, reach asymmetry as the primary lever**, run on the AIRE HPC with
a local LLM (Qwen3 family or larger if compute permits). Frequency
asymmetry follows once reach is well-characterised. Model selection is
itself an open question — the Qwen3-8B "non-persuasive" finding under
package-mode is contaminated by the pre-v0.7 survey-context bug and needs
re-measurement under the patched code before any model claim is final.

---

## Rulebook for this document

- **Append-only.** Existing notes are not edited or rewritten; corrections
  go in a new note that supersedes the old one. The historical record of
  thinking is itself valuable.
- **Newest at the top.** New notes go directly under the "## Notes" heading
  below. Date each note `YYYY-MM-DD` in the heading.
- **One topic per note.** Don't bundle. A note on prompt design and a note
  on calibration are two notes.
- **Cite, don't summarise.** Where a point connects to a result, link to
  the run directory or notebook with a `[brief label](relative/path/)`.
  Don't restate findings in full — that's `result_report.md`'s job.
- **Explain like you'd want it explained — verbose over dense.** This
  document is read by collaborators who are smart but not necessarily
  steeped in the statistics or ML jargon. Every technical term (e.g.
  Spearman ρ, difference-in-differences, ANCOVA, effect size, regression-
  to-mean) gets a plain-language definition — and, where it helps, an
  everyday analogy — the *first* time it appears in a note. Prefer a
  longer paragraph a non-specialist can follow over a compressed expert
  synthesis; if you catch yourself using a term of art without unpacking
  it, unpack it. Spelling things out here is a feature, not clutter: the
  precise numbers live in `result_report.md`, so this file has room to be
  generous with explanation. This rule exists so the "can you explain what
  that means?" question never has to be asked twice.
- **Framing here, numbers there.** This file holds research *framing*,
  strategy, goals, and next steps. Concrete result tables and exact
  statistics belong in `result_report.md`; link to the relevant section
  and quote at most a headline figure in prose.
- **Mark superseded notes inline.** If a later note overrides an earlier
  one, prepend the older note with `> **SUPERSEDED YYYY-MM-DD:** see
  [note title](#anchor).` — do not delete it.
- **Out of scope here.** This file is NOT for: bug write-ups, code-change
  rationale, version-bump records, or anything that belongs in
  `CHANGE_LOG.md`, `DEVELOPMENT_HISTORY.md`, or `result_report.md`. Cross-
  reference those documents instead.

---

## Notes

### 2026-07-03 — Validation strategy: what the four tiers aim to do (plain-language overview)

*(This is the plain-terms companion to the "difference engine" note below.
It explains the validation strategy in everyday language; the formal
framing and the term definitions live in that note, and the precise
numbers live in [result_report.md](result_report.md).)*

The whole thing exists to solve one problem: **the model is biased upward on
climate.** Every agent drifts more pro‑climate than the real person it
represents. So we can't trust the model's *absolute* numbers. But we think we
*can* trust the *differences* between conditions — like a thermometer that
always reads 5° too high is useless for "what's the temperature?" but
perfectly fine for "is today warmer than yesterday?"

The four tiers are just four questions we have to answer "yes" to before we're
allowed to make that claim. In plain terms:

**Tier P — "Is the model even listening to who each agent is supposed to be?"**
Before anything else: if we tell the model "you are a 60‑year‑old Leave‑voting
farmer," does its opinion actually change compared to "you are a 25‑year‑old
Green city student"? We test this by giving agents the *wrong* personas
(shuffled) or *blank* personas and checking that their opinions fall apart. If
a farmer and a student give the same answer, the model is ignoring the persona
and the whole project is dead on arrival. This is the foundation — a sanity
check that there's a real signal at all.

**Tier 1 — "Does the bias cancel out when we subtract conditions?"**
This is the thermometer claim itself. We check that the +5° error is roughly
the *same* for everyone and in *every* condition — because only then does it
disappear when you take a difference. If the bias were bigger whenever the
Green side is loud, subtracting wouldn't clean it out, and our comparisons
would be measuring the bias instead of the persuasion. We also check the model
keeps agents in the *right order* (most sceptical to most green), because
that's what tells us the bias is a harmless re‑leveling and not scrambling who
believes what.

**Tier 2 — "Are we being fooled by the ruler running out of room?"**
Our opinion scale stops at +3. Agents who already start near the top can't move
much further — they're squashed against the ceiling. That can create fake
patterns (it can *look* like the Green side persuades more easily just because
the Reform side has more room to move). This tier re‑measures the same results
using rulers that don't have a ceiling (like "how far did each agent travel
from its start?") and checks the story doesn't change.

**Tier 3 — "Does the finding hold up, or did we just get lucky?"**
The big one. A single result on one model with one random seed could be a
fluke. So we repeat the *whole* thing across several different AI models and
several random seeds. If the same conclusion (e.g. "more reach for the Green
side moves opinion more than more reach for the Reform side") shows up
everywhere, it's real. If it flips around depending on which model we used,
it's an artifact and we can't publish it.

The logic is a chain: **Tier P** proves there's a signal → **Tier 1** proves
the bias cancels → **Tier 2** proves it's not a ruler artifact → **Tier 3**
proves it's not a fluke. Only if all four hold do we get to say "absolute
levels don't matter, but our *differences* are trustworthy science."

---

### 2026-07-03 — Handling the systematic pro-climate bias: treat the model as a "difference engine," not a "level predictor"

*(Precise statistics for everything referenced here are in
[result_report.md → "bias-invariance / difference-in-differences
validation"](result_report.md). This note is the framing and the plan; go
there for the numbers.)*

**The problem, in plain terms.** On Day 0 we seed each agent with the real
YouGov answer of the person it represents, so on Day 0 the simulation
matches reality exactly. But over the simulated week, *every* experimental
condition drifts **upward** — the agents end up more pro-climate than the
real people they started as. This is a systematic bias baked into the
language model itself (LLMs, trained on internet text, lean progressive on
climate). It means we cannot trust the model's **absolute** numbers: if the
simulation says "average support ended at +1.1," we have no grounds to claim
the real population would be at +1.1, because the model inflates everything.

**Why this felt like it might sink the project.** The whole point of the
asymmetry experiments is to compare conditions — does giving the Green side
more reach push opinion further than giving the Reform side more reach? If
the pro-climate bias were *tangled up with the treatment* (say, it inflated
more strongly whenever the Green side is loud), then the comparison would be
measuring the bias, not the persuasion, and the results would be worthless.

**The decision — a "difference engine."** Rather than trying to scrub the
bias out with prompt tricks (which risks overfitting and is hard to defend
to reviewers), we change what we *claim*. We stop reporting absolute levels
as findings and report only **differences between conditions**. The formal
statement we are committing to:

> *We treat absolute opinion levels as uninterpretable and restrict all
> inference to within-model, between-condition differences (difference-in-
> differences), where a common additive model prior cancels. We validate
> that this cancellation holds (bias-invariance test), that rank-order
> fidelity to ground truth is preserved, and that conclusions are invariant
> across models, debias framings, and seeds.*

**Why this is legitimate and not a cop-out — the thermometer analogy.**
Imagine a thermometer that always reads 5°C too high. It is useless for
answering "is it exactly 20°C outside?" but perfectly good for answering "is
today warmer than yesterday?" — because the +5 error is the same on both
days and *subtracts out* when you take the difference. Our model is that
thermometer. As long as the pro-climate bias is a roughly constant amount
added to everyone (an **additive offset**), any comparison between two
conditions cancels it. That is the entire logic of the framing, and it is
only valid if two things are actually true of our data — which is what the
Tier-1 test checked.

**The two things that have to be true (and the terms involved).**

1. **Rank fidelity must be high.** "Rank fidelity" means: if you sort the
   agents from most-sceptical to most-pro-climate using their real YouGov
   scores, does the simulation put them in the *same order*? We measure it
   with **Spearman's ρ** — a correlation that looks only at rank order, not
   raw values (ρ = 1 is a perfect order match, ρ = 0 is random). High rank
   fidelity is what tells us the inflation is a harmless re-leveling (the
   thermometer case) rather than the model scrambling who believes what. If
   the order is right, the model has genuinely learned the *structure* of
   opinion from the personas — it just reports it on a shifted scale.
2. **The bias must not interact with the treatment.** In plain terms, the
   +offset has to be about the same size in every condition. We check this
   two ways: an **ANCOVA homogeneity-of-slopes test** (a single test asking
   "is the relationship between real score and simulated score the same
   shape in all conditions?" — we *want* it to find no difference), and,
   more directly, a **difference-in-differences (DiD)** analysis. Because
   the same 50 agents appear in every condition, we can take one agent and
   subtract its result in condition B from its result in condition A; the
   bias cancels *for that individual*. The **acid test** is then: does that
   per-agent difference depend on where the agent started (its real score)?
   If it doesn't (a flat, non-significant relationship), the treatment
   effect is the same for sceptics and greens alike, and the bias has
   provably cancelled.

**What the Tier-1 validation found (numbers in
[result_report.md](result_report.md)).** Both conditions hold. Rank fidelity
is high in every run (ρ ≈ 0.8+). The bias is statistically the same shape
across conditions (the ANCOVA finds no difference). The treatment effects
are real and do **not** depend on any agent's starting position — and, going
further, they don't depend on the agent's *affinity* either (the score the
exposure-assignment rule uses to sort agents into who-hears-whom), so the
comparisons aren't secretly driven by the sorting mechanism. As a bonus, the
persuasion effect shows up exactly where the mechanism says it should — in
the agents who actually receive both broadcasts, and not in the unexposed
group — which is what a genuine causal effect looks like. **Verdict: the
reach-asymmetry conclusions are valid as differences. The framing works.**

**The one honest caveat we carry — the ceiling effect.** Our opinion scale
is bounded (it stops at +3), and the population already starts high (real
mean +0.587, with some agents already at the maximum). When a condition
pushes opinion upward, agents near the top *can't move much further* —
they're squashed against the ceiling. This is a mild form of **regression to
the mean** (extreme values have nowhere to go but back toward the middle),
and it shows up most in the green-dominant run. Two consequences: the Green
side's measured effect is if anything *under*-stated (conservative), and part
of the striking "Green amplifies easily but Reform can't drag opinion
negative" story is partly an artefact of the bounded ruler, not purely the
model being more persuadable in the green direction. It does **not** break
the difference framing, but a reviewer will spot it, so we pre-empt it.

**Next steps / strategy.**

- **Tier-2 — close the ceiling loophole (soon, cheap).** Re-express the
  outcome so the ceiling can't distort it: measure *distance travelled from
  the Day-0 anchor*, or transform the bounded score onto an unbounded scale
  (a rank or logistic transform), and confirm the ordering of the treatment
  effects is unchanged. It almost certainly will be; the point is to have
  the robustness check on record.
- **Tier-3 — the multiverse (the real work before publication).** Our
  committing statement promises the conclusions are "invariant across
  models, debias framings, and seeds." We have only shown it on one model
  (Qwen3-14B) and one seed so far. To earn that sentence we need to repeat
  the whole bias-invariance test on at least two more model families and two
  more random seeds, and treat the debias-prompt variants (Conditions
  A/B/D) as robustness arms rather than the main analysis. If the *direction
  and ordering* of the asymmetry effects survive all of that, the level bias
  is provably irrelevant to our claims and the paper is bulletproof on this
  axis.
- **Feeds the experiments-for-publication planning session** (the one we
  said we'd sit down for). The multiverse grid above is the backbone of it.

**The goal in one line.** Absolute opinion levels are reported only as
description; every *inferential* claim in the paper is a within-model,
between-condition difference, validated to be bias-free by the tests above.

---

### 2026-06-23 — "What a human sees" vs "what the LLM needs": two prompt-element categories

**Context.** During the design discussion for the v2 memory & context
architecture (see [plan in session memory], soon to land in
[src/cag/abm/agent.py](../src/cag/abm/agent.py)), a recurring tension
surfaced: do we shape the assembled-context prompt around what a real
surveyed citizen would have in mind when answering a survey, or around
what the LLM needs in order to *behave* like that citizen? These pull in
different directions and the choice is not always conscious.

**Framing.** Every element in a citizen-agent prompt falls into one of two
categories:

1. **Cognitive-architecture analog.** Things a real citizen would have
   functional access to — persona, recent peer-conversation memories,
   broadcast exposure, reflections-after-conversations, faded older
   memory. The mapping is `simulation feature ↔ human-cognition feature`.
   Examples in our code: `assemble_context`'s persona block, reflections
   bullets, daily summaries, the Day-0 anchor as "your original prior
   position."
2. **LLM-behavioural scaffolding.** Things added because the LLM has its
   own biases — sycophancy, recency, pattern-following, refusal styles,
   format-following — and we need to counteract them to recover human-
   like behaviour. The mapping is `prompt element ↔ behavioural correction
   in the LLM`. Examples in our code: the debias preamble (Condition B),
   "respond in first person", structured-output asks, anti-sycophancy
   phrasing, the "be honest about uncertainty" framing.

Both categories are legitimate, but **mixing them unconsciously creates
artefacts**. Concrete examples from our own runs:

- The debias preamble (a category-2 LLM-correction element) reduces Day-0
  inflation by ~97% in NB 13 but also makes survey reasoning
  unrealistically formal and list-like — category-2 leakage into the
  category-1 simulation trace (`survey_reasoning.csv` no longer reads like
  a real survey response, even though the numeric answer is better
  calibrated).
- The "Remember who you are: ..." trailing line being dropped in v2 is
  the reverse case: a category-1 element (re-priming identity) that the
  LLM doesn't actually need (modern instruction-tuned models retain the
  top-of-context persona), so it was acting as redundant noise rather
  than functional cognition.

**Practical implication.** When designing each prompt element, ask:
*is this here because (a) the citizen's human counterpart would have it,
or (b) the LLM needs it to behave well?* Both are valid; the danger is
unlabelled mixing. Two corollaries:

- **Architecture flexibility.** Build the `assemble_context` helpers as
  small, composable section-builders so that swapping category-1 elements
  (different memory tiers, different orderings) or category-2 elements
  (different debias styles, different output-structure asks) is a
  config-flag-sized change, not architectural surgery. This makes the
  inevitable "let's try a different prompt strategy" experiment cheap.
- **Validation matters more than intuition.** If we treat a prompt design
  as a hypothesis ("this structure makes the LLM behave like a real
  surveyed citizen"), it should be falsifiable the way hypotheses are
  falsifiable — with measurement (calibration MAE, cross-bucket
  gap-widening, persona-signal shuffle test), not by trusting that the
  prompt "reads right." The 3-condition smoke (baseline / v2-no-Day-0-
  anchor / v2-full) on a small run is a cheap way to keep this honest.

**Status.** No code change driven directly by this note. It informs the
v2 memory architecture work (in the
[session plan]) and the
upcoming sandbox notebook (`notebooks/33_*_sandbox.ipynb`). Revisit when
the 30-day production sweep starts and we have real persuasion signals
to interpret — at that point the category-1 vs category-2 lens becomes
the diagnostic tool for "is this a model finding, or a prompt artefact?"
