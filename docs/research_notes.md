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

### 2026-07-06 — Tier 3 (network arm), seed sweep: the finding replicates across seeds, and the "SBM is stronger" hint goes away

This is the follow-up to the 2026-07-05 network note below. That earlier note ran on a **single random
seed** and flagged two loose ends: (1) it could only speak to the *direction* of the effect, not its
*size*, and (2) the stochastic-block network (SBM) looked a touch stronger than the others, which we
called "a hint, not a result." We have now closed both by re-running the whole thing on **three seeds
(42, 43, 44)** — a full 3 networks × 3 conditions × 3 seeds = **27 runs**. See
[result_report.md](result_report.md) (2026-07-06 Tier-3 seed-sweep section) for the tables; this is the
plain reading. (The model arm — Apertus, Llama — is still a separate, pending gate.)

**What a "seed" is, and why three of them matters.** The seed is the random draw that decides which 100
people we simulate and how the graph gets wired. One seed is one roll of the dice: a result that looks
clean on a single roll might just be luck. Running the same experiment on three independent seeds and
combining them (300 matched people per network instead of 100) tells us whether the effect is real or a
fluke of one draw. Because the people are re-drawn each seed, we always compare a person to *themselves*
within the same seed, then pool the three — never mixing people across seeds.

**Finding 1 — the headline is now seed-replicated.** A louder Green side beats a louder Reform side on
**every one of the nine** network-by-seed combinations, and the pooled effect is strong and clearly
significant on all three networks: SBM **+0.42**, Barabási–Albert **+0.34**, Watts–Strogatz **+0.36**
(package-index points; all p well below 0.001). So the reach-asymmetry isn't just robust to network
*shape* — it's robust to the random draw too. This upgrades the earlier note from "directionally true on
one seed" to "replicated."

**Finding 2 — the SBM "edge" was a lucky seed, and it's now retracted.** On the single pilot seed the SBM
came out at +0.53 versus +0.32 and +0.36 for the other two, which is why we hedged about it. With three
seeds the story is clear: SBM's per-seed values are **0.53, 0.42, 0.31** — the pilot happened to catch
its *highest* draw. Averaged out it lands at +0.42, and its confidence interval now overlaps the other
two networks completely. In other words, the three networks are **indistinguishable in effect size**;
there is no special amplification from the stochastic-block graph. This sits comfortably with Finding 2
of the old note (the SBM was never actually an echo chamber — its exposure-sorting score is ≈ 0), so
there was never a mechanism for it to be genuinely stronger. Watts–Strogatz, for what it's worth, was
astonishingly steady across seeds (0.363 / 0.360 / 0.357).

**Finding 3 — pooling tightened a loose thread.** On the single pilot seed, one of the two "halves" of
the asymmetry — the *Green amplifies people upward* half — was not statistically clean on the
Barabási–Albert graph (it was a bit noisy). With three seeds it firms up and becomes significant, so we
can now say **both** halves contribute on **all three** networks: turning the Green side up pushes
opinion up, and turning the Reform side up pushes it down. The extra data removed the wobble rather than
moving the conclusion.

**Everything else still holds.** Rank fidelity — the model keeping people in the right order relative to
the real survey — stays high (Spearman ρ ≈ 0.78–0.87) on every network and condition, so Qwen keeps the
persona signal when we rewire the graph. And in the genuinely contested audience (the ~60% who hear
*both* sides), the three networks agree tightly (effect 0.44–0.50), so the small whole-population
differences are about how the message *spills over* to people who weren't directly targeted, not about
the persuasion itself.

**Where this leaves Tier 3.** The network arm is now fully passed *and* seed-replicated: the finding
reproduces on scale-free and small-world graphs, at the same size, correctly-signed, rank-faithful, and
bias-invariant. The one caveat the old note left open — a possible SBM size advantage — is closed and
retracted. The only remaining Tier-3 gate is the **model arm**: does the same hold on a different AI
model family?

### 2026-07-05 — Tier 3 (network arm): the reach-asymmetry isn't an artefact of the social graph

