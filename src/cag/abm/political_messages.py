"""
Offline political message pool for Climate-Action-GABM.

Loads pre-authored political broadcast messages from CSV files in
``data/political_messages/`` and serves them to the simulator in a
deterministic, seeded rotation. Used when ``SIM_CONFIG["political_message_source"]``
is ``"offline"`` (the default).

The CSV files are produced by ``scripts/build_political_messages_v1.py``.
This module is read-only: it never writes to the data files.

Cell key convention:
    Single-policy cell: ``(side, str(policy_id))``  e.g. ``("A", "5")``
    Package cell:       ``(side, "PACKAGE")``

Sides:
    "A" -> pro-climate political agent (Green Party of England and Wales)
    "B" -> anti-climate political agent (Reform UK)

Determinism:
    At load time, each cell's message list is shuffled once using a
    seeded ``random.Random`` instance, with the seed mixed by the cell key.
    A per-cell cursor advances by one on every ``next()`` call and wraps
    around at the end of the list. Two runs with the same seed and the
    same data files produce the same sequence of messages.
"""

# Metadata
__author__ = ["Ajaykumar Manivannan <ashwamanivannan@gmail.com>"]
__version__ = "0.6.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import csv
import hashlib
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

# Default data root: <repo>/data/political_messages/
# Computed relative to this file: src/cag/abm/political_messages.py
# -> parents[3] is the repo root.
_DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[3] / "data" / "political_messages"

PACKAGE_KEY = "PACKAGE"

REQUIRED_MESSAGE_COLUMNS = (
    "message_id", "policy_id", "side", "message_text",
    "source_type", "provenance_refs",
    "generation_method", "length_words", "version", "notes",
)

REQUIRED_SOURCE_COLUMNS = (
    "source_id", "policy_id", "side", "party_name",
    "speaker", "speaker_role", "date", "venue",
    "citation_url", "quote_text", "manifesto_or_hansard_ref", "notes",
)


class MessagePoolError(RuntimeError):
    """Raised when the offline message pool cannot satisfy a request."""


@dataclass
class MessageRecord:
    """A single broadcast message row from messages_*.csv."""
    message_id: str
    policy_key: str       # str(policy_id) or "PACKAGE"
    side: str             # "A" or "B"
    message_text: str
    source_type: str      # "verbatim_summary" | "llm_generated"
    provenance_refs: tuple[str, ...]  # source_ids
    generation_method: str
    length_words: int
    version: str
    notes: str


@dataclass
class SourceRecord:
    """A single attributed source quote row from sources_*.csv."""
    source_id: str
    policy_id: int
    side: str
    party_name: str
    speaker: str
    speaker_role: str
    date: str
    venue: str
    citation_url: str
    quote_text: str
    manifesto_or_hansard_ref: str
    notes: str


@dataclass
class MessagePool:
    """
    In-memory pool of offline political messages with deterministic rotation.

    Use :func:`load_message_pool` to construct.
    """
    set_id: str
    messages_path: Path
    sources_path: Path
    seed: int
    # cell_key -> ordered list of MessageRecord (shuffled at load time)
    _cells: dict[tuple[str, str], list[MessageRecord]] = field(default_factory=dict)
    # cell_key -> next index to serve (wraps modulo len(cell))
    _cursors: dict[tuple[str, str], int] = field(default_factory=dict)
    # source_id -> SourceRecord (full provenance)
    sources: dict[str, SourceRecord] = field(default_factory=dict)

    # -- public API -------------------------------------------------------

    def has_cell(self, side: str, policy_key: int | str) -> bool:
        return self._cell_key(side, policy_key) in self._cells

    def cell_size(self, side: str, policy_key: int | str) -> int:
        return len(self._cells[self._cell_key(side, policy_key)])

    def cells(self) -> list[tuple[str, str]]:
        return list(self._cells.keys())

    def next(self, side: str, policy_key: int | str) -> tuple[str, str]:
        """
        Return ``(message_id, message_text)`` for the next message in the
        ``(side, policy_key)`` cell, advancing the cursor.

        ``policy_key`` may be an integer policy id (1..6) for single-policy
        broadcasts, or the literal string ``"PACKAGE"`` for the package mode.

        Raises :class:`MessagePoolError` if the cell is not loaded.
        """
        key = self._cell_key(side, policy_key)
        if key not in self._cells:
            raise MessagePoolError(
                f"No offline messages loaded for cell side={side!r} "
                f"policy={policy_key!r}. Available cells: {sorted(self._cells)}"
            )
        bucket = self._cells[key]
        idx = self._cursors[key]
        rec = bucket[idx]
        self._cursors[key] = (idx + 1) % len(bucket)
        return rec.message_id, rec.message_text

    def peek(self, side: str, policy_key: int | str) -> tuple[str, str]:
        """Return the next ``(message_id, message_text)`` without advancing."""
        key = self._cell_key(side, policy_key)
        if key not in self._cells:
            raise MessagePoolError(
                f"No offline messages loaded for cell side={side!r} "
                f"policy={policy_key!r}."
            )
        bucket = self._cells[key]
        rec = bucket[self._cursors[key]]
        return rec.message_id, rec.message_text

    def get_record(self, message_id: str) -> MessageRecord:
        """Return the full :class:`MessageRecord` for a given message id."""
        for bucket in self._cells.values():
            for rec in bucket:
                if rec.message_id == message_id:
                    return rec
        raise KeyError(message_id)

    def validate_required(
        self,
        sides: Iterable[str],
        policy_ids: Iterable[int],
        *,
        include_package: bool = False,
    ) -> None:
        """
        Raise :class:`MessagePoolError` if any required cell is missing or empty.

        Called at simulation start to fail fast rather than silently falling
        back to the LLM path.
        """
        missing: list[str] = []
        for side in sides:
            for pid in policy_ids:
                key = self._cell_key(side, pid)
                if key not in self._cells or not self._cells[key]:
                    missing.append(f"({side}, {pid})")
            if include_package:
                key = self._cell_key(side, PACKAGE_KEY)
                if key not in self._cells or not self._cells[key]:
                    missing.append(f"({side}, PACKAGE)")
        if missing:
            raise MessagePoolError(
                f"Offline message pool {self.set_id!r} is missing required "
                f"cells: {', '.join(missing)}. Source: {self.messages_path}"
            )

    # -- internals --------------------------------------------------------

    @staticmethod
    def _cell_key(side: str, policy_key) -> tuple[str, str]:
        """
        Normalise a policy key to ``(side, str)``.

        Accepts:
          - plain ``int``                       -> ``str(int)``
          - the literal string ``"PACKAGE"``    -> unchanged
          - a numeric ``str``                   -> validated, unchanged
          - any object with an ``.id`` attribute holding an int
            (e.g. ``ClimatePolicyID`` from :mod:`cag.abm.attributes.opinion`)
        """
        if isinstance(policy_key, str):
            return (side, policy_key)
        if isinstance(policy_key, int):
            return (side, str(policy_key))
        inner = getattr(policy_key, "id", None)
        if isinstance(inner, int):
            return (side, str(inner))
        raise TypeError(
            f"policy_key must be int, str, or have an int .id attribute; "
            f"got {type(policy_key).__name__}: {policy_key!r}"
        )


