# Reading list: governing AI agents

A short, annotated list. Curated for engineering and product leaders who need to put agents into production in a regulated, Canadian context. Each entry says why it is worth your time.

> Suggestions welcome via pull request. Prefer primary sources (regulators, standards bodies, maintainers) over commentary.

## Canadian regulation and guidance

- **[PIPEDA, Office of the Privacy Commissioner of Canada](https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/)**: Canada's federal private-sector privacy law. The ten fair information principles in Schedule 1 are the yardstick for what an agent may do with personal information.
- **[OSFI Guideline E-23: Model Risk Management](https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/guideline-e-23-model-risk-management-2027)**: model risk expectations for federally regulated banks and insurers, explicitly including AI/ML. Essential if your agent touches financial decisions.
- **[Directive on Automated Decision-Making, Treasury Board of Canada Secretariat](https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32592)**: the federal government's rules for automated decisions, including impact assessment and human intervention. A useful model even outside government.

## Frameworks and standards

- **[NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)**: the Govern / Map / Measure / Manage structure most enterprise AI programs borrow from. Read the companion Playbook for concrete actions.
- **[ISO/IEC 42001: AI management systems](https://www.iso.org/standard/81230.html)**: the certifiable management-system standard for AI. Think ISO 27001, for AI.
- **[EU Artificial Intelligence Act](https://artificialintelligenceact.eu/)**: risk-tiered obligations; Articles 12 (record-keeping) and 14 (human oversight) map directly onto agent audit and approval controls.

## Security of LLM applications

- **[OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/)**: the standard threat list. *Excessive Agency* is the risk this repository is built around.
- **[MITRE ATLAS](https://atlas.mitre.org/)**: adversary tactics and techniques against AI systems, in the style of ATT&CK. Good for threat modeling an agent.

## Building blocks

- **[Amazon Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)**: managed agents with action groups backed by Lambda; the adapter in this repo plugs into an action group.
- **[Amazon Bedrock Guardrails](https://aws.amazon.com/bedrock/guardrails/)**: content and PII filtering on model inputs and outputs. Complements action-level governance.
- **[Open Policy Agent](https://www.openpolicyagent.org/)**: general-purpose policy engine (Rego). The natural next step when YAML rules are not expressive enough.
- **[Microsoft Presidio](https://microsoft.github.io/presidio/)**: open-source PII detection and anonymization; a stronger replacement for regex redaction.

## Broader collections

- **[Awesome AI Agent Governance](https://github.com/agentrust-io/awesome-ai-governance)**: a large, community-maintained list of tools, standards and papers on agent governance.

---

*My notes:* add a line under any entry with how you have applied it. That annotation is what makes a curated list worth reading.
