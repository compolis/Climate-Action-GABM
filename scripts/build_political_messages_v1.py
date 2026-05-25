"""
Build script for the v1 offline political message dataset.

Generates two CSVs under data/political_messages/:

  - sources_v1.csv     — 24 attributed source quotes (audit-grade provenance).
                         Normalized: one row per quote.

  - messages_v1.csv    — 242 broadcast messages:
                           * 240 single-policy messages (20 per side x policy cell):
                               - 12 verbatim_summary entries (2 per cell, taken
                                 directly from the research doc's
                                 "Broadcast-ready message" lines).
                               - Wait, only ONE verbatim per cell exists in the
                                 doc; counted again: 12 verbatim_summary entries
                                 (1 per cell x 12 cells) and 18 llm_generated
                                 per cell = 19 per cell ... but the plan calls
                                 for 20 per cell.
                                 We treat the single doc broadcast as
                                 verbatim_summary and add 19 llm_generated per
                                 cell so each cell has exactly 20 messages.
                           * 2 placeholder package-mode messages (one per side),
                             constructed by concatenating that side's 6
                             per-policy verbatim messages. Tagged
                             generation_method='placeholder_concat'. Bespoke
                             package messages will replace these in v2.

Provenance:
  - For verbatim_summary messages: provenance_refs lists the source_ids of the
    two quotes the broadcast message was synthesized from in the research doc.
  - For llm_generated messages: provenance_refs lists the same two source_ids
    of the cell. The 19 llm_generated messages per cell paraphrase / recombine
    the themes attested by those quotes plus the narrative analysis section of
    the research doc. No new factual claims are introduced.
  - Message texts never name the party or speaker; attribution lives only in
    sources_v1.csv. This preserves the de-identified prompt convention adopted
    in v0.5.1.

Re-running this script overwrites the CSVs. For v2, build a new script.

Decisions captured here are documented in /memories/session/plan.md.
"""

from __future__ import annotations

import csv
from pathlib import Path

DATASET_VERSION = "v1"
GENERATION_METHOD_LLM = "claude_in_session_2026-05-22"
GENERATION_METHOD_VERBATIM = "doc_broadcast_ready"
GENERATION_METHOD_PACKAGE_PLACEHOLDER = "placeholder_concat"

# Repo root inferred from this file's location: <repo>/scripts/this_file.py
REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data" / "political_messages"
SOURCES_CSV = OUT_DIR / "sources_v1.csv"
MESSAGES_CSV = OUT_DIR / "messages_v1.csv"

# ----------------------------------------------------------------------------
# Policy id mapping (mirrors cag.abm.attributes.opinion.ClimatePolicyID)
# ----------------------------------------------------------------------------
POLICY_RENEWABLES = 1          # RENEWABLE_ENERGY
POLICY_BAN_FOSSIL = 2          # BAN_FOSSIL_FUEL
POLICY_BAN_PETROL = 3          # BAN_PETROL_CARS
POLICY_GREEN_HOUSING = 4       # GREEN_HOUSING
POLICY_CARBON_TAX = 5          # CARBON_TAX
POLICY_COMPENSATION = 6        # CLIMATE_COMPENSATION

ALL_POLICIES = [
    POLICY_RENEWABLES,
    POLICY_BAN_FOSSIL,
    POLICY_BAN_PETROL,
    POLICY_GREEN_HOUSING,
    POLICY_CARBON_TAX,
    POLICY_COMPENSATION,
]

SIDE_A = "A"  # pro_climate  -> Green Party of England and Wales
SIDE_B = "B"  # anti_climate -> Reform UK

PARTY_NAME = {
    SIDE_A: "Green Party of England and Wales",
    SIDE_B: "Reform UK",
}

# ----------------------------------------------------------------------------
# SOURCES (24 quotes, 2 per cell)
# ----------------------------------------------------------------------------
# Schema:
#   source_id, policy_id, side, party_name, speaker, speaker_role,
#   date, venue, citation_url, quote_text, manifesto_or_hansard_ref, notes

SOURCES: list[dict] = [
    # --- B (Reform) on Renewables ------------------------------------------
    {
        "source_id": "B_01_01",
        "policy_id": POLICY_RENEWABLES, "side": SIDE_B,
        "speaker": "Nigel Farage", "speaker_role": "Leader",
        "date": "2024-06-17",
        "venue": "Reform UK Manifesto 'Our Contract with You'",
        "citation_url": "",
        "quote_text": (
            "We will scrap Net Zero to cut bills and restore growth. "
            "[...] Scrap Net Zero and Related Subsidies. "
            "[...] Scrap Annual GBP 10 Billion of Renewable Energy Subsidies."
        ),
        "manifesto_or_hansard_ref": "Reform UK: Our Contract with You",
        "notes": "Manifesto text; GBP substituted for ASCII safety.",
    },
    {
        "source_id": "B_01_02",
        "policy_id": POLICY_RENEWABLES, "side": SIDE_B,
        "speaker": "Richard Tice", "speaker_role": "Deputy Leader",
        "date": "2025-11-12",
        "venue": "Parliamentary Motion (Hansard) - Energy",
        "citation_url": "https://hansard.parliament.uk/commons/2025-11-12/debates/405C1215-88FD-4C29-B774-77155B86F954/Energy",
        "quote_text": (
            "That this House calls on the Government to introduce a plan for "
            "cheap power by cutting public expenditure to remove the 'Carbon "
            "Tax' (UK Emissions Trading Scheme) from electricity generation "
            "and end Renewable Obligation subsidies"
        ),
        "manifesto_or_hansard_ref": "Hansard 2025-11-12",
        "notes": "",
    },

    # --- A (Green) on Renewables -------------------------------------------
    {
        "source_id": "A_01_01",
        "policy_id": POLICY_RENEWABLES, "side": SIDE_A,
        "speaker": "Carla Denyer & Adrian Ramsay", "speaker_role": "Co-Leaders",
        "date": "2024-06-12",
        "venue": "Green Party Manifesto 'Real Hope. Real Change'",
        "citation_url": "https://www.local.gov.uk/about/campaigns/general-election-hub/green-party-manifesto",
        "quote_text": (
            "We estimate green investment will require an average investment "
            "of GBP 40 billion per year over the course of the parliament... "
            "Electricity generation, transmission and storage: GBP 50 billion"
        ),
        "manifesto_or_hansard_ref": "Green Party Manifesto 2024",
        "notes": "GBP substituted for ASCII safety.",
    },
    {
        "source_id": "A_01_02",
        "policy_id": POLICY_RENEWABLES, "side": SIDE_A,
        "speaker": "Carla Denyer & Adrian Ramsay", "speaker_role": "Co-Leaders",
        "date": "2024-06-12",
        "venue": "Green Party Manifesto 'Real Hope. Real Change'",
        "citation_url": "https://www.dsc.org.uk/wp-content/uploads/2024/06/Manifesto-Mashup-General-Election-2024-FINAL.pdf",
        "quote_text": (
            "Drive a rooftop solar revolution by expanding incentives for "
            "households to install solar panels, including a guaranteed fair "
            "price for electricity sold back into the grid."
        ),
        "manifesto_or_hansard_ref": "Green Party Manifesto 2024",
        "notes": "",
    },

    # --- B (Reform) on Ban Fossil Licenses ---------------------------------
    {
        "source_id": "B_02_01",
        "policy_id": POLICY_BAN_FOSSIL, "side": SIDE_B,
        "speaker": "Nigel Farage", "speaker_role": "Leader",
        "date": "2024-06-17",
        "venue": "Reform UK Manifesto 'Our Contract with You'",
        "citation_url": "",
        "quote_text": (
            "We will unlock Britain's vast energy treasure of oil and gas to "
            "slash energy bills, beat the cost-of-living crisis and unleash "
            "real economic growth."
        ),
        "manifesto_or_hansard_ref": "Reform UK: Our Contract with You",
        "notes": "",
    },
    {
        "source_id": "B_02_02",
        "policy_id": POLICY_BAN_FOSSIL, "side": SIDE_B,
        "speaker": "Reform UK Spokesperson", "speaker_role": "Spokesperson",
        "date": "2025-05-23",
        "venue": "The Guardian",
        "citation_url": "https://www.theguardian.com/business/2025/may/23/reform-uk-promise-to-reverse-ban-on-north-sea-oil-drilling-if-elected",
        "quote_text": (
            "As long as there's oil in the North Sea, we should be drilling "
            "for it. There are clear benefits for securing jobs and energy "
            "independence."
        ),
        "manifesto_or_hansard_ref": "The Guardian 2025-05-23",
        "notes": "",
    },

    # --- A (Green) on Ban Fossil Licenses ----------------------------------
    {
        "source_id": "A_02_01",
        "policy_id": POLICY_BAN_FOSSIL, "side": SIDE_A,
        "speaker": "Carla Denyer & Adrian Ramsay", "speaker_role": "Co-Leaders",
        "date": "2024-06-12",
        "venue": "Green Party Manifesto 'Real Hope. Real Change'",
        "citation_url": "https://www.coalaction.org.uk/2024/06/17/uk-election-2024-parties-line-up-to-ban-more-coal-mining/",
        "quote_text": (
            "Cancel recent fossil fuel licences such as for Rosebank and stop "
            "all new fossil fuel extraction projects in the UK."
        ),
        "manifesto_or_hansard_ref": "Green Party Manifesto 2024",
        "notes": "",
    },
    {
        "source_id": "A_02_02",
        "policy_id": POLICY_BAN_FOSSIL, "side": SIDE_A,
        "speaker": "Carla Denyer", "speaker_role": "Co-Leader",
        "date": "2025-07-15",
        "venue": "Parliamentary Speech (Hansard)",
        "citation_url": "https://www.parallelparliament.co.uk/debate/2025-07-15/commons",
        "quote_text": (
            "We are already battling deadly heatwaves and overshooting climate "
            "limits, so it is critical that we stop extracting new oil and gas."
        ),
        "manifesto_or_hansard_ref": "Hansard 2025-07-15",
        "notes": "",
    },

    # --- B (Reform) on Ban Petrol Cars -------------------------------------
    {
        "source_id": "B_03_01",
        "policy_id": POLICY_BAN_PETROL, "side": SIDE_B,
        "speaker": "Nigel Farage", "speaker_role": "Leader",
        "date": "2024-06-17",
        "venue": "Reform UK Manifesto 'Our Contract with You'",
        "citation_url": "",
        "quote_text": (
            "Net Zero has sent energy costs soaring. It is making us poorer "
            "and colder, damaging British industry and forcing drivers off "
            "the road."
        ),
        "manifesto_or_hansard_ref": "Reform UK: Our Contract with You",
        "notes": "",
    },
    {
        "source_id": "B_03_02",
        "policy_id": POLICY_BAN_PETROL, "side": SIDE_B,
        "speaker": "Richard Tice", "speaker_role": "Deputy Leader",
        "date": "2025-12-07",
        "venue": "Official X/Twitter Account",
        "citation_url": "https://voteclimate.uk/mps/richard-tice/tweets",
        "quote_text": (
            "Reform will totally scrap this disastrous, destructive Net Zero "
            "EV policy."
        ),
        "manifesto_or_hansard_ref": "X/Twitter post 2025-12-07",
        "notes": "",
    },

    # --- A (Green) on Ban Petrol Cars --------------------------------------
    {
        "source_id": "A_03_01",
        "policy_id": POLICY_BAN_PETROL, "side": SIDE_A,
        "speaker": "Carla Denyer & Adrian Ramsay", "speaker_role": "Co-Leaders",
        "date": "2024-06-12",
        "venue": "Green Party Manifesto 'Real Hope. Real Change'",
        "citation_url": "https://www.local.gov.uk/about/campaigns/general-election-hub/green-party-manifesto",
        "quote_text": (
            "An end to sales of new petrol and diesel fuelled vehicles by "
            "2027 and to the use of petrol and diesel vehicles on the road "
            "by 2035."
        ),
        "manifesto_or_hansard_ref": "Green Party Manifesto 2024",
        "notes": "",
    },
    {
        "source_id": "A_03_02",
        "policy_id": POLICY_BAN_PETROL, "side": SIDE_A,
        "speaker": "Carla Denyer & Adrian Ramsay", "speaker_role": "Co-Leaders",
        "date": "2024-06-12",
        "venue": "Green Party Manifesto 'Real Hope. Real Change'",
        "citation_url": "https://www.local.gov.uk/about/campaigns/general-election-hub/green-party-manifesto",
        "quote_text": (
            "Within a decade we want to see all petrol and diesel vehicles "
            "replaced by Electric Vehicles (EVs). We would push for an "
            "extensive vehicle scrappage scheme to support this rapid "
            "transition"
        ),
        "manifesto_or_hansard_ref": "Green Party Manifesto 2024",
        "notes": "",
    },

    # --- B (Reform) on Green Housing ---------------------------------------
    {
        "source_id": "B_04_01",
        "policy_id": POLICY_GREEN_HOUSING, "side": SIDE_B,
        "speaker": "Lee Anderson", "speaker_role": "Reform MP",
        "date": "2025-01-13",
        "venue": "Parliamentary Speech (Hansard)",
        "citation_url": "https://hansard.parliament.uk/commons/2025-01-13/debates/6a437f7f-d596-4ea6-b3e3-d42e8df22d01/DraftCleanHeatMarketMechanismRegulations2024",
        "quote_text": (
            "The cost of installing a heat pump is about three times that of "
            "installing a new gas boiler. That is before considering the "
            "extra hidden costs... such as more insulation."
        ),
        "manifesto_or_hansard_ref": "Hansard 2025-01-13 - Draft Clean Heat Market Mechanism Regulations 2024",
        "notes": "",
    },
    {
        "source_id": "B_04_02",
        "policy_id": POLICY_GREEN_HOUSING, "side": SIDE_B,
        "speaker": "Nigel Farage", "speaker_role": "Leader",
        "date": "2024-06-17",
        "venue": "Reform UK Manifesto 'Our Contract with You'",
        "citation_url": "",
        "quote_text": (
            "The economy isn't growing. It is being wrecked by record taxes, "
            "wasteful government spending and nanny state regulations. "
            "[...] Britain has a housing crisis."
        ),
        "manifesto_or_hansard_ref": "Reform UK: Our Contract with You",
        "notes": "",
    },

    # --- A (Green) on Green Housing ----------------------------------------
    {
        "source_id": "A_04_01",
        "policy_id": POLICY_GREEN_HOUSING, "side": SIDE_A,
        "speaker": "Carla Denyer & Adrian Ramsay", "speaker_role": "Co-Leaders",
        "date": "2024-06-12",
        "venue": "Green Party Manifesto 'Real Hope. Real Change'",
        "citation_url": "https://www.dsc.org.uk/wp-content/uploads/2024/06/Manifesto-Mashup-General-Election-2024-FINAL.pdf",
        "quote_text": (
            "Make homes warmer and cheaper to heat with a ten-year emergency "
            "upgrade programme, starting with free insulation and heat pumps "
            "for those on low incomes, and ensure that all new homes are "
            "zero-carbon."
        ),
        "manifesto_or_hansard_ref": "Green Party Manifesto 2024",
        "notes": "",
    },
    {
        "source_id": "A_04_02",
        "policy_id": POLICY_GREEN_HOUSING, "side": SIDE_A,
        "speaker": "Carla Denyer & Adrian Ramsay", "speaker_role": "Co-Leaders",
        "date": "2024-06-12",
        "venue": "Green Party Manifesto 'Real Hope. Real Change'",
        "citation_url": "https://www.ciob.org/industry/politics-government/campaigns/UK-General-Election/what-UK-election-manifestos-mean-built-environment",
        "quote_text": (
            "Campaigning to change building regulations so that all new homes "
            "meet Passivhaus or equivalent standards."
        ),
        "manifesto_or_hansard_ref": "Green Party Manifesto 2024",
        "notes": "",
    },

    # --- B (Reform) on Carbon Tax ------------------------------------------
    {
        "source_id": "B_05_01",
        "policy_id": POLICY_CARBON_TAX, "side": SIDE_B,
        "speaker": "Richard Tice", "speaker_role": "Deputy Leader",
        "date": "2025-12-11",
        "venue": "Parliamentary Speech (Hansard) - Oil Refining Sector",
        "citation_url": "https://hansard.parliament.uk/Commons/2025-12-11/debates/7496C0EF-CD26-4B20-985A-8B8CDA12EEFF/OilRefiningSector",
        "quote_text": (
            "The soaring carbon tax is crippling the refining sector. Will "
            "the Minister explain how refineries are supposed to survive when "
            "the Government are planning to increase the carbon tax between "
            "now and 2050?"
        ),
        "manifesto_or_hansard_ref": "Hansard 2025-12-11",
        "notes": "",
    },
    {
        "source_id": "B_05_02",
        "policy_id": POLICY_CARBON_TAX, "side": SIDE_B,
        "speaker": "Richard Tice", "speaker_role": "Deputy Leader",
        "date": "2025-11-12",
        "venue": "Parliamentary Speech (Hansard) - Energy",
        "citation_url": "https://hansard.parliament.uk/commons/2025-11-12/debates/405C1215-88FD-4C29-B774-77155B86F954/Energy",
        "quote_text": (
            "Our cheap power plan would cut electricity bills for everyone by "
            "20%, and under it, we take a common-sense approach to British "
            "energy."
        ),
        "manifesto_or_hansard_ref": "Hansard 2025-11-12",
        "notes": "",
    },

    # --- A (Green) on Carbon Tax -------------------------------------------
    {
        "source_id": "A_05_01",
        "policy_id": POLICY_CARBON_TAX, "side": SIDE_A,
        "speaker": "Carla Denyer & Adrian Ramsay", "speaker_role": "Co-Leaders",
        "date": "2024-06-12",
        "venue": "Green Party Manifesto 'Real Hope. Real Change'",
        "citation_url": "https://www.tax.org.uk/election-2024-greens-manifesto",
        "quote_text": (
            "Introduce a carbon tax on all fossil fuel imports and domestic "
            "extraction, based on greenhouse gas emissions produced when fuel "
            "is burned... set initially at GBP 120 per tonne of carbon emitted."
        ),
        "manifesto_or_hansard_ref": "Green Party Manifesto 2024",
        "notes": "GBP substituted for ASCII safety.",
    },
    {
        "source_id": "A_05_02",
        "policy_id": POLICY_CARBON_TAX, "side": SIDE_A,
        "speaker": "Carla Denyer & Adrian Ramsay", "speaker_role": "Co-Leaders",
        "date": "2024-06-12",
        "venue": "Green Party Manifesto 'Real Hope. Real Change'",
        "citation_url": "https://www.local.gov.uk/about/campaigns/general-election-hub/green-party-manifesto",
        "quote_text": (
            "A carbon tax to make polluters pay and provide money to invest "
            "in the green transition."
        ),
        "manifesto_or_hansard_ref": "Green Party Manifesto 2024",
        "notes": (
            "Stance is Mixed/Conditional vs the survey's dividend framing: "
            "Green Party supports the tax but redirects revenue to green "
            "investment and public services rather than a per-person dividend."
        ),
    },

    # --- B (Reform) on Compensation ----------------------------------------
    {
        "source_id": "B_06_01",
        "policy_id": POLICY_COMPENSATION, "side": SIDE_B,
        "speaker": "Richard Tice", "speaker_role": "Deputy Leader",
        "date": "2026-01-08",
        "venue": "Interview with Politico",
        "citation_url": "https://subscriber.politicopro.com/article/eenews/2026/01/08/farage-deputy-says-uk-should-follow-trump-and-quit-un-climate-bodies-00716058",
        "quote_text": (
            "[UN climate bodies] are deeply flawed, unaccountable and "
            "expensive institutions."
        ),
        "manifesto_or_hansard_ref": "Politico interview 2026-01-08",
        "notes": "Bracket inserted to make grammatical sense without the elided subject.",
    },
    {
        "source_id": "B_06_02",
        "policy_id": POLICY_COMPENSATION, "side": SIDE_B,
        "speaker": "Nigel Farage", "speaker_role": "Leader",
        "date": "2024-06-17",
        "venue": "Reform UK Manifesto 'Our Contract with You'",
        "citation_url": "",
        "quote_text": (
            "We are ruled by an out-of-touch political class who have turned "
            "their backs on our country... Cut foreign aid by 50%."
        ),
        "manifesto_or_hansard_ref": "Reform UK: Our Contract with You",
        "notes": "",
    },

    # --- A (Green) on Compensation -----------------------------------------
    {
        "source_id": "A_06_01",
        "policy_id": POLICY_COMPENSATION, "side": SIDE_A,
        "speaker": "Carla Denyer", "speaker_role": "Co-Leader",
        "date": "2024-09-10",
        "venue": "Parliamentary Speech (Hansard)",
        "citation_url": "https://hansard.parliament.uk/pdf/commons/2024-09-10",
        "quote_text": (
            "We need to come to an honest agreement on how much we can commit "
            "financially to repairing the damage done to many developing "
            "nations. I am confident that... this Government will stick to "
            "the agreement."
        ),
        "manifesto_or_hansard_ref": "Hansard 2024-09-10",
        "notes": "",
    },
    {
        "source_id": "A_06_02",
        "policy_id": POLICY_COMPENSATION, "side": SIDE_A,
        "speaker": "Carla Denyer", "speaker_role": "Co-Leader",
        "date": "2024-10-30",
        "venue": "Parliamentary Speech (Hansard)",
        "citation_url": "https://hansard.parliament.uk/pdf/commons/2024-10-30",
        "quote_text": (
            "We need to ensure that we are not storing up further problems "
            "for the future by providing climate finance in the form of "
            "loans, which make things harder for the poorest people in the "
            "poorest countries."
        ),
        "manifesto_or_hansard_ref": "Hansard 2024-10-30",
        "notes": "",
    },
]


