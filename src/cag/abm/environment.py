"""
Environment module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Ajaykumar Manivannan <ashwamanivannan@gmail.com>", "Andy Turner <agdturner@gmail.com>", "Charlie Pilgrim <pilgrimcharlie2@gmail.com>"]
__version__ = "0.2.0"
__copyright__ = "Copyright (c) 2026 GABM contributors, University of Leeds"

# Standard library imports
import logging
import random
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
from cag.abm.attributes.opinion import PACKAGE_SCOPE, ordinal_score

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
        self.message_log = []
        self.network = None
        self.political_agent_a = None
        self.political_agent_b = None

    def _log_message_event(self, **event):
        """Append a structured message event to the research log."""
        self.message_log.append(event)

    def run_baseline(self, api_key=None, model="gpt-5-mini", provider="openai", max_agents=5, thinking=False):
       
        baseline_rows = []
       
        agents = list(self.agents_active.values())[:max_agents]
        logging.info(f"Running baseline for {len(agents)} agents using model '{model}' and provider '{provider}'. If you want more agents then change max_agents in environment.run_baseline()")

        for agent in agents:
            agent_result = agent.run_baseline(api_key=api_key, model=model, provider=provider, thinking=thinking)
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
    
    def run_end_of_day_survey(self, policy_id, day, api_key=None, model="gpt-5-mini", provider="openai", temperature=0.5, thinking=False, debias=False):

        endofday_rows = []
        agents = list(self.agents_active.values())
        logging.info(f"Running end-of-day survey for {len(agents)} agents, policy {policy_id}, day {day}")

        for agent in agents:
            # Get previous opinion (last entry in history)
            history = agent.opinion_history.get(policy_id, [])
            previous_numeric = history[-1][1] if history else None

            letter, numeric = agent.administer_survey(
                policy_id=policy_id, day=day, api_key=api_key,
                model=model, provider=provider, temperature=temperature,
                thinking=thinking, debias=debias)

            shift = numeric - previous_numeric if previous_numeric is not None else 0
            logging.info(f"Agent {agent.id}: {letter} ({numeric:+d}), previous={previous_numeric}, shift={shift:+d}")

            endofday_rows.append({
                "agent_id": agent.id,
                "policy_id": str(policy_id),
                "day": day,
                "raw_letter": letter,
                "raw_numeric": numeric,
                "previous_numeric": previous_numeric,
                "shift": shift,
            })

        df = pd.DataFrame(endofday_rows)
        mean_shift = df["shift"].mean()
        logging.info(f"Mean shift: {mean_shift:+.2f}")

        shift_counts = df["shift"].value_counts().sort_index()
        logging.info(f"Shift distribution:\n{shift_counts.to_string()}")

        return df


    def assign_political_exposure(self):
        """
        Assign political exposure categories to all citizens based on voting
        history and political self-placement.

        The guiding principle is that **any directional political signal**
        means the citizen is exposed to political communication.  Only
        citizens with *zero* signal across Brexit vote, GE2019 vote, and
        left-right self-placement are assigned "neither".

        Literature reference: true political-information isolates comprise
        roughly 5-12 % of a UK sample (Prior 2007; Fletcher & Nielsen 2017).

        Priority rules (checked in order):

        CLEAR ECHO CHAMBER (both votes known, consistent):
         1. Leave + Conservative/Brexit             → "B-only"
         2. Remain + Labour/Green/LibDem            → "A-only"

        CROSS-PRESSURED (both votes known, contradictory):
         3. Leave + Labour/Green/LibDem             → "both"
         4. Remain + Conservative/Brexit            → "both"

        ONE KNOWN VOTE (partial signal):
         5. Leave + (DK/Other/Unknown GE)           → "both"
         6. Remain + (DK/Other/Unknown GE)          → "both"
         7. (DK/Unknown Brexit) + left party        → "both"
         8. (DK/Unknown Brexit) + right party       → "both"

        POLITICS-ONLY SIGNAL (no usable vote data):
         9. Any left-right self-placement (1-7)     → "both"

        TRULY DISENGAGED (zero directional signal):
        10. DK/Unknown across all three dimensions  → "neither"

        Also populates political_agent_a.connected_citizens and
        political_agent_b.connected_citizens.
        """
        left_parties = {UKGE2019VoteID.LABOUR, UKGE2019VoteID.GREEN,
                        UKGE2019VoteID.LIBERAL_DEMOCRATS}
        right_parties = {UKGE2019VoteID.CONSERVATIVE, UKGE2019VoteID.BREXIT}
        unknown_brexit = {BrexitVoteID.UNKNOWN, BrexitVoteID.DONT_KNOW}
        unknown_ge = {UKGE2019VoteID.UNKNOWN, UKGE2019VoteID.DONT_KNOW,
                      UKGE2019VoteID.OTHER}
        no_politics = {PoliticsID.UNKNOWN, PoliticsID.DONT_KNOW}

        a_citizens = []
        b_citizens = []

        for citizen in self.agents_active.values():
            brexit = citizen.brexit_vote_id
            ge = citizen.ukge2019_vote_id
            politics = citizen.politics_id

            # --- Rules 1-2: clear echo chamber ---
            if brexit == BrexitVoteID.LEAVE and ge in right_parties:
                exposure = "B-only"
            elif brexit == BrexitVoteID.REMAIN and ge in left_parties:
                exposure = "A-only"
            # --- Rules 3-4: cross-pressured ---
            elif brexit == BrexitVoteID.LEAVE and ge in left_parties:
                exposure = "both"
            elif brexit == BrexitVoteID.REMAIN and ge in right_parties:
                exposure = "both"
            # --- Rules 5-6: one known Brexit vote, GE unknown ---
            elif brexit == BrexitVoteID.LEAVE and ge in unknown_ge:
                exposure = "both"
            elif brexit == BrexitVoteID.REMAIN and ge in unknown_ge:
                exposure = "both"
            # --- Rules 7-8: Brexit unknown, one known party vote ---
            elif brexit in unknown_brexit and ge in left_parties:
                exposure = "both"
            elif brexit in unknown_brexit and ge in right_parties:
                exposure = "both"
            # --- Rule 9: politics-only signal ---
            elif politics not in no_politics:
                exposure = "both"
            # --- Rule 10: truly disengaged ---
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

    def apply_audience_cap(self, cap=None, seed=42):
        """
        Cap each political agent's audience to at most ``cap`` citizens by
        uniform random subsampling.

        Must be called *after* :meth:`assign_political_exposure` and
        *before* :meth:`apply_reach_subsample` so that ``reach`` is then
        a fraction of the *capped* (canonical) audience.

        Use this to neutralise the structural audience asymmetry that
        :meth:`assign_political_exposure` produces from the YouGov panel
        (e.g. A-audience = 27 vs B-audience = 20 at N=30) by setting
        ``cap = min(|A|, |B|)``. With both audiences capped to the same
        size, ``reach_a = reach_b = 1.0`` becomes a genuine symmetric
        baseline and (C1, C3) become true mirror conditions.

        Citizens are dropped uniformly at random from each agent's
        ``connected_citizens`` (independent draws per agent) using
        ``numpy.random.default_rng`` seeded by ``seed + 100`` (agent A)
        and ``seed + 101`` (agent B). Per-citizen ``political_exposure``
        labels are unchanged. Peer messaging is unaffected.

        Args:
            cap: maximum audience size for each political agent. If
                ``None`` or larger than the current audience, that side
                is left unchanged. Must be a non-negative integer.
            seed: base random seed; agent A draws use ``seed + 100``,
                agent B draws use ``seed + 101``.
        """
        if cap is None:
            return
        if not isinstance(cap, int) or cap < 0:
            raise ValueError(
                f"audience_cap must be a non-negative int or None, got {cap!r}"
            )

        import numpy as _np

        for agent, side_seed_offset in (
            (self.political_agent_a, 100),
            (self.political_agent_b, 101),
        ):
            if agent is None:
                continue
            full = list(agent.connected_citizens)
            if cap >= len(full):
                logging.info(
                    f"Audience cap: {agent.id} audience "
                    f"{len(full)}/{len(full)} (cap={cap}, no trim needed)"
                )
                continue
            rng = _np.random.default_rng(int(seed) + side_seed_offset)
            idx = rng.choice(len(full), size=cap, replace=False)
            agent.connected_citizens = [full[i] for i in sorted(idx)]
            logging.info(
                f"Audience cap: {agent.id} audience "
                f"{len(agent.connected_citizens)}/{len(full)} (cap={cap})"
            )

    def apply_reach_subsample(self, reach_a=1.0, reach_b=1.0, seed=42):
        """
        Subsample each political agent's audience to model broadcast reach
        asymmetry.

        Must be called *after* :meth:`assign_political_exposure`. Replaces
        ``political_agent_{a,b}.connected_citizens`` with a deterministic
        subset of size ``floor(reach * len(connected))``. Citizens are
        chosen uniformly without replacement using NumPy's
        ``default_rng`` seeded by ``seed`` (agent A) and ``seed + 1``
        (agent B), so the two sides draw independently and the result
        is reproducible.

        ``political_exposure`` labels on citizens are *not* changed; only
        the broadcast audience that each political agent will address is
        narrowed. Peer-messaging is unaffected.

        Args:
            reach_a: fraction in [0.0, 1.0] of A-audience reached by
                pro-climate political agent broadcasts.
            reach_b: fraction in [0.0, 1.0] of B-audience reached by
                anti-climate political agent broadcasts.
            seed: base random seed; agent A uses ``seed``, agent B uses
                ``seed + 1``.
        """
        for name, val in (("reach_a", reach_a), ("reach_b", reach_b)):
            if not (0.0 <= float(val) <= 1.0):
                raise ValueError(
                    f"{name} must be in [0.0, 1.0], got {val!r}"
                )

        import numpy as _np

        if self.political_agent_a is not None:
            full_a = list(self.political_agent_a.connected_citizens)
            n_a = int(len(full_a) * float(reach_a))
            if reach_a < 1.0 and n_a < len(full_a):
                rng_a = _np.random.default_rng(int(seed))
                idx = rng_a.choice(len(full_a), size=n_a, replace=False)
                self.political_agent_a.connected_citizens = [full_a[i] for i in sorted(idx)]
            logging.info(
                f"Reach subsample: agent_a audience "
                f"{len(self.political_agent_a.connected_citizens)}/{len(full_a)} "
                f"(reach_a={reach_a})"
            )

        if self.political_agent_b is not None:
            full_b = list(self.political_agent_b.connected_citizens)
            n_b = int(len(full_b) * float(reach_b))
            if reach_b < 1.0 and n_b < len(full_b):
                rng_b = _np.random.default_rng(int(seed) + 1)
                idx = rng_b.choice(len(full_b), size=n_b, replace=False)
                self.political_agent_b.connected_citizens = [full_b[i] for i in sorted(idx)]
            logging.info(
                f"Reach subsample: agent_b audience "
                f"{len(self.political_agent_b.connected_citizens)}/{len(full_b)} "
                f"(reach_b={reach_b})"
            )

    def create_network(
        self,
        network_type="stochastic_block",
        network_params=None,
        seed=42,
        # Back-compat: legacy flat keyword arguments
        n_blocks=None,
        p_intra=None,
        p_inter=None,
    ):
        """Create the peer-messaging network using the pluggable factory.

        Must call assign_political_exposure() before this method.

        Parameters
        ----------
        network_type : str
            One of :data:`cag.abm.networks.NETWORK_TYPES`.
            Default ``"stochastic_block"`` preserves v0.5 behaviour.
        network_params : dict | None
            Type-specific parameters. See :mod:`cag.abm.networks` for each
            builder's accepted keys.
        seed : int
            Random seed.
        n_blocks, p_intra, p_inter : optional
            Deprecated flat-keyword form for ``stochastic_block`` only.
            If provided, they are folded into ``network_params`` and a
            DeprecationWarning is logged.

        Returns
        -------
        nx.Graph
            The created graph, also stored as ``self.network``.
        """
        from cag.abm.networks import build_network

        params = dict(network_params or {})

        # Legacy flat keys: fold in with a deprecation warning.
        legacy = {}
        if p_intra is not None:
            legacy["p_intra"] = p_intra
        if p_inter is not None:
            legacy["p_inter"] = p_inter
        if n_blocks is not None and int(n_blocks) != 2:
            logging.warning(
                "create_network: n_blocks=%r is no longer honoured; "
                "stochastic_block is fixed to 2 blocks driven by "
                "political_exposure.",
                n_blocks,
            )
        if legacy:
            logging.warning(
                "create_network: flat keyword args %s are deprecated; "
                "pass via network_params={...} instead.",
                list(legacy.keys()),
            )
            for k, v in legacy.items():
                params.setdefault(k, v)

        agents = list(self.agents_active.values())
        G = build_network(network_type, agents, params=params, seed=int(seed))

        self.network = G
        self.network_type = network_type
        self.network_params = params
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

    def run_political_broadcast(self, phase, policy_id, day, api_key=None,
                                model="gpt-5-mini", provider="openai",
                                temperature=0.5, thinking=False):
        """
        Run a political broadcast phase (P-A or P-B).

        The selected political agent generates one persuasive message about the
        target policy and delivers it to all its connected citizens.  Each
        receiving citizen produces a private reflection.

        Args:
            phase: "P-A" or "P-B".
            policy_id: The target ClimatePolicyID.
            day: Current simulation day number.
            api_key: LLM API key.
            model: LLM model identifier.
            provider: LLM provider ("openai" or "genai").
            temperature: Sampling temperature.

        Returns:
            dict with keys "message", "reflections_count", "sample_reflections".
        """
        if phase == "P-A":
            agent = self.political_agent_a
        elif phase == "P-B":
            agent = self.political_agent_b
        else:
            raise ValueError(f"phase must be 'P-A' or 'P-B', got '{phase}'")

        message = agent.generate_message(policy_id, api_key=api_key, model=model,
                                         provider=provider, temperature=temperature,
                                         thinking=thinking)

        reflections = []
        for citizen in agent.connected_citizens:
            self._log_message_event(
                day=day,
                phase=phase,
                message_type="political_broadcast",
                sender_type="political_agent",
                sender_id=agent.id,
                sender_side=agent.side,
                recipient_id=citizen.id,
                recipient_scope="broadcast",
                policy_id=policy_id,
                package_scope="",
                policy_ids=[],
                message_text=message,
            )
            reflection = citizen.receive_political_message(
                message, policy_id, phase, day,
                api_key=api_key, model=model, provider=provider,
                temperature=temperature, thinking=thinking,
            )
            reflections.append(reflection)

        logging.info(
            f"[{phase}] Day {day}: delivered message to "
            f"{len(reflections)} citizens. Message (first 120 chars): "
            f"{message[:120]}..."
        )
        if reflections:
            logging.info(f"[{phase}] Sample reflection: {reflections[0][:200]}...")

        return {
            "message": message,
            "reflections_count": len(reflections),
            "sample_reflections": reflections[:2],
        }

    def run_package_broadcast(self, phase, policy_ids, day, api_key=None,
                              model="gpt-5-mini", provider="openai",
                              temperature=0.5, thinking=False):
        """Run a bundled political broadcast over a package of policies."""
        if phase == "P-A":
            agent = self.political_agent_a
        elif phase == "P-B":
            agent = self.political_agent_b
        else:
            raise ValueError(f"phase must be 'P-A' or 'P-B', got '{phase}'")

        message = agent.generate_package_message(
            policy_ids, api_key=api_key, model=model,
            provider=provider, temperature=temperature,
            thinking=thinking,
        )

        reflections = []
        for citizen in agent.connected_citizens:
            self._log_message_event(
                day=day,
                phase=phase,
                message_type="political_broadcast",
                sender_type="political_agent",
                sender_id=agent.id,
                sender_side=agent.side,
                recipient_id=citizen.id,
                recipient_scope="broadcast",
                policy_id="",
                package_scope=PACKAGE_SCOPE,
                policy_ids=list(policy_ids),
                message_text=message,
            )
            reflection = citizen.receive_package_political_message(
                message, policy_ids, phase, day,
                api_key=api_key, model=model, provider=provider,
                temperature=temperature, thinking=thinking,
            )
            reflections.append(reflection)

        logging.info(
            f"[{phase}] Day {day}: delivered package message to "
            f"{len(reflections)} citizens. Message (first 120 chars): "
            f"{message[:120]}..."
        )
        if reflections:
            logging.info(f"[{phase}] Sample package reflection: {reflections[0][:200]}...")

        return {
            "message": message,
            "reflections_count": len(reflections),
            "sample_reflections": reflections[:2],
        }

    def run_peer_messaging(self, policy_id, day, k_peers=3, api_key=None,
                           model="gpt-5-mini", provider="openai",
                           temperature=0.5, thinking=False):
        """
        Run the peer messaging phase (C) with simultaneous update.

        Step 1: Select random neighbors for each citizen.
        Step 2: ALL citizens generate their messages BEFORE any reflections.
        Step 3: Deliver messages and have each recipient reflect.

        Args:
            policy_id: The target ClimatePolicyID.
            day: Current simulation day number.
            k_peers: Max number of peers each citizen exchanges messages with.
            api_key: LLM API key.
            model: LLM model identifier.
            provider: LLM provider.
            temperature: Sampling temperature.

        Returns:
            dict with keys "messages_generated", "reflections_count",
            "sample_messages", "sample_reflections".
        """
        # Step 1: Select neighbors for each citizen
        selections = {}  # citizen_id -> list of neighbor citizen objects
        for citizen in self.agents_active.values():
            if not citizen.network_neighbors:
                continue
            k = min(k_peers, len(citizen.network_neighbors))
            selections[citizen.id] = random.sample(citizen.network_neighbors, k)

        # Step 2: Generate ALL messages first (simultaneous update)
        generated_messages = {}  # citizen_id -> message text
        for cid in selections:
            citizen = self.agents_active[cid]
            msg = citizen.generate_peer_message(
                policy_id, day=day, api_key=api_key, model=model,
                provider=provider, temperature=temperature,
                thinking=thinking,
            )
            generated_messages[cid] = msg

        # Step 3: Build inbox (which messages each citizen receives) and reflect
        inbox = {}  # citizen_id -> list of message strings
        for sender_id, neighbors in selections.items():
            for neighbor in neighbors:
                self._log_message_event(
                    day=day,
                    phase="C",
                    message_type="peer_message",
                    sender_type="citizen",
                    sender_id=sender_id,
                    sender_side="",
                    recipient_id=neighbor.id,
                    recipient_scope="direct",
                    policy_id=policy_id,
                    package_scope="",
                    policy_ids=[],
                    message_text=generated_messages[sender_id],
                )
                inbox.setdefault(neighbor.id, []).append(
                    generated_messages[sender_id]
                )

        reflections = []
        for recipient_id, messages in inbox.items():
            citizen = self.agents_active[recipient_id]
            reflection = citizen.receive_peer_messages(
                messages, policy_id, day,
                api_key=api_key, model=model, provider=provider,
                temperature=temperature, thinking=thinking,
            )
            reflections.append(reflection)

        sample_msgs = list(generated_messages.values())[:2]
        logging.info(
            f"[C] Day {day}: {len(generated_messages)} citizens generated "
            f"messages, {len(reflections)} citizens reflected."
        )
        if sample_msgs:
            logging.info(f"[C] Sample message: {sample_msgs[0][:200]}...")

        return {
            "messages_generated": len(generated_messages),
            "reflections_count": len(reflections),
            "sample_messages": sample_msgs,
            "sample_reflections": reflections[:2],
        }

    def run_package_peer_messaging(self, policy_ids, day, k_peers=3,
                                   api_key=None, model="gpt-5-mini",
                                   provider="openai", temperature=0.5,
                                   thinking=False):
        """Run simultaneous peer messaging about a bundled policy package."""
        selections = {}
        for citizen in self.agents_active.values():
            if not citizen.network_neighbors:
                continue
            k = min(k_peers, len(citizen.network_neighbors))
            selections[citizen.id] = random.sample(citizen.network_neighbors, k)

        generated_messages = {}
        for cid in selections:
            citizen = self.agents_active[cid]
            msg = citizen.generate_package_peer_message(
                policy_ids, day=day, api_key=api_key, model=model,
                provider=provider, temperature=temperature,
                thinking=thinking,
            )
            generated_messages[cid] = msg

        inbox = {}
        for sender_id, neighbors in selections.items():
            for neighbor in neighbors:
                self._log_message_event(
                    day=day,
                    phase="C",
                    message_type="peer_message",
                    sender_type="citizen",
                    sender_id=sender_id,
                    sender_side="",
                    recipient_id=neighbor.id,
                    recipient_scope="direct",
                    policy_id="",
                    package_scope=PACKAGE_SCOPE,
                    policy_ids=list(policy_ids),
                    message_text=generated_messages[sender_id],
                )
                inbox.setdefault(neighbor.id, []).append(generated_messages[sender_id])

        reflections = []
        for recipient_id, messages in inbox.items():
            citizen = self.agents_active[recipient_id]
            reflection = citizen.receive_package_peer_messages(
                messages, policy_ids, day,
                api_key=api_key, model=model, provider=provider,
                temperature=temperature, thinking=thinking,
            )
            reflections.append(reflection)

        sample_msgs = list(generated_messages.values())[:2]
        logging.info(
            f"[C] Day {day}: {len(generated_messages)} citizens generated "
            f"package messages, {len(reflections)} citizens reflected."
        )
        if sample_msgs:
            logging.info(f"[C] Sample package message: {sample_msgs[0][:200]}...")

        return {
            "messages_generated": len(generated_messages),
            "reflections_count": len(reflections),
            "sample_messages": sample_msgs,
            "sample_reflections": reflections[:2],
        }
