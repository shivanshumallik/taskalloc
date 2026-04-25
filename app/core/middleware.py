import time
import uuid
from typing import Callable

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import AsyncSessionLocal


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Writes an AuditLog record for every mutating request (POST/PATCH/DELETE)."""

    SKIP_PATHS = {"/health", "/health/db", "/docs", "/openapi.json", "/redoc"}
    MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        response = await call_next(request)

        if (
            request.method in self.MUTATING_METHODS
            and request.url.path not in self.SKIP_PATHS
        ):
            try:
                await self._write_audit_log(request, response, start)
            except Exception:
                pass  # Never let audit logging crash the app

        return response

    async def _write_audit_log(self, request: Request, response: Response, start: float):
        from app.models.audit_log import AuditLog

        user_id = None
        try:
            from app.core.security import decode_access_token
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                payload = decode_access_token(auth[7:])
                if payload:
                    user_id = payload.get("sub")
        except Exception:
            pass

        path_parts = request.url.path.strip("/").split("/")
        resource = path_parts[0] if path_parts else "unknown"
        resource_id = path_parts[1] if len(path_parts) > 1 else ""

        log = AuditLog(
            user_id=user_id,
            action=request.method,
            resource=resource,
            resource_id=resource_id,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", ""),
            status_code=response.status_code,
        )

        async with AsyncSessionLocal() as session:
            session.add(log)
            await session.commit()
