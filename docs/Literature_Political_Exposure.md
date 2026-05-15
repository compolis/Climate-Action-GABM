# Literature Survey — Direct Political-Agent Exposure on UK Climate Policy

**Status:** initial draft, 2026-05-14. Compiled to inform Priority 2 of the
v0.5 planning cycle (rule-based broadcast-audience assignment in
`Model_Design.md`). **All numerical figures below should be treated as
approximate until verified against the cited primary sources.** Specific
percentages were assembled from working knowledge of the listed reports and
are flagged where confidence is low. Use this document as a scaffold for a
full literature survey rather than a finished citation.

---

## 1. Why this question matters for the model

The model's current `assign_political_exposure()` function (in
`src/cag/abm/agent.py`) places every citizen into one of four cells —
`A-only`, `B-only`, `both`, `neither` — using deterministic rules over
voting history and self-reported political identity. The realised
distribution of those four cells is therefore an unintended artefact of
the YouGov sample composition, not a calibrated quantity.

To make the model defensible at the population level, the four-cell
distribution needs to be either (a) treated as an explicit experimental
parameter with sensitivity bands, or (b) calibrated to UK media-reach
data. This document collects the empirical evidence relevant to that
calibration.

---

## 2. Population-level news reach (UK)

### 2.1 Reuters Institute Digital News Report (annual)

The single most-cited cross-national source on news consumption.
Published by the Reuters Institute for the Study of Journalism (Oxford).

- Reuters Institute (2024). *Digital News Report 2024.*
  Landing page: <https://reutersinstitute.politics.ox.ac.uk/digital-news-report/2024>
- Reuters Institute (2025). *Digital News Report 2025.*
  Landing page: <https://reutersinstitute.politics.ox.ac.uk/digital-news-report/2025>

Headline figures relevant to this model (UK chapter, **approximate**):

- Weekly news access: ~75–80% of UK adults.
- **Selective news avoidance** (sometimes / often): ~40–46% — roughly
  doubled since 2017. This is the strongest empirical motivation for a
  large `neither` cell in the four-way split.
- Trust in news (UK): ~30–36%, persistently below the cross-national average.

### 2.2 Ofcom News Consumption in the UK

Statutory regulator's annual survey; the canonical UK source on
platform-level reach.

- Ofcom. *News Consumption in the UK* (annual report).
  Landing page: <https://www.ofcom.org.uk/news-and-data/data/news-consumption-research>

Headline UK reach figures most relevant here (most recent reports,
**approximate**):

- TV news: ~65–70% weekly reach (BBC ~55–60%, ITV ~30–40%).
- Online news: ~65–70%.
- Social media as news source: ~45–55% (Facebook largest; YouTube and
  TikTok rising; X declining among older cohorts but central for
  political-elite messaging).
- Print: ~15–25% and falling.
- Radio news: ~30–40%.

These are **outlet** reach, not party-attributable reach — which is the
quantity the model actually needs.

### 2.3 Hansard Society Audit of Political Engagement

Long-running UK survey on political interest. Last full audit was 2019;
subsequent work appears under different titles.

- Hansard Society. *Audit of Political Engagement 16* (2019).
  Landing page: <https://www.hansardsociety.org.uk/publications/reports/audit-of-political-engagement-16>

Approximate distribution: ~30% follow politics "a great deal", ~30%
"a fair amount", ~40% "not much / not at all". The bottom ~40% is a
plausible upper bound on `neither` in the model's four-cell split.

---

## 3. Direct exposure to *party* messaging

Outlet reach (Section 2) overstates direct partisan exposure, because
much news content is non-partisan or party-balanced. The literature on
party-attributable exposure is sparser; the most useful sources are:

### 3.1 Audience overlap and "echo chambers"

- Dubois, E., & Blank, G. (2018). The echo chamber is overstated: the
  moderating effect of political interest and diverse media.
  *Information, Communication & Society*, 21(5), 729–745.
  DOI: <https://doi.org/10.1080/1369118X.2018.1428656>

  **Key finding (UK survey):** when *all* media use is counted (not just
  one platform), only a small minority of UK adults — figures in the
  paper put it around **8%** — fall into a strict echo chamber. The
  modal user encounters at least some cross-cutting content. Sets a
  ceiling on the `A-only` and `B-only` cells when measured strictly,
  but the threshold for "exposure" in the model is much weaker than
  Dubois & Blank's strict echo-chamber criterion, so the model's
  `A-only` / `B-only` cells should be larger than 8%.

