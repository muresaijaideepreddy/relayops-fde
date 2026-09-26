# Contributing

Use synthetic tickets and documents in examples and tests. Start from the local setup in the README.

Before opening a pull request, run the backend tests and offline evaluation, the frontend type check/tests/build, and `python scripts/smoke.py` against a local demo server. Include a screenshot for interface changes and the relevant evaluation case for retrieval or policy changes.

Preserve the tenant boundary in every read and write. Analysis may propose an action; only the approval route may apply a local simulated CRM note. Never put API keys, real support exports, local databases, or `.env` files in a commit. Keep new providers and connectors opt-in and mock their network calls in tests.

Describe the user problem, the resulting behavior, and how it was verified. Document changed configuration and known limits alongside the code.
