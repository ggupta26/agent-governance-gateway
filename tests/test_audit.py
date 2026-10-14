import json

from governed_agent.audit import GENESIS_HASH, AuditLog


def _lines(path):
    return path.read_text(encoding="utf-8").splitlines()


def test_chain_links_records(tmp_path):
    log = AuditLog(tmp_path / "a.jsonl")
    r1 = log.append({"event": "x"})
    r2 = log.append({"event": "y"})
    assert r1["prev_hash"] == GENESIS_HASH
    assert r2["prev_hash"] == r1["hash"]
    assert log.verify() == (True, "OK: 2 records, chain intact")


def test_reopen_continues_chain(tmp_path):
    path = tmp_path / "a.jsonl"
    AuditLog(path).append({"event": "x"})
    log = AuditLog(path)
    r = log.append({"event": "y"})
    assert r["seq"] == 2
    assert log.verify()[0]


def test_edit_detected(tmp_path):
    path = tmp_path / "a.jsonl"
    log = AuditLog(path)
    for i in range(3):
        log.append({"event": "tool_call", "status": "denied", "i": i})
    lines = _lines(path)
    rec = json.loads(lines[1])
    rec["status"] = "executed"
    lines[1] = json.dumps(rec)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ok, msg = AuditLog(path).verify()
    assert not ok and "Record 2 was modified" in msg


def test_deletion_detected(tmp_path):
    path = tmp_path / "a.jsonl"
    log = AuditLog(path)
    for i in range(3):
        log.append({"i": i})
    lines = _lines(path)
    del lines[1]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ok, msg = AuditLog(path).verify()
    assert not ok and "Sequence gap" in msg


def test_rehashed_edit_still_breaks_link(tmp_path):
    """An attacker who recomputes the edited record's own hash still breaks the next link."""
    from governed_agent.audit import _hash

    path = tmp_path / "a.jsonl"
    log = AuditLog(path)
    for i in range(3):
        log.append({"i": i})
    lines = _lines(path)
    rec = json.loads(lines[0])
    rec["i"] = 99
    rec["hash"] = _hash(rec)
    lines[0] = json.dumps(rec)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ok, msg = AuditLog(path).verify()
    assert not ok and "Chain broken at record 2" in msg
