"""Authentication endpoints for the single organization."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import create_access_token, hash_password, verify_password
from ...database import get_session
from ...models import Organization, User, UserRole
from ...schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


async def _token_response(user: User, request: Request) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user, request),
        user=UserResponse(id=str(user.id), email=user.email, role=user.role.value),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    existing_count = await session.scalar(select(func.count()).select_from(User))
    if existing_count:
        raise HTTPException(status_code=403, detail="Initial registration is complete")
    organization = await session.scalar(
        select(Organization).where(Organization.slug == request.app.state.settings.default_org_id)
    )
    if organization is None:
        organization = Organization(
            slug=request.app.state.settings.default_org_id, name="Droit Organization"
        )
        session.add(organization)
        await session.flush()
    user = User(
        organization_id=organization.id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.ADMIN,
    )
    session.add(user)
    await session.flush()
    return await _token_response(user, request)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    user = await session.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return await _token_response(user, request)