# RelayOps 1.0.0

An FDE portfolio project built around a fictional support-operations engagement, with a runnable application and a documented delivery process.

## Included

- React/TypeScript operations workbench: ticket queue, cited analysis, evidence, execution trace, approvals, knowledge, baseline evaluations and audit history.
- FastAPI application with tenant-scoped SQLAlchemy records, SQLite and PostgreSQL configuration, JSON ingestion, and replay-safe transactional approval.
- Offline extractive analysis by default; opt-in OpenAI Responses integration with validated structured output and citation IDs.
- Four read-only MCP tools with a stdio server, bounded inputs, structured outputs, fixed tenant credentials and protocol tests.
- Docker packaging, GitHub Actions, customer discovery brief, architecture decisions, runbook and interview/resume guidance.

## Validation

102 automated tests passed locally: 74 backend, 16 frontend and 12 MCP. Backend statement coverage was 96%. Eight deterministic regression scenarios passed. The compiled interface was exercised in Chrome at desktop and mobile dimensions, including a full approval workflow and cross-tenant switching. See [validation](validation.md) and [CI](https://github.com/muresaijaideepreddy/relayops-fde/actions) for scope and revision-specific results.

All five [GitHub CI jobs passed](https://github.com/muresaijaideepreddy/relayops-fde/actions/runs/36255539724), including real PostgreSQL API integration and the built Docker application's end-to-end smoke workflow.

## Boundaries

Demo customers and data are synthetic. CRM writes are local simulations. The live provider path is tested with mocks; no live model call, real customer deployment, or productivity improvement is claimed. This release is a portfolio demonstration with documented prerequisites for a real pilot.