> **Update (2026-07-06):** the single-seed caveat below has since been closed by a three-seed sweep —
> see the 2026-07-06 note above. The headline replicated; the tentative "SBM is a touch stronger" hint
> in Finding 1 did **not** survive the extra seeds and is retracted. The rest of this note still stands.

Tier 3 is the "does it replicate?" gate. It has two independent arms: swap the **AI model** (does the
finding survive on other model families?) and swap the **social network** (does it survive a different
peer-messaging graph?). This note covers the **network arm** only; the model arm (Apertus, Llama) is
separate and still running. See [result_report.md](result_report.md) (2026-07-05 Tier-3 network
section) for the tables — this is the plain reading.

**Why the network could matter.** Citizens don't only hear the political broadcasts; they also pass
messages to their neighbours on a social network, so *who is wired to whom* can amplify or dampen a
persuasion effect. Our default network is a **stochastic-block model (SBM)** — two communities with
dense ties inside and sparse ties across. Crucially, those two blocks are built from each citizen's
**exposure bucket** (the A-only crowd in one block, the B-only crowd in the other). That raised a
fair worry: maybe the reach-asymmetry only shows up because the graph *itself* is organised around
who hears which side — a built-in echo chamber doing the work, not the messages. To test that, we
re-ran the exact same experiment on two networks that are **blind to exposure**: a **Barabási–Albert**
graph (a "scale-free" network with a few very highly-connected hubs, like a handful of influencers)
and a **Watts–Strogatz** graph (a "small-world" network — mostly local, tight-knit clusters with a
few long-range shortcuts). All three were tuned to the same average number of connections per person
(~10), so we change the *shape* of the wiring, not its overall density.

**The clean part of the design.** Because we fixed the random seed, all three networks contain the
*same 100 people*, with the same real opinions, the same exposure assignment, and the same
broadcasts — the *only* thing that changes is the wiring. So any difference in the result is due to
network shape and nothing else. (Caveat: this is a single random draw, so we read the *direction* and
*significance* within that draw, not a claim about the effect's exact *size* across many draws — a
seed sweep is the deferred next step.)

**Finding 1 — the headline survives on every network.** A louder Green side still beats a louder
Reform side on all three graphs, correctly signed and statistically clear in each. The effect is a
touch larger on the SBM, but the confidence intervals overlap, so we treat "SBM is stronger" as a
hint, not a result. The reach-asymmetry is **not** an artefact of the stochastic-block graph — it is
safe to move away from SBM.

**Finding 2 — and it corrects our going-in worry — the SBM is not actually an echo chamber.** We
measured how strongly the network sorts people by exposure — a number called *assortativity* (+1 =
perfectly sorted into like-with-like, 0 = no sorting at all). For the SBM it came out ≈ 0. The reason
is our exposure design: ~90% of citizens are in the `both` or `neither` buckets, and those get split
evenly across the two SBM blocks; only the ~10% dedicated-audience citizens are actually sorted by
side. So the SBM was never the treatment-aligned echo chamber we feared, which means its slightly
larger effect *can't* be attributed to homophily. A nice example of the data correcting an
assumption we walked in with.

**Finding 3 — the model still keeps people in the right order, off-SBM too.** The whole
difference-engine argument needs the simulation to preserve *who is greener than whom* relative to the
real survey (measured by Spearman ρ, a rank-order correlation where near +1 means the ordering is
faithfully kept). That held comfortably (ρ ≈ 0.82–0.90) on every network — Qwen doesn't lose the
persona signal when we rewire the graph. (This is the same test on which the smaller Llama-3.1-8B
model fell apart at ρ ≈ 0.46, which is why Qwen-14B stays our primary model.)

**Where this leaves Tier 3.** The network arm passes: the finding reproduces on scale-free and
small-world graphs, correctly-signed, rank-faithful, and bias-invariant. The remaining Tier-3 gates
are the **model arm** — does the same hold on a different AI model family? — and, for a full
effect-*size* claim, a seed sweep on the alternative topologies.

