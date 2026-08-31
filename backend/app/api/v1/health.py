"""Service health endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", summary="Check whether the API process is running")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}