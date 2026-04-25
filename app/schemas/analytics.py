import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.task import TaskStatus, TaskPriority


class OverviewStats(BaseModel):
    total_tasks: int
    pending: int
    in_progress: int
    under_review: int
    completed: int
    cancelled: int
    overdue: int


class OverdueTask(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    title: str
    status: TaskStatus
    priority: TaskPriority
    assigned_to: uuid.UUID
    due_date: datetime | None
