"""Version 1 API router."""

from fastapi import APIRouter

from .documents import router as documents_router
from .health import router as health_router
from .query import router as query_router
from .auth import router as auth_router
from .settings import router as settings_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(documents_router)
api_router.include_router(query_router)
api_router.include_router(auth_router)
api_router.include_router(settings_router)