### 2026-07-05 — Tier 2: the sceptic-tilt was the ruler, not the people (and bias-invariance is restored)

Tier 2 asks the one question Tier 1 couldn't answer about itself: *are we being fooled by the
opinion ruler running out of room?* Our scale stops at +3, so citizens who already sit near the top
physically can't move much further. That can fake an asymmetry — the Green side looks more
persuasive just because pro-climate citizens have no headroom while sceptics do. See
[result_report.md](result_report.md) (2026-07-05 Tier-2 section) for the tables; this is the plain
reading. It is a **pure re-analysis — no new runs**: the same 12 Tier-1 runs, re-measured on four
rulers (the raw −3…+3 scale; a "headroom" ruler that scores movement as a fraction of the room a
citizen had; a "logit" ruler that stretches moves near the ceiling; and a pure rank ruler that keeps
only the ordering and so is immune to any scale distortion).

**Finding 1 — the headline is bulletproof.** A louder Green side beats a louder Reform side on
*every* ruler, including the scale-free rank one (same direction, similar standardised size, all
overwhelmingly significant). The core result is not an artefact of how we drew the scale.

**Finding 2 — and this corrects Tier 1 — the "sceptics move more" tilt is the ruler, not the
people.** On the two ceiling-free rulers the tilt vanishes (flat, non-significant); only a negligible
ordinal residual survives on the rank ruler (significant merely because we have 300 citizens — the
same negligibility-vs-significance trap we flagged in Tier P). Tier 1 had tried to rule out a ceiling
by dropping the citizens literally pinned at +3, and the tilt held — but that missed the point: the
bounded scale gradually squashes the *whole* upper range, not just the pinned few. Re-scaling fixes
that graded squash, and the tilt evaporates.

**Why this is good news.** The effect turns out to be **roughly uniform** across the spectrum — it
moves sceptics and greens by about the same amount. So the reach-asymmetry effect does *not* depend
on where a citizen started, which is exactly the **bias-invariance** the whole difference-engine
argument needs. Tier 1's raw-scale acid-test "failure" was itself a scale artefact; on an appropriate
ruler, bias-invariance holds cleanly. The honest, load-bearing claim is therefore simpler and
stronger than the Tier-1 draft below: *a broad, directional, bias-invariant persuasion effect,
robust to how the opinion scale is drawn.* The last remaining gate is Tier 3 — does it replicate
across different AI models and seeds?

### 2026-07-04 — Tier 1 in plain language: the aim and the full implications (explainer)

#### What Tier 1 was trying to find out

The model has a known quirk (from NB 37): its simulated citizens sound **more pro-climate than real people** — it's inflated in *level*. That's a problem if you read opinions off it directly.

But the whole point of the project is not to predict *levels* — it's to measure **what happens when one political side can shout louder than the other**. So Tier 1 asked one simple question:

> **When we give the Green side a bigger megaphone than the Reform side (or vice versa), does the resulting shift in public opinion come through clearly — even though the model is biased?**

