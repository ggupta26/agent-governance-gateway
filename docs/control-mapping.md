# Control mapping

How each gateway control supports a specific regulatory or framework expectation, and where it stops.

> **Scope note.** A technical control *supports* compliance; it does not by itself make an organization compliant. Each framework also expects governance processes, documentation and people that no code provides. Always read the source text; links are in the [reading list](reading-list.md).

## Controls

| ID | Control | Implementation |
|---|---|---|
| C1 | Deny by default | Tools absent from the policy are refused (`Policy.evaluate`) |
| C2 | Policy as code | Version-controlled YAML, `version` and `owner` fields, reviewed via pull request |
| C3 | Risk-tiered decisions | `allow` / `require_approval` / `deny` per tool and per parameter rule; strictest wins |
| C4 | Human approval | Gateway calls an approver and runs the tool only on an explicit yes |
| C5 | Rate limits | Per-session cap on executed calls per tool |
| C6 | Tamper-evident audit log | One record per call, SHA-256 hash chain, `verify()` detects edit, deletion, reordering |
| C7 | Redaction before logging | PII patterns and sensitive keys removed from params, rationale and confidential outputs |
| C8 | Data classification | Each tool tagged `internal` / `confidential` / `restricted`; drives redaction |
| C9 | Decision rationale capture | Agent's stated reason, matched rules and policy version are stored with every record |
| C10 | Containment of tool failures | Exceptions in tools are caught, logged, and never crash the agent loop |

## PIPEDA (Personal Information Protection and Electronic Documents Act), Schedule 1 principles

| Principle | How the gateway helps | Not covered |
|---|---|---|
| 4.1 Accountability | C2: the policy names an owner; C6: evidence of what the agent did with personal information | Designating the accountable individual; privacy program |
| 4.4 Limiting Collection | C7: the audit trail stores proof of activity, not copies of personal data | What the business tools themselves collect |
| 4.5 Limiting Use, Disclosure and Retention | C3: `export_customers` to non-internal destinations is denied; external email needs approval | Retention schedules and deletion of the audit log itself |
| 4.7 Safeguards | C1, C5: least privilege and bulk-action limits; C6: integrity of records | Encryption, access control to the log, infrastructure security |
| 4.8 Openness | C2: rules are human-readable and can be summarized for privacy notices | Public-facing policy |
| 4.10 Challenging Compliance | C6, C9: a reviewable trail for investigating a complaint about an agent's action | Complaint-handling process |

## OSFI Guideline E-23: Model Risk Management

Applies to federally regulated financial institutions in Canada, and explicitly covers AI/ML models. The gateway supports the expectation that controls are **proportional to model risk** and that models are **monitored** in use.

| Expectation (summarized) | Gateway control |
|---|---|
| Risk-based approach: rigor scales with impact | C3: low-risk actions run autonomously; higher-impact actions need approval or are denied |
| Clear accountability for model use | C2: policy owner; C4: named approver on each approved action |
| Ongoing monitoring of model behaviour in production | C6 + `report` command: allowed, blocked and approved actions per tool, as monitoring evidence |
| Controls over model outputs before they drive decisions | C1, C3, C4: the LLM's chosen action is checked before it affects customers or money |

Not covered: model inventory, validation, development standards, and the enterprise model risk framework itself. Check OSFI's site for the current text and effective date.

## NIST AI Risk Management Framework 1.0

| Function | Gateway support |
|---|---|
| **Govern** | C2 policy as code with an owner and change review |
| **Map** | C8 data classification of every tool the agent can reach |
| **Measure** | C6 audit log and `report`: rates of denials, approvals, errors |
| **Manage** | C1, C3, C4, C5 runtime enforcement; C6 evidence for incident response |

## OWASP Top 10 for LLM Applications (2025)

| Risk | Mitigation here |
|---|---|
| LLM06 Excessive Agency | C1 least-privilege tool list, C3 parameter thresholds, C4 approvals, C5 rate limits |
| LLM01 Prompt Injection | Impact limited by C1 and C3: an injected instruction can only trigger permitted actions, and the attempt is logged. Does not *detect* injection |
| LLM02 Sensitive Information Disclosure | C7 redaction in logs; C3 blocks external export. Does not filter what the model says to the user |

## EU AI Act (for organizations serving EU users)

| Article | Gateway support |
|---|---|
| Art. 12 Record-keeping (high-risk systems) | C6 automatic, per-event logging with timestamps and outcomes |
| Art. 14 Human oversight | C4 approval step; C1/C3 ability to stop or restrict the system's actions |

## Government of Canada Directive on Automated Decision-Making

For federal institutions. Relevant themes are human intervention for higher-impact decisions and keeping records of automated decisions; C4 and C6 support both. The Directive's Algorithmic Impact Assessment is out of scope.
