"""Command-line interface.

    python -m governed_agent demo [--interactive]   run the scripted agent shift
    python -m governed_agent verify                 check the audit chain
    python -m governed_agent report                 summarize the audit log
    python -m governed_agent tamper-demo            show tamper detection
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

from .audit import AuditLog
from .gateway import GovernedToolGateway
from .policy import Policy
from .scenarios import SCENARIOS
from .tools import TOOLS

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY = ROOT / "policies" / "default.yaml"
DEFAULT_LOG = ROOT / "audit" / "audit.jsonl"

ICONS = {"executed": "✅", "denied": "⛔", "approval_rejected": "✋", "error": "⚠️"}


def _approver(interactive: bool):
    def approve(tool, params, reasons):
        print(f"     🔔 Approval needed: {'; '.join(reasons)}")
        if interactive:
            answer = input(f"     Approve {tool}({json.dumps(params)})? [y/N] ").strip().lower()
            return answer in {"y", "yes"}
        # Non-interactive demo: the reviewer approves amounts up to $500 only.
        decision = tool == "issue_refund" and float(params.get("amount", 0)) <= 500
        print(f"     👤 Reviewer {'APPROVED' if decision else 'REJECTED'} (simulated)")
        return decision

    return approve


def cmd_demo(args) -> int:
    log_path = Path(args.log)
    if log_path.exists() and not args.append:
        log_path.unlink()
    gateway = GovernedToolGateway(
        tools=TOOLS,
        policy=Policy.from_file(args.policy),
        audit=AuditLog(log_path),
        approver=_approver(args.interactive),
    )
    print(f"\nPolicy {gateway.policy.version}  ·  audit log → {log_path}\n")
    for i, s in enumerate(SCENARIOS, 1):
        print(f"{i}. {s['title']}")
        print(f"   agent → {s['tool']}({json.dumps(s['params'])})")
        r = gateway.call(s["tool"], s["params"], session_id="shift-001",
                         agent_id="support-agent-v1", rationale=s["rationale"])
        print(f"   {ICONS.get(r.status, '?')} {r.status.upper()}  ·  {'; '.join(r.reasons)}  ·  audit #{r.audit_seq}\n")
    ok, msg = gateway.audit.verify()
    print(f"Audit chain: {msg}")
    print("Next: `python -m governed_agent report` or `python -m governed_agent tamper-demo`\n")
    return 0 if ok else 1


def cmd_verify(args) -> int:
    ok, msg = AuditLog(args.log).verify()
    print(("✅ " if ok else "❌ ") + msg)
    return 0 if ok else 1


def cmd_report(args) -> int:
    log = AuditLog(args.log)
    records = [r for r in log.records() if r.get("event") == "tool_call"]
    if not records:
        print("Audit log is empty. Run `python -m governed_agent demo` first.")
        return 1
    print(f"\nAudit report · {len(records)} tool calls · policy {records[-1]['policy_version']}\n")
    print("By outcome:")
    for status, n in Counter(r["status"] for r in records).most_common():
        print(f"  {ICONS.get(status, '?')} {status:<18} {n}")
    print("\nBy tool:")
    for tool, n in Counter(r["tool"] for r in records).most_common():
        print(f"  {tool:<20} {n}")
    approvals = [r for r in records if r.get("approval")]
    print(f"\nHuman approvals requested: {len(approvals)} "
          f"(approved {sum(r['approval']['approved'] for r in approvals)})")
    print("\nBlocked actions:")
    for r in records:
        if r["status"] != "executed":
            print(f"  #{r['seq']:<3} {r['tool']:<18} {'; '.join(r['reasons'])}")
    ok, msg = log.verify()
    print(f"\nIntegrity: {msg}\n")
    return 0


def cmd_tamper_demo(args) -> int:
    src = Path(args.log)
    if not src.exists() or src.stat().st_size == 0:
        print("Run `python -m governed_agent demo` first.")
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "audit.jsonl"
        shutil.copy(src, copy)
        print(f"Working on a copy: {copy}\n")
        print("Before:", AuditLog(copy).verify()[1])
        lines = copy.read_text(encoding="utf-8").splitlines()
        target = next((i for i, l in enumerate(lines) if '"status": "denied"' in l), 0)
        record = json.loads(lines[target])
        print(f"\nAn insider edits record #{record['seq']} ({record['tool']}) to hide that it was denied...")
        record["status"], record["decision"] = "executed", "allow"
        lines[target] = json.dumps(record)
        copy.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ok, msg = AuditLog(copy).verify()
        print("After: ", ("✅ " if ok else "❌ ") + msg)
    print("\nYour real audit log was not changed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="governed_agent", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="run the scripted agent shift")
    demo.add_argument("--interactive", action="store_true", help="you act as the human approver")
    demo.add_argument("--append", action="store_true", help="keep the existing audit log")
    sub.add_parser("verify", help="verify the audit hash chain")
    sub.add_parser("report", help="summarize the audit log")
    sub.add_parser("tamper-demo", help="show that edits to the log are detected")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return {"demo": cmd_demo, "verify": cmd_verify, "report": cmd_report,
            "tamper-demo": cmd_tamper_demo}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