- Bakshy, E., Messing, S., & Adamic, L. A. (2015). Exposure to
  ideologically diverse news and opinion on Facebook.
  *Science*, 348(6239), 1130–1132.
  DOI: <https://doi.org/10.1126/science.aaa1160>

  US Facebook study; widely cited. Approximately 20–25% of users'
  partisan-identified content was *cross-cutting*. Not UK and not
  recent, but it is the standard reference point for cross-platform
  audience-overlap arguments.

- Eady, G., Nagler, J., Bonneau, R., & Tucker, J. (2019). How many
  people live in political bubbles on social media? Evidence from
  linked survey and Twitter data. *SAGE Open*, 9(1).
  DOI: <https://doi.org/10.1177/2158244019832705>

  Strict echo-chamber subset on Twitter ~10–20%; majority of users
  follow accounts spanning a non-trivial ideological range.

### 3.2 Political-knowledge studies as a proxy for "Both" exposure

Where direct-exposure surveys do not exist, knowledge of party
*positions* is a reasonable lower-bound proxy for exposure to those
positions.

- British Election Study (BES) panel data — party-position recall items.
  Landing page: <https://www.britishelectionstudy.com>

- Whitmarsh, L., Capstick, S., et al. (2022). Use of aviation by
  climate-change researchers; and related Cardiff CAST climate
  engagement panel work.
  CAST programme: <https://cast.ac.uk>

  CAST publishes UK climate-attitude tracker data. Relevant approximate
  finding from Whitmarsh / CAST work: a substantial minority of UK
  adults report rarely or never hearing climate-policy positions
  attributed to a specific party; the share who can correctly attribute
  a *specific climate position* to *both* a left-of-centre and a
  right-of-centre party is in the low double digits. **Exact figures
  need verification from the underlying survey reports.**

---

## 4. Climate-specific audience segmentation (UK)

Climate-policy attitudes do not map cleanly onto general left/right
identity, and the audience-segmentation literature is the closest thing
the model has to a topic-specific calibration target.

- Climate Outreach. *Britain Talks Climate* and *Climate Barometer*
  programme.
  Landing page: <https://climateoutreach.org/reports/britain-talks-climate>
  Climate Barometer: <https://climatebarometer.org>

  Britain Talks Climate identifies seven UK audience segments ranging
  from "Progressive Activists" (most engaged on climate) to
  "Backbone Conservatives" / "Disengaged Traditionalists" (least
  engaged). Relevant for assignment: the highly-engaged pro-climate
  segment is a plausible "A-only" audience; the climate-sceptic /
  disengaged segments map to "B-only" or "neither". Exact segment
  sizes should be cited from the most recent BTC report.

- Steentjes, K., Pidgeon, N., Poortinga, W., et al. (2017).
  *European Perceptions of Climate Change.* Cardiff University.
  Landing page: <https://orca.cardiff.ac.uk/id/eprint/98660/>

  Comparative cross-country baseline; older but still cited.

- Capstick, S., Whitmarsh, L., Poortinga, W., Pidgeon, N., & Upham, P.
  (2015). International trends in public perceptions of climate change
  over the past quarter century. *WIREs Climate Change*, 6(1), 35–61.
  DOI: <https://doi.org/10.1002/wcc.321>

  Methodological background on tracking UK climate attitudes.

---

## 5. Reform-vs-Green asymmetry (the model's exemplar pair)

The model's two political agents are exemplars of a more general
"committed minority vs committed minority" structure, but the
Reform-vs-Green pairing is a useful anchoring case because (a) both are
politically salient in 2024–2026, and (b) their media reach is
strikingly *asymmetric*.

### 5.1 Reform UK reach

- Ofcom audience tracking of GB News and Talk TV (annual reports).
- Press Gazette reach reports (Telegraph, Mail, Express, Spectator).
- Public X analytics: Nigel Farage personal account is among the
  largest UK political accounts (multi-million followers as of 2024).

Approximate audience profile (qualitative consensus across the above):
GB News audience skews older (~70% over-50), Leave-voter (~60–70%),
and over-indexes on prior Brexit Party / Reform UK voters. A pure
"B-only" cluster on climate is structurally large because the legacy
right-of-centre press carries climate-sceptic framing more
consistently than left-of-centre press carries pro-climate framing.

### 5.2 Green Party reach

