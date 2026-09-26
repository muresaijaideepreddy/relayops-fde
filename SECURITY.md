# Security scope

RelayOps is a portfolio demonstration with synthetic data and a local simulated CRM connector. It is not an audited multi-user production service. Built-in demo API keys are public by design; run demo mode on localhost.

Tenant filtering, structured output validation, bounded input, approval transactions and an audit history demonstrate application controls. They do not replace SSO, user roles, rate limiting, a secrets manager, a privacy review, backups, schema migrations, tamper-resistant audit storage or independent security testing.

Before a real pilot, disable demo mode, configure strong tenant keys, put the service behind TLS and an identity-aware gateway, define individual review permissions, assess the model provider's data terms, and implement the production readiness items in the runbook. Documents and tickets remain untrusted input. A valid citation ID does not prove a model's answer is factually correct.

For a vulnerability report, share a minimal reproduction using synthetic data through GitHub's private vulnerability reporting if available. Do not post credentials or customer data in a public issue.