The trick to answering it: run the **same 100 citizens** through four different worlds (equal megaphones, green-louder, reform-louder, and a silent "no broadcasts" control), and compare each person **to themselves** across worlds. Because everyone starts pinned to their *real* survey opinion, when you subtract one world from another the bias is identical in both and **cancels out** — leaving only the effect of who was louder. (That's the "difference-in-differences" method.) We repeated everything for three random samples so nothing rests on one lucky draw.

#### What we found — and what it means

**1. The core method works. The persuasion effect is real, strong, and cleanly directional.**
A louder Green side leaves people meaningfully more pro-climate than a louder Reform side (+0.42 on a −3…+3 scale, a medium-sized effect, essentially certain to be real, same direction in all three samples). The silent placebo confirms it: green pushes opinion up, reform pushes it down. So **yes — the model can be trusted to measure the *direction and relative size* of a messaging asymmetry, despite its bias.** This is the green light for the asymmetry paper.

**2. The effect is broad, not a fluke of one issue.**
All six climate policies moved the right way. The biggest movements were on **contested** policies (banning petrol cars, banning fossil-fuel licences, carbon tax); the smallest were on policies **almost everyone already supports** (renewable energy, green housing) — and those are small mostly because people are already at the top of the scale with nowhere to go. So the signal is genuinely spread across the board.

**3. A twist that looked real at first — but wasn't.**
On the raw −3…+3 scale the effect *appears* bigger for sceptics (≈+0.70 for the most-sceptical third of people vs +0.14 for the greenest third), and dropping the people literally pinned at the top didn't remove it — so our first reading called it a genuine behavioural fact. **Tier 2 (done minutes later) overturned that.** The bounded scale quietly squashes *everyone* in the upper range, not just the pinned few; when we re-measure on rulers with no ceiling (see the 2026-07-05 Tier-2 note above), the tilt disappears. So it was **largely a measurement artefact of the ruler**, not a real difference between sceptics and greens.

**4. What's actually true: the effect is close to uniform — and that's good news.**
Once the ceiling is handled properly, a louder Green side moves sceptics and already-green citizens by about the *same* amount. That means the persuasion effect doesn't depend on where a person started — which is exactly the **bias-invariance** we wanted: the model's pro-climate lean cancels cleanly in the difference, for everyone.

#### The bottom line

- **For the model:** it's a valid "difference engine." You can't trust its absolute opinion *levels*, but you **can** trust it to measure how an imbalance in political messaging changes opinion — the thing the whole study is about.
- **For the science:** louder one-sided messaging produces a broad, correctly-signed shift in public opinion, roughly **uniform across the spectrum** — it moves sceptics and greens alike, rather than only winning over one group. (Our first-pass "it mostly wins over sceptics" reading turned out to be a scale-ceiling artefact — see point 3.)
- **For the paper:** state it as *"a broad, directional persuasion effect that survives the model's bias and is uniform across the opinion spectrum"* — i.e. genuinely **bias-invariant**, robust to how the opinion scale is drawn.
- **For what's next:** Tier 2 has now done the scale-aware re-measurement and confirmed the effect is uniform (the ceiling was the culprit). The remaining question is Tier 3: does the whole finding replicate across different AI models and seeds?

### 2026-07-04 — Tier 1: the difference-engine works (headline robust) — [updated 2026-07-05: the raw-scale "sceptic-tilt" below was a scale artefact; see the Tier-2 note above]

Tier 1 is the honest, multi-seed rerun of the reach-asymmetry pilot (n=100,
three seeds, four worlds: equal reach, green-dominant, reform-dominant, and a
no-broadcast placebo). It set out to answer one question: when one political
side gets a louder megaphone, does the opinion shift it causes come through
cleanly once we strip out the model's known pro-climate lean? See
[result_report.md](result_report.md) (2026-07-04 Tier-1 section) for the tables;
this note is the plain-language reading.

**The good news — the difference engine holds.** Comparing the same citizen
across worlds and differencing (so the ground-truth anchor and the model's
inflation cancel), a louder Green side leaves people about **+0.42 index points**
more pro-climate than a louder Reform side — a solid, medium-sized, wildly
significant effect that is the same sign in every seed, and the placebo moves the
two sides in opposite directions (green up, reform down). Breaking it down policy
by policy, **all six policies move the right way**, biggest on the contested ones
(ban petrol cars, ban fossil licences, carbon tax) and smallest on the
near-consensus favourites (renewable energy, green housing) where most people are
already maxed out. So the persuasion signal is broad, not a one-policy artefact.

**The apparent caveat — and why Tier 2 overturned it.** On the raw scale the effect *looks* like it
depends on the starting point — markedly larger for sceptical citizens (+0.70 in the most-sceptical
third vs +0.14 in the greenest third) — and removing the citizens literally pinned at the +3 ceiling
doesn't change it, which initially led us to call it a genuine behavioural sceptic-tilt. **Tier 2
(2026-07-05) showed that was wrong.** The bounded ruler compresses the *whole* upper range, not just
the pinned agents; on ceiling-free rulers (headroom, logit) the slope goes flat and only a
negligible ordinal residual remains. So the effect is essentially **uniform** across the spectrum —
which means the pilot's original *bias-invariant* reading was right after all, and Tier-1's raw-scale
acid-test "failure" was itself the scale artefact.

**What this means for the paper.** We *can* claim bias-invariance: one-sided messaging produces a
broad, correctly-signed shift that survives the model's level bias in every contrast, across all six
policies, and (per Tier 2) on every ceiling-free ruler, roughly **uniformly across the opinion
spectrum**. The residual level-inflation on high-consensus policies is a measurement ceiling that
also produced the raw-scale sceptic-tilt illusion — both are handled by scale-aware measurement, not
real threats to the contrast. Tier 2 is now done; Tier 3 (replication across models and seeds) is
the last gate.

### 2026-07-04 — Calibration: the raw model is inflated in *level* but faithful in *rank* — the empirical licence for anchoring

This is the companion to the Tier-P note below. Tier P proved the model
*orders* agents correctly; this note explains what we found when we asked the
harder question — *how far off are the actual numbers?* — and why the answer is
the justification for anchoring Day 0 to ground truth. The exact metrics live
in [result_report.md](result_report.md) ("v0.9 — Tier-P calibration & anchor
justification"); the analysis is [NB 37](../notebooks/37_tierP_calibration.ipynb).

**The distinction that matters: level vs rank.** An opinion measurement can be
wrong in two very different ways. It can put people in the *wrong order* (rank
error — thinks a sceptic is greener than an activist), or it can order everyone
correctly but read *systematically too high* across the board (level error —
like a thermometer that always reads 5° hot). These have opposite consequences
for this project. Rank error is fatal: if the model can't tell who's greener,
no downstream comparison means anything. Level error is *survivable* — because
when you compare two conditions run on the same agents, a common offset
subtracts out. Tier P already told us rank is good (ρ ≈ 0.62). NB 37 measures
the level error and checks it really is just an offset.

**What we found.** Running the Day-0 survey with *no* anchor (letting the model
derive each opinion from the persona), the model reads about **+0.64 too high**
on the package pro-climate index — and with *no persona at all* it reads **+1.5
too high**, sitting at a near-uniform "climate is good" answer. So a real
persona pulls each agent most of the way back toward its true position, but a
residual pro-climate tilt remains. Crucially, that residual is a *level*
problem: the rank order is preserved (ρ ≈ 0.62), and the bias has the *same
sign right across* the opinion range — it's an offset, not a scramble. It's
worse on the salient behaviour-change policies (banning petrol cars is inflated
+1.6, carbon tax +1.0) and essentially absent on green housing standards, which
is a sensible pattern: the model is most over-eager exactly where real public
opinion is most divided and cost-sensitive.

**One honest caveat — the ceiling.** The scale stops at +3, and a chunk of
agents already sit there in reality. The model can't inflate someone who's
already maxed out, which mechanically bends the fitted line and makes sceptics
*look* like they're inflated more than greens. Some of the "regression to the
mean" we see is therefore a scale artefact, not a modelling failure — which is
precisely what the later scale-robustness tier is built to disentangle. Worth
flagging now so we don't over-read the bias-vs-truth slope.

**Why this is the licence to anchor.** Because the error is a preserved-order
offset, we can remove it *by construction*: the production setting
(`ground_truth_with_rationale`) seeds each agent's Day-0 *number* from the real
survey value and asks the model only to *write the reasoning* behind it. That
zeroes the Day-0 level error (perfect calibration by definition) while keeping a
coherent, persona-grounded reasoning chain to drive the subsequent dynamics. In
other words: we don't trust the model to tell us *where opinion sits*, but we do
trust it to tell us *how opinion moves* once correctly placed — and NB 37 is the
evidence that this division of labour is legitimate. This is the same
"difference engine" logic as the v0.8 work, now backed by a direct calibration
measurement of the thing anchoring throws away.

---

### 2026-07-04 — Tier P cleared: the model is genuinely reading personas (foundation gate = GO)

The first of the four validation tiers is done, and it passed cleanly. This is
the note explaining *what that means and why it matters*; the exact numbers
live in [result_report.md](result_report.md) (the "v0.9 — Tier-P persona-null
ablation" section), and the analysis is in
[NB 36](../notebooks/36_tierP_persona_null.ipynb).

**Why this gate had to come first.** The whole project rests on one bet: that
even though the model reads *too* pro-climate in absolute terms, it still
places agents in the *right order* and *reacts to who each agent is*. If that
bet is wrong — if the model just emits a generic "climate is good" answer
regardless of the persona we hand it — then every downstream comparison is
measuring the prompt, not the person, and the project is dead on arrival. Tier
P is the sanity check for exactly that.

**How we tested it.** We ran the Day-0 survey three ways on the same 100
agents, three random seeds each. In the **real** arm each agent got its own
YouGov persona. In the **shuffled** arm we handed every agent *someone else's*
entire persona (a *derangement* — a reshuffle where nobody keeps their own, so
each agent is wearing a stranger's biography). In the **neutral** arm we
stripped the persona entirely, leaving only "I am an adult living in the United
Kingdom." Then we asked: does the model's opinion follow the persona, or not?

**What we found — three things, all pointing the same way.**

1. *Real agents recover their own opinions.* The rank correlation between the
   model's Day-0 opinion and each agent's real survey answer is **ρ ≈ 0.62**
   (Spearman ρ is a rank correlation: 1.0 means the model orders agents exactly
   as the survey does, 0 means no relationship). That's a strong, seed-stable
   signal — the model is clearly listening.

2. *The smoking gun — shuffled agents track the persona they were handed, not
   their own body.* When an agent wears a stranger's persona, its opinion
   correlates **+0.61 with that stranger's** real opinion and essentially
   **zero with its own** (−0.12, and even that small negative is a mechanical
   side-effect of the reshuffle, not real signal — see the result report). This
   is the cleanest possible evidence that the *persona text itself* drives the
   answer. It isn't the agent's identity, or a fixed prior, or anything baked
   into the model — swap the biography and the opinion swaps with it. That
   dissociation is worth more than the real-arm correlation alone, because a
   high real-arm correlation *could* in principle be an artefact of some other
   agent property; the shuffle rules that out by construction.

3. *No persona → no diversity.* Strip the persona and the 100 agents collapse
   onto essentially one answer: the spread of opinions shrinks to **~10%** of
   the real-arm spread, and they all land at a uniformly high pro-climate value.
   This confirms that the variety we see across agents in the real runs is
   *coming from the personas*, not from sampling noise or temperature.

**What this licenses — and what it doesn't.** Tier P proves there *is* a
persona-driven signal to work with, so the difference-engine program is cleared
to continue to Tier 1 (does the bias cancel in differences?), Tier 2 (are we
fooled by the scale ceiling?), and Tier 3 (does it replicate across models and
seeds?). It does **not** say the model's *levels* are right — in fact this same
run quantifies how wrong they are: the persona-free "neutral" floor sits about
+1.5 above the true mean, and even the real agents read about +0.6 high. That
inflation is the very thing the anchoring machinery is designed to subtract,
and measuring it precisely is a separate calibration notebook (deliberately
kept out of this Tier-P analysis so the validity gate and the calibration story
don't get tangled).

**One methodological lesson worth remembering.** The automated GO/NO-GO check
first *failed* Tier P on a technicality: it asked whether the shuffled-vs-own
correlation's confidence interval excluded zero, and at n=300 even a trivially
small −0.12 clears that bar. But "is this effect *negligibly small*?" is a
different question from "is this effect *distinguishable from zero*?" — with
enough data everything is distinguishable from zero. The fix was to score that
gate as a *negligibility* test (is |ρ| small, and far below the used-persona
correlation?) rather than a significance test. The finding never changed; only
the yardstick did. Good reminder that for "this should be ≈0" claims,
significance testing is the wrong tool.

---

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
