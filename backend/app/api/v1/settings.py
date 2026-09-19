"""Admin-managed LLM settings."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import AdminUser
from ...core.pii import encrypt_value
from ...database import get_session
from ...models import LLMSetting, Organization
from ...schemas import LLMSettingsRequest, LLMSettingsResponse
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