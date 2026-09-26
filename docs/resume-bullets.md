# Resume-ready project entry

Place this under **Projects**, not employment. Use only bullets for code you have reviewed, run, and can explain.

**RelayOps — Support Operations Copilot | Independent Project**

Python, FastAPI, SQLAlchemy, React, TypeScript, REST APIs, MCP, retrieval-augmented workflows, pytest

GitHub: [muresaijaideepreddy/relayops-fde](https://github.com/muresaijaideepreddy/relayops-fde)

Choose three or four bullets to fit the role:

- Built a full-stack support operations workbench with React, TypeScript, and FastAPI, connecting ticket intake, policy retrieval, structured analysis, and human review using synthetic customer data.
- Implemented tenant-scoped access and idempotent ticket ingestion with SQLAlchemy, preserving separate ticket, knowledge, action, and audit records for two demo organizations.
- Developed an evidence-backed analysis workflow with document citations, escalation signals, step traces, an offline deterministic provider, and an optional OpenAI Responses integration.
- Added approval and rejection handling for simulated CRM notes, with persisted action results and conflict detection to support repeatable decision requests.
- Created repeatable offline evaluations and API tests for workflow behavior, tenant isolation, and action decisions; documented the distinction between regression checks and live-model quality evaluation.
- Validated the application with 102 automated tests across backend, frontend, and MCP suites, achieving 96% backend statement coverage and passing eight deterministic retrieval/escalation regression scenarios.
- Packaged the application with Docker Compose and SQLite/PostgreSQL configuration paths, and added CI definitions for backend, frontend, database, and container checks.
- Implemented four read-only MCP tools for tenant-scoped ticket, evidence, and metrics access; verified structured responses, input validation, and the stdio subprocess handshake with the official Python SDK.
- Produced a fictional customer discovery brief, architecture trade-offs, pilot acceptance criteria, and an operational runbook to demonstrate the delivery and handoff work around an FDE engagement.

## Compact two-bullet version

- Built RelayOps, a React/TypeScript and FastAPI support copilot with tenant-scoped policy retrieval, cited analysis, human approvals, and a simulated CRM integration.
- Implemented idempotent ingestion, audit history, and deterministic evaluations; documented customer-discovery assumptions, integration trade-offs, and a proposed pilot measurement plan.

## Skills to list accurately

The implemented scope supports discussion of Python, TypeScript, React, FastAPI, REST API design, Pydantic validation, SQLAlchemy, SQLite, tenant isolation, lexical retrieval, structured AI output, MCP tools, human review workflows, idempotency, automated testing, and technical documentation. Describe PostgreSQL as a configurable database path unless you have run and validated it. Describe the OpenAI path as an integration implementation unless you have separately tested it against the live API.

Use [validation](validation.md) to add only verified facts such as a test count or measured local runtime. A local test pass rate is not model accuracy, customer satisfaction, or productivity improvement.

## Claims to avoid

- “Reduced support costs by 40%,” “served thousands of customers,” or “deployed for Northstar Logistics”: no such results or engagement are established.
- “Production-ready enterprise platform” or “enterprise-grade security”: this project does not implement or validate the full operational and security controls implied by those phrases.
- “Built a vector database,” “fine-tuned an LLM,” or “deployed Kubernetes/Terraform”: these are not implemented features.
- “Autonomous CRM agent”: the integration is local and simulated, and execution requires a review decision.

The strongest interview version is the one you can demonstrate and explain without overstating its scope.
