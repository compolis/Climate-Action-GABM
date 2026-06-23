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
**YouGov survey (January 2024)** — the simulation starts from observed
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
- **Mark superseded notes inline.** If a later note overrides an earlier
  one, prepend the older note with `> **SUPERSEDED YYYY-MM-DD:** see
  [note title](#anchor).` — do not delete it.
- **Out of scope here.** This file is NOT for: bug write-ups, code-change
  rationale, version-bump records, or anything that belongs in
  `CHANGE_LOG.md`, `DEVELOPMENT_HISTORY.md`, or `result_report.md`. Cross-
  reference those documents instead.

---

## Notes

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
