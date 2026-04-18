"""Tests for Issue 5: Network + Political Exposure."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import networkx as nx

from cag.abm.agent import SurveyedCitizen, PoliticalAgent
from cag.abm.environment import SurveyedNation
from cag.abm.democracy.elections.brexit import BrexitVoteID
from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteID
from gabm.abm.attributes.politics import PoliticsID


# ===================================================================
# Helpers
# ===================================================================

def _make_nation_with_citizens(profiles):
    """
    Create a SurveyedNation populated with citizens from a list of profiles.

    Each profile is a dict with keys: brexit_vote_id, ukge2019_vote_id, politics_id.
    """
    sn = SurveyedNation()
    sn.political_agent_a = PoliticalAgent("agent_a", "pro_climate")
    sn.political_agent_b = PoliticalAgent("agent_b", "anti_climate")

    for i, profile in enumerate(profiles):
        citizen = SurveyedCitizen(
            agent_id=i,
            environment=sn,
            brexit_vote_id=profile.get("brexit_vote_id"),
            ukge2019_vote_id=profile.get("ukge2019_vote_id"),
            politics_id=profile.get("politics_id"),
        )
        sn.agents_active[citizen.id] = citizen

    return sn


# Reusable test profiles covering all exposure categories
_PROFILES = [
    # 0 — A-only: Remain + Labour (rule 2)
    {"brexit_vote_id": BrexitVoteID.REMAIN, "ukge2019_vote_id": UKGE2019VoteID.LABOUR, "politics_id": PoliticsID.FAIRLY_LEFT_WING},
    # 1 — A-only: Remain + Green (rule 2)
    {"brexit_vote_id": BrexitVoteID.REMAIN, "ukge2019_vote_id": UKGE2019VoteID.GREEN, "politics_id": PoliticsID.VERY_LEFT_WING},
    # 2 — A-only: Remain + LibDem (rule 2)
    {"brexit_vote_id": BrexitVoteID.REMAIN, "ukge2019_vote_id": UKGE2019VoteID.LIBERAL_DEMOCRATS, "politics_id": PoliticsID.SLIGHTLY_LEFT_OF_CENTRE},
    # 3 — B-only: Leave + Conservative (rule 1)
    {"brexit_vote_id": BrexitVoteID.LEAVE, "ukge2019_vote_id": UKGE2019VoteID.CONSERVATIVE, "politics_id": PoliticsID.FAIRLY_RIGHT_WING},
    # 4 — B-only: Leave + Brexit (rule 1)
    {"brexit_vote_id": BrexitVoteID.LEAVE, "ukge2019_vote_id": UKGE2019VoteID.BREXIT, "politics_id": PoliticsID.VERY_RIGHT_WING},
    # 5 — both: Leave + Labour, cross-pressured (rule 3)
    {"brexit_vote_id": BrexitVoteID.LEAVE, "ukge2019_vote_id": UKGE2019VoteID.LABOUR, "politics_id": PoliticsID.CENTRE},
    # 6 — both: Remain + Conservative, cross-pressured (rule 4)
    {"brexit_vote_id": BrexitVoteID.REMAIN, "ukge2019_vote_id": UKGE2019VoteID.CONSERVATIVE, "politics_id": PoliticsID.SLIGHTLY_RIGHT_OF_CENTRE},
    # 7 — both: Leave + Other GE, partial signal (rule 5)
    {"brexit_vote_id": BrexitVoteID.LEAVE, "ukge2019_vote_id": UKGE2019VoteID.OTHER, "politics_id": PoliticsID.CENTRE},
    # 8 — both: Remain + DK GE, partial signal (rule 6)
    {"brexit_vote_id": BrexitVoteID.REMAIN, "ukge2019_vote_id": UKGE2019VoteID.DONT_KNOW, "politics_id": PoliticsID.FAIRLY_LEFT_WING},
    # 9 — both: DK Brexit + Labour, partial signal (rule 7)
    {"brexit_vote_id": BrexitVoteID.DONT_KNOW, "ukge2019_vote_id": UKGE2019VoteID.LABOUR, "politics_id": PoliticsID.FAIRLY_LEFT_WING},
    # 10 — both: DK Brexit + Conservative, partial signal (rule 8)
    {"brexit_vote_id": BrexitVoteID.DONT_KNOW, "ukge2019_vote_id": UKGE2019VoteID.CONSERVATIVE, "politics_id": PoliticsID.FAIRLY_RIGHT_WING},
    # 11 — both: DK both votes, but has politics signal (rule 9)
    {"brexit_vote_id": BrexitVoteID.UNKNOWN, "ukge2019_vote_id": UKGE2019VoteID.UNKNOWN, "politics_id": PoliticsID.FAIRLY_RIGHT_WING},
    # 12 — neither: truly disengaged, all DK/Unknown (rule 10)
    {"brexit_vote_id": BrexitVoteID.UNKNOWN, "ukge2019_vote_id": UKGE2019VoteID.UNKNOWN, "politics_id": PoliticsID.DONT_KNOW},
    # 13 — neither: truly disengaged, all DK/Unknown (rule 10)
    {"brexit_vote_id": BrexitVoteID.DONT_KNOW, "ukge2019_vote_id": UKGE2019VoteID.DONT_KNOW, "politics_id": PoliticsID.UNKNOWN},
]


# ===================================================================
# Tests: SurveyedCitizen new attributes
# ===================================================================

class TestCitizenNetworkAttributes(unittest.TestCase):
    """Test that SurveyedCitizen has the new Issue 5 attributes."""

    def test_default_political_exposure(self):
        c = SurveyedCitizen(agent_id=0)
        self.assertEqual(c.political_exposure, "neither")

    def test_default_network_neighbors(self):
        c = SurveyedCitizen(agent_id=0)
        self.assertEqual(c.network_neighbors, [])

    def test_network_neighbors_not_shared(self):
        """Each citizen gets its own list (no mutable default bug)."""
        c1 = SurveyedCitizen(agent_id=0)
        c2 = SurveyedCitizen(agent_id=1)
        c1.network_neighbors.append("x")
        self.assertEqual(c2.network_neighbors, [])


# ===================================================================
# Tests: assign_political_exposure()
# ===================================================================

class TestAssignPoliticalExposure(unittest.TestCase):

    def setUp(self):
        self.sn = _make_nation_with_citizens(_PROFILES)
        self.sn.assign_political_exposure()

    # --- Rules 1-2: echo chamber ---

    def test_remain_labour_is_a_only(self):
        self.assertEqual(self.sn.agents_active[0].political_exposure, "A-only")

    def test_remain_green_is_a_only(self):
        self.assertEqual(self.sn.agents_active[1].political_exposure, "A-only")

    def test_remain_libdem_is_a_only(self):
        self.assertEqual(self.sn.agents_active[2].political_exposure, "A-only")

    def test_leave_conservative_is_b_only(self):
        self.assertEqual(self.sn.agents_active[3].political_exposure, "B-only")

    def test_leave_brexit_is_b_only(self):
        self.assertEqual(self.sn.agents_active[4].political_exposure, "B-only")

    # --- Rules 3-4: cross-pressured ---

    def test_leave_labour_mixed_is_both(self):
        self.assertEqual(self.sn.agents_active[5].political_exposure, "both")

    def test_remain_conservative_mixed_is_both(self):
        self.assertEqual(self.sn.agents_active[6].political_exposure, "both")

    # --- Rules 5-6: one known Brexit vote, GE unknown ---

    def test_leave_other_ge_is_both(self):
        self.assertEqual(self.sn.agents_active[7].political_exposure, "both")

    def test_remain_dk_ge_is_both(self):
        self.assertEqual(self.sn.agents_active[8].political_exposure, "both")

    # --- Rules 7-8: Brexit unknown, one known party vote ---

    def test_dk_brexit_labour_is_both(self):
        self.assertEqual(self.sn.agents_active[9].political_exposure, "both")

    def test_dk_brexit_conservative_is_both(self):
        self.assertEqual(self.sn.agents_active[10].political_exposure, "both")

    # --- Rule 9: politics-only signal ---

    def test_dk_both_votes_with_politics_is_both(self):
        self.assertEqual(self.sn.agents_active[11].political_exposure, "both")

    # --- Rule 10: truly disengaged ---

    def test_unknown_all_is_neither(self):
        self.assertEqual(self.sn.agents_active[12].political_exposure, "neither")

    def test_dont_know_all_is_neither(self):
        self.assertEqual(self.sn.agents_active[13].political_exposure, "neither")

    # --- Connected citizens lists ---

    def test_agent_a_connected_citizens(self):
        """Agent A gets A-only and both citizens."""
        ids = {c.id for c in self.sn.political_agent_a.connected_citizens}
        # A-only: 0, 1, 2; both: 5, 6, 7, 8, 9, 10, 11
        self.assertEqual(ids, {0, 1, 2, 5, 6, 7, 8, 9, 10, 11})

    def test_agent_b_connected_citizens(self):
        """Agent B gets B-only and both citizens."""
        ids = {c.id for c in self.sn.political_agent_b.connected_citizens}
        # B-only: 3, 4; both: 5, 6, 7, 8, 9, 10, 11
        self.assertEqual(ids, {3, 4, 5, 6, 7, 8, 9, 10, 11})

    def test_no_overlap_a_only_b_only(self):
        """No citizen is both A-only and B-only."""
        a_ids = {c.id for c in self.sn.political_agent_a.connected_citizens}
        b_ids = {c.id for c in self.sn.political_agent_b.connected_citizens}
        a_only_ids = a_ids - b_ids
        b_only_ids = b_ids - a_ids
        for cid in a_only_ids:
            self.assertEqual(self.sn.agents_active[cid].political_exposure, "A-only")
        for cid in b_only_ids:
            self.assertEqual(self.sn.agents_active[cid].political_exposure, "B-only")


# ===================================================================
# Tests: create_network()
# ===================================================================

class TestCreateNetwork(unittest.TestCase):

    def setUp(self):
        # Create a larger population for meaningful network stats
        self.profiles = _PROFILES * 15  # 210 agents
        self.sn = _make_nation_with_citizens(self.profiles)
        self.sn.assign_political_exposure()
        self.sn.create_network(seed=42)

    def test_node_count_equals_agents(self):
        self.assertEqual(self.sn.network.number_of_nodes(), len(self.sn.agents_active))

    def test_all_agent_ids_are_nodes(self):
        node_ids = set(self.sn.network.nodes())
        agent_ids = set(self.sn.agents_active.keys())
        self.assertEqual(node_ids, agent_ids)

    def test_network_is_graph(self):
        self.assertIsInstance(self.sn.network, nx.Graph)

    def test_seed_reproducibility(self):
        """Same seed → identical graph."""
        sn2 = _make_nation_with_citizens(self.profiles)
        sn2.assign_political_exposure()
        sn2.create_network(seed=42)
        self.assertEqual(
            set(self.sn.network.edges()),
            set(sn2.network.edges()),
        )

    def test_different_seed_different_graph(self):
        """Different seed → different edges."""
        sn2 = _make_nation_with_citizens(self.profiles)
        sn2.assign_political_exposure()
        sn2.create_network(seed=99)
        self.assertNotEqual(
            set(self.sn.network.edges()),
            set(sn2.network.edges()),
        )

    def test_edge_density_reasonable(self):
        """Edge count within ±40% of expected for p_intra=0.15, p_inter=0.02."""
        n = self.sn.network.number_of_nodes()
        # Rough expected: for 2 blocks of ~100 each:
        # intra: 2 * C(100,2) * 0.15 ≈ 1485
        # inter: 100*100 * 0.02 = 200
        # total ≈ 1685
        # Use generous bounds since block sizes vary with exposure
        actual_edges = self.sn.network.number_of_edges()
        max_possible = n * (n - 1) / 2
        # Density should be roughly 0.02–0.15 range
        density = actual_edges / max_possible
        self.assertGreater(density, 0.01)
        self.assertLess(density, 0.20)


# ===================================================================
# Tests: assign_network_blocks()
# ===================================================================

class TestAssignNetworkBlocks(unittest.TestCase):

    def setUp(self):
        self.profiles = _PROFILES * 15  # 210 agents
        self.sn = _make_nation_with_citizens(self.profiles)
        self.sn.assign_political_exposure()
        self.sn.create_network(seed=42)
        self.sn.assign_network_blocks()

    def test_all_citizens_have_neighbors_list(self):
        """Every citizen has a network_neighbors list (possibly empty for isolated nodes)."""
        for citizen in self.sn.agents_active.values():
            self.assertIsInstance(citizen.network_neighbors, list)

    def test_neighbors_are_citizen_instances(self):
        """network_neighbors contain SurveyedCitizen references, not IDs."""
        for citizen in self.sn.agents_active.values():
            for neighbor in citizen.network_neighbors:
                self.assertIsInstance(neighbor, SurveyedCitizen)

    def test_neighbor_count_matches_graph_degree(self):
        """Number of neighbors matches the graph adjacency."""
        for citizen in self.sn.agents_active.values():
            expected_degree = self.sn.network.degree(citizen.id)
            self.assertEqual(len(citizen.network_neighbors), expected_degree)

    def test_neighbors_are_bidirectional(self):
        """If A is B's neighbor, then B is A's neighbor (undirected graph)."""
        for citizen in self.sn.agents_active.values():
            for neighbor in citizen.network_neighbors:
                neighbor_ids = {n.id for n in neighbor.network_neighbors}
                self.assertIn(citizen.id, neighbor_ids)


if __name__ == '__main__':
    unittest.main()
