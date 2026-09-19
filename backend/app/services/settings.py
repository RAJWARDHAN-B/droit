"""Runtime configuration loaded from persisted organization settings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import SecretStr

from ..config import Settings
from ..core.pii import decrypt_value
from ..models import LLMSetting, Organization


async def effective_settings(
    session: AsyncSession, settings: Settings
) -> Settings:
    organization = await session.scalar(
        select(Organization).where(Organization.slug == settings.default_org_id)
    )
    if organization is None:
        return settings
    stored = await session.scalar(
        select(LLMSetting).where(LLMSetting.organization_id == organization.id)
    )
    if stored is None:
        return settings
    api_key = (
        SecretStr(decrypt_value(stored.api_key_encrypted, settings))
        if stored.api_key_encrypted
        else None
    )
    return settings.model_copy(
        update={
            "llm_provider": stored.provider,
            "llm_model": stored.model,
            "llm_base_url": stored.base_url,
            "llm_api_key": api_key,
        }
    )