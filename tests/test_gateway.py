from pathlib import Path

import pytest

from governed_agent import AuditLog, GovernedToolGateway, Policy

POLICY_FILE = Path(__file__).resolve().parent.parent / "policies" / "default.yaml"


def make_gateway(tmp_path, approver=None, tools=None):
    calls = []

    def refund(customer_id, amount, reason=""):
        calls.append(("refund", amount))
        return {"refund_id": "R-1", "amount": amount}

    def lookup(customer_id):
        return {"customer_id": customer_id, "email": "pat@example.com"}

    def delete(customer_id):
        calls.append(("delete", customer_id))

    registry = tools or {"issue_refund": refund, "lookup_customer": lookup, "delete_customer": delete}
    kwargs = {"approver": approver} if approver else {}
    gw = GovernedToolGateway(registry, Policy.from_file(POLICY_FILE), AuditLog(tmp_path / "a.jsonl"), **kwargs)
    return gw, calls


def test_allowed_call_executes_and_is_logged(tmp_path):
    gw, calls = make_gateway(tmp_path)
    r = gw.call("issue_refund", {"customer_id": "C-1", "amount": 20})
    assert r.ok and calls == [("refund", 20)]
    rec = list(gw.audit.records())[-1]
    assert rec["status"] == "executed" and rec["decision"] == "allow"


def test_denied_call_never_runs(tmp_path):
    gw, calls = make_gateway(tmp_path)
    r = gw.call("delete_customer", {"customer_id": "C-1"})
    assert r.status == "denied" and calls == []


def test_approval_required_and_rejected_by_default(tmp_path):
    gw, calls = make_gateway(tmp_path)
    r = gw.call("issue_refund", {"customer_id": "C-1", "amount": 300})
    assert r.status == "approval_rejected" and calls == []
    rec = list(gw.audit.records())[-1]
    assert rec["approval"] == {"required": True, "approved": False, "approver": "human-reviewer"}


def test_approval_granted_runs_tool(tmp_path):
    seen = []
    gw, calls = make_gateway(tmp_path, approver=lambda t, p, r: seen.append(r) or True)
    r = gw.call("issue_refund", {"customer_id": "C-1", "amount": 300})
    assert r.ok and r.approved_by == "human-reviewer" and calls == [("refund", 300)]
    assert "over $100" in seen[0][0]


def test_approver_not_consulted_for_denials(tmp_path):
    gw, _ = make_gateway(tmp_path, approver=lambda *a: pytest.fail("should not be asked"))
    assert gw.call("issue_refund", {"customer_id": "C-1", "amount": 9999}).status == "denied"


def test_tool_error_is_contained_and_logged(tmp_path):
    def broken(customer_id):
        raise RuntimeError("CRM timeout")

    gw, _ = make_gateway(tmp_path, tools={"lookup_customer": broken})
    r = gw.call("lookup_customer", {"customer_id": "C-1"})
    assert r.status == "error" and "CRM timeout" in r.reasons[0]
    assert list(gw.audit.records())[-1]["status"] == "error"


def test_confidential_output_redacted_in_log_not_in_result(tmp_path):
    gw, _ = make_gateway(tmp_path)
    r = gw.call("lookup_customer", {"customer_id": "C-1"})
    assert r.output["email"] == "pat@example.com"
    assert list(gw.audit.records())[-1]["output"]["email"] == "[REDACTED:EMAIL]"


def test_every_call_produces_one_record_and_chain_holds(tmp_path):
    gw, _ = make_gateway(tmp_path)
    gw.call("issue_refund", {"customer_id": "C-1", "amount": 5})
    gw.call("delete_customer", {"customer_id": "C-1"})
    gw.call("unknown_tool", {})
    assert len(list(gw.audit.records())) == 3
    assert gw.audit.verify()[0]
