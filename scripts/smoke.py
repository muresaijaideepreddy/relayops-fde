"""Exercise a running DEMO instance with synthetic data. No external API calls.

Usage: python scripts/smoke.py --base-url http://127.0.0.1:8000
Creates a demo ticket and one approved local CRM note; safe to run repeatedly.
"""

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    def request(path, method="GET", body=None, key="northstar-demo-key", expected=200):
        headers = {"Content-Type": "application/json"}
        if key:
            headers["X-API-Key"] = key
        req = Request(
            base + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(req, timeout=30) as response:
                status, data = response.status, response.read()
        except HTTPError as error:
            status, data = error.code, error.read()
        assert status == expected, (
            f"{method} {path}: expected {expected}, got {status}: {data[:300]!r}"
        )
        return json.loads(data) if data else None

    for attempt in range(60):
        try:
            health = request("/health", key=None)
            assert health["status"] == "ok"
            break
        except (URLError, ConnectionError):
            if attempt == 59:
                raise
            time.sleep(1)

    prefix = "/api/v1"
    request(prefix + "/tickets", key=None, expected=401)
    northstar = request(prefix + "/workspace")
    meridian = request(prefix + "/workspace", key="meridian-demo-key")
    assert northstar["tenant"]["id"] != meridian["tenant"]["id"]
    assert northstar["mode"] == "demo", "Smoke tests must run in demo mode"
    payload = {
        "tickets": [
            {
                "external_id": "SMOKE-SHIPMENT-001",
                "title": "Shipment tracking stopped updating",
                "body": "Our shipment tracking has no scan update for 48 hours. How do we investigate the delayed delivery?",
                "customer": "Synthetic Smoke Customer",
                "priority": "high",
            }
        ]
    }
    first = request(prefix + "/ingest", "POST", payload)
    assert first["imported"] + first["skipped"] == 1
    repeat = request(prefix + "/ingest", "POST", payload)
    assert repeat == {"imported": 0, "skipped": 1}
    ticket = next(
        t for t in request(prefix + "/tickets") if t["external_id"] == "SMOKE-SHIPMENT-001"
    )
    ticket_path = prefix + "/tickets/" + ticket["id"]
    request(ticket_path, key="meridian-demo-key", expected=404)
    analysis = request(ticket_path + "/analyze", "POST")
    assert analysis["citations"], "Known shipment question should retrieve seeded evidence"
    assert analysis["steps"] and analysis["draft_reply"] and analysis["provider"] == "demo"
    action_path = prefix + "/actions/" + analysis["action_id"] + "/approve"
    request(
        action_path,
        "POST",
        {"decision": "approve", "note": "Tenant isolation check"},
        key="meridian-demo-key",
        expected=404,
    )
    decision = {"decision": "approve", "note": "Synthetic smoke test; local simulation only."}
    approved = request(action_path, "POST", decision)
    repeated = request(action_path, "POST", decision)
    assert approved == repeated and approved["status"] == "approved"
    request(action_path, "POST", {"decision": "reject", "note": "Conflict test"}, expected=409)
    evaluation = request(prefix + "/evaluations/run", "POST")
    assert evaluation["total"] > 0 and evaluation["passed"] == evaluation["total"], evaluation
    assert request(prefix + "/audit")
    assert request(prefix + "/metrics")["approved_actions"] >= 1
    print(
        json.dumps(
            {
                "status": "passed",
                "checks": [
                    "health",
                    "authentication",
                    "tenant isolation",
                    "ingestion replay",
                    "grounded analysis",
                    "approval replay",
                    "decision conflict",
                    "evaluation",
                    "audit",
                ],
                "evaluation_passed": evaluation["passed"],
                "evaluation_total": evaluation["total"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