Mainstream political coverage of the Green Party is much thinner. Green
co-leaders receive a small fraction of the broadcast minutes that
Reform leadership does. Pro-climate framing reaches audiences mainly
through outlets (BBC environment desk, Guardian, FT) that *also* carry
Labour and Lib-Dem voices, so true "A-only" exposure to Green-attributed
climate messaging is rarer than "B-only" exposure to Reform-attributed
climate messaging. **No single primary source quantifies this cleanly;
this is a synthesis claim that needs assembly from Ofcom airtime data
plus party-coverage content analyses.**

### 5.3 Implication for the model

The Reform > Green asymmetry is an *empirical regularity*, not a
modelling assumption. Symmetric reach is the counter-factual condition
worth running, not the default. **However** — see Section 7 — the user
prefers to keep the political agents *exchangeable* by default and
expose the asymmetry as a configurable control, so that the model is
not over-fitted to one specific pair of UK parties.

---

## 6. Synthesised four-cell breakdown (UK climate)

These figures are the analyst's synthesis, not lifted from a single
source. They should be treated as a *defensible starting point* rather
than ground truth, and revisited once the cited sources are read in
detail.

| Cell | UK adult % (approx.) | Source signal |
|---|---|---|
| `Neither` | 35–50% | Reuters news avoidance + Hansard low-interest + climate-disengaged segments |
| `Both`    | 15–25% | Politically engaged subset; Whitmarsh "knows both sides" item; Dubois & Blank non-echo-chamber majority |
| `B-only`  | 20–30% | Reform / GB News / right-press cluster |
| `A-only`  | 10–20% | Climate-engaged Green / Guardian / BBC-environment cluster |

Modal cell on a niche topic like climate is `Neither`, not `Both`. The
`B-only` cell is structurally larger than the `A-only` cell under
current UK media conditions.

### 6.1 What the current code actually produces (measured 2026-05-14)

For comparison, running the existing `assign_political_exposure()` on
the full YouGov pool (`YouGovProcessedData.csv`, N = 1483):

| Cell      | Count | Share  |
|-----------|------:|-------:|
| `A-only`  |   405 | 27.31% |
| `B-only`  |   285 | 19.22% |
| `both`    |   725 | **48.89%** |
| `neither` |    68 |  **4.59%** |

A-audience = 76.2 %, B-audience = 68.1 % — i.e. the YouGov-driven
rule produces an **A > B** asymmetry of ~8 pp, which is the *opposite*
of the UK media reality summarised in Section 5, and a `neither` share
roughly an order of magnitude smaller than the lit-supported range.

This is the gap the calibration mechanism in `Model_Design.md` §18 is
designed to close.

### 6.2 Two senses of `neither` and who is actually in it

A recurring confusion when reading the four-cell split is what
`neither` is supposed to mean. There are two distinct readings, and
the lit supports very different numbers for each.

**Sense 1 — "hears nothing about politics or climate from any source,
ever".** Vanishingly small. Reuters DNR's *consistent* news avoiders
(people who say they always — not just sometimes — avoid news) sit
around 6–9 % across markets. Even those few are not in an information
vacuum: workplace conversations, family WhatsApp groups, ambient TV in
public spaces, school-gate chat and TikTok-on-the-train all carry
political and climate references. The information-isolation literature
(Prior 2007 onwards in the US, replicated for the UK in smaller
studies) puts true "no political information at all" at ~2–4 %.

**Sense 2 — "receives no direct *party-attributed broadcast*
messaging".** This is the reading the model actually uses: a `neither`
citizen is absent from both political agents' `connected_citizens`
lists and so does not receive a daily political-agent broadcast. They
still go through peer messaging, end-of-day survey, memory updates and
everything else. Under this reading, **35–45 %** is comfortably
lit-supported:

- Reuters DNR 2024: UK selective news avoidance 46 %; news interest
  almost halved 2015 → 2024 (70 % → 38 %); women and under-35s
  driving the decline.
- Reuters DNR 2025: news avoidance still rising; Bulgaria (63 %),
  Croatia (61 %) at the top end; UK firmly in the upper-middle band.
- Hansard *Audit of Political Engagement 16* (2019): ~40 % "not much
  / not at all" interested in politics — these respondents are not
  parsing party-attributed climate-policy claims even when they brush
  past them on a feed.
