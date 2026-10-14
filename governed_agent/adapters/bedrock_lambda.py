"""AWS Bedrock Agents adapter: run the gateway inside an action-group Lambda.

Architecture
------------
    User ─> Bedrock Agent (LLM plans the next step)
              │  invokes action group
              ▼
            Lambda: lambda_handler  ── this file
              │  GovernedToolGateway.call(...)
              ├─ policy check / approval
              ├─ real tool (CRM, email, payments)
              └─ audit record ─> S3 (Object Lock) / CloudWatch

The LLM decides *what* it wants to do; this Lambda decides whether it *may*.
Because Bedrock can only reach tools through the action group, the gateway
cannot be bypassed by a prompt injection.

This handler uses the function-details action group format. Configure the
action group's functions with the same names and parameters as `TOOLS`.

Approvals: when the policy returns `require_approval` the handler does not run
the tool; it returns a message telling the agent the action is pending human
review. Bedrock's built-in "user confirmation" setting on an action group is a
complementary option for simple yes/no confirmation by the end user.

Reference implementation: deploy with your own IAM, logging and storage
choices. Audit logs written to /tmp disappear with the Lambda container, so
production should stream records to durable, write-once storage.
"""

from __future__ import annotations

import json
import os
from typing import Any

from ..audit import AuditLog
from ..gateway import GovernedToolGateway, deny_all_approver
from ..policy import Policy
from ..tools import TOOLS

_POLICY_PATH = os.environ.get(
    "POLICY_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "policies", "default.yaml"),
)
_AUDIT_PATH = os.environ.get("AUDIT_LOG_PATH", "/tmp/audit.jsonl")

_gateway: GovernedToolGateway | None = None


def _get_gateway() -> GovernedToolGateway:
    global _gateway
    if _gateway is None:  # reused across warm invocations
        _gateway = GovernedToolGateway(
            tools=TOOLS,
            policy=Policy.from_file(_POLICY_PATH),
            audit=AuditLog(_AUDIT_PATH),
            approver=deny_all_approver,  # approvals happen out of band
            approver_id="pending-human-review",
        )
    return _gateway


def _coerce(param: dict[str, Any]) -> Any:
    value, kind = param.get("value"), str(param.get("type", "string")).lower()
    try:
        if kind in {"number", "integer"}:
            return float(value) if "." in str(value) else int(value)
        if kind == "boolean":
            return str(value).lower() == "true"
    except (TypeError, ValueError):
        pass
    return value


def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    tool = event.get("function", "")
    params = {p["name"]: _coerce(p) for p in event.get("parameters", [])}
    result = _get_gateway().call(
        tool,
        params,
        session_id=event.get("sessionId", "unknown"),
        agent_id=(event.get("agent") or {}).get("name", "bedrock-agent"),
        rationale=event.get("inputText", ""),
    )

    if result.ok:
        body = json.dumps(result.output, default=str)
        state = None
    elif result.status == "approval_rejected":
        body = (f"Action '{tool}' needs human approval ({'; '.join(result.reasons)}). "
                f"It has been logged as reference {result.call_id}. Tell the user it is pending review.")
        state = "REPROMPT"
    else:
        body = (f"Action '{tool}' is not permitted: {'; '.join(result.reasons)}. "
                "Do not retry it. Offer the user a permitted alternative or a human handoff.")
        state = "REPROMPT"

    function_response: dict[str, Any] = {"responseBody": {"TEXT": {"body": body}}}
    if state:
        function_response["responseState"] = state

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "function": tool,
            "functionResponse": function_response,
        },
        "sessionAttributes": event.get("sessionAttributes", {}),
        "promptSessionAttributes": event.get("promptSessionAttributes", {}),
    }
