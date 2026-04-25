from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register(data: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    user = await auth_service.register_user(data, db)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ip = request.client.host if request.client else ""
    access_token, refresh_token = await auth_service.login_user(data, db, ip)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(data: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    access_token = await auth_service.refresh_access_token(data.refresh_token, db)
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(data: LogoutRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    await auth_service.logout_user(data.refresh_token, db)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserRead)
async def get_me(current_user: CurrentUser):
    return current_user


@router.patch("/me/password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await auth_service.change_password(current_user, data, db)
    return MessageResponse(message="Password changed successfully")