# ----------------------------------------------------------------------------
# Loader
# ----------------------------------------------------------------------------

def _resolve_paths(
    set_id: str,
    data_root: Path | str | None,
    messages_path: Path | str | None,
    sources_path: Path | str | None,
) -> tuple[Path, Path]:
    if messages_path is not None and sources_path is not None:
        return Path(messages_path), Path(sources_path)
    root = Path(data_root) if data_root is not None else _DEFAULT_DATA_ROOT
    msgs = Path(messages_path) if messages_path is not None else root / f"messages_{set_id}.csv"
    srcs = Path(sources_path) if sources_path is not None else root / f"sources_{set_id}.csv"
    return msgs, srcs


def _read_csv(path: Path, required_columns: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.exists():
        raise MessagePoolError(f"Required data file does not exist: {path}")
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise MessagePoolError(f"Empty or unreadable CSV: {path}")
        missing_cols = [c for c in required_columns if c not in reader.fieldnames]
        if missing_cols:
            raise MessagePoolError(
                f"CSV {path} is missing required columns: {missing_cols}. "
                f"Found: {reader.fieldnames}"
            )
        rows = list(reader)
    if not rows:
        raise MessagePoolError(f"CSV {path} has a header but no data rows.")
    return rows


def _parse_provenance(raw: str) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(";") if part.strip())


def _build_message_records(rows: list[dict[str, str]]) -> list[MessageRecord]:
    records: list[MessageRecord] = []
    seen_ids: set[str] = set()
    for i, row in enumerate(rows, start=2):  # +1 for header, +1 for 1-indexed
        mid = row["message_id"].strip()
        if not mid:
            raise MessagePoolError(f"Row {i}: empty message_id.")
        if mid in seen_ids:
            raise MessagePoolError(f"Row {i}: duplicate message_id {mid!r}.")
        seen_ids.add(mid)

        side = row["side"].strip()
        if side not in ("A", "B"):
            raise MessagePoolError(f"Row {i} ({mid}): side must be 'A' or 'B', got {side!r}.")

        policy_key = row["policy_id"].strip()
        if policy_key != PACKAGE_KEY:
            try:
                _ = int(policy_key)
            except ValueError as exc:
                raise MessagePoolError(
                    f"Row {i} ({mid}): policy_id must be an int or 'PACKAGE', got {policy_key!r}."
                ) from exc

        text = row["message_text"].strip()
        if not text:
            raise MessagePoolError(f"Row {i} ({mid}): empty message_text.")

        source_type = row["source_type"].strip()
        if source_type not in ("verbatim_summary", "llm_generated"):
            raise MessagePoolError(
                f"Row {i} ({mid}): source_type must be 'verbatim_summary' or "
                f"'llm_generated', got {source_type!r}."
            )

        try:
            length_words = int(row["length_words"]) if row["length_words"] else len(text.split())
        except ValueError as exc:
            raise MessagePoolError(
                f"Row {i} ({mid}): length_words must be an integer, got {row['length_words']!r}."
            ) from exc

        records.append(MessageRecord(
            message_id=mid,
            policy_key=policy_key,
            side=side,
            message_text=text,
            source_type=source_type,
            provenance_refs=_parse_provenance(row["provenance_refs"]),
            generation_method=row["generation_method"].strip(),
            length_words=length_words,
            version=row["version"].strip(),
            notes=row.get("notes", "").strip(),
        ))
    return records


