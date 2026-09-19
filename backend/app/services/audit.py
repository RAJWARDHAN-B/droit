"""Audit event persistence."""

from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLog, User


async def record_audit(
    session: AsyncSession,
    request: Request,
    *,
    user: User,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    details: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditLog(
            organization_id=user.organization_id,
            user_id=user.id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=details or {},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    )