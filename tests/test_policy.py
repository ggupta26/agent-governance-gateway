from pathlib import Path

import pytest

from governed_agent.policy import Decision, Policy

POLICY_FILE = Path(__file__).resolve().parent.parent / "policies" / "default.yaml"


@pytest.fixture
def policy():
    return Policy.from_file(POLICY_FILE)


def test_unknown_tool_is_denied_by_default(policy):
    d = policy.evaluate("run_shell_command", {"cmd": "ls"})
    assert d.decision == Decision.DENY
    assert "not in the policy" in d.reasons[0]


def test_small_refund_allowed(policy):
    assert policy.evaluate("issue_refund", {"customer_id": "C-1", "amount": 50}).decision == Decision.ALLOW


def test_medium_refund_needs_approval(policy):
    d = policy.evaluate("issue_refund", {"customer_id": "C-1", "amount": 450})
    assert d.decision == Decision.REQUIRE_APPROVAL
    assert "refund.over_100" in d.matched_rules


def test_strictest_rule_wins(policy):
    d = policy.evaluate("issue_refund", {"customer_id": "C-1", "amount": 5000})
    assert d.decision == Decision.DENY
    assert set(d.matched_rules) == {"refund.over_100", "refund.over_1000"}


def test_boundary_is_exclusive(policy):
    assert policy.evaluate("issue_refund", {"amount": 100}).decision == Decision.ALLOW
    assert policy.evaluate("issue_refund", {"amount": 100.01}).decision == Decision.REQUIRE_APPROVAL


def test_external_email_needs_approval(policy):
    assert policy.evaluate("send_email", {"to": "a@example.com"}).decision == Decision.ALLOW
    assert policy.evaluate("send_email", {"to": "a@EXAMPLE.COM"}).decision == Decision.ALLOW
    assert policy.evaluate("send_email", {"to": "a@other.com"}).decision == Decision.REQUIRE_APPROVAL


def test_rate_limit_applies_per_session(policy):
    for _ in range(3):
        assert policy.evaluate("issue_refund", {"amount": 10}, "s1").decision == Decision.ALLOW
        policy.record_execution("issue_refund", "s1")
    d = policy.evaluate("issue_refund", {"amount": 10}, "s1")
    assert d.decision == Decision.DENY and "Rate limit" in d.reasons[0]
    assert policy.evaluate("issue_refund", {"amount": 10}, "s2").decision == Decision.ALLOW


def test_missing_parameter_does_not_match_rules(policy):
    assert policy.evaluate("issue_refund", {}).decision == Decision.ALLOW


def test_invalid_policy_rejected():
    with pytest.raises(ValueError):
        Policy.from_dict({"tools": {"x": {"decision": "maybe"}}})
    with pytest.raises(ValueError):
        Policy.from_dict({"tools": {"x": {"rules": [{"decision": "deny"}]}}})
    with pytest.raises(ValueError):
        Policy.from_dict({"default": "deny"})
