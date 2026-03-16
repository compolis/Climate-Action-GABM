
import sys
import os
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteID, UKGE2019Vote, UKGE2019VoteMap
from gabm.abm.democracy.election import ElectionID

class TestUKGE2019Vote(unittest.TestCase):
    def setUp(self):
        self.election_id = ElectionID(0)
        self.vote_map = UKGE2019VoteMap(self.election_id)

    def test_vote_id_mapping(self):
        self.assertEqual(self.vote_map.get(UKGE2019VoteID.CONSERVATIVE).description, "Conservative")
        self.assertEqual(self.vote_map.get(UKGE2019VoteID.LABOUR).description, "Labour")
        self.assertEqual(self.vote_map.get(UKGE2019VoteID.UNKNOWN).description, "unknown")
        self.assertEqual(self.vote_map.get(UKGE2019VoteID.DONT_KNOW).description, "don't know")

    def test_invalid_vote_id(self):
        class DummyVoteID:
            pass
        with self.assertRaises(TypeError):
            self.vote_map.get(DummyVoteID())

    def test_vote_object(self):
        vote = UKGE2019Vote(UKGE2019VoteID.LABOUR, "Labour", self.election_id)
        self.assertEqual(vote.description, "Labour")
        self.assertEqual(getattr(vote, 'vote_id', getattr(vote, 'id', None)), UKGE2019VoteID.LABOUR)
        self.assertEqual(vote.election_id, self.election_id)

if __name__ == "__main__":
    unittest.main()
