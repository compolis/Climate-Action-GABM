"""
Environment module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>", "Charlie Pilgrim <pilgrimcharlie2@gmail.com>"]
__version__ = "0.2.0"
__copyright__ = "Copyright (c) 2026 GABM contributors, University of Leeds"

# Standard library imports
import logging
import pandas as pd
from typing import Dict
import networkx as nx
# GABM imports
from gabm.abm.environment import Nation
from gabm.abm.attributes.gender import GenderMap
from gabm.abm.attributes.politics import PoliticsID
# Local imports
from gabm.abm.attributes.opinion import OpinionTopicID, Opinion
from cag.abm.agent import PoliticalAgent
from cag.abm.democracy.elections.brexit import BrexitVoteID
from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteID
from cag.abm.attributes.region import UKRegionMap
from cag.abm.attributes.education import SurveyEducationMap
from cag.abm.attributes.ethnicity import SurveyEthnicityMap
from cag.abm.attributes.income import SurveyIncomeMap
from cag.abm.attributes.politics import SurveyPoliticsMap
from cag.abm.attributes.family import SurveyFamilyMap
from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteMap
from cag.abm.democracy.elections.brexit import BrexitVoteMap
from cag.abm.attributes.narratives import SelftranscMap, SelfenhMap, OpennessMap, ConformTradMap, SDOMap, EDOMap, RWAMap
from cag.abm.attributes.opinion import ordinal_score

class SurveyedNation(Nation):
    """
    A Surveyed Nation environment class for Climate-Action-GABM, inheriting from the GABM Nation class.

    .. note::
            Inherits all attributes from :class:`Nation`.

    Attributes:
        region_map (UKRegionMap):
            A UKRegionMap instance for region attribute lookups.
        education_map (SurveyEducationMap):
            A SurveyEducationMap instance for education attribute lookups.
        ethnicity_map (SurveyEthnicityMap):
            A SurveyEthnicityMap instance for ethnicity attribute lookups.
        income_map (SurveyIncomeMap):
            A SurveyIncomeMap instance for income attribute lookups.
        politics_map (SurveyPoliticsMap):
            A SurveyPoliticsMap instance for politics attribute lookups.
        family_map (SurveyFamilyMap):
            A SurveyFamilyMap instance for family attribute lookups.
        ukge2019_vote_map (UKGE2019VoteMap):
            A UKGE2019VoteMap instance for UK General Election 2019 vote attribute lookups.
        brexit_vote_map (BrexitVoteMap):
            A BrexitVoteMap instance for Brexit referendum vote attribute lookups.
        selftransc_map (SelftranscMap):
            A SelftranscMap instance for self-transcendence value attribute lookups.
        selfenh_map (SelfenhMap):
            A SelfenhMap instance for self-enhancement value attribute lookups.
        openness_map (OpennessMap):
            An OpennessMap instance for openness attribute lookups.
        conformtrad_map (ConformTradMap):
            A ConformTradMap instance for conformity-tradition attribute lookups.
        sdo_map (SDOMap):
            An SDOMap instance for social dominance orientation attribute lookups.
        edo_map (EDOMap):
            An EDOMap instance for environmental dominance orientation attribute lookups.
        rwa_map (RWAMap):
            An RWAMap instance for right-wing authoritarianism attribute lookups.
    """
    def __init__(self, year: int = 2026, place: str = "UK", 
        gender_map: GenderMap = None,
        opinions: Dict[OpinionTopicID, Opinion] = None,
        region_map: UKRegionMap = None,
        education_map: SurveyEducationMap = None,
        ethnicity_map: SurveyEthnicityMap = None,
        income_map: SurveyIncomeMap = None,
        politics_map: SurveyPoliticsMap = None,
        family_map: SurveyFamilyMap = None,
        ukge2019_vote_map: UKGE2019VoteMap = None,
        brexit_vote_map: BrexitVoteMap = None,
        selftransc_map: SelftranscMap = None,
        selfenh_map: SelfenhMap = None,
        openness_map: OpennessMap = None,
        conformtrad_map: ConformTradMap = None,
        sdo_map: SDOMap = None,
        edo_map: EDOMap = None,
        rwa_map: RWAMap = None):
        """
        Initialize.
        Args:
            year (int):
                The current year in the simulation.
            place (str):
                The name of the nation.
            gender_map (GenderMap):
                A GenderMap instance for gender attribute lookups.
            opinions (Dict[OpinionTopicID, Opinion]):
                A dictionary of opinions, where the key is an OpinionTopicID and the value is an Opinion object.
                This allows the environment to have an overview of opinions of Persons and OpinionatedGroups.
            region_map (UKRegionMap):
                A UKRegionMap instance for region attribute lookups.
            education_map (SurveyEducationMap):
                A SurveyEducationMap instance for education attribute lookups.
            ethnicity_map (SurveyEthnicityMap):
                A SurveyEthnicityMap instance for ethnicity attribute lookups.
            income_map (SurveyIncomeMap):
                A SurveyIncomeMap instance for income attribute lookups.
            politics_map (SurveyPoliticsMap):
                A SurveyPoliticsMap instance for politics attribute lookups.
            family_map (SurveyFamilyMap):
                A SurveyFamilyMap instance for family attribute lookups.
            ukge2019_vote_map (UKGE2019VoteMap):
                A UKGE2019VoteMap instance for UK General Election 2019 vote attribute lookups.
            brexit_vote_map (BrexitVoteMap):
                A BrexitVoteMap instance for Brexit referendum vote attribute lookups.
            selftransc_map (SelftranscMap):
                A SelftranscMap instance for self-transcendence value attribute lookups.
            selfenh_map (SelfenhMap):
                A SelfenhMap instance for self-enhancement value attribute lookups.
            openness_map (OpennessMap):
                An OpennessMap instance for openness attribute lookups.
            conformtrad_map (ConformTradMap):
                A ConformTradMap instance for conformity-tradition attribute lookups.
            sdo_map (SDOMap):
                An SDOMap instance for social dominance orientation attribute lookups.
            edo_map (EDOMap):
                An EDOMap instance for environmental dominance orientation attribute lookups.
            rwa_map (RWAMap):
                An RWAMap instance for right-wing authoritarianism attribute lookups.
        """
        super().__init__(year=year, place=place, gender_map=gender_map, opinions=opinions,
            region_map=region_map, education_map=education_map, ethnicity_map=ethnicity_map,
            income_map=income_map)
        self.politics_map = politics_map
        self.family_map = family_map
        self.ukge2019_vote_map = ukge2019_vote_map
        self.brexit_vote_map = brexit_vote_map
        self.selftransc_map = selftransc_map
        self.selfenh_map = selfenh_map
        self.openness_map = openness_map
        self.conformtrad_map = conformtrad_map
        self.sdo_map = sdo_map
        self.edo_map = edo_map
        self.rwa_map = rwa_map
        self.network = None
        self.political_agent_a = None
        self.political_agent_b = None

    def run_baseline(self, api_key=None, model="gpt-4o-mini", provider="openai", max_agents=5):
       
        baseline_rows = []
       
        agents = list(self.agents_active.values())[:max_agents]
        logging.info(f"Running baseline for {len(agents)} agents using model '{model}' and provider '{provider}'. If you want more agents then change max_agents in environment.run_baseline()")

        for agent in agents:
            agent_result = agent.run_baseline(api_key=api_key, model=model, provider=provider)
            for policy_id, (letter, numeric) in agent_result.items():
                real_response = agent.get_real_survey_response(policy_id=policy_id)
                logging.info(f"Agent {agent.id} - Policy {policy_id}: LLM response = {letter} ({numeric}), Real survey response = {real_response}")
                baseline_rows.append({
                    "agent_id": agent.id,
                    "policy_id": str(policy_id),
                    "llm_letter": letter,
                    "llm_numeric": numeric,
                    "real_response": real_response,
                    "match": (numeric == real_response),
                    "ordinal_score": ordinal_score(numeric, real_response),
                })
        df = pd.DataFrame(baseline_rows)
        # log overall accuracy
        overall_accuracy = df["match"].mean()
        overall_ordinal = df["ordinal_score"].mean()
        print(f"Overall baseline accuracy: {overall_accuracy:.1%} (exact match), {overall_ordinal:.3f} (ordinal score)")

        # log accuracy per policy
        policy_stats = df.groupby("policy_id").agg({"match": "mean", "ordinal_score": "mean"})
        for policy_id, row in policy_stats.iterrows():
            print(f"Policy {policy_id} - Exact: {row['match']:.1%}, Ordinal: {row['ordinal_score']:.3f}")

        return df

    def assign_political_exposure(self):
        """
        Assign political exposure categories to all citizens based on voting history.

        Priority rules (checked in order):
        1. Leave + Conservative/Brexit → "B-only"
        2. Remain + Labour/Green/LibDem → "A-only"
        3. Leave + Labour/Green/LibDem (mixed) → "both"
        4. Remain + Conservative (mixed) → "both"
        5. Centre politics (any votes) → "both"
        6. Unknown/DontKnow both votes → "neither"
        7. Fallback → "neither"

        Also populates political_agent_a.connected_citizens and
        political_agent_b.connected_citizens.
        """
        left_parties = {UKGE2019VoteID.LABOUR, UKGE2019VoteID.GREEN,
                        UKGE2019VoteID.LIBERAL_DEMOCRATS}
        right_parties = {UKGE2019VoteID.CONSERVATIVE, UKGE2019VoteID.BREXIT}
        unknown_brexit = {BrexitVoteID.UNKNOWN, BrexitVoteID.DONT_KNOW}
        unknown_ge = {UKGE2019VoteID.UNKNOWN, UKGE2019VoteID.DONT_KNOW}

        a_citizens = []
        b_citizens = []

        for citizen in self.agents_active.values():
            brexit = citizen.brexit_vote_id
            ge = citizen.ukge2019_vote_id
            politics = citizen.politics_id

            if brexit == BrexitVoteID.LEAVE and ge in right_parties:
                exposure = "B-only"
            elif brexit == BrexitVoteID.REMAIN and ge in left_parties:
                exposure = "A-only"
            elif brexit == BrexitVoteID.LEAVE and ge in left_parties:
                exposure = "both"
            elif brexit == BrexitVoteID.REMAIN and ge in right_parties:
                exposure = "both"
            elif politics == PoliticsID.CENTRE:
                exposure = "both"
            elif brexit in unknown_brexit and ge in unknown_ge:
                exposure = "neither"
            else:
                exposure = "neither"

            citizen.political_exposure = exposure

            if exposure in ("A-only", "both"):
                a_citizens.append(citizen)
            if exposure in ("B-only", "both"):
                b_citizens.append(citizen)

        if self.political_agent_a is not None:
            self.political_agent_a.connected_citizens = a_citizens
        if self.political_agent_b is not None:
            self.political_agent_b.connected_citizens = b_citizens

    def create_network(self, n_blocks=2, p_intra=0.15, p_inter=0.02, seed=42):
        """
        Create a stochastic block model network with citizens assigned to blocks
        based on their political exposure categories.

        Must call assign_political_exposure() before this method.

        Args:
            n_blocks: Number of blocks (default 2).
            p_intra: Within-block connection probability.
            p_inter: Between-block connection probability.
            seed: Random seed for reproducibility.

        Returns:
            The created nx.Graph, also stored as self.network.
        """
        agents = list(self.agents_active.values())

        # Sort citizens into blocks based on exposure
        block_0 = []  # A-leaning
        block_1 = []  # B-leaning
        swing = []     # both + neither — distribute across blocks

        for citizen in agents:
            if citizen.political_exposure == "A-only":
                block_0.append(citizen)
            elif citizen.political_exposure == "B-only":
                block_1.append(citizen)
            else:
                swing.append(citizen)

        # Round-robin distribute swing citizens across blocks
        for i, citizen in enumerate(swing):
            if i % 2 == 0:
                block_0.append(citizen)
            else:
                block_1.append(citizen)

        # Build the ordered agent list (block 0 first, then block 1)
        ordered_agents = block_0 + block_1
        block_sizes = [len(block_0), len(block_1)]

        # Build probability matrix
        p_matrix = [[p_intra if i == j else p_inter
                      for j in range(n_blocks)]
                     for i in range(n_blocks)]

        G = nx.stochastic_block_model(block_sizes, p_matrix, seed=seed)

        # Relabel nodes from integer indices to agent IDs
        mapping = {i: ordered_agents[i].id for i in range(len(ordered_agents))}
        G = nx.relabel_nodes(G, mapping)

        self.network = G
        return G

    def assign_network_blocks(self):
        """
        Populate each citizen's network_neighbors from the graph adjacency.

        Must call create_network() before this method.
        """
        for citizen in self.agents_active.values():
            citizen.network_neighbors = [
                self.agents_active[neighbor_id]
                for neighbor_id in self.network.neighbors(citizen.id)
            ]