def _build_source_records(rows: list[dict[str, str]]) -> dict[str, SourceRecord]:
    out: dict[str, SourceRecord] = {}
    for i, row in enumerate(rows, start=2):
        sid = row["source_id"].strip()
        if not sid:
            raise MessagePoolError(f"Sources row {i}: empty source_id.")
        if sid in out:
            raise MessagePoolError(f"Sources row {i}: duplicate source_id {sid!r}.")
        try:
            pid = int(row["policy_id"])
        except ValueError as exc:
            raise MessagePoolError(
                f"Sources row {i} ({sid}): policy_id must be an integer, got {row['policy_id']!r}."
            ) from exc
        out[sid] = SourceRecord(
            source_id=sid,
            policy_id=pid,
            side=row["side"].strip(),
            party_name=row["party_name"].strip(),
            speaker=row["speaker"].strip(),
            speaker_role=row["speaker_role"].strip(),
            date=row["date"].strip(),
            venue=row["venue"].strip(),
            citation_url=row["citation_url"].strip(),
            quote_text=row["quote_text"].strip(),
            manifesto_or_hansard_ref=row["manifesto_or_hansard_ref"].strip(),
            notes=row.get("notes", "").strip(),
        )
    return out


def _validate_provenance(
    records: list[MessageRecord],
    sources: dict[str, SourceRecord],
) -> None:
    for rec in records:
        for ref in rec.provenance_refs:
            if ref not in sources:
                raise MessagePoolError(
                    f"Message {rec.message_id!r} references unknown source_id "
                    f"{ref!r}. Available source_ids: {sorted(sources)[:8]}..."
                )


def _shuffle_cells(
    records: list[MessageRecord],
    seed: int,
) -> dict[tuple[str, str], list[MessageRecord]]:
    grouped: dict[tuple[str, str], list[MessageRecord]] = {}
    for rec in records:
        key = (rec.side, rec.policy_key)
        grouped.setdefault(key, []).append(rec)

    out: dict[tuple[str, str], list[MessageRecord]] = {}
    for key, bucket in grouped.items():
        # Sort first by message_id for a deterministic baseline order regardless
        # of CSV row order, then shuffle with a per-cell seed.
        bucket_sorted = sorted(bucket, key=lambda r: r.message_id)
        seed_material = f"{seed}:{key[0]}:{key[1]}".encode("utf-8")
        cell_seed = int.from_bytes(
            hashlib.sha256(seed_material).digest()[:8], "big"
        )
        rng = random.Random(cell_seed)
        rng.shuffle(bucket_sorted)
        out[key] = bucket_sorted
    return out


def load_message_pool(
    set_id: str = "default_v1",
    *,
    seed: int = 0,
    data_root: Path | str | None = None,
    messages_path: Path | str | None = None,
    sources_path: Path | str | None = None,
) -> MessagePool:
    """
    Load and validate an offline message pool from CSV files.

    Parameters
    ----------
    set_id
        Identifier appended to the default CSV filenames:
        ``messages_{set_id}.csv`` and ``sources_{set_id}.csv``.
    seed
        Seed for the per-cell deterministic shuffle.
    data_root
        Override the directory containing the default-named CSVs.
        Ignored when ``messages_path`` / ``sources_path`` are provided.
    messages_path, sources_path
        Explicit paths to the CSV files. Override ``data_root`` and ``set_id``.

    Returns
    -------
    MessagePool
        A loaded, validated, shuffled pool ready for use.

    Raises
    ------
    MessagePoolError
        If files are missing, columns are missing, rows are malformed, or
        provenance refers to unknown source ids.
    """
    msgs_path, srcs_path = _resolve_paths(set_id, data_root, messages_path, sources_path)

    src_rows = _read_csv(srcs_path, REQUIRED_SOURCE_COLUMNS)
    msg_rows = _read_csv(msgs_path, REQUIRED_MESSAGE_COLUMNS)

    sources = _build_source_records(src_rows)
    records = _build_message_records(msg_rows)
    _validate_provenance(records, sources)

    cells = _shuffle_cells(records, seed)
    cursors = {key: 0 for key in cells}

    pool = MessagePool(
        set_id=set_id,
        messages_path=msgs_path,
        sources_path=srcs_path,
        seed=seed,
        _cells=cells,
        _cursors=cursors,
        sources=sources,
    )

    logger.info(
        "Loaded offline message pool %r: %d cells, %d messages, %d sources (seed=%d)",
        set_id, len(cells), sum(len(b) for b in cells.values()), len(sources), seed,
    )
    return pool
