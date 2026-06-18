#!/usr/bin/env python3
"""Quick off-repo sanity check: audience split per reach condition.

Mirrors the AIRE __main__.py setup (seed=42, n_citizens=50,
political_exposure_mode="rule_affinity_rank", default targets/weights)
and reports, for each of three reach configs, how many citizens end up
in agent_a's audience vs agent_b's audience after:

    1) assign_political_exposure (assigns A / B / both / neither labels)
    2) apply_audience_cap (no-op here; cap=None)
    3) apply_reach_subsample (the broadcast reach we vary)

NO simulation, NO LLM calls. Run from repo root:

    PYTHONPATH=src python3 sandbox/ajay_sandbox/check_reach_split.py
"""
import sys
from pathlib import Path

# Ensure src/ is importable even if PYTHONPATH wasn't set
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gabm.abm.attributes.gender import GenderMap, GenderID
from gabm.abm.attributes.politics import PoliticsID
from gabm.abm.democracy.election import ElectionID

from cag.io.survey import load
from cag.abm.agent import SurveyedCitizen
from cag.abm.environment import SurveyedNation
from cag.abm.attributes.region import UKRegionMap, RegionID
from cag.abm.attributes.education import SurveyEducationMap, EducationID
from cag.abm.attributes.ethnicity import SurveyEthnicityMap, EthnicityID
from cag.abm.attributes.income import SurveyIncomeMap, IncomeID
from cag.abm.attributes.politics import SurveyPoliticsMap
from cag.abm.attributes.family import SurveyFamilyMap, FamilyID
from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteMap, UKGE2019VoteID
from cag.abm.democracy.elections.brexit import BrexitVoteMap, BrexitVoteID
from cag.abm.attributes.narratives import (
    SelftranscMap, SelfenhMap, OpennessMap, ConformTradMap,
    SDOMap, EDOMap, RWAMap, rescale_1_6, rescale_1_7,
)
from cag.abm.agent import PoliticalAgent


# ── AIRE config ──────────────────────────────────────────
SURVEY_CSV = ROOT / "data" / "yougov_survey_data" / "YouGovProcessedData.csv"
N_CITIZENS = 50
SEED = 42
YEAR = 2026


def build_nation(data, year=YEAR):
    """Identical to __main__.build_nation."""
    UKGE2019_ELECTION_ID = ElectionID(0)
    BREXIT_REFERENDUM_ID = ElectionID(1)

    sn = SurveyedNation(
        year=year, place="UK",
        gender_map=GenderMap(),
        region_map=UKRegionMap(),
        education_map=SurveyEducationMap(),
        ethnicity_map=SurveyEthnicityMap(),
        income_map=SurveyIncomeMap(),
        politics_map=SurveyPoliticsMap(),
        family_map=SurveyFamilyMap(),
        ukge2019_vote_map=UKGE2019VoteMap(UKGE2019_ELECTION_ID),
        brexit_vote_map=BrexitVoteMap(BREXIT_REFERENDUM_ID),
        selftransc_map=SelftranscMap,
        selfenh_map=SelfenhMap,
        openness_map=OpennessMap,
        conformtrad_map=ConformTradMap,
        sdo_map=SDOMap,
        edo_map=EDOMap,
        rwa_map=RWAMap,
    )

    for i in range(len(data)):
        row = data.iloc[i]
        sc = SurveyedCitizen(
            agent_id=row.get("ID", None),
            environment=sn,
            year_of_birth=year - int(row.get("age", 0)),
            gender_id=GenderID.MALE if int(row.get("male_dummy", 0)) == 1 else GenderID.FEMALE,
            region_id=RegionID(int(row.get("tprofile_GOR", 0))),
            education_id=EducationID(int(row.get("profile_education_level", 0))),
            income_id=IncomeID(int(row.get("tprofile_gross_household", 0))),
            ethnicity_id=EthnicityID(int(row.get("ethnicity_R", 0))),
            family_id=FamilyID.PARENT if int(row.get("parent_dummy", 0)) == 1 else FamilyID.NOT_PARENT,
            ukge2019_vote_id=UKGE2019VoteID(int(row.get("Vote2019R", 0))),
            brexit_vote_id=BrexitVoteID(int(row.get("pastvote_EURef", 0))),
            politics_id=PoliticsID(int(row.get("Political_Left_Right", 0))),
            selftransc_id=rescale_1_6(int(row.get("Selftransc_Val", 0))),
            selfenh_id=rescale_1_6(int(row.get("Selfenh_Values", 0))),
            openness_id=rescale_1_6(int(row.get("Openness", 0))),
            conformtrad_id=rescale_1_6(int(row.get("ConformTrad", 0))),
            sdo_id=rescale_1_7(int(row.get("SDO", 0))),
            edo_id=rescale_1_7(int(row.get("EDO", 0))),
            rwa_id=rescale_1_6(int(row.get("RWA", 0))),
            original_survey_data=data.iloc[i],
        )
        sn.agents_active[sc.id] = sc

    return sn


