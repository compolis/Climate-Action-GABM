"""Tests for the pluggable network factory and diagnostics."""

import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import networkx as nx

from cag.abm.networks import (
    NETWORK_TYPES,
    DEFAULT_HOMOPHILY_ATTRIBUTES,
    build_network,
    compute_diagnostics,
)


# ── Helpers ────────────────────────────────────────────────────────

def _make_agents(n, exposure_split=("A-only", "B-only"), attrs=None):
    """Return a list of mock agents with .id, .political_exposure, plus
    any extra keyword attributes uniformly set."""
    agents = []
    for i in range(n):
        m = MagicMock()
        m.id = f"agent_{i:03d}"
        m.political_exposure = exposure_split[i % len(exposure_split)]
        for k, v in (attrs or {}).items():
            setattr(m, k, v[i] if isinstance(v, list) else v)
        agents.append(m)
    return agents


# ── Builder tests ──────────────────────────────────────────────────

class TestBuilders(unittest.TestCase):

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            build_network("not_a_real_type", _make_agents(5))

    def test_zero_agents_raises(self):
        with self.assertRaises(ValueError):
            build_network("erdos_renyi", [])

    def test_all_builders_return_graph_with_agent_id_nodes(self):
        agents = _make_agents(40, attrs={
            "ukge2019_vote_id": [i % 4 for i in range(40)],
            "brexit_vote_id":   [i % 3 for i in range(40)],
            "region_id":        [i % 5 for i in range(40)],
        })
        for net_type in NETWORK_TYPES:
            with self.subTest(net_type=net_type):
                params = self._sane_params(net_type)
                G = build_network(net_type, agents, params=params, seed=7)
                self.assertIsInstance(G, nx.Graph)
                self.assertEqual(G.number_of_nodes(), len(agents))
                self.assertEqual(set(G.nodes), {a.id for a in agents})

    def test_seed_reproducibility(self):
        agents = _make_agents(30, attrs={
            "ukge2019_vote_id": list(range(30)),
            "brexit_vote_id":   list(range(30)),
            "region_id":        list(range(30)),
        })
        for net_type in NETWORK_TYPES:
            with self.subTest(net_type=net_type):
                params = self._sane_params(net_type)
                G1 = build_network(net_type, agents, params=params, seed=42)
                G2 = build_network(net_type, agents, params=params, seed=42)
                self.assertEqual(set(G1.edges), set(G2.edges))

    def test_erdos_renyi_invalid_p(self):
        with self.assertRaises(ValueError):
            build_network("erdos_renyi", _make_agents(10), params={"p": 1.5})

    def test_watts_strogatz_invalid_k(self):
        with self.assertRaises(ValueError):
            build_network("watts_strogatz", _make_agents(20), params={"k": 3})

    def test_barabasi_albert_invalid_m(self):
        with self.assertRaises(ValueError):
            build_network("barabasi_albert", _make_agents(10), params={"m": 0})

    def test_homophily_weighted_perfect_homophily(self):
        # Two clusters with identical attributes inside, totally disjoint
        # across; high scale + low threshold ⇒ within-cluster nearly fully
        # connected, across-cluster nearly empty.
        n = 20
        agents = _make_agents(
            n,
            attrs={
                "ukge2019_vote_id": [0] * (n // 2) + [1] * (n // 2),
                "brexit_vote_id":   [0] * (n // 2) + [1] * (n // 2),
                "region_id":        [0] * (n // 2) + [1] * (n // 2),
            },
        )
        G = build_network(
            "homophily_weighted", agents,
            params={"scale": 20.0, "threshold": 5.0,
                    "attributes": list(DEFAULT_HOMOPHILY_ATTRIBUTES)},
            seed=0,
        )
        within = 0
        across = 0
        for u, v in G.edges:
            ui = int(u.split("_")[1]); vi = int(v.split("_")[1])
            same = (ui < n // 2) == (vi < n // 2)
            within += int(same)
            across += int(not same)
        self.assertGreater(within, across)

    def test_homophily_weighted_weight_mismatch(self):
        with self.assertRaises(ValueError):
            build_network(
                "homophily_weighted", _make_agents(5),
                params={"attributes": ["region_id"], "weights": [1.0, 2.0]},
            )

    def test_homophily_weighted_default_attributes_missing_ok(self):
        # Agents with all None attrs should still produce a valid (sparse) graph.
        agents = _make_agents(10, attrs={
            "ukge2019_vote_id": [None] * 10,
            "brexit_vote_id":   [None] * 10,
            "region_id":        [None] * 10,
        })
        G = build_network("homophily_weighted", agents,
                          params={"threshold": 0.0, "scale": 1.0}, seed=1)
        self.assertEqual(G.number_of_nodes(), 10)

    @staticmethod
    def _sane_params(net_type):
        return {
            "stochastic_block":   {"p_intra": 0.2, "p_inter": 0.02},
            "erdos_renyi":        {"p": 0.1},
            "watts_strogatz":     {"k": 4, "beta": 0.1},
            "barabasi_albert":    {"m": 2},
            "homophily_weighted": {"scale": 6.0, "threshold": 3.0},
        }[net_type]


# ── Diagnostics tests ──────────────────────────────────────────────

class TestDiagnostics(unittest.TestCase):

    def test_diagnostics_basic_keys(self):
        agents = _make_agents(30)
        G = build_network("erdos_renyi", agents, params={"p": 0.2}, seed=1)
        d = compute_diagnostics(G, agents=agents, timeout_s=10)
        for key in ("n_nodes", "n_edges", "density", "mean_degree",
                    "median_degree", "max_degree", "degree_histogram",
                    "n_connected_components", "largest_component_size",
                    "elapsed_s", "timed_out"):
            self.assertIn(key, d)
        self.assertEqual(d["n_nodes"], 30)
        self.assertFalse(d["timed_out"])

    def test_diagnostics_assortativity_present(self):
        agents = _make_agents(40, exposure_split=("A-only", "B-only"))
        G = build_network("stochastic_block", agents,
                          params={"p_intra": 0.5, "p_inter": 0.01}, seed=2)
        d = compute_diagnostics(G, agents=agents, timeout_s=10)
        # A strong SBM should be positively assortative on the splitting attr.
        self.assertIsNotNone(d["assortativity_political_exposure"])
        self.assertGreater(d["assortativity_political_exposure"], 0.3)

    def test_diagnostics_disconnected_handled(self):
        agents = _make_agents(20)
        G = nx.Graph()
        G.add_nodes_from(a.id for a in agents)  # zero edges → disconnected
        d = compute_diagnostics(G, agents=agents, timeout_s=10)
        self.assertEqual(d["n_connected_components"], 20)
        # Average path length / diameter computed on largest CC (size 1)
        # — they should still produce defensible (zero) values without error.
        self.assertIn("average_clustering", d)

    def test_diagnostics_timeout_zero_disables_cap(self):
        agents = _make_agents(15)
        G = build_network("erdos_renyi", agents, params={"p": 0.3}, seed=3)
        d = compute_diagnostics(G, agents=agents, timeout_s=0)
        self.assertFalse(d["timed_out"])


# ── Integration with SurveyedNation.create_network ─────────────────

class TestEnvironmentDispatch(unittest.TestCase):

    def _nation_with_exposure(self, n=30):
        from cag.abm.environment import SurveyedNation
        from cag.abm.agent import SurveyedCitizen, PoliticalAgent
        from cag.abm.democracy.elections.brexit import BrexitVoteID
        from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteID
        from gabm.abm.attributes.politics import PoliticsID

        sn = SurveyedNation()
        sn.political_agent_a = PoliticalAgent("agent_a", "pro_climate")
        sn.political_agent_b = PoliticalAgent("agent_b", "anti_climate")
        for i in range(n):
            c = SurveyedCitizen(
                agent_id=i, environment=sn,
                brexit_vote_id=BrexitVoteID.REMAIN if i % 2 == 0 else BrexitVoteID.LEAVE,
                ukge2019_vote_id=UKGE2019VoteID.LABOUR if i % 2 == 0 else UKGE2019VoteID.CONSERVATIVE,
                politics_id=PoliticsID.CENTRE,
            )
            sn.agents_active[c.id] = c
        sn.assign_political_exposure(mode="rule_priority_chain")
        return sn

    def test_default_call_still_builds_sbm(self):
        sn = self._nation_with_exposure()
        G = sn.create_network()
        self.assertIsInstance(G, nx.Graph)
        self.assertEqual(G.number_of_nodes(), 30)
        self.assertEqual(sn.network_type, "stochastic_block")

    def test_dispatch_to_erdos_renyi(self):
        sn = self._nation_with_exposure()
        G = sn.create_network(network_type="erdos_renyi",
                              network_params={"p": 0.1}, seed=1)
        self.assertEqual(G.number_of_nodes(), 30)
        self.assertEqual(sn.network_type, "erdos_renyi")
        sn.assign_network_blocks()
        for c in sn.agents_active.values():
            self.assertIsInstance(c.network_neighbors, list)

    def test_legacy_flat_kwargs_still_work(self):
        sn = self._nation_with_exposure()
        G = sn.create_network(p_intra=0.3, p_inter=0.05, seed=1)
        self.assertEqual(G.number_of_nodes(), 30)


if __name__ == "__main__":
    unittest.main()
