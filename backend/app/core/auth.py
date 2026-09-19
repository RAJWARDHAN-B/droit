"""JWT authentication and role dependencies."""

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import User, UserRole

_bearer = HTTPBearer(auto_error=False)
_passwords = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _passwords.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _passwords.verify(password, password_hash)


def create_access_token(user: User, request: Request) -> str:
    settings = request.app.state.settings
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": str(user.id), "role": user.role.value, "exp": expires},
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


async def current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User | None:
    if credentials is None:
        if request.app.state.settings.auth_required:
            raise HTTPException(status_code=401, detail="Authentication required")
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            request.app.state.settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
        )
        user_id = UUID(str(payload["sub"]))
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid authentication token") from exc
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive or unknown user")
    return user


async def required_user(user: Annotated[User | None, Depends(current_user)]) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def require_roles(*roles: UserRole):
    async def dependency(user: Annotated[User, Depends(required_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
RevealUser = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST))]