# ----------------------------------------------------------------------------
# VERBATIM broadcast-ready messages (1 per cell, 12 total).
# Taken verbatim from the "Broadcast-ready message" lines in the research doc.
# Light ASCII normalisation (curly quotes -> straight) for CSV stability.
# ----------------------------------------------------------------------------
VERBATIM: dict[tuple[str, int], str] = {
    (SIDE_B, POLICY_RENEWABLES): (
        "Net Zero is making us poorer and colder. We must scrap all renewable "
        "energy subsidies that push up our electricity bills to pay for "
        "intermittent power. We need a common-sense plan for cheap power, not "
        "a political consensus that shelters the renewables industry and "
        "forces working people to endure the multi-billion-pound costs of "
        "Net Zero."
    ),
    (SIDE_A, POLICY_RENEWABLES): (
        "We must accelerate clean energy investment and delivery. By "
        "investing GBP 40 billion annually, we can drive a rooftop solar "
        "revolution and ensure wind power provides the vast majority of our "
        "electricity by 2030. This unprecedented investment will end our "
        "reliance on volatile fossil fuel markets, bringing down energy bills "
        "and securing our future."
    ),
    (SIDE_B, POLICY_BAN_FOSSIL): (
        "As long as there's oil in the North Sea, we should be drilling for "
        "it. Banning new oil and gas licences is a disastrous policy that "
        "destroys skilled jobs and prioritises expensive foreign imports over "
        "UK production. We must unlock Britain's vast energy treasure to "
        "secure our independence, slash energy bills, and unleash real "
        "economic growth."
    ),
    (SIDE_A, POLICY_BAN_FOSSIL): (
        "We are already battling deadly heatwaves and overshooting climate "
        "limits, so it is critical that we stop extracting new oil and gas "
        "immediately. We must cancel recent licences like Rosebank and ban "
        "all new fossil fuel extraction projects in the UK. We cannot drill "
        "our way out of a climate emergency while fossil fuel companies "
        "extract record profits."
    ),
    (SIDE_B, POLICY_BAN_PETROL): (
        "We will totally scrap the disastrous and destructive mandate forcing "
        "manufacturers to produce electric vehicles. The ban on new petrol "
        "and diesel cars is a Net Zero vanity project that is damaging "
        "British industry and forcing working drivers off the road. We must "
        "protect consumer choice and end these crippling nanny-state "
        "regulations."
    ),
    (SIDE_A, POLICY_BAN_PETROL): (
        "We want to see all petrol and diesel vehicles replaced by electric "
        "vehicles within a decade. We will push for an end to sales of new "
        "petrol and diesel vehicles by 2027, supported by a GBP 5 billion "
        "annual vehicle scrappage scheme to help ordinary people make the "
        "transition quickly and fairly, vastly improving the air quality in "
        "our communities."
    ),
    (SIDE_B, POLICY_GREEN_HOUSING): (
        "Mandating heat pumps and expensive insulation is a nanny-state "
        "regulation making us poorer and worsening the housing crisis. The "
        "cost of installing a heat pump is three times that of a new gas "
        "boiler, even before the hidden costs of tearing up your home for "
        "insulation. We must scrap these net zero targets that wreck the "
        "economy and punish ordinary homeowners."
    ),
    (SIDE_A, POLICY_GREEN_HOUSING): (
        "We must ensure that all new homes are built to zero-carbon "
        "Passivhaus standards, with house builders required to include solar "
        "panels and heat pumps. Alongside this, our emergency upgrade "
        "programme will provide free insulation and heat pumps for low-income "
        "households, eradicating fuel poverty and making homes permanently "
        "warmer and cheaper to run."
    ),
    (SIDE_B, POLICY_CARBON_TAX): (
        "The soaring carbon tax is crippling British industry and making "
        "households poorer by driving up wholesale electricity prices. We "
        "will remove the carbon tax entirely to cut your bills instantly by "
        "20%. We need a common-sense approach to cheap energy, not punitive "
        "taxes that destroy our jobs to meet impossible Net Zero targets."
    ),
    (SIDE_A, POLICY_CARBON_TAX): (
        "We must introduce a carbon tax on all fossil fuel extraction and "
        "imports, starting at GBP 120 per tonne, to make the biggest "
        "polluters pay for the damage they cause. Rather than handing out "
        "dividends, we will use these vital revenues to invest heavily in "
        "the green transition and rescue our crumbling public services."
    ),
    (SIDE_B, POLICY_COMPENSATION): (
        "U.N. climate bodies are deeply flawed, unaccountable, and expensive "
        "institutions that are failing British voters. We are ruled by an "
        "out-of-touch political class giving away our money. Instead of "
        "sending billions abroad in climate compensation, we must cut foreign "
        "aid by 50% and use that money to fix our own broken country."
    ),
    (SIDE_A, POLICY_COMPENSATION): (
        "We must come to an honest agreement to commit financially to "
        "repairing the devastating damage done to developing nations. It is "
        "vital we provide international climate finance as direct grants, "
        "not loans, so we do not store up toxic debt for the poorest "
        "countries facing the catastrophic impacts of climate breakdown."
    ),
}


