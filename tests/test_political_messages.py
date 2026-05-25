"""
Tests for the offline political message pool loader
(``cag.abm.political_messages``).

Covers:
- CSV schema load and provenance validation
- Deterministic per-cell shuffle and cursor rotation
- Distinctness across consecutive broadcasts in the same cell
- Wrap-around behaviour after a full cycle
- Missing-cell and malformed-row errors
- The shipped v1 dataset loads and contains all 12 single-policy cells
  plus 2 package cells with the expected sizes
"""
import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cag.abm.political_messages import (
    MessagePool,
    MessagePoolError,
    PACKAGE_KEY,
    REQUIRED_MESSAGE_COLUMNS,
    REQUIRED_SOURCE_COLUMNS,
    load_message_pool,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "political_messages"


def _write_csv(path: Path, header: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(header), quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _minimal_sources_row(source_id: str, policy_id: int, side: str) -> dict:
    return {
        "source_id": source_id, "policy_id": str(policy_id), "side": side,
        "party_name": "Test Party", "speaker": "Tester", "speaker_role": "Role",
        "date": "2026-01-01", "venue": "Test", "citation_url": "",
        "quote_text": "Q", "manifesto_or_hansard_ref": "", "notes": "",
    }


def _minimal_message_row(
    message_id: str, policy_key: str, side: str, text: str,
    *, source_type: str = "llm_generated",
    provenance_refs: str = "",
) -> dict:
    return {
        "message_id": message_id, "policy_id": policy_key, "side": side,
        "message_text": text, "source_type": source_type,
        "provenance_refs": provenance_refs,
        "generation_method": "test", "length_words": str(len(text.split())),
        "version": "test", "notes": "",
    }


class TestSyntheticPool(unittest.TestCase):
    """Round-trip tests against a tiny hand-built dataset in a tmp dir."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.set_id = "tiny"

        sources = [
            _minimal_sources_row("A_01_01", 1, "A"),
            _minimal_sources_row("A_01_02", 1, "A"),
            _minimal_sources_row("B_01_01", 1, "B"),
            _minimal_sources_row("B_01_02", 1, "B"),
        ]
        prov_A = "A_01_01;A_01_02"
        prov_B = "B_01_01;B_01_02"
        messages = [
            _minimal_message_row("A_01_01", "1", "A", "alpha one",
                                 source_type="verbatim_summary",
                                 provenance_refs=prov_A),
            _minimal_message_row("A_01_02", "1", "A", "alpha two",
                                 provenance_refs=prov_A),
            _minimal_message_row("A_01_03", "1", "A", "alpha three",
                                 provenance_refs=prov_A),
            _minimal_message_row("B_01_01", "1", "B", "beta one",
                                 source_type="verbatim_summary",
                                 provenance_refs=prov_B),
            _minimal_message_row("B_01_02", "1", "B", "beta two",
                                 provenance_refs=prov_B),
        ]

        _write_csv(self.root / f"sources_{self.set_id}.csv",
                   REQUIRED_SOURCE_COLUMNS, sources)
        _write_csv(self.root / f"messages_{self.set_id}.csv",
                   REQUIRED_MESSAGE_COLUMNS, messages)

    def tearDown(self):
        self.tmp.cleanup()

    def _load(self, seed: int = 0) -> MessagePool:
        return load_message_pool(self.set_id, seed=seed, data_root=self.root)

    def test_loads_with_correct_cell_sizes(self):
        pool = self._load()
        self.assertTrue(pool.has_cell("A", 1))
        self.assertTrue(pool.has_cell("B", 1))
        self.assertEqual(pool.cell_size("A", 1), 3)
        self.assertEqual(pool.cell_size("B", 1), 2)
        self.assertEqual(len(pool.sources), 4)

    def test_next_advances_cursor_and_wraps(self):
        pool = self._load(seed=42)
        seen = [pool.next("A", 1) for _ in range(6)]
        # First three should be a permutation of the three messages.
        ids_cycle1 = [mid for mid, _ in seen[:3]]
        ids_cycle2 = [mid for mid, _ in seen[3:]]
        self.assertEqual(sorted(ids_cycle1),
                         ["A_01_01", "A_01_02", "A_01_03"])
        # Wrap-around: second cycle should match first cycle's order.
        self.assertEqual(ids_cycle1, ids_cycle2)

    def test_deterministic_under_same_seed(self):
        a = [self._load(seed=7).next("A", 1)[0] for _ in range(3)]
        b = [self._load(seed=7).next("A", 1)[0] for _ in range(3)]
        self.assertEqual(a, b)

    def test_different_seeds_yield_different_orders(self):
        # Cell of size 3 has 6 permutations; with two distinct seeds we
        # expect a different sequence for at least one of several pairs.
        seqs = []
        for s in (1, 2, 3, 4, 5):
            seqs.append(tuple(self._load(seed=s).next("A", 1)[0] for _ in range(3)))
        self.assertGreater(len(set(seqs)), 1)

    def test_seed_11_has_stable_expected_order(self):
        pool = self._load(seed=11)
        seq = tuple(pool.next("A", 1)[0] for _ in range(3))
        self.assertEqual(seq, ("A_01_03", "A_01_02", "A_01_01"))

    def test_peek_does_not_advance(self):
        pool = self._load(seed=0)
        first = pool.peek("A", 1)
        again = pool.peek("A", 1)
        self.assertEqual(first, again)
        next_call = pool.next("A", 1)
        self.assertEqual(next_call, first)

    def test_consecutive_broadcasts_distinct_within_cycle(self):
        pool = self._load(seed=0)
        cycle = {pool.next("A", 1)[0] for _ in range(pool.cell_size("A", 1))}
        self.assertEqual(len(cycle), 3)

    def test_missing_cell_raises_in_validate(self):
        pool = self._load()
        with self.assertRaises(MessagePoolError):
            pool.validate_required(("A", "B"), (1, 2))

    def test_present_cells_pass_validate(self):
        pool = self._load()
        pool.validate_required(("A", "B"), (1,))  # should not raise

    def test_next_on_unknown_cell_raises(self):
        pool = self._load()
        with self.assertRaises(MessagePoolError):
            pool.next("A", 99)

    def test_get_record_returns_full_metadata(self):
        pool = self._load()
        rec = pool.get_record("A_01_01")
        self.assertEqual(rec.side, "A")
        self.assertEqual(rec.policy_key, "1")
        self.assertEqual(rec.source_type, "verbatim_summary")
        self.assertEqual(rec.provenance_refs, ("A_01_01", "A_01_02"))


class TestProvenanceValidation(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.set_id = "bad"

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, sources: list[dict], messages: list[dict]) -> None:
        _write_csv(self.root / f"sources_{self.set_id}.csv",
                   REQUIRED_SOURCE_COLUMNS, sources)
        _write_csv(self.root / f"messages_{self.set_id}.csv",
                   REQUIRED_MESSAGE_COLUMNS, messages)

    def test_unknown_provenance_ref_raises(self):
        self._write(
            sources=[_minimal_sources_row("A_01_01", 1, "A")],
            messages=[_minimal_message_row(
                "A_01_01", "1", "A", "x",
                provenance_refs="A_01_01;A_99_99",
            )],
        )
        with self.assertRaises(MessagePoolError):
            load_message_pool(self.set_id, data_root=self.root)

    def test_duplicate_message_id_raises(self):
        self._write(
            sources=[_minimal_sources_row("A_01_01", 1, "A")],
            messages=[
                _minimal_message_row("A_01_01", "1", "A", "x",
                                     provenance_refs="A_01_01"),
                _minimal_message_row("A_01_01", "1", "A", "y",
                                     provenance_refs="A_01_01"),
            ],
        )
        with self.assertRaises(MessagePoolError):
            load_message_pool(self.set_id, data_root=self.root)

    def test_bad_side_raises(self):
        self._write(
            sources=[_minimal_sources_row("A_01_01", 1, "A")],
            messages=[_minimal_message_row(
                "A_01_01", "1", "C", "x",
                provenance_refs="A_01_01",
            )],
        )
        with self.assertRaises(MessagePoolError):
            load_message_pool(self.set_id, data_root=self.root)

    def test_bad_source_type_raises(self):
        self._write(
            sources=[_minimal_sources_row("A_01_01", 1, "A")],
            messages=[_minimal_message_row(
                "A_01_01", "1", "A", "x",
                source_type="hand_written",
                provenance_refs="A_01_01",
            )],
        )
        with self.assertRaises(MessagePoolError):
            load_message_pool(self.set_id, data_root=self.root)

    def test_missing_file_raises(self):
        with self.assertRaises(MessagePoolError):
            load_message_pool("does_not_exist", data_root=self.root)


@unittest.skipUnless(
    (DATA_DIR / "messages_v1.csv").exists()
    and (DATA_DIR / "sources_v1.csv").exists(),
    "v1 dataset not present",
)
class TestShippedV1Dataset(unittest.TestCase):
    """Sanity checks against the real data/political_messages/*_v1.csv files."""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_message_pool("v1", seed=0, data_root=DATA_DIR)

    def test_has_all_12_single_policy_cells(self):
        for side in ("A", "B"):
            for pid in (1, 2, 3, 4, 5, 6):
                self.assertTrue(
                    self.pool.has_cell(side, pid),
                    f"Missing cell ({side}, {pid}) in v1 dataset.",
                )
                self.assertEqual(self.pool.cell_size(side, pid), 20)

    def test_has_two_package_cells(self):
        for side in ("A", "B"):
            self.assertTrue(self.pool.has_cell(side, PACKAGE_KEY))
            self.assertEqual(self.pool.cell_size(side, PACKAGE_KEY), 20)

    def test_validate_required_for_single_policy_run(self):
        # Should not raise for the full 6-policy x 2-side single-policy run.
        self.pool.validate_required(("A", "B"), (1, 2, 3, 4, 5, 6))

    def test_validate_required_for_package_run(self):
        self.pool.validate_required(("A", "B"), (1, 2, 3, 4, 5, 6),
                                    include_package=True)

    def test_sources_count(self):
        self.assertEqual(len(self.pool.sources), 24)

    def test_full_rotation_covers_every_message(self):
        # For cell ("A", 5) — carbon tax — cycling 20 times should hit
        # every message id exactly once.
        size = self.pool.cell_size("A", 5)
        seen = [self.pool.next("A", 5)[0] for _ in range(size)]
        self.assertEqual(len(set(seen)), size)


if __name__ == "__main__":
    unittest.main()
