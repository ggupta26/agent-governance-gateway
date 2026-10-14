# Design decisions

Trade-offs made in this implementation and why. Written as short decision records.

---

## 1. Enforce at the tool boundary, not in the prompt

**Decision.** All tool access goes through `GovernedToolGateway.call()`. The agent is given tool *names*, never tool functions.

**Why.** A system prompt saying "never issue refunds over $1,000" is a suggestion the model can be talked out of. A check in code that runs before the refund function is a control. Putting the check at the tool boundary also means it works the same whichever model or framework sits above it.

**Trade-off.** The gateway only governs *actions*. It does not filter what the model says to the user; that is a job for output guardrails (e.g. Bedrock Guardrails), which complement this layer.

---

## 2. Deny by default; strictest matching rule wins

**Decision.** Unlisted tools are denied. If several rules match, `deny` beats `require_approval` beats `allow`.

**Why.** Policy authoring errors should fail closed. Strictest-wins also makes rule order irrelevant, so reviewers can read rules independently.

**Trade-off.** New tools are blocked until someone adds them to the policy. That friction is intended.

---

## 3. YAML policies instead of a policy language

**Decision.** A small set of operators (`gt`, `in`, `not_endswith`, `matches`, …) in YAML.

**Why.** The audience for the policy includes privacy, risk and legal reviewers. YAML is readable in a pull request without training. The engine is ~150 lines and easy to audit.

**Trade-off.** No cross-parameter logic or external lookups. Organizations that need that, or already run Open Policy Agent, should swap in a Rego backend; the gateway's interface stays the same.

---

## 4. One audit record per call, written in all outcomes

**Decision.** Executed, denied, rejected and errored calls each produce exactly one record, including the agent's rationale, matched rules and policy version.

**Why.** Auditors ask two questions: "show me what went wrong" and "show me it behaved the rest of the time." The second needs the full population of calls. The policy version lets you reconstruct *which* rules were in force when a decision was made.

---

## 5. Hash chain: tamper-evident, not tamper-proof

**Decision.** Each record includes the previous record's SHA-256 hash.

**Why.** It is cheap, dependency-free and detects editing, deleting or reordering past records, including an attacker who recomputes the edited record's own hash (the next link breaks).

**Limit.** Someone with write access could rewrite the *entire* file and recompute every hash. Production therefore needs (a) write-once storage such as S3 Object Lock in compliance mode, and (b) periodically publishing the latest hash somewhere the log writer cannot change.

---

## 6. Redact before writing, keep the real result for the agent

**Decision.** The agent receives the unredacted tool output it needs to do its job. The audit log stores a redacted copy.

**Why.** The log must prove what happened without becoming a second store of personal information that needs its own retention, access control and breach response.

**Trade-off.** Regex redaction misses names and free-form identifiers, and fully redacted recipients make it harder to correlate records for one customer. Next step: keyed-hash pseudonymization plus a dedicated PII detection service.

---

## 7. Approvals as a synchronous callback (for now)

**Decision.** The approver is a function the gateway calls. The CLI uses a console prompt or a simulated reviewer; the Bedrock adapter uses deny-and-report-pending.

**Why.** It keeps the core logic testable and small.

**Trade-off.** Real approvals are asynchronous: the agent should park the request, a reviewer acts in a queue or chat tool, and the action resumes. That is the first roadmap item.