# ----------------------------------------------------------------------------
# LLM-GENERATED messages (19 per cell, 228 total).
# Authored by Claude (Anthropic, Opus 4.7) in-session on 2026-05-22.
# Constraints applied:
#   - ~50-90 words per message
#   - Party voice preserved; no party / leader / personal names
#   - No new factual claims beyond the research doc
#   - Varied framing within each cell
# Provenance refs for every message = both cell source_ids.
# ----------------------------------------------------------------------------
LLM_MESSAGES: dict[tuple[str, int], list[str]] = {
    (SIDE_B, POLICY_RENEWABLES): [
        "Working households are being crushed by sky-high electricity bills, and a huge part of that bill is the Renewable Obligation and other green levies. Scrapping these subsidies would put money straight back into people's pockets. We need cheap power, not policies that protect a heavily subsidised industry at the public's expense.",
        "Wind and solar cannot keep the lights on alone. They require expensive backup gas and constant grid upgrades, all paid for by ordinary bill-payers. The honest answer is to cut public expenditure on these subsidies and pursue a cheap power plan that delivers reliability instead of intermittency.",
        "Net Zero subsidies have become a multi-billion-pound transfer from struggling families to a sheltered renewables industry. Every year another ten billion pounds of public money props up wind and solar projects that still leave the country dependent on imported gas. It is time to scrap the lot and restore growth.",
        "The current Renewable Obligation regime forces every household to subsidise generators they did not choose. Removing these obligations would cut electricity bills and end the rigged market that punishes ordinary consumers. A common-sense plan for cheap power means stopping these payments now.",
        "Decisions made by a distant political class have left British families colder and poorer this winter. Renewable subsidies have not delivered the cheap, abundant energy that was promised, only higher bills and weaker industry. We must scrap Net Zero targets and the subsidies that follow from them.",
        "If we lifted the carbon tax from electricity generation and ended the Renewable Obligation, bills would fall dramatically and industry would have a fighting chance. Instead, the consensus continues to pour billions into intermittent renewables while shutting down reliable plants. That is not energy policy, it is ideology.",
        "Cheap power should be the goal of every energy policy, not a side effect to be hoped for. By cutting public expenditure on Net Zero subsidies and the carbon tax on generation, electricity bills can fall by around twenty percent for everyone. That is what a serious plan looks like.",
        "Britain's renewables industry has been turned into a permanent welfare client, taking in around ten billion pounds of subsidies every year while bills keep rising. Ending those payments would not switch off the lights; it would simply force the sector to stand on its own and stop draining household budgets.",
        "Net Zero is making us poorer and colder, and the renewables subsidy machine is at the heart of that failure. Working people see their bills rise to fund projects that cannot guarantee the power they promise. A common-sense plan must remove these subsidies and protect families from further damage.",
        "Pretending wind and solar are cheap while ignoring the cost of backup generation, transmission upgrades and standing subsidies is dishonest. The full system bill keeps rising, and households pay it. We must end the political consensus that hides these costs and instead deliver a plan for genuinely cheap power.",
        "Every pound spent subsidising wind farms is a pound taken from a family that is struggling to pay their heating bill. The Renewable Obligation and related schemes have to go, and any new spending on green infrastructure must end. Working people deserve cheaper energy, not more handouts to a protected industry.",
        "Industry is being driven offshore by some of the highest electricity prices in the developed world. Carbon levies on generation and never-ending renewable subsidies are direct contributors. Removing both would help reopen factories, defend skilled jobs and put downward pressure on prices for every household.",
        "The political consensus around Net Zero has been a one-way ratchet for higher bills. There has been no honest reckoning with how much intermittent power actually costs once subsidies and backup are added in. It is time to scrap the consensus, scrap the subsidies and put cheap power first.",
        "Pensioners are choosing between heating and eating while billions go to subsidise renewables and prop up the carbon tax. That cannot be a moral policy. Cutting these costs out of the electricity bill is the fastest, fairest way to give families immediate relief this winter and every winter that follows.",
        "Government has no business picking which technologies win or lose. Yet through subsidies, obligations and carbon levies it has rigged the entire electricity market in favour of renewables. Ending those distortions would deliver lower bills, more reliable power and a much healthier economy.",
        "The promise was that renewables would bring bills down. The reality is the opposite, because the subsidies and grid costs are passed straight to consumers. Honesty demands we admit the policy has failed and dismantle the subsidy machine before more families are pushed into fuel poverty.",
        "A common-sense plan for cheap power has three steps: remove the carbon tax from generation, end the Renewable Obligation and stop signing new subsidy contracts. Together these would slash electricity bills, restore competitiveness and break the grip of a Net Zero ideology that has made the country poorer.",
        "Net Zero ideology is making families poorer and colder. We must end the ten billion pounds handed every year in subsidies to the renewables industry, which drives up electricity bills to pay for intermittent power. Cheap, reliable energy is the foundation of growth, and any serious plan must put that first.",
        "The simplest test of an energy policy is whether it delivers cheap, reliable power. By that test, decades of renewable subsidies have failed. Scrapping them and removing the carbon tax from electricity generation would deliver lower bills immediately and put the country back on a competitive footing.",
    ],

    (SIDE_A, POLICY_RENEWABLES): [
        "A rooftop solar revolution is within reach if we expand household incentives and guarantee a fair price for electricity sold back into the grid. Every roof that generates power is one less family exposed to gas price spikes. This is how we turn the cost of living crisis into an opportunity to rebuild.",
        "Around fifty billion pounds over a parliament should be directed straight into electricity generation, transmission and storage. That investment would put wind and solar at the heart of a modern grid, create skilled jobs across every region and finally unlock the cheap power that British households have been waiting for.",
        "Volatile gas markets sent energy bills soaring, and they will do so again. The only durable answer is to invest at scale in domestic renewables so that the wholesale price of electricity is set by wind and sun, not by distant conflicts and corporate margins.",
        "Wind power can and should provide the vast majority of our electricity by 2030, alongside expanded solar and proper storage. Reaching that point requires honest public investment now, not more delay. The cheapest unit of electricity is one that does not depend on a fuel that has to be bought.",
        "Decent green jobs in manufacturing, installation and grid services would follow rapidly from a forty billion pound annual investment commitment. Communities that lost industry decades ago could be at the centre of building, maintaining and operating the new energy system. That is the economic case for the renewables roll-out.",
        "Households that install solar should be paid a fair price for the power they put back into the grid. Today the rates are derisory and the rules are confusing. A guaranteed price and simpler incentives would unleash a wave of installation and reduce bills across the country.",
        "Storage is the missing piece of the renewables story, and it must be funded as core public infrastructure rather than left to chance. With proper battery capacity and grid upgrades, intermittent generation becomes reliable supply, and the case against rapid expansion collapses.",
        "Energy security and climate action are the same project. Every wind turbine and solar panel built at home is one less unit of imported gas, one less exposure to price shocks, and one more block of permanent low-cost power for households and industry.",
        "The cost of building wind and solar has collapsed over the last decade. What is missing is the political will to invest at the scale the science demands. A serious public investment plan would unlock private capital alongside it and accelerate the transition in a way the market alone never will.",
        "Fuel poverty is a policy choice. By investing tens of billions a year in clean power and insulation, we can break the link between household bills and global gas prices, and ensure that no family has to choose between heating their home and putting food on the table.",
        "Public investment in renewable generation and storage repays itself many times over in lower bills, cleaner air and a more stable economy. Continuing to depend on fossil fuels means continuing to gamble with household finances. The transition has to be funded boldly and built quickly.",
        "Every new solar roof, onshore wind project and offshore array is a small piece of insurance against the next price shock. Building enough of them takes a long-term plan and consistent funding. Half measures have failed; the answer is to commit and deliver.",
        "Communities should share directly in the benefits of nearby renewable projects through lower bills, community ownership and local investment. That is what makes the transition fair as well as fast, and it is the only way to ensure broad public support over the long haul.",
        "Coordinated public investment in transmission, distribution and storage is essential if renewable generation is to reach every household at low cost. Without grid upgrades, even the best wind and solar projects cannot deliver. Funding the grid is funding lower bills.",
        "Apprenticeships and training in installation, retrofit, grid engineering and offshore wind must scale with the build-out. A serious green investment plan funds the workforce as well as the kit, ensuring decent jobs follow every project rather than being treated as an afterthought.",
        "Slow delivery costs more than rapid delivery. Every year of delay means more years of fossil-fuel bills, more lost industrial opportunity and more damage to the climate. The plan must be to invest now, build now and benefit now.",
        "A rapid renewables roll-out lowers bills, ends our dependence on imported fuel, creates secure jobs and cuts emissions. Refusing to fund it at scale serves no one except the fossil fuel interests profiting from delay. The case for forty billion pounds a year is overwhelming.",
        "We need a forty billion pound annual green investment programme to scale up wind, solar and storage at the pace this country requires. Public investment on this scale will end our exposure to volatile fossil fuel markets, bring down household energy bills permanently and give us real energy security based on what we build at home.",
        "Cheap, clean electricity is the foundation of a modern industrial strategy. Investing at scale in domestic renewables means lower bills, more secure jobs and a stronger economy. The country that builds the energy system of the future will benefit for generations.",
    ],

    (SIDE_B, POLICY_BAN_FOSSIL): [
        "Refusing to issue new oil and gas licences does not lower global emissions; it only moves the production overseas. The result is higher imports, more shipping pollution and lost British jobs. Common sense says we should produce what we use, at home, for our own benefit.",
        "Energy independence is national security. Letting our domestic production decline while we import the same fuels from abroad makes the country weaker. New North Sea licences would mean more tax revenue, more jobs and more leverage in a dangerous world.",
        "The cost-of-living crisis was made worse by exposure to international gas markets. Producing more at home would reduce that exposure and keep more of the supply chain inside the UK. Cancelling licences is economic self-harm dressed up as virtue.",
        "Skilled North Sea workers and supply-chain firms in coastal communities are being told their work is no longer wanted. That is a betrayal. Issuing new licences would protect tens of thousands of well-paid jobs and the towns that depend on them.",
        "Every barrel we do not produce here is a barrel we buy from somewhere else, usually at higher cost and with worse environmental standards. Refusing new licences is a moral and economic mistake that punishes British workers to make foreign producers richer.",
        "We have a vast energy resource sitting beneath our own waters. Choosing not to develop it while begging other countries for supply is absurd. New licences would generate billions in tax revenue that could be used to cut bills and fund public services.",
        "Banning new oil and gas licences while still consuming oil and gas is the worst of both worlds: high bills, lost jobs, lost tax revenue, and no reduction in actual emissions. Honest energy policy means producing what we use until alternatives are genuinely ready.",
        "The North Sea industry built much of modern Britain's energy security and tax base. Strangling it through licence bans without a credible replacement is reckless. We must keep issuing licences to maintain investment, jobs and supply through the long transition ahead.",
        "Anti-drilling policies do not change demand, they only change the supplier. The losers are British workers and British taxpayers. The winners are overseas producers and shipping companies. Common sense and economic patriotism both demand that we reverse course.",
        "Investment decisions in the North Sea depend on confidence that new licences will be granted. Removing that confidence destroys long-term planning, drives investors out and accelerates decline. Restoring licences is the only way to keep the basin viable through this decade.",
        "Working families face higher bills every time imported gas prices spike. Producing more at home is one of the few measures that genuinely insulates British households from international turmoil. New licences are part of that protection.",
        "The argument that domestic production does not lower bills misses the wider picture: it lowers tax burdens, sustains jobs and reduces import dependence, all of which support household incomes. Cancelling licences delivers the opposite on every count.",
        "Communities in Aberdeen, Teesside and elsewhere have spent decades building world-class expertise in offshore energy. That expertise should be expanded and rewarded, not shut down by a licence ban driven by a London-centric political consensus.",
        "A serious industrial policy would use North Sea revenues to fund domestic investment, training and infrastructure. Choking off the source of that revenue makes everything harder. New licences and a long view are needed, not symbolic bans.",
        "The transition to lower emissions will take decades. During that time, choosing to import oil and gas rather than produce them domestically is a deliberate choice to hurt British workers and enrich foreign rivals. We should not make that choice.",
        "Energy independence is a strategic asset that should not be given away. Once licences are denied and infrastructure is dismantled, it cannot be rebuilt quickly. Defending domestic production is defending the country's long-term resilience.",
        "We should be drilling for the oil and gas under the North Sea, securing the jobs that come with it, slashing import bills and unleashing real economic growth. A licence ban achieves none of these goals and weakens the country in every measurable way.",
        "As long as there is oil and gas under the North Sea, we should be producing it. Banning new licences hands the market to foreign producers, drives up household bills and destroys skilled jobs in Aberdeen and beyond. The patriotic and economic case is to unlock our own resources.",
        "Tax revenue from North Sea production has historically funded essential public services and infrastructure. Cancelling new licences removes that revenue stream at a time when budgets are already strained. The honest course is to keep producing and reinvest the proceeds at home.",
    ],

    (SIDE_A, POLICY_BAN_FOSSIL): [
        "Every new field locked in today commits decades of future emissions. The science is unambiguous: we cannot afford to extract any more oil, gas or coal than is already in production. A full ban on new licences is the minimum responsible step.",
        "There is no national interest in handing further licences to fossil fuel companies that are already extracting record profits. Cancelling Rosebank and similar projects would signal that the climate emergency is being taken seriously and that the era of new extraction is over.",
        "North Sea oil is sold on international markets at international prices. New licences do not lower household bills; they line the pockets of producers while locking in emissions for decades. Stopping new extraction is honest climate policy and honest energy policy.",
        "A just transition for workers in the offshore industry requires planning, funding and lead time. None of that is helped by issuing more licences. It is helped by a clear cut-off and a serious investment programme in renewables, insulation and grid jobs in the same communities.",
        "We cannot drill our way out of a climate emergency. Banning new licences is the threshold question that separates serious climate policy from greenwash. Until that line is drawn, every other target lacks credibility.",
        "The argument that more domestic extraction means lower bills has been disproven by years of evidence. What it really means is more emissions, more profits for oil majors and more dependence on a fuel that has to be phased out. The licences must stop.",
        "Cancelling recent fossil fuel licences would put the country back in line with the temperature limits its own government has signed up to. Continuing to issue them puts those commitments out of reach and undermines international climate diplomacy.",
        "Public money should never again subsidise the expansion of fossil fuel extraction, whether through tax breaks, loan guarantees or favourable licences. A clear ban removes the ambiguity and forces capital toward the energy system we actually need.",
        "Fossil fuel companies are extracting record profits while the rest of the country struggles with the cost of climate impacts. Allowing them to open new fields makes that injustice worse. Stopping new licences is the most basic act of fairness in energy policy.",
        "Every new licence sends a signal to investors, workers and the world that this country is not serious about its climate obligations. Withdrawing that signal and committing to no new extraction is essential for credibility at home and abroad.",
        "Workers in the offshore sector deserve a real plan for transition, not endless extension of an industry with no future. Banning new licences and funding decent green jobs in the same coastal communities is how a just transition is actually delivered.",
        "The climate emergency is not a future risk; it is here in the form of heatwaves, floods and crop failures. Authorising new oil and gas extraction in the middle of that emergency is incoherent. The licences must stop now.",
        "Continued exploration locks in infrastructure, jobs and political pressure for decades of future production. Once built, these projects are hard to retire. The only way out of that trap is to refuse new licences in the first place.",
        "Other governments are already moving to halt new exploration. The UK should be a leader, not a laggard. A clear ban on new oil, gas and coal licences would put the country in the camp of those treating the crisis seriously.",
        "Reducing demand for fossil fuels through insulation, renewables and electrification is the heart of climate policy, but it cannot succeed if supply keeps expanding. Capping new licences is the supply-side complement that completes credible action.",
        "The case for new licences usually rests on dubious claims about bills or jobs that do not survive examination. The honest case for ending them rests on physics, on public health and on basic intergenerational fairness. The choice is straightforward.",
        "Cancel recent fossil fuel licences such as Rosebank, refuse all new ones and put public investment behind the alternative system that is now urgently needed. That is what a responsible climate policy looks like in the second half of the twenty-twenties.",
        "We are already living with deadly heatwaves and breaching climate limits. New oil and gas licences in this decade are indefensible. Recent grants such as Rosebank must be cancelled and no further extraction projects approved if there is to be any chance of keeping warming within survivable bounds.",
        "Communities most exposed to climate impacts are also those least responsible for emissions. Continuing to license new extraction makes their situation worse for the benefit of a small number of shareholders. A licence ban is a question of basic justice.",
    ],

    (SIDE_B, POLICY_BAN_PETROL): [
        "Electric vehicles are still out of reach for most working households, and the charging infrastructure is patchy at best. Forcing a ban on new petrol and diesel cars by 2030 punishes the people who depend on affordable motoring most. The deadline must be dropped.",
        "British car manufacturing is being squeezed between green mandates and global competition. Scrapping the EV quota and the petrol-car ban would give the industry breathing space to compete, save thousands of skilled jobs and protect a vital pillar of the economy.",
        "Banning new petrol and diesel cars does not reduce emissions in the way the policy claims; it just shifts costs onto households and forces them into more expensive vehicles. A Net Zero vanity project should not override the everyday transport needs of working families.",
        "Drivers in rural areas, on shift work, or with limited budgets have no realistic alternative to a petrol or diesel car. The 2030 ban is a policy designed by people who never have to think about these realities. It must be reversed in defence of ordinary motorists.",
        "Manufacturers are being forced to discount EVs and produce vehicles at a loss to meet arbitrary quotas. That cannot continue without damaging the entire automotive supply chain. Scrapping the mandate would restore market sense and protect British jobs.",
        "Petrol and diesel cars will remain part of the fleet for many years regardless of any ban. Pretending otherwise just adds confusion, drives up costs and pushes work overseas. A sensible policy would let manufacturers and consumers decide the pace of change.",
        "Charging infrastructure outside major cities remains unreliable and unequal. Forcing households into EVs before that gap is closed is a recipe for resentment and stranded drivers. The 2030 deadline should be replaced with realistic targets that match the infrastructure.",
        "The cost of a new EV remains far above that of a comparable petrol car for most segments of the market. Pretending otherwise does not change the family budget. Removing the ban would give households genuine choice rather than a forced and expensive upgrade.",
        "Nanny-state regulation of personal transport ends with people priced off the road. That is what the petrol-car ban delivers. The policy treats drivers as a problem to be managed rather than citizens to be served, and it has to go.",
        "Net Zero has sent energy and transport costs soaring while delivering no measurable benefit to ordinary households. The ban on new petrol cars is the most visible symbol of that failure. Scrapping it would be a clear signal that government has heard the public.",
        "Used-car prices have been distorted by the ban, hitting families that rely on second-hand vehicles hardest. The policy hurts most those least able to afford a new EV. Reversing the ban would restore a healthier and more affordable used market.",
        "British carmakers risk being undercut by subsidised foreign EVs that meet the same mandates more cheaply. Without scrapping the quota system, domestic production cannot survive. Defending jobs requires honesty about what the policy is doing.",
        "Drivers should be free to choose the vehicle that suits their family, their wallet and their working day. The 2030 ban removes that choice in favour of an option that many simply cannot afford. The policy is wrong in principle and damaging in practice.",
        "The transition to electric vehicles will happen at the pace technology and price allow. It does not need to be forced by ban dates that ignore reality. Removing the mandate would let the market evolve without pushing households into hardship.",
        "Forcing rapid EV adoption without the grid capacity, charging coverage or affordable supply to back it up is bad policy. The result will be blackouts, queues and frustration. The petrol-car ban should be scrapped until the rest of the system can actually cope.",
        "Net Zero policies have been imposed on drivers without honest accounting of the costs. The petrol-car ban is one of the most expensive examples. Scrapping it would put cash back in family budgets and restore confidence that government policy is grounded in reality.",
        "The 2030 ban is a destructive policy that damages British industry, pushes ordinary drivers off the road and delivers no clear climate benefit. It must be totally scrapped, and a sensible, market-led approach to lower-emission vehicles must take its place.",
        "The ZEV mandate is forcing manufacturers to make cars that ordinary drivers cannot afford and do not want. The result is a damaged industry, higher prices and working people pushed off the road. The whole policy should be scrapped and consumer choice restored.",
        "Net Zero has sent energy costs soaring, made families poorer and colder, damaged British industry and forced drivers off the road. The petrol-car ban concentrates all of those failures into a single policy. Scrapping it is the most direct way to put working drivers first.",
    ],

    (SIDE_A, POLICY_BAN_PETROL): [
        "Air pollution from petrol and diesel vehicles is causing tens of thousands of early deaths every year. Bringing forward the end of new sales to 2027 and ending road use by 2035 would deliver immediate health gains, particularly in our most polluted communities.",
        "A serious EV transition has to include the people who cannot afford a new vehicle. That is why a five billion pound annual scrappage scheme must sit alongside the ban, helping working households switch to cleaner transport rather than being left behind.",
        "Electric cars are cheaper to run per mile, quieter in our streets and far cleaner in our lungs. The 2030 deadline is the bare minimum; bringing forward sales to 2027 would lock in those benefits sooner and signal that the country is finally serious about clean transport.",
        "Charging infrastructure, public transport investment and active travel networks must expand together with the ban. The goal is not to force everyone into a private EV but to make clean transport, in all its forms, the realistic default for every community.",
        "The car industry has been calling for clarity for years. A firm and earlier end-date for new petrol and diesel sales gives manufacturers and investors the long-term signal they need to commit fully to electric production lines and the supply chains that go with them.",
        "Every year of delay means more lifetime emissions locked in by petrol and diesel vehicles bought now. Bringing the cut-off forward to 2027 sharply cuts those locked-in emissions and helps put the transport sector on track with our overall climate obligations.",
        "Buses, trains and cycling deserve far more investment than they have received, and the funds released by the transition must back them. A scrappage scheme paired with rapid expansion of public and active transport would give families real alternatives, not just a different car.",
        "Children growing up next to busy roads breathe pollution that damages their lungs for life. Ending the sale of new petrol and diesel cars by 2027 is a basic act of public health policy for the next generation, and it should not be diluted.",
        "Cities across Europe have been moving faster than the UK on banning new combustion sales. There is no reason a serious industrial economy cannot match or exceed them. Bringing the date forward to 2027 puts the country back among the leaders.",
        "Scrappage support should be targeted first at low-income households and those most exposed to air pollution, ensuring the transition reduces inequality rather than entrenching it. A well-designed scheme is the difference between a fair transition and a punitive one.",
        "Investing in domestic battery and EV manufacturing alongside the ban turns the transition into an industrial opportunity rather than a threat. A serious plan funds the factories, training and grid links needed for the new sector to thrive.",
        "Charging at home or work is straightforward for many drivers and getting easier all the time. Public charging in apartments and rural areas needs more investment, and the policy package must fund it. The ban itself is only one piece of a wider plan.",
        "Removing all petrol and diesel vehicles from the road by 2035 would deliver enormous gains in air quality and noise reduction in every community. The 2035 horizon gives time to plan, with the 2027 sales cut-off ensuring fleet turnover accelerates.",
        "The argument that EVs are unaffordable ignores rapidly falling costs, lower running expenses and the scrappage support being proposed. The honest comparison shows that delaying the transition costs more, in money, health and emissions, than accelerating it.",
        "A genuine industrial strategy for British car-making is built on electrification, not on prolonging the life of an engine technology that has no future. Backing the ban with investment is how we keep skilled jobs in this country rather than losing them to faster movers abroad.",
        "Vehicle scrappage at scale would not only retire the most polluting cars but also free road space for cleaner alternatives. Paired with serious public transport investment, it transforms the experience of urban travel for everyone, including those who do not drive.",
        "Ending sales of new petrol and diesel vehicles by 2027 and use by 2035, supported by a multi-billion-pound annual scrappage scheme, is the package needed to clean our air, meet our climate obligations and modernise our roads. Half-measures will not deliver any of these.",
        "All petrol and diesel vehicles should be replaced by electric vehicles within a decade. Sales of new petrol and diesel cars must end by 2027, supported by a substantial annual scrappage scheme so ordinary families can make the switch quickly and fairly.",
        "Clean transport is not a luxury for the better-off; it is a basic public health requirement and an economic opportunity. The combination of an earlier ban, a generous scrappage scheme and serious investment in public transport delivers on all three fronts.",
    ],

    (SIDE_B, POLICY_GREEN_HOUSING): [
        "A heat pump costs roughly three times the price of a new gas boiler to install, before the hidden costs of new radiators and major insulation work. Forcing them on every new build inflates housing prices for no proportionate benefit.",
        "Britain has a housing crisis, and yet government keeps loading additional Net Zero requirements onto every new development. The mandates make homes more expensive to build, slower to deliver and unaffordable for first-time buyers. They should be lifted.",
        "Insulation upgrades that involve tearing up walls and floors come with hidden costs that the official policy quietly ignores. Ordinary homeowners and renters end up paying twice: once through higher prices and again through disruption. The mandates are punishing the wrong people.",
        "Letting builders choose proven, affordable heating systems would help more homes be built faster. Imposing expensive technologies that the market has not yet brought down in price only makes the housing crisis worse and chases away small developers.",
        "Record taxes, wasteful government spending and nanny-state regulations are wrecking the economy. The mandate for heat pumps, solar panels and high-level insulation on every new build is one of the most visible examples. Removing it would help builders deliver affordable homes.",
        "Solar panels and heat pumps are valuable for some households, but they should not be forced on every new build regardless of cost, location or suitability. Letting buyers decide what they want in their home is a basic question of liberty as well as affordability.",
        "The cost gap between a gas boiler and a heat pump system is enormous, and the running cost advantage often disappears under real-world conditions. The mandate ignores both, leaving households worse off and forcing builders to inflate sale prices.",
        "Bureaucrats setting detailed technical mandates for every new home produces costly, slow and inflexible housing. Letting market signals shape choices would deliver more homes, more affordable homes and homes that better match what families actually want.",
        "Hidden compliance costs from green building standards are absorbed by buyers and tenants in higher prices and rents. There is nothing fair about that. Removing the mandates would put downward pressure on costs across the housing market.",
        "Workers in traditional heating and building trades risk being squeezed out by mandates that favour a narrow set of approved technologies. A fair approach would respect the existing supply chain and let proven, affordable solutions stay in the market.",
        "Net Zero targets are wrecking the economy and the housing market alike. The green housing mandates are a clear example of how good intentions translate into higher costs for ordinary people. They should be scrapped to give the construction sector room to deliver.",
        "Households in colder regions need reliable, powerful heating. Forcing every new home onto heat pumps regardless of local conditions risks leaving families cold in winter. Letting builders choose appropriate systems would protect comfort as well as costs.",
        "Solar panel mandates on every roof, regardless of orientation or shading, produce poor returns on expensive kit. Removing the blanket requirement and letting installers choose where solar actually makes sense would be cheaper, simpler and just as effective.",
        "The housing crisis is the most important domestic economic problem facing the country. Layering Net Zero mandates onto an already struggling construction sector deepens that crisis. Removing the mandates would help bring more homes to market more quickly.",
        "Insulation standards already in building regulations have improved over decades without mandating Passivhaus-level performance everywhere. The latest round of mandates is overreach that adds cost without delivering meaningfully better outcomes for most homes.",
        "Government should be cutting taxes and removing regulations to help families afford a home, not adding compliance costs that price first-time buyers out. The current green building mandates work directly against affordable home ownership.",
        "Scrap the green housing mandates, simplify building regulations and let builders use proven, affordable heating and insulation. That is how we end the housing crisis, protect ordinary homeowners and stop nanny-state rules from making everything more expensive.",
        "Mandating heat pumps and Passivhaus-level insulation on every new home is nanny-state regulation that drives up prices in the middle of a housing crisis. Builders pass the costs on to buyers, and ordinary families are priced out. These mandates should be scrapped.",
        "The economy is being wrecked by record taxes, wasteful spending and a relentless flow of new green regulations. Mandating heat pumps and high-level insulation on every new home is part of that pattern. Removing the mandate would help the housing market work for ordinary buyers again.",
    ],

    (SIDE_A, POLICY_GREEN_HOUSING): [
        "A ten-year emergency upgrade programme should provide free insulation and heat pumps to low-income households first, ending fuel poverty for those most affected by cold, damp homes. This is climate policy and social policy in one programme.",
        "Cold, damp housing is killing people every winter and pushing the NHS into avoidable crisis. Mandating high insulation standards in new builds and accelerating retrofit in existing stock is one of the most cost-effective health investments the country could make.",
        "Building regulations must be changed so that every new home meets Passivhaus or equivalent standards. Doing this now is far cheaper than fixing it later, and it gives the construction industry a clear long-term signal to invest in skills and supply chains.",
        "Heat pumps and solar panels turn homes from energy sinks into productive parts of the energy system. Mandating them on all new builds, supported by training and grants, accelerates the transition and reduces household bills permanently.",
        "Free insulation and heat pump installation for those on low incomes would deliver immediate cuts to bills, improvements in health and reductions in emissions. It is the kind of programme that pays back many times over and should have started years ago.",
        "A serious workforce plan must accompany the building upgrade programme: training installers, electricians, retrofit coordinators and Passivhaus designers. Without that, the policy stalls. With it, the country gains tens of thousands of decent green jobs.",
        "All new homes being zero-carbon from day one removes a major source of long-term emissions. Anything less commits the country to expensive future retrofits and decades of avoidable bills for residents. The standards must be set high and enforced consistently.",
        "Building Passivhaus from the start does add some upfront cost, but it dramatically reduces lifetime running costs, repairs and health impacts. The honest comparison strongly favours building well now rather than building poorly and paying again later.",
        "Solar panels on every new roof would significantly cut electricity bills for residents and add meaningful generation capacity to the grid over time. There is no good reason new homes should be built without them in this decade.",
        "Retrofit at street scale, rather than home by home, brings down costs and disruption. A national programme should support local authorities to organise area-based upgrades, starting with the homes and households most in need.",
        "Energy efficiency is the cheapest unit of energy. Every pound spent on insulation today is repaid many times over in bills, comfort and emissions reductions tomorrow. A national programme is overdue and should be funded with the urgency the situation requires.",
        "Health inequalities driven by cold homes fall disproportionately on poorer households, older people and children with respiratory conditions. A serious upgrade programme would lift those burdens directly and reduce pressure on health services.",
        "Modern heat pumps work reliably in cold climates and have been deployed at scale across northern Europe. The objections raised here are increasingly out of date. Standardising them in new builds and supporting retrofit is straightforward, proven policy.",
        "The housing crisis and the climate crisis must be solved together. Building large numbers of new homes to high standards is the only honest answer; building poorly to save short-term cost simply moves the bill onto residents for decades.",
        "Public investment in retrofit creates skilled jobs in every constituency. Unlike many infrastructure investments, the work is distributed across the whole country and supports small and medium-sized firms as well as larger contractors.",
        "Building standards that fall short of Passivhaus today will be obviously inadequate within a decade. Refusing to set the bar high now condemns residents and future taxpayers to expensive corrective work. Setting it high now is both cheaper and fairer.",
        "All new homes built to zero-carbon Passivhaus standards with solar and heat pumps; existing homes upgraded through a ten-year programme starting with the poorest. That is the green housing policy this country needs, and it should start without further delay.",
        "All new homes must be built to zero-carbon Passivhaus or equivalent standards, with solar panels and heat pumps fitted as standard. Building to these standards from the start is cheaper than retrofitting later and locks in low bills and warm homes for the lifetime of every property.",
        "An emergency upgrade programme for existing homes is the fastest route to lower bills and warmer winters for millions. Starting with free insulation and heat pumps for those on low incomes ensures the most exposed households benefit first.",
    ],

    (SIDE_B, POLICY_CARBON_TAX): [
        "Refineries are being asked to operate under a rising carbon tax that climbs steadily to 2050 with no honest plan for how they will remain viable. The result is industrial decline and lost jobs. The tax must be removed.",
        "Carbon taxes are passed straight from generators to households through electricity bills. Pretending they fall on polluters rather than people is dishonest. The fastest way to cut bills is to scrap the tax.",
        "A common-sense approach to British energy starts with cheap power, and cheap power starts with removing the carbon tax from generation. Doing so would deliver immediate, visible relief to every electricity bill payer.",
        "Domestic industry already faces some of the highest energy prices in the developed world. Layering a carbon tax on top of that is a deliberate choice to deindustrialise. Removing it would restore a level playing field and protect skilled jobs.",
        "Pensioners and low-income households suffer most when carbon levies push up electricity prices. The tax is regressive in practice no matter how it is described in theory. Removing it is a simple, fair way to protect those least able to absorb higher bills.",
        "The cheap power plan would slash electricity bills by removing the carbon tax and ending Renewable Obligation subsidies. That is a clear, concrete proposal grounded in common sense rather than ideology.",
        "Scheduled carbon tax increases through 2050 amount to a slow strangulation of British industry. No serious industrial strategy can coexist with that trajectory. The honest choice is to reverse it now before more capacity is lost.",
        "Other countries do not impose comparable carbon costs on their producers. Maintaining ours just exports our industry and our emissions while raising bills at home. Removing the tax restores competitiveness without changing global emissions in any meaningful way.",
        "Behind every carbon tax bill is a steelworker, a refinery operator or a manufacturing worker whose job is being put at risk. The tax does not abstractly punish polluters; it concretely punishes British workers. It must go.",
        "A twenty percent cut in electricity bills is not a small change. It would help every household, every small business and every industrial site in the country. That is what removing the carbon tax would deliver, and there is no good reason to delay.",
        "Carbon pricing was sold to the public as a way to drive innovation. In practice it has driven offshoring, deindustrialisation and higher bills. The policy has failed on its own terms and should be scrapped.",
        "When industry leaves, the supply chain leaves with it. The carbon tax is one of the main forces pushing manufacturing offshore. Removing it would help keep skilled jobs and the communities that depend on them alive.",
        "The country cannot meet its commitments to manufacturing, energy security and household affordability while continuing to raise carbon taxes on home producers. Something has to give. The honest answer is to remove the tax.",
        "Refining capacity once lost is extremely difficult to rebuild. Watching it disappear because of an avoidable domestic tax is reckless. Removing the carbon tax is a precondition for any credible plan to keep this strategic sector.",
        "The political class has chosen Net Zero targets over working people's bills and jobs. That balance must be reversed. Cutting the carbon tax is the most direct way to put household and industrial interests back at the top of the agenda.",
        "Cheap, reliable power is the foundation of any modern economy. Carbon taxes that drive up prices are incompatible with that foundation. Removing them is a basic requirement for restoring growth and competitiveness.",
        "Scrap the carbon tax on generation, slash electricity bills by around twenty percent and let industry compete again. That is a common-sense plan for cheap British energy and the working families and businesses who rely on it.",
        "The carbon tax is crippling refineries, steel, chemicals and other foundation industries while driving up wholesale electricity prices for every household. Removing it would cut bills by around twenty percent and give British industry a fighting chance to survive.",
        "Energy-intensive manufacturers cannot compete internationally while paying domestic carbon levies that overseas rivals do not face. Removing the tax restores the basic conditions for industry to invest, hire and grow in this country again.",
    ],

    (SIDE_A, POLICY_CARBON_TAX): [
        "Carbon tax revenues, estimated at tens of billions a year, should fund retrofit, renewables, public transport and the NHS rather than being handed back as small individual dividends. That investment delivers more lasting benefit than a per-person payment ever could.",
        "Polluters must pay for the harm they cause. A serious carbon tax sends a clear price signal to investors and producers, while the revenue must be directed to the public goods that make a genuine transition possible.",
        "Carbon pricing is most effective when paired with sustained public investment in the alternatives. Using revenues to expand renewables, upgrade homes and modernise transport ensures the tax actually accelerates the transition rather than just raising costs.",
        "Setting the tax at one hundred and twenty pounds per tonne immediately, rising toward five hundred pounds per tonne over a decade, gives investors a credible long-term signal. Without that clarity, capital will keep flowing into fossil infrastructure. With it, the transition becomes financeable at scale.",
        "Fossil fuel companies have made record profits while ordinary households absorb the impacts of climate change. A serious tax on their extraction and imports is basic fairness, and using the revenue for public investment compounds the benefit.",
        "Public services have been hollowed out by years of underinvestment. Earmarking carbon tax revenue for the NHS, transport and housing aligns climate and social policy and ensures the proceeds reach the public in tangible, lasting ways.",
        "A direct cash dividend was a tempting design, but evidence suggested it would not deliver the structural investment the transition needs. Redirecting revenues into renewables, retrofit and public transport produces deeper, more durable benefits for households over time.",
        "Carbon pricing alone will not change the energy system at the necessary speed. It has to fund a parallel programme of public investment in clean alternatives, infrastructure and skills. Without that, the price signal does too little, too slowly.",
        "International evidence shows that carbon prices in this range, used to fund public investment, can accelerate emissions reductions without harming overall economic activity. The combination of tax and targeted spending is what works.",
        "Imposing a real cost on fossil fuel extraction stops public subsidy of an industry whose product is incompatible with the climate limits we have signed up to. The carbon tax is one of the cleanest tools to end that hidden subsidy.",
        "Households need protection from rising energy costs during the transition. That protection is best delivered through investment in insulation, public transport and renewables, all funded from carbon tax revenue. That route reduces bills permanently rather than offsetting them temporarily.",
        "Border adjustments must accompany the carbon tax so that domestic producers are not undercut by imports from countries with weaker climate policies. Properly designed, the tax then becomes a tool for industrial strategy as well as decarbonisation.",
        "Putting a serious price on carbon, alongside ending new oil and gas licences, would finally align market signals with the climate emergency. The two policies reinforce each other and should be introduced together.",
        "Investment funded by carbon tax revenue should be focused on the communities most affected by the transition, ensuring fossil fuel regions become centres of renewable manufacturing and retrofit work rather than victims of policy.",
        "A predictable, escalating carbon price is more useful to investors than a cash-back scheme that fluctuates with politics. Committing to a clear trajectory through to five hundred pounds per tonne creates the certainty needed for long-term capital allocation.",
        "Revenue from the carbon tax should be ring-fenced for transition spending, with transparent annual reporting on what was raised and how it was deployed. That accountability is essential to maintain public trust in the policy.",
        "Introduce the carbon tax at one hundred and twenty pounds per tonne, escalate it on a clear schedule and direct the revenue into the green transition and crumbling public services. That is honest, effective climate and economic policy, even if it means foregoing a per-person dividend.",
        "A carbon tax should be introduced on all fossil fuel imports and domestic extraction, starting at one hundred and twenty pounds per tonne and rising over a decade. The biggest polluters must pay for the damage they cause, with revenues used to invest in the green transition and rescue public services.",
        "Making polluters pay and investing the proceeds in the green transition is the cleanest pairing in climate economics. It puts the cost where it belongs, funds the alternatives at scale and avoids the inefficiency of recycling small sums back to every household.",
    ],

    (SIDE_B, POLICY_COMPENSATION): [
        "An out-of-touch political class has been giving away British taxpayers' money through climate compensation schemes for years. Cutting the aid budget in half and refocusing on domestic priorities would put resources back where they are most needed.",
        "Quitting expensive UN climate bodies and ending climate compensation payments would save substantial sums every year. Those funds belong to British taxpayers and should be used to fix domestic problems first.",
        "Climate compensation is dressed up as moral obligation, but in practice it is a transfer from struggling British households to foreign governments. That is not fair on the people who actually pay the bill.",
        "Foreign aid budgets have grown despite repeated promises of reform. Climate compensation is now being added on top. A sensible approach would halve aid spending overall and remove climate-specific transfers entirely.",
        "Multilateral climate bodies impose obligations on countries like Britain while doing little to constrain the largest emitters. The arrangement is unbalanced and expensive. Leaving these bodies would protect taxpayer money and national sovereignty.",
        "There is no shortage of urgent domestic problems to address: NHS waiting lists, crumbling infrastructure, struggling schools. Adding climate compensation payments to the budget while these go unsolved gets priorities exactly backwards.",
        "The political class that signed up to climate compensation never asked the public whether they supported sending billions abroad while their own bills rose. That democratic deficit should be corrected by ending the payments.",
        "Compensation payments rarely reach the people they are supposedly intended to help, lost instead to bureaucracy and intermediaries. Cutting them would lose little while saving substantial sums for the British public.",
        "Ruling elites have turned their backs on this country, dispatching public money to international schemes while domestic services degrade. Cutting foreign aid by fifty percent and ending climate compensation would begin to reverse that betrayal.",
        "Britain should not be apologising for its history or paying ongoing penalties for it. Other major emitters do not behave this way. Continuing to do so isolates the country and weakens its negotiating position abroad.",
        "Every pound spent on overseas climate compensation is a pound not spent on a struggling school, a delayed surgery or a pothole-riddled road in this country. That is the real trade-off and the public deserves to see it clearly.",
        "Following the example of other countries withdrawing from UN climate bodies would protect the British taxpayer and restore policy sovereignty. There is no good reason to remain inside expensive institutions that fail to deliver.",
        "International climate finance has become a vehicle for permanent ongoing payments rather than discrete time-limited assistance. Ending compensation payments stops that ratchet from continuing to grow at British taxpayers' expense.",
        "Charity begins at home. Working families struggling with bills should not be funding foreign governments' climate programmes through their taxes. Cutting aid by half and ending compensation transfers is a basic act of common sense.",
        "Climate compensation lacks any clear measure of success. Money goes out, but accountability for outcomes is weak. That is no way to spend taxpayer funds, and it is enough reason on its own to end the payments.",
        "The country can be a constructive partner on climate issues without writing open-ended cheques. Practical cooperation, including trade, does not require the kind of permanent transfer that climate compensation has become.",
        "Quit expensive UN climate bodies, cut the foreign aid budget in half and use the savings to fix the country's own broken services. That is what an honest, patriotic climate and aid policy looks like.",
        "UN climate bodies are deeply flawed, unaccountable and expensive institutions that fail British voters. Sending billions abroad in climate compensation while domestic services struggle is indefensible. Foreign aid should be cut sharply and the savings used to fix the country's own problems.",
        "We are ruled by an out-of-touch political class that has turned its back on its own country, sending money abroad while bills rise at home. Halving the foreign aid budget and ending climate compensation payments would restore proper priorities.",
    ],

    (SIDE_A, POLICY_COMPENSATION): [
        "International climate finance must be provided as direct grants, not loans, so that the poorest countries are not driven further into debt by a crisis they did not create. Loan-based finance simply stores up more problems for the future.",
        "Developing countries facing rising seas, failing harvests and intensifying storms are already paying with lives and livelihoods. The richest countries, responsible for the bulk of historic emissions, have a clear obligation to support them with predictable, grant-based finance.",
        "The Loss and Damage Fund has been one of the most important international agreements of the decade. This country should contribute generously, provide grants rather than loans and push other wealthy countries to do the same.",
        "Climate finance provided as loans makes things harder for the poorest people in the poorest countries. The choice between debt and disaster is not a real choice. Grant-based finance is the only honest form of climate compensation.",
        "Historic responsibility for emissions sits overwhelmingly with industrialised countries. Acknowledging that responsibility through serious financial support for those now facing the worst impacts is a question of basic fairness and international honour.",
        "Climate impacts in the Global South already drive displacement, food insecurity and conflict. Investing in climate compensation, adaptation and resilience is far cheaper than dealing with the cascading consequences when the situation worsens further.",
        "Domestic resources should fund domestic services, but the climate emergency is not a domestic problem. It is global. Acting as if international climate finance is a luxury rather than an obligation gets the moral picture exactly wrong.",
        "Compensation for climate-induced loss and damage is not foreign aid in the traditional sense. It is partial repair for harm caused by historical emissions, and it should be designed and accounted for differently from other aid spending.",
        "The cost of failing to act on loss and damage will fall first on vulnerable countries and then, through migration, food prices and instability, on every country including this one. Generous, well-targeted finance is in everyone's interest.",
        "Each new climate agreement that includes a finance commitment must be honoured, not quietly diluted. Credibility on climate diplomacy depends on actually paying what has been pledged, on time, and as grants.",
        "Public health, women's rights, agriculture and education in vulnerable countries are all being undermined by climate impacts. Direct grant finance helps address those frontline impacts and supports the institutions that can build long-term resilience.",
        "Loss and damage finance should be additional to existing aid budgets, not carved out of them. Treating climate compensation as a competition with other development funding is a false framing that harms recipients twice over.",
        "Honest accounting of historical emissions makes clear who owes what. The UK ranks high on that ledger. Meeting that obligation generously and transparently is part of being a responsible global citizen.",
        "Investing in adaptation, early-warning systems and resilient infrastructure in vulnerable countries reduces the human and economic costs of climate disasters before they unfold. That is what grant-based climate finance can deliver if it is provided at scale.",
        "The right framework for climate finance is reparative as well as developmental: it repairs harm already done while supporting capacity to cope with what is coming. Both functions require grants rather than debt-creating loans.",
        "Domestic and international climate commitments rise or fall together. A country that cuts its emissions at home but refuses to support those abroad is not a credible climate leader. Both halves of the policy are required.",
        "Commit to honest, grant-based climate finance at the scale the science demands; defend the Loss and Damage Fund; and ensure compensation is additional rather than a redirection of existing aid. That is climate justice in practice.",
        "An honest financial commitment is needed to repair the devastating damage done to many developing nations by climate impacts they did little to cause. The country should stick firmly to its agreements and provide finance at the scale the science and the justice of the situation require.",
        "Climate finance provided as loans rather than grants stores up further problems for the future, particularly for the poorest people in the poorest countries. Direct grant funding is the only responsible form of international climate support.",
    ],
}