def label_counts(nation):
    """Tally political_exposure labels across all active citizens."""
    counts = {"A-only": 0, "B-only": 0, "both": 0, "neither": 0}
    for c in nation.agents_active.values():
        counts[c.political_exposure] = counts.get(c.political_exposure, 0) + 1
    return counts


def report(label, reach_a, reach_b, data):
    """Build a fresh nation, apply exposure + reach, print the split."""
    nation = build_nation(data)
    nation.political_agent_a = PoliticalAgent("agent_a", "pro_climate")
    nation.political_agent_b = PoliticalAgent("agent_b", "anti_climate")

    # Step 1: assign A/B/both/neither labels (defaults: rule_affinity_rank,
    # committed_minority_symmetric targets, balanced weights, seed=42)
    nation.assign_political_exposure(
        mode="rule_affinity_rank",
        targets=None,
        weights=None,
        seed=SEED,
    )
    counts = label_counts(nation)

    # Underlying (canonical) audience sizes BEFORE any reach trim.
    a_full = len(nation.political_agent_a.connected_citizens)
    b_full = len(nation.political_agent_b.connected_citizens)

    # Step 2: audience cap (no-op for AIRE: cap=None)
    nation.apply_audience_cap(cap=None, seed=SEED)

    # Step 3: reach subsample
    nation.apply_reach_subsample(reach_a=reach_a, reach_b=reach_b, seed=SEED)

    a_after = len(nation.political_agent_a.connected_citizens)
    b_after = len(nation.political_agent_b.connected_citizens)

    print(f"\n── {label}  (reach_a={reach_a}, reach_b={reach_b}) ──")
    print(f"  exposure labels   : A-only={counts['A-only']:>2}  B-only={counts['B-only']:>2}  "
          f"both={counts['both']:>2}  neither={counts['neither']:>2}  "
          f"(total {sum(counts.values())})")
    print(f"  canonical audience: agent_a={a_full:>2}  agent_b={b_full:>2}  "
          f"(includes 'both' on each side)")
    print(f"  after reach trim  : agent_a={a_after:>2}  agent_b={b_after:>2}")
    print(f"  reach delta       : A {a_full}->{a_after} (-{a_full - a_after}), "
          f"B {b_full}->{b_after} (-{b_full - b_after})")


def main():
    print(f"Loading {SURVEY_CSV} ...")
    data = load(str(SURVEY_CSV))
    data = data.sample(n=N_CITIZENS, random_state=SEED).reset_index(drop=True)
    print(f"Sampled {len(data)} citizens with seed={SEED}")
    print("Settings: mode=rule_affinity_rank, targets=default(committed_minority_symmetric), "
          "weights=default(balanced), audience_cap=None")
    print("Note: agent_a = pro_climate, agent_b = anti_climate. "
          "'both' citizens count toward BOTH audiences; 'neither' count toward neither.")

    report("S_symmetric         ", reach_a=1.0,  reach_b=1.0,  data=data)
    report("C_A_dominant (reach_a=1.0, reach_b=0.25)",
           reach_a=1.0,  reach_b=0.25, data=data)
    report("C_B_dominant (reach_a=0.25, reach_b=1.0)",
           reach_a=0.25, reach_b=1.0,  data=data)


if __name__ == "__main__":
    main()
