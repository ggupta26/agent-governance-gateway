"""Agent Governance Gateway.

A policy-enforcing, audited gateway that sits between an AI agent and the
tools it can call. Every tool call is checked against a declarative policy,
optionally routed to a human approver, executed, and written to a
tamper-evident audit log with personal information redacted.
"""

from .audit import AuditLog
from .gateway import GovernedToolGateway, ToolResult
from .policy import Decision, Policy, PolicyDecision
from .redaction import redact

__all__ = [
    "AuditLog",
    "Decision",
    "GovernedToolGateway",
    "Policy",
    "PolicyDecision",
    "ToolResult",
    "redact",
]

__version__ = "0.1.0"
