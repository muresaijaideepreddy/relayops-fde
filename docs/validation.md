# Validation record

Executed on September 26, 2026. This record describes a synthetic portfolio demo, not a production certification or a customer-impact study.

## Local verification

Environment: Windows, Python 3.13.7, Node.js 24.19.0, pnpm 11.19.0, SQLite and Google Chrome. Dependencies are pinned in the backend/MCP requirements and frontend lockfile.

| Check | Observed result |
| --- | --- |
| Backend Pytest suite | **74 passed**; **96% statement coverage** (606 statements, 22 missed) |
| Frontend Vitest suite | **16 passed** |
| TypeScript and Vite production build | Passed |
| MCP suite | **12 passed**, including a real subprocess stdio handshake/tool discovery |
| Offline fixture evaluation | **8 / 8 passed**; [saved baseline JSON](evaluation-baseline.json) |
| Running API smoke workflow | Passed authentication, tenant isolation, repeated ingestion, cited analysis, approval replay, conflicting decisions, evaluation and audit checks |
| Browser workflow | Passed analysis, evidence, execution trace, approval, evaluation, document creation, audit visibility, duplicate import, empty search, tenant switching and invalid-key state clearing |
| Responsive browser check | 1440 × 1080 desktop and 390 × 844 mobile; no horizontal overflow or uncaught page errors in the exercised flow |
| Development launcher | Alternate API/UI ports, Vite proxy, tenant header forwarding, health check and Windows shutdown cleanup passed |

The 102 automated tests are distinct from the eight baseline evaluation scenarios. Parameterized backend cases include separate authentication checks for each protected business route. Coverage is statement coverage, not proof of correctness or security.

## Reproduce

```sh
# backend/ using the project's Python environment
python -m pytest --cov=app --cov-report=term-missing
python -m app.evaluate --output ../docs/evaluation-baseline.json

# repository root
pnpm --dir frontend test
pnpm --dir frontend build
python scripts/smoke.py --base-url http://127.0.0.1:8000

# separate MCP environment, dependencies from integrations/mcp/requirements-dev.txt
python -m pytest integrations/mcp -q
```

The local sandbox required a writable `--basetemp` directory for Pytest; normal environments can use its default. Browser checks used the production bundle served by FastAPI. Screenshots are real rendered application states from synthetic fixtures, not image mockups.

## CI and remaining limits

The [CI workflow](../.github/workflows/ci.yml) has backend, frontend, MCP, PostgreSQL API, and container jobs. See the [GitHub run history](https://github.com/muresaijaideepreddy/relayops-fde/actions/workflows/ci.yml) for the status of a specific revision. Docker and PostgreSQL were not available on the local Windows machine; their execution is verified separately by CI when a successful run is recorded.

No live OpenAI request was made. The optional provider adapter is covered with mocked responses for structured-output validation, refusals/incomplete responses, unexpected citation IDs, and sanitized provider failures. The deterministic evaluation is a small fixture regression suite using the bundled synthetic policies. It is not a held-out model quality benchmark, adversarial robustness assessment, load test, or a business efficiency measurement. Latencies in the saved baseline come from one local run and are not an SLA.

No actual CRM, email, refund or customer system was contacted. Approval only records a local simulated CRM note.
