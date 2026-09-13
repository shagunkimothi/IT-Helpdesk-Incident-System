from datetime import datetime

from app.models import Incident
from app.services import calculate_priority, calculate_sla_due_at, is_overdue


def test_priority_for_all_impact_urgency_combinations():
    expected = {
        ("high", "high"): "critical",
        ("high", "medium"): "high",
        ("high", "low"): "high",
        ("medium", "high"): "high",
        ("medium", "medium"): "medium",
        ("medium", "low"): "medium",
        ("low", "high"): "high",
        ("low", "medium"): "medium",
        ("low", "low"): "low",
    }
    for inputs, priority in expected.items():
        assert calculate_priority(*inputs) == priority


def test_sla_duration_for_each_priority():
    created = datetime(2026, 9, 13, 9, 0)
    assert calculate_sla_due_at(created, "critical") == datetime(2026, 9, 13, 10, 0)
    assert calculate_sla_due_at(created, "high") == datetime(2026, 9, 13, 13, 0)
    assert calculate_sla_due_at(created, "medium") == datetime(2026, 9, 13, 17, 0)
    assert calculate_sla_due_at(created, "low") == datetime(2026, 9, 14, 9, 0)


def test_overdue_and_non_overdue_incidents():
    due = datetime(2026, 9, 13, 10, 0)
    incident = Incident(status="open", sla_due_at=due)
    assert is_overdue(incident, datetime(2026, 9, 13, 10, 1)) is True
    assert is_overdue(incident, datetime(2026, 9, 13, 9, 59)) is False


def test_resolved_before_sla_is_not_overdue():
    due = datetime(2026, 9, 13, 10, 0)
    incident = Incident(
        status="resolved",
        sla_due_at=due,
        resolved_at=datetime(2026, 9, 13, 9, 30),
    )
    assert is_overdue(incident, datetime(2026, 9, 13, 11, 0)) is False
