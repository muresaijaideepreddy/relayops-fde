import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


NORTH = {"X-API-Key": "northstar-demo-key"}
MERIDIAN = {"X-API-Key": "meridian-demo-key"}


@pytest.fixture
def application(tmp_path):
    return create_app(Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}"))


@pytest.fixture
def client(application):
    with TestClient(application) as instance:
        yield instance


@pytest.fixture
def ticket(client):
    return next(
        t
        for t in client.get("/api/v1/tickets", headers=NORTH).json()
        if t["external_id"] == "NS-1042"
    )


@pytest.fixture
def action(client, ticket):
    result = client.post(f"/api/v1/tickets/{ticket['id']}/analyze", headers=NORTH)
    assert result.status_code == 200, result.text
    return result.json()["action_id"]
