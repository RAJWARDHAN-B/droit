"""Service health endpoints."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_session

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", summary="Check whether the API process is running")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Check whether required dependencies are available")
async def readiness(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    checks: dict[str, str] = {}
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = "unavailable"
        raise HTTPException(status_code=503, detail={"status": "not_ready", **checks}) from exc

    try:
        client_factory = request.app.state.health_client or httpx.AsyncClient(timeout=2.0)
        async with client_factory as client:
            response = await client.get(f"{request.app.state.settings.qdrant_url}/healthz")
            response.raise_for_status()
        checks["qdrant"] = "ok"
    except httpx.HTTPError:
        checks["qdrant"] = "unavailable"
        raise HTTPException(status_code=503, detail={"status": "not_ready", **checks})

    return {"status": "ready", **checks}