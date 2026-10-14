"""Demo scenarios: a scripted support agent working through a shift.

The agent's "plan" is scripted so the demo is deterministic, runs offline and
needs no API keys. The governance layer is identical to what a live LLM agent
would go through: see `adapters/bedrock_lambda.py` for the AWS Bedrock wiring.
"""

from __future__ import annotations

SCENARIOS = [
    {
        "title": "Look up a customer",
        "tool": "lookup_customer",
        "params": {"customer_id": "C-1001"},
        "rationale": "Customer asked about their account balance.",
    },
    {
        "title": "Email the customer",
        "tool": "send_email",
        "params": {
            "to": "avery.tremblay@example.com",
            "subject": "Your balance",
            "body": "Hi Avery, your current balance is $182.40.",
        },
        "rationale": "Reply to the customer's question.",
    },
    {
        "title": "Small goodwill refund",
        "tool": "issue_refund",
        "params": {"customer_id": "C-1001", "amount": 25, "reason": "late delivery"},
        "rationale": "Policy allows small goodwill credits for late delivery.",
    },
    {
        "title": "Larger refund (needs a human)",
        "tool": "issue_refund",
        "params": {"customer_id": "C-1002", "amount": 450, "reason": "damaged item"},
        "rationale": "Customer reports a damaged item worth $450.",
    },
    {
        "title": "Refund outside the agent's mandate",
        "tool": "issue_refund",
        "params": {"customer_id": "C-1002", "amount": 5000, "reason": "goodwill"},
        "rationale": "Customer is upset; trying to retain them.",
    },
    {
        "title": "Email someone outside the customer domain",
        "tool": "send_email",
        "params": {
            "to": "partner@othercorp.com",
            "subject": "Customer list",
            "body": "Contact Jordan at 416-555-0187.",
        },
        "rationale": "Forwarding details to a partner.",
    },
    {
        "title": "Delete a customer record",
        "tool": "delete_customer",
        "params": {"customer_id": "C-1002"},
        "rationale": "Customer asked to close their account.",
    },
    {
        "title": "Export customers to an outside address",
        "tool": "export_customers",
        "params": {"destination": "s3://public-bucket.example.net"},
        "rationale": "Analytics team wants the data.",
    },
    {
        "title": "Call a tool nobody approved",
        "tool": "run_shell_command",
        "params": {"cmd": "cat /etc/passwd"},
        "rationale": "Prompt-injected instruction found in a support ticket.",
    },
]
