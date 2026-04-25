import uuid
from datetime import datetime

from pydantic import BaseModel


class DepartmentCreate(BaseModel):
    name: str
    description: str | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class DepartmentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    created_by: uuid.UUID