- Climate Outreach *Britain Talks Climate*: "Disengaged Battlers" +
  "Disengaged Traditionalists" together ~25–30 %, and these are the
  *climate-specific* equivalent of `neither`.

**The model's `neither` cell is therefore a "no-broadcast-receipt"
cell, not an "information void" cell**, and 35 % is defensible. The
intuition that disengaged citizens still pick up climate talk through
peers is correct and is *already* what the simulation does — peer
messaging runs for everyone.

#### 6.2.1 Demographic signature of the genuinely disengaged

The lit converges on a recognisable profile for the people who sit in
Sense 2 `neither`. Useful as understanding-the-population context
even though we cannot directly source new respondents matching it (see
§8 below for why):

- **Voting history.** Heavily over-represented among UK general-
  election non-voters (GE2019 turnout was 67 % overall but ~40 %
  among the "not at all interested in politics" tier); over-represented
  among "Don't know" Brexit responses; over-represented among
  "Other / refused" and "None" GE2019 responses.
- **Age.** Bimodal: 18–24 (digital news-skippers) and 75 + (cohort
  exit from political engagement). Reuters DNR confirms the under-35
  half of this distribution is the part that has grown most this
  decade.
- **Education.** Strong gradient — disengagement concentrated among
  those without a degree.
- **Income.** Mild gradient, lower deciles modestly over-represented.
- **Party identification.** "None" / "Don't know" / "Other" responses
  are dramatically over-represented relative to the politically-engaged
  cells.
- **Climate-policy *literacy*.** CAST tracker work (Whitmarsh et al.)
  shows the disengaged segments hold *attitudes* toward climate but
  cannot reliably attribute a specific climate policy to a specific
  party — they have feelings, not party-mapped feelings.

#### 6.2.2 Implication for our YouGov-driven model

Our YouGov pool currently contributes 68 `neither` rows out of 1483
(4.6 %). YouGov is recruited politically-engaged by panel design, so
those 68 are best characterised as "engaged respondents who happened
to give DK on three questions", **not** as the Hansard / Reuters /
CAST disengaged cluster described above. When we resample to hit a
35 % `neither` target (`Model_Design.md` §18.7), we are inflating that
same demographically-narrow subset. This is a known limitation of the
v0.5 design and is documented as a deferred research question in
`Model_Design.md` §18.14, not a v0.5 blocker.

---

## 7. How the model should use this evidence

See `Model_Design.md` §18 for the full implementation design.
Summarised here:

1. **Default condition: symmetric reach.** Equal audience size for
   `A-only` and `B-only`. This isolates the dynamics of two-sided
   committed-minority influence from the confounding effect of audience
   asymmetry. The §18.4 default is
   `{A-only: 0.225, B-only: 0.225, both: 0.20, neither: 0.35}`.

2. **UK-realistic condition: asymmetric reach.** Use the Section 6
   bands (with the `B-only` > `A-only` skew) as a configurable
   experimental condition to study how audience asymmetry interacts
   with the message-frequency asymmetry planned in Priority 3.

3. **Calibration rather than sample inheritance.** Re-sample the YouGov
   pool to hit target marginals from the population-level evidence
   above, rather than letting the YouGov sample composition silently
   determine the four-cell distribution. See `Model_Design.md` §18.5
   for the stratified-resampling algorithm and §18.8 for the
   replication-variance implications.

---

## 8. Open gaps to close in a full survey

The following are weak points in this draft that the comprehensive
literature survey should address:

- **Direct party-attributable exposure on climate, UK, post-2022.** No
  single survey appears to measure this cleanly. Closest proxies are
  the BES party-position recall items and Climate Outreach segment
  attributes.
- **Quantifying Reform vs Green airtime asymmetry.** Requires either an
  Ofcom Section 320 (due impartiality) tracking dataset or a custom
  content analysis. Cite Cardiff School of Journalism / Loughborough
  Centre for Research in Communication and Culture work if available.
- **Echo-chamber prevalence specifically on climate.** Most echo-chamber
  literature is about general politics. The climate-specific subset is
  thinner; CAST and Tyndall Centre publications are the natural place
  to look.
- **Cross-platform exposure overlap in 2024–2026.** Most cited
  echo-chamber studies are pre-2020; the platform landscape (TikTok
  rise, X changes, decline of Facebook news) has shifted.

---

*Initial draft compiled 2026-05-14 to support `Model_Design.md` §18
planning. Many figures are approximate and should be confirmed against
the primary sources before publication.*
