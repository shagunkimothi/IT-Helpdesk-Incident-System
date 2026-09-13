from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRole(str, Enum):
    requester = "requester"
    agent = "agent"
    admin = "admin"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    role: UserRole = UserRole.requester

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Invalid email address")
        return value


class UserRead(UserCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class CategoryRead(CategoryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    priority: Priority = Priority.medium
    requester_id: int = Field(gt=0)
    category_id: int = Field(gt=0)
    assignee_id: int | None = Field(default=None, gt=0)


class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    priority: Priority | None = None
    category_id: int | None = Field(default=None, gt=0)
    assignee_id: int | None = Field(default=None, gt=0)


class StatusUpdate(BaseModel):
    status: IncidentStatus


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: IncidentStatus
    priority: Priority
    requester_id: int
    assignee_id: int | None
    category_id: int
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None
    sla_due_at: datetime
    is_overdue: bool
    sla_status: str


class CommentCreate(BaseModel):
    author_id: int = Field(gt=0)
    content: str = Field(min_length=1)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    author_id: int
    content: str
    created_at: datetime
