"""The governed tool gateway: the single choke point for agent actions.

    agent ──> gateway.call(tool, params, rationale)
                 │
                 ├─ 1. policy.evaluate()        allow / require_approval / deny
                 ├─ 2. approver(call, reasons)  human-in-the-loop, if required
                 ├─ 3. tool(**params)           only if allowed or approved
                 └─ 4. audit.append()           always, success or failure

The agent never holds a direct reference to a tool function, so it cannot
skip the checks. Whatever happens, exactly one audit record is written.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from .audit import AuditLog
from .policy import Decision, Policy
from .redaction import redact

Approver = Callable[[str, dict[str, Any], tuple[str, ...]], bool]


def deny_all_approver(tool: str, params: dict[str, Any], reasons: tuple[str, ...]) -> bool:
    """Safe default when no human is available: nothing gets approved."""
    return False


@dataclass
class ToolResult:
    status: str  # executed | denied | approval_rejected | error
    tool: str
    output: Any = None
    reasons: tuple[str, ...] = ()
    call_id: str = ""
    audit_seq: int = 0
    approved_by: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "executed"


class GovernedToolGateway:
    def __init__(
        self,
        tools: dict[str, Callable[..., Any]],
        policy: Policy,
        audit: AuditLog,
        approver: Approver = deny_all_approver,
        approver_id: str = "human-reviewer",
    ):
        self._tools = dict(tools)
        self.policy = policy
        self.audit = audit
        self.approver = approver
        self.approver_id = approver_id

    @property
    def tool_names(self) -> list[str]:
        return sorted(self._tools)

    def call(
        self,
        tool: str,
        params: dict[str, Any] | None = None,
        *,
        session_id: str = "default",
        agent_id: str = "agent",
        rationale: str = "",
    ) -> ToolResult:
        params = dict(params or {})
        call_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()

        verdict = self.policy.evaluate(tool, params, session_id)
        result = ToolResult(status="denied", tool=tool, reasons=verdict.reasons, call_id=call_id)
        approval: dict[str, Any] | None = None

        if verdict.decision == Decision.REQUIRE_APPROVAL:
            approved = bool(self.approver(tool, params, verdict.reasons))
            approval = {"required": True, "approved": approved, "approver": self.approver_id}
            if not approved:
                result.status = "approval_rejected"
            else:
                result.approved_by = self.approver_id

        may_run = verdict.decision == Decision.ALLOW or (approval is not None and approval["approved"])

        if may_run:
            fn = self._tools.get(tool)
            if fn is None:
                result.status = "error"
                result.reasons = (f"Tool '{tool}' is allowed by policy but not registered",)
            else:
                try:
                    result.output = fn(**params)
                    result.status = "executed"
                    self.policy.record_execution(tool, session_id)
                except Exception as exc:  # the tool failed; the gateway must not
                    result.status = "error"
                    result.reasons = (f"{type(exc).__name__}: {exc}",)

        logged_output = result.output
        if verdict.redact_output or verdict.data_classification in {"confidential", "restricted"}:
            logged_output = redact(logged_output)

        record = self.audit.append(
            {
                "event": "tool_call",
                "call_id": call_id,
                "session_id": session_id,
                "agent_id": agent_id,
                "tool": tool,
                "params": redact(params),
                "rationale": redact(rationale),
                "policy_version": self.policy.version,
                "decision": verdict.decision.value,
                "matched_rules": list(verdict.matched_rules),
                "reasons": list(result.reasons),
                "data_classification": verdict.data_classification,
                "approval": approval,
                "status": result.status,
                "output": logged_output,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        )
        result.audit_seq = record["seq"]
        return result
