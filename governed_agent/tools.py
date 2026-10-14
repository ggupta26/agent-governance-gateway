"""Sample business tools for the demo: a tiny in-memory CRM.

These stand in for the real systems an enterprise agent would touch
(CRM, email, payments). All data is fictional.
"""

from __future__ import annotations

from typing import Any

CUSTOMERS: dict[str, dict[str, Any]] = {
    "C-1001": {
        "name": "Avery Tremblay",
        "email": "avery.tremblay@example.com",
        "phone": "604-555-0142",
        "postal_code": "V6B 1A1",
        "tier": "gold",
        "balance": 182.40,
    },
    "C-1002": {
        "name": "Jordan Singh",
        "email": "jordan.singh@example.com",
        "phone": "416-555-0187",
        "postal_code": "M5V 2T6",
        "tier": "standard",
        "balance": 1260.00,
    },
}

OUTBOX: list[dict[str, str]] = []
REFUNDS: list[dict[str, Any]] = []


def lookup_customer(customer_id: str) -> dict[str, Any]:
    if customer_id not in CUSTOMERS:
        raise KeyError(f"No customer {customer_id}")
    return {"customer_id": customer_id, **CUSTOMERS[customer_id]}


def send_email(to: str, subject: str, body: str) -> dict[str, str]:
    message = {"to": to, "subject": subject, "body": body}
    OUTBOX.append(message)
    return {"status": "queued", "message_id": f"MSG-{len(OUTBOX):04d}"}


def issue_refund(customer_id: str, amount: float, reason: str = "") -> dict[str, Any]:
    if customer_id not in CUSTOMERS:
        raise KeyError(f"No customer {customer_id}")
    refund = {"refund_id": f"R-{len(REFUNDS) + 1:04d}", "customer_id": customer_id, "amount": float(amount)}
    REFUNDS.append(refund)
    return refund


def delete_customer(customer_id: str) -> dict[str, str]:
    CUSTOMERS.pop(customer_id, None)
    return {"status": "deleted", "customer_id": customer_id}


def export_customers(destination: str) -> dict[str, Any]:
    return {"status": "exported", "rows": len(CUSTOMERS), "destination": destination}


TOOLS = {
    "lookup_customer": lookup_customer,
    "send_email": send_email,
    "issue_refund": issue_refund,
    "delete_customer": delete_customer,
    "export_customers": export_customers,
}
