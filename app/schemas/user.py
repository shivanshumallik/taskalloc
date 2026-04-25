import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.user import Role


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    username: str
    email: EmailStr
    role: Role
    is_active: bool
    is_verified: bool
    last_login: datetime | None
    created_at: datetime


class UserUpdate(BaseModel):
    username: str | None = None
    email: EmailStr | None = None


class UserRoleUpdate(BaseModel):
    role: Role


class UserListResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    username: str
    email: str
    role: Role
    is_active: bool
    created_at: datetime
