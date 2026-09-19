"""Admin-managed LLM settings."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import AdminUser
from ...core.generation import LLMGenerator
from ...core.pii import encrypt_value
from ...database import get_session
from ...models import LLMSetting, Organization
from ...schemas import ConnectionTestResponse, LLMSettingsRequest, LLMSettingsResponse
from ...services.audit import record_audit

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/llm", response_model=LLMSettingsResponse)
async def get_llm_settings(
    request: Request,
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LLMSettingsResponse:
    setting = await session.scalar(
        select(LLMSetting).where(LLMSetting.organization_id == user.organization_id)
    )
    if setting is None:
        return LLMSettingsResponse(
            provider=request.app.state.settings.llm_provider,
            model=request.app.state.settings.llm_model,
            base_url=request.app.state.settings.llm_base_url,
            api_key_configured=request.app.state.settings.llm_api_key is not None,
        )
    return LLMSettingsResponse(
        provider=setting.provider,
        model=setting.model,
        base_url=setting.base_url,
        api_key_configured=setting.api_key_encrypted is not None,
    )


@router.put("/llm", response_model=LLMSettingsResponse)
async def update_llm_settings(
    payload: LLMSettingsRequest,
    request: Request,
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LLMSettingsResponse:
    setting = await session.scalar(
        select(LLMSetting).where(LLMSetting.organization_id == user.organization_id)
    )
    if setting is None:
        setting = LLMSetting(
            organization_id=user.organization_id,
            provider=payload.provider.lower(),
            model=payload.model,
            base_url=payload.base_url,
            api_key_encrypted=encrypt_value(payload.api_key, request.app.state.settings)
            if payload.api_key
            else None,
        )
        session.add(setting)
    else:
        setting.provider = payload.provider.lower()
        setting.model = payload.model
        setting.base_url = payload.base_url
        if payload.api_key:
            setting.api_key_encrypted = encrypt_value(payload.api_key, request.app.state.settings)
    await record_audit(session, request, user=user, action="llm_settings.updated", resource_type="llm_settings")
    return LLMSettingsResponse(
        provider=setting.provider,
        model=setting.model,
        base_url=setting.base_url,
        api_key_configured=setting.api_key_encrypted is not None,
    )


@router.post("/llm/test", response_model=ConnectionTestResponse)
async def test_llm_settings(
    payload: LLMSettingsRequest,
    request: Request,
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConnectionTestResponse:
    from ...services.settings import effective_settings

    configured = await effective_settings(session, request.app.state.settings)
    test_settings = configured.model_copy(
        update={
            "llm_provider": payload.provider.lower(),
            "llm_model": payload.model,
            "llm_base_url": payload.base_url,
        }
    )
    if payload.api_key:
        from pydantic import SecretStr

        test_settings.llm_api_key = SecretStr(payload.api_key)
    try:
        await LLMGenerator(test_settings).test_connection()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="The language model provider is unavailable") from exc
    return ConnectionTestResponse(success=True, message="Connection successful")