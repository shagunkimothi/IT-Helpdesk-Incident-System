from fastapi.testclient import TestClient

from app.database import engine
from app.main import app
from app.models import IncidentEvent


def test_health():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_create_and_validate_incident():
    with TestClient(app) as client:
        client.get("/health")
        response = client.post(
            "/incidents",
            json={
                "title": "VPN unavailable",
                "description": "Remote access is failing.",
                "priority": "high",
                "requester_id": 3,
                "category_id": 3,
                "assignee_id": 1,
            },
        )
        assert response.status_code == 201
        incident = response.json()
        assert incident["status"] == "open"
        assert incident["is_overdue"] is False
        assert incident["sla_status"] == "Not overdue"
        with engine.connect() as connection:
            events = connection.execute(
                IncidentEvent.__table__.select().where(
                    IncidentEvent.incident_id == incident["id"]
                )
            ).fetchall()
        assert len(events) == 1
        assert events[0].event_type == "created"

        invalid = client.patch(
            f"/incidents/{incident['id']}/status",
            json={"status": "closed"},
        )
        assert invalid.status_code == 400
