# Local runbook

RelayOps defaults to synthetic workspaces, an offline deterministic provider, and a local simulated CRM. Use the [README](../README.md) for dependency installation and the exact project scripts. Use [validation](validation.md) for the environments and commands actually verified.

## Start and verify

The project targets Python 3.13, Node.js 24, and pnpm 11.19.0. After installing dependencies as described in the README, use the project virtual environment's Python to start both servers from the repository root:

```powershell
python scripts/dev.py
```

To start the processes separately for debugging, start the API from `backend/`:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, start the frontend from `frontend/`:

```powershell
pnpm dev
```

The frontend uses a Vite proxy to the API. Run `pnpm build` from `frontend/` for a compiled single-origin application; the backend serves `frontend/dist` when it exists. Restart the backend if it was started before the build directory existed.

Docker Compose provides an alternative local runtime from the repository root:

```powershell
docker compose up --build
```

For the PostgreSQL demonstration:

```powershell
docker compose -f compose.yaml -f compose.postgres.yaml up --build
```

Both expose the application at `http://localhost:8000` and retain data in named Docker volumes. The PostgreSQL override uses public local demo database credentials. See [validation](validation.md) before assuming these container paths were executed on the current development machine.

Check the public health endpoint:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health'
```

Then verify a business route with the Northstar demo key:

```powershell
$relayHeaders = @{ 'X-API-Key' = 'northstar-demo-key' }
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/workspace' -Headers $relayHeaders
```

`meridian-demo-key` selects the second fictional tenant. The built-in keys work only when demo mode is enabled. They are public demo values, not private credentials. API provider credentials belong only on the server; never paste an `OPENAI_API_KEY` into the browser's tenant key control.

## Smoke workflow

1. Open a seeded ticket and run analysis. Confirm evidence, provider identity, and a pending action appear.
2. Review the action and approve or reject it. Approval should create only a local simulated note. Rejection should leave no connector write.
3. Inspect the audit view for the decision and its entity.
4. Run the evaluation view. It always executes the offline deterministic baseline, even when the analysis provider is configured as OpenAI.
5. Switch tenants and confirm the workbench reloads that tenant's data.

Do not use a browser-only smoke check as a substitute for the API tests that verify authorization boundaries.

## Configuration

| Setting | Meaning |
| --- | --- |
| `DEMO_MODE` | `true` by default; permits built-in demo keys and synthetic seed data |
| `TENANT_API_KEYS` | JSON object mapping custom keys to `{ "id": "tenant-id", "name": "Tenant name" }`; required when demo mode is `false` |
| `DATABASE_URL` | Defaults to `sqlite:///./relayops.db`; PostgreSQL URLs must use `postgresql+psycopg://` |
| `AI_PROVIDER` | `demo` for deterministic offline analysis, or `openai` for an explicitly enabled live provider |
| `OPENAI_API_KEY` | Server-side provider credential required for live analysis |
| `OPENAI_MODEL` | Explicit model identifier required for live analysis; there is no implicit model choice |

Read the repository's environment example and [backend settings](../backend/app/config.py) for the complete configuration. Custom keys must be at least 24 characters and cannot equal the published demo keys. A custom tenant starts empty and needs imported tickets and knowledge. Invalid or unsafe configuration must be corrected before startup; do not weaken its validation to make an environment start.

Live analysis sends the selected ticket and retrieved context to the configured provider and can incur usage charges. It requires an account credential and separately validated data-handling settings. The offline demo and evaluation path do not require live-model calls.

## Troubleshooting

| Symptom | Check and response |
| --- | --- |
| Frontend reports API unavailable | Verify `/health`, backend port 8000, and the frontend proxy. Read the API terminal error and retry after recovery. |
| HTTP 401 or invalid key | Use the tenant key, verify demo mode or custom credential configuration, and reload the workspace. A provider key is not a tenant key. |
| HTTP 404 for a known ticket | Confirm the current tenant; inaccessible IDs must remain inaccessible. Do not remove tenant filters. |
| HTTP 409 on an action | The action already has a different decision. Inspect the saved result; do not bypass the decision guard. |
| Duplicate import is skipped | The `external_id` already exists for that tenant. Use a genuinely new external ID for a different ticket. |
| Input validation error | Check required JSON fields and bounds: at most 100 tickets per ingest, 10,000 characters per ticket body, and 20,000 characters per document. |
| Analysis has weak or missing evidence | Check tenant knowledge, policy wording, and the retrieved excerpts. Improve the corpus or escalate; do not treat a low-evidence draft as verified. |
| Live-provider request fails with HTTP 502 | Check server-side credential/model configuration, network availability, and provider error details. Refusals, provider failures, or invalid cited output must not persist a successful analysis or action. |
| New build is not visible | Confirm the build completed to `frontend/dist`, restart the API if needed, and refresh the browser. |

## Data recovery and diagnosis

The local database contains imported synthetic data, analyses, decisions, audit events, and evaluation runs. Stop the API before copying a SQLite database for a consistent local backup. Determine the actual path from `DATABASE_URL` or backend settings rather than guessing. Keep a backup before any reset. Deleting a database destroys its local history; seed data can be recreated in demo mode, but prior decisions cannot.

For PostgreSQL, use that deployment's database backup and restore procedure. This repository does not establish a production recovery point or recovery time objective. Never paste provider secrets or real customer payloads into a public GitHub issue.

When reporting a bug, include the revision, provider mode, database type, route or UI action, HTTP status, expected behavior, and the relevant sanitized error. The application audit view and analysis trace explain workflow events; they are not a replacement for a centralized production logging system.

## Before a real pilot

Complete the [pilot plan](customer-discovery.md) and the missing controls in [architecture](architecture.md#trust-boundaries). A production operating owner must define alerting, rollback, backups, quotas, secret rotation, incident response, and access review. Record actual live-provider and connector validation separately from the offline baseline.
