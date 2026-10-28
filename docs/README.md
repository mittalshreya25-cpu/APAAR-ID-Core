# Project documentation

The original [PROJECT_SPEC.md](../PROJECT_SPEC.md) is preserved unchanged as the consolidated research baseline. These topic files contain its complete relevant sections for implementation use; they do not indicate implemented software.

- [Product requirements](PRD.md)
- [Architecture](ARCHITECTURE.md)
- [Data model and ownership](DATA_MODEL.md)
- [Technology stack](TECH_STACK.md)
- [API and event contracts](API_CONTRACTS.md)
- [Identity and enrolment](IDENTITY_AND_ENROLMENT.md)
- [Validation and intake policy](VALIDATION_RULES.md)
- [Submission and certification workflow](SUBMISSION_WORKFLOW.md)
- [Security and privacy](SECURITY_AND_PRIVACY.md)
- [Verification and certificates](VERIFICATION_AND_CERTIFICATES.md)
- [Testing and evaluation](TESTING_AND_EVALUATION.md)
- [Guardrails and engineering rules](GUARDRAILS.md)
- [Operations and deployment](OPERATIONS_AND_DEPLOYMENT.md)
- [Risks and open questions](RISKS_AND_OPEN_QUESTIONS.md)
- [Research and sources](RESEARCH_AND_SOURCES.md)

## Working context

- [Agent instructions](../AGENTS.md)
- [Phases and tasks](../PHASES_AND_TASKS.md)
- [Durable context](../CONTEXT.md)
- [Current handover](../HANDOVER.md)

## Maintenance and precedence

Topic files are the working design documents after this split. Preserve PROJECT_SPEC.md as the dated baseline unless the user asks to edit it. Record later changes with date, reason and affected contracts in the relevant topic file; update context and phases/tasks, and replace handover at meaningful boundaries. A later documented topic decision supersedes the baseline only for its stated scope. Resolve conflicting working documents explicitly; do not silently maintain competing policies. Existing citations remain linked to the source catalogue; cite new evidence directly when adding decisions.

## Repository setup

GitHub repository: https://github.com/mittalshreya25-cpu/APAAR-ID-Core. Use repository-local Git email tushardoesstuff@gmail.com; do not change global identity or infer a GitHub account/remote from that address. No application implementation or deployment is authorized by this documentation split.
