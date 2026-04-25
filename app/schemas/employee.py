import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr


class EmployeeCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    department_id: uuid.UUID
    designation: str
    date_joined: date
    user_id: uuid.UUID


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    department_id: uuid.UUID | None = None
    designation: str | None = None


class EmployeeRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    full_name: str
    email: str
    phone: str | None
    department_id: uuid.UUID
    designation: str
    date_joined: date
    user_id: uuid.UUID
    is_active: bool
    created_at: datetime


class EmployeeStats(BaseModel):
    employee_id: uuid.UUID
    full_name: str
    total_tasks: int
    pending: int
    in_progress: int
    under_review: int
    completed: int
    cancelled: int
    overdue: int
