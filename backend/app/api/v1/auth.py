"""Authentication endpoints for the single organization."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import Settings
from ...core.auth import create_access_token, hash_password, required_user, verify_password
from ...database import get_session
from ...models import Organization, User, UserRole
from ...schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


async def _token_response(user: User, request: Request, response: Response) -> TokenResponse:
    token = create_access_token(user, request)
    _set_session_cookie(response, token, request.app.state.settings)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=str(user.id), email=user.email, role=user.role.value),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
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
    return await _token_response(user, request, response)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    user = await session.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return await _token_response(user, request, response)


@router.get("/me", response_model=UserResponse)
async def me(user: Annotated[User, Depends(required_user)]) -> UserResponse:
    return UserResponse(id=str(user.id), email=user.email, role=user.role.value)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response) -> None:
    settings = request.app.state.settings
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )