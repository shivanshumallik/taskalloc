import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.task import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to: uuid.UUID
    department_id: uuid.UUID | None = None
    due_date: datetime | None = None
    estimated_hours: float | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None
    estimated_hours: float | None = None
    actual_hours: float | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskAssignUpdate(BaseModel):
    assigned_to: uuid.UUID


class TaskFilter(BaseModel):
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assigned_to: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    due_before: datetime | None = None
    due_after: datetime | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 20
    sort_by: Literal["due_date", "created_at", "priority"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"


class TaskRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assigned_to: uuid.UUID
    assigned_by: uuid.UUID
    department_id: uuid.UUID | None
    due_date: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    estimated_hours: float | None
    actual_hours: float | None
    created_at: datetime
    updated_at: datetime
