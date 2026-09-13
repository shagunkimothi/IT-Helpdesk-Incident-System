from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import Category, Incident, User, utc_now

SLA_HOURS = {"critical": 1, "high": 4, "medium": 8, "low": 24}
IMPACT_URGENCY_LEVELS = {"low": 1, "medium": 2, "high": 3}
VALID_TRANSITIONS = {
    "open": {"in_progress"},
    "in_progress": {"open", "resolved"},
    "resolved": {"in_progress", "closed"},
    "closed": set(),
}


def calculate_sla_due_at(created_at: datetime, priority: str) -> datetime:
    return created_at + timedelta(hours=SLA_HOURS[priority])


def calculate_priority(impact: str, urgency: str) -> str:
    impact = impact.lower()
    urgency = urgency.lower()
    impact_level = IMPACT_URGENCY_LEVELS[impact]
    urgency_level = IMPACT_URGENCY_LEVELS[urgency]
    if impact == "high" and urgency == "high":
        return "critical"
    if max(impact_level, urgency_level) == IMPACT_URGENCY_LEVELS["high"]:
        return "high"
    if max(impact_level, urgency_level) == IMPACT_URGENCY_LEVELS["medium"]:
        return "medium"
    return "low"


def is_overdue(incident: Incident, now: datetime | None = None) -> bool:
    comparison_time = incident.resolved_at if incident.resolved_at else (now or utc_now())
    return comparison_time > incident.sla_due_at


def sla_status(incident: Incident, now: datetime | None = None) -> str:
    return "Overdue" if is_overdue(incident, now) else "Not overdue"


def get_or_404(db: Session, model: type, object_id: int):
    instance = db.get(model, object_id)
    if instance is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return instance


def validate_references(
    db: Session,
    requester_id: int,
    category_id: int,
    assignee_id: int | None,
) -> tuple[User, Category, User | None]:
    requester = get_or_404(db, User, requester_id)
    category = get_or_404(db, Category, category_id)
    assignee = get_or_404(db, User, assignee_id) if assignee_id else None
    if assignee and assignee.role not in {"agent", "admin"}:
        raise HTTPException(status_code=400, detail="Assignee must be an agent or admin")
    return requester, category, assignee


def change_status(incident: Incident, new_status: str) -> None:
    if new_status == incident.status:
        return
    if new_status not in VALID_TRANSITIONS[incident.status]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition incident from {incident.status} to {new_status}",
        )
    if new_status == "in_progress" and incident.assignee_id is None:
        raise HTTPException(status_code=400, detail="Incident must be assigned before work starts")
    now = utc_now()
    incident.status = new_status
    if new_status == "resolved":
        incident.resolved_at = now
    elif new_status == "closed":
        incident.closed_at = now
    elif new_status == "in_progress" and incident.resolved_at:
        incident.resolved_at = None
