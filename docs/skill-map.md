# FDE skill map

This mapping was reviewed against primary career pages on **26 September 2026**. It is a focused portfolio plan, not an exhaustive list of hiring requirements or a claim of professional experience.

OpenAI's FDE posting emphasizes discovery, technical scoping, full-stack delivery, rollout, evaluation-driven learning, and stakeholder communication. This project demonstrates a local implementation and planning artifacts for that lifecycle; it does not establish actual production adoption. [OpenAI FDE role](https://openai.com/careers/forward-deployed-engineer-%28fde%29-sf-san-francisco/)

Palantir's FDSE posting connects end-to-end customer ownership with architecture, data, custom applications, LLM workflows, and secure engineering. Its early-talent guidance also emphasizes independent problem-solving and communication. [Palantir FDSE role](https://jobs.lever.co/palantir/5168e8fd-fec1-4fea-b7a1-81bdaea65850), [Palantir early talent](https://www.palantir.com/careers/students-and-early-talent/)

| Relevant capability | Evidence in this repository | Scope and honest interview claim |
| --- | --- | --- |
| Customer discovery and scoping | [Discovery and pilot plan](customer-discovery.md) | Formulated stakeholder questions and acceptance criteria for a fictional workflow; no actual interviews |
| Full-stack engineering | [Frontend](../frontend), [backend](../backend) | Built the ticket-to-review workflow with React/TypeScript and Python/FastAPI |
| API and integration design | Ticket ingest and action APIs in [backend](../backend) | Implemented typed requests, per-tenant deduplication, and a simulated CRM adapter |
| Model Context Protocol | [MCP adapter](../integrations/mcp/README.md), [protocol tests](../integrations/mcp/test_server.py) | Built four read-only stdio tools with fixed tenant credentials, bounded inputs, structured results, and subprocess handshake verification |
| Applied AI and retrieval | Analysis workflow in [backend](../backend), [architecture](architecture.md) | Implemented lexical evidence retrieval and structured analysis; optional live provider is distinct from the offline default |
| Data modeling and SQL | SQLAlchemy models in [backend](../backend) | Persisted tickets, knowledge, analysis, actions, audits, and evaluations; SQLite default with PostgreSQL configuration support |
| Security judgment | Tenant-scoped routes and tests; [trust boundaries](architecture.md#trust-boundaries) | Demonstrated access boundaries and input validation; documented identity and operational controls still needed |
| Evaluation and failure analysis | Evaluation API, [tests](../backend/tests), [validation](validation.md) | Built repeatable application regression checks; live-model accuracy and real-user usefulness require separate evaluation |
| Action reliability | Approval decision path and tests in [backend](../backend) | Persisted decisions/results and rejected conflicting retries; remote delivery semantics remain future integration work |
| Operability and handoff | [Runbook](runbook.md), analysis trace and audit views | Documented startup, diagnostics, recovery, and local operation; no production on-call history claimed |
| Reproducible delivery | [Dockerfile](../Dockerfile), [Compose](../compose.yaml), [PostgreSQL override](../compose.postgres.yaml), [CI](../.github/workflows) | Packaged local deployment paths and automated checks; executed results are recorded separately in validation |
| Technical communication | [Architecture](architecture.md), [interview guide](interview-guide.md) | Explained assumptions, trade-offs, a demo, and next experiments in language a stakeholder can inspect |

## Additional skills need evidence before they go on the resume

Cloud infrastructure, Kubernetes, Terraform, vector databases, streaming pipelines, distributed queues, SSO/RBAC, and real CRM integrations can matter for particular jobs. They are not implemented here. OpenAI's government FDE posting, for example, mentions cloud and infrastructure tools; that is a role-specific reason to learn them, not a reason to claim this repository uses them. [OpenAI government FDE role](https://openai.com/careers/forward-deployed-engineer-gov-washington-dc/)

Prefer the next addition that resolves a demonstrated constraint: semantic retrieval after measured recall failures; a job queue after measured latency or concurrency problems; a real sandbox connector after agreeing on identity, permissions, and retry semantics. Each extension should produce runnable code, a failure test, and a documented result.

MCP is included because it makes this workbench's context accessible through a standard host interface. It is an implemented integration choice, not a claim that every FDE role requires it. Its implementation follows the [official MCP Python SDK](https://py.sdk.modelcontextprotocol.io/).