# ----------------------------------------------------------------------------
# Build & write
# ----------------------------------------------------------------------------
SOURCES_HEADER = [
    "source_id", "policy_id", "side", "party_name",
    "speaker", "speaker_role", "date", "venue",
    "citation_url", "quote_text", "manifesto_or_hansard_ref", "notes",
]

MESSAGES_HEADER = [
    "message_id", "policy_id", "side", "message_text",
    "source_type", "provenance_refs",
    "generation_method", "length_words", "version", "notes",
]

# Provenance helpers: the two source_ids for a cell.
def _cell_source_ids(side: str, policy_id: int) -> list[str]:
    pid2 = f"{policy_id:02d}"
    return [f"{side}_{pid2}_01", f"{side}_{pid2}_02"]


def _word_count(text: str) -> int:
    return len(text.split())


def build_messages_rows() -> list[dict]:
    rows: list[dict] = []

    # 1) Per-cell single-policy messages: 1 verbatim + 19 LLM = 20.
    for side in (SIDE_A, SIDE_B):
        for policy_id in ALL_POLICIES:
            pid2 = f"{policy_id:02d}"
            provenance = ";".join(_cell_source_ids(side, policy_id))

            verbatim_text = VERBATIM[(side, policy_id)]
            rows.append({
                "message_id": f"{side}_{pid2}_01",
                "policy_id": str(policy_id),
                "side": side,
                "message_text": verbatim_text,
                "source_type": "verbatim_summary",
                "provenance_refs": provenance,
                "generation_method": GENERATION_METHOD_VERBATIM,
                "length_words": str(_word_count(verbatim_text)),
                "version": DATASET_VERSION,
                "notes": "Broadcast-ready message from research doc; ASCII-normalised.",
            })

            llm_msgs = LLM_MESSAGES[(side, policy_id)]
            if len(llm_msgs) != 19:
                raise RuntimeError(
                    f"Cell ({side}, {policy_id}) has {len(llm_msgs)} LLM messages; expected 19."
                )
            for idx, text in enumerate(llm_msgs, start=2):
                rows.append({
                    "message_id": f"{side}_{pid2}_{idx:02d}",
                    "policy_id": str(policy_id),
                    "side": side,
                    "message_text": text,
                    "source_type": "llm_generated",
                    "provenance_refs": provenance,
                    "generation_method": GENERATION_METHOD_LLM,
                    "length_words": str(_word_count(text)),
                    "version": DATASET_VERSION,
                    "notes": "",
                })

    # 2) Placeholder package messages: concat of each side's 6 per-policy verbatim
    # messages, separated by a blank line. Provenance = all 12 source_ids for the side.
    for side in (SIDE_A, SIDE_B):
        per_policy_texts = [VERBATIM[(side, pid)] for pid in ALL_POLICIES]
        package_text = "\n\n".join(per_policy_texts)
        all_side_sources = []
        for pid in ALL_POLICIES:
            all_side_sources.extend(_cell_source_ids(side, pid))
        rows.append({
            "message_id": f"{side}_PKG_01",
            "policy_id": "PACKAGE",
            "side": side,
            "message_text": package_text,
            "source_type": "verbatim_summary",
            "provenance_refs": ";".join(all_side_sources),
            "generation_method": GENERATION_METHOD_PACKAGE_PLACEHOLDER,
            "length_words": str(_word_count(package_text)),
            "version": DATASET_VERSION,
            "notes": (
                "Placeholder package message: concatenation of this side's 6 "
                "per-policy verbatim broadcast messages. To be replaced with "
                "bespoke package-mode messages in v2."
            ),
        })

    return rows


