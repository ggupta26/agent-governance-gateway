"""Tamper-evident, append-only audit log.

Each record stores the SHA-256 hash of the previous record, forming a hash
chain. Editing, deleting or reordering any past record breaks the chain, and
`verify()` reports the first record where it breaks.

This makes tampering *detectable*, not impossible. In production the log
should also be shipped to write-once storage (for example S3 Object Lock in
compliance mode) so that it cannot be silently rewritten end to end.
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

GENESIS_HASH = "0" * 64


def _canonical(record: dict[str, Any]) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _hash(record: dict[str, Any]) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    return hashlib.sha256(_canonical(body)).hexdigest()


class AuditLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self._lock = threading.Lock()
        self._seq, self._last_hash = self._tail()

    def _tail(self) -> tuple[int, str]:
        seq, last = 0, GENESIS_HASH
        for record in self.records():
            seq, last = record["seq"], record["hash"]
        return seq, last

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            record = {
                "seq": self._seq + 1,
                "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                "prev_hash": self._last_hash,
                **event,
            }
            record["hash"] = _hash(record)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, default=str) + "\n")
            self._seq, self._last_hash = record["seq"], record["hash"]
            return record

    def records(self) -> Iterator[dict[str, Any]]:
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)

    def verify(self) -> tuple[bool, str]:
        """Return (ok, message). Checks hashes, links and sequence numbers."""
        prev, expected_seq, count = GENESIS_HASH, 1, 0
        try:
            for record in self.records():
                seq = record.get("seq")
                if seq != expected_seq:
                    return False, f"Sequence gap at record {seq} (expected {expected_seq})"
                if record.get("prev_hash") != prev:
                    return False, f"Chain broken at record {seq}: prev_hash does not match"
                if _hash(record) != record.get("hash"):
                    return False, f"Record {seq} was modified after it was written"
                prev, expected_seq, count = record["hash"], expected_seq + 1, count + 1
        except json.JSONDecodeError as exc:
            return False, f"Unreadable record near line {expected_seq}: {exc}"
        return True, f"OK: {count} records, chain intact"
