from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Incident, IncidentComment, IncidentEvent, User, utc_now
from ..schemas import (
    CommentCreate,
    CommentRead,
    IncidentCreate,
    IncidentRead,
    IncidentStatus,
    IncidentUpdate,
    Priority,
    StatusUpdate,
)
from ..services import (
    calculate_sla_due_at,
    change_status,
    get_or_404,
    is_overdue,
    sla_status,
    validate_references,
)

router = APIRouter(prefix="/incidents", tags=["incidents"])


def incident_response(incident: Incident) -> IncidentRead:
    return IncidentRead.model_validate(
        {
            **incident.__dict__,
            "is_overdue": is_overdue(incident),
            "sla_status": sla_status(incident),
        }
    )


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    requester, category, assignee = validate_references(
        db, payload.requester_id, payload.category_id, payload.assignee_id
    )
    created_at = utc_now()
    incident = Incident(
        **payload.model_dump(),
        created_at=created_at,
        updated_at=created_at,
        sla_due_at=calculate_sla_due_at(created_at, payload.priority.value),
    )
    db.add(incident)
    db.flush()
    db.add(
        IncidentEvent(
            incident_id=incident.id,
            event_type="created",
            description=f"Incident created with {incident.priority.value} priority",
        )
    )
    db.commit()
    db.refresh(incident)
    return incident_response(incident)


@router.get("", response_model=list[IncidentRead])
def list_incidents(
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    assignee_id: int | None = None,
    category_id: int | None = None,
    requester_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Incident)
    if status_filter:
        query = query.filter(Incident.status == status_filter.value)
    if priority:
        query = query.filter(Incident.priority == priority.value)
    for field, value in (
        (Incident.assignee_id, assignee_id),
        (Incident.category_id, category_id),
        (Incident.requester_id, requester_id),
    ):
        if value is not None:
            query = query.filter(field == value)
    return [incident_response(item) for item in query.order_by(Incident.created_at.desc()).all()]


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    return incident_response(get_or_404(db, Incident, incident_id))


@router.put("/{incident_id}", response_model=IncidentRead)
def update_incident(incident_id: int, payload: IncidentUpdate, db: Session = Depends(get_db)):
    incident = get_or_404(db, Incident, incident_id)
    if incident.status == "closed":
        raise HTTPException(status_code=400, detail="Closed incidents cannot be modified")
    values = payload.model_dump(exclude_unset=True)
    if "category_id" in values or "assignee_id" in values:
        validate_references(
            db,
            incident.requester_id,
            values.get("category_id", incident.category_id),
            values.get("assignee_id", incident.assignee_id),
        )
    if "priority" in values:
        values["priority"] = values["priority"].value
        incident.sla_due_at = calculate_sla_due_at(incident.created_at, values["priority"])
    for key, value in values.items():
        setattr(incident, key, value)
    incident.updated_at = utc_now()
    db.add(
        IncidentEvent(
            incident_id=incident.id,
            event_type="updated",
            description=f"Incident fields updated: {', '.join(values)}",
        )
    )
    db.commit()
    db.refresh(incident)
    return incident_response(incident)


@router.patch("/{incident_id}/status", response_model=IncidentRead)
def update_status(incident_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    incident = get_or_404(db, Incident, incident_id)
    change_status(incident, payload.status.value)
    incident.updated_at = utc_now()
    db.add(
        IncidentEvent(
            incident_id=incident.id,
            event_type="status_changed",
            description=f"Incident status changed to {incident.status}",
        )
    )
    db.commit()
    db.refresh(incident)
    return incident_response(incident)


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = get_or_404(db, Incident, incident_id)
    db.delete(incident)
    db.commit()


@router.post("/{incident_id}/comments", response_model=CommentRead, status_code=201)
def add_comment(incident_id: int, payload: CommentCreate, db: Session = Depends(get_db)):
    get_or_404(db, Incident, incident_id)
    get_or_404(db, User, payload.author_id)
    comment = IncidentComment(incident_id=incident_id, **payload.model_dump())
    db.add(comment)
    db.add(
        IncidentEvent(
            incident_id=incident_id,
            event_type="comment_added",
            description="Incident comment added",
        )
    )
    db.commit()
    db.refresh(comment)
    return comment


@router.get("/{incident_id}/comments", response_model=list[CommentRead])
def list_comments(incident_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Incident, incident_id)
    return (
        db.query(IncidentComment)
        .filter(IncidentComment.incident_id == incident_id)
        .order_by(IncidentComment.created_at)
        .all()
    )