def build_sources_rows() -> list[dict]:
    rows = []
    for src in SOURCES:
        rows.append({
            "source_id": src["source_id"],
            "policy_id": str(src["policy_id"]),
            "side": src["side"],
            "party_name": PARTY_NAME[src["side"]],
            "speaker": src["speaker"],
            "speaker_role": src["speaker_role"],
            "date": src["date"],
            "venue": src["venue"],
            "citation_url": src["citation_url"],
            "quote_text": src["quote_text"],
            "manifesto_or_hansard_ref": src["manifesto_or_hansard_ref"],
            "notes": src["notes"],
        })
    return rows


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sources_rows = build_sources_rows()
    if len(sources_rows) != 24:
        raise RuntimeError(f"Expected 24 sources rows, got {len(sources_rows)}.")
    write_csv(SOURCES_CSV, SOURCES_HEADER, sources_rows)

    messages_rows = build_messages_rows()
    # 12 cells * 20 msgs + 2 package placeholders = 242
    if len(messages_rows) != 242:
        raise RuntimeError(f"Expected 242 messages rows, got {len(messages_rows)}.")
    write_csv(MESSAGES_CSV, MESSAGES_HEADER, messages_rows)

    print(f"Wrote {len(sources_rows)} rows -> {SOURCES_CSV}")
    print(f"Wrote {len(messages_rows)} rows -> {MESSAGES_CSV}")


if __name__ == "__main__":
    main()
