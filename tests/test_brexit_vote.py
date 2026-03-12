
import sys
import os
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from cag.abm.democracy.elections.brexit import BrexitVoteID, BrexitVote, BrexitVoteMap
from gabm.abm.democracy.election import ElectionID

class TestBrexitVote(unittest.TestCase):
    def setUp(self):
        self.election_id = ElectionID(1)
        self.vote_map = BrexitVoteMap(self.election_id)

    def test_vote_id_mapping(self):
        self.assertEqual(self.vote_map.get(BrexitVoteID.REMAIN).description, "Remain")
        self.assertEqual(self.vote_map.get(BrexitVoteID.LEAVE).description, "Leave")
        self.assertEqual(self.vote_map.get(BrexitVoteID.UNKNOWN).description, "Unknown")
        self.assertEqual(self.vote_map.get(BrexitVoteID.DONT_KNOW).description, "Don't know")

    def test_invalid_vote_id(self):
        class DummyVoteID:
            pass
        with self.assertRaises(TypeError):
            self.vote_map.get(DummyVoteID())

    def test_vote_object(self):
        vote = BrexitVote(BrexitVoteID.LEAVE, self.election_id, description="Leave")
        self.assertEqual(vote.description, "Leave")
        self.assertEqual(getattr(vote, 'vote_id', getattr(vote, 'id', None)), BrexitVoteID.LEAVE)
        self.assertEqual(vote.election_id, self.election_id)

if __name__ == "__main__":
    unittest.main()
