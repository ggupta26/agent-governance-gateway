"""Declarative policy engine for agent tool calls.

Policies are plain YAML so that non-engineers (risk, privacy, legal) can read
and review them in a pull request. Evaluation is deterministic and
deny-by-default: a tool that is not listed in the policy cannot be called.

When several rules match a call, the strictest outcome wins:
    DENY  >  REQUIRE_APPROVAL  >  ALLOW
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class Decision(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"

    @property
    def severity(self) -> int:
        return {"allow": 0, "require_approval": 1, "deny": 2}[self.value]


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    reasons: tuple[str, ...]
    matched_rules: tuple[str, ...] = ()
    data_classification: str = "internal"
    redact_output: bool = False


def _check(op: str, actual: Any, expected: Any) -> bool:
    """Evaluate one comparison operator. Missing values never match."""
    if actual is None:
        return False
    try:
        if op == "eq":
            return actual == expected
        if op == "ne":
            return actual != expected
        if op == "gt":
            return float(actual) > float(expected)
        if op == "gte":
            return float(actual) >= float(expected)
        if op == "lt":
            return float(actual) < float(expected)
        if op == "lte":
            return float(actual) <= float(expected)
        if op == "in":
            return actual in expected
        if op == "not_in":
            return actual not in expected
        if op == "endswith":
            return str(actual).lower().endswith(str(expected).lower())
        if op == "not_endswith":
            return not str(actual).lower().endswith(str(expected).lower())
        if op == "matches":
            return re.search(str(expected), str(actual)) is not None
    except (TypeError, ValueError):
        return False
    raise ValueError(f"Unknown policy operator: {op!r}")


@dataclass
class Policy:
    """A loaded, validated policy plus per-session rate-limit counters."""

    raw: dict[str, Any]
    _calls: dict[tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))

    @classmethod
    def from_file(cls, path: str | Path) -> "Policy":
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(yaml.safe_load(fh))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Policy":
        if not isinstance(data, dict) or "tools" not in data:
            raise ValueError("Policy must be a mapping with a 'tools' section")
        default = data.get("default", "deny")
        Decision(default)  # validates the value
        for name, spec in data["tools"].items():
            Decision(spec.get("decision", default))
            for rule in spec.get("rules", []):
                Decision(rule["decision"])
                if "when" not in rule:
                    raise ValueError(f"Rule on tool {name!r} is missing 'when'")
        return cls(raw=data)

    @property
    def version(self) -> str:
        return str(self.raw.get("version", "unversioned"))

    def evaluate(self, tool: str, params: dict[str, Any], session_id: str = "default") -> PolicyDecision:
        tools = self.raw["tools"]
        default = Decision(self.raw.get("default", "deny"))

        if tool not in tools:
            return PolicyDecision(
                decision=default,
                reasons=(f"Tool '{tool}' is not in the policy (default: {default.value})",),
            )

        spec = tools[tool]
        decision = Decision(spec.get("decision", default.value))
        reasons: list[str] = [spec.get("reason", f"Base decision for '{tool}'")]
        matched: list[str] = []

        for i, rule in enumerate(spec.get("rules", [])):
            cond = rule["when"]
            param = cond.get("param")
            ops = {k: v for k, v in cond.items() if k != "param"}
            value = params.get(param)
            if all(_check(op, value, expected) for op, expected in ops.items()):
                rule_decision = Decision(rule["decision"])
                rule_id = rule.get("id", f"{tool}.rule{i + 1}")
                matched.append(rule_id)
                if rule_decision.severity > decision.severity:
                    decision = rule_decision
                    reasons = [rule.get("reason", rule_id)]
                elif rule_decision.severity == decision.severity and rule_decision != Decision.ALLOW:
                    reasons.append(rule.get("reason", rule_id))

        limit = spec.get("rate_limit")
        if limit is not None:
            key = (session_id, tool)
            if self._calls[key] >= int(limit) and decision != Decision.DENY:
                decision = Decision.DENY
                reasons = [f"Rate limit reached: max {limit} '{tool}' calls per session"]
                matched.append(f"{tool}.rate_limit")

        return PolicyDecision(
            decision=decision,
            reasons=tuple(reasons),
            matched_rules=tuple(matched),
            data_classification=spec.get("data_classification", "internal"),
            redact_output=bool(spec.get("redact_output", False)),
        )

    def record_execution(self, tool: str, session_id: str = "default") -> None:
        """Count an executed call toward the session's rate limit."""
        self._calls[(session_id, tool)] += 1
