"""LLM settings API schemas."""

from pydantic import BaseModel, Field


class LLMSettingsRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=50)
    model: str = Field(min_length=1, max_length=200)
    base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=500)


class LLMSettingsResponse(BaseModel):
    provider: str
    model: str
    base_url: str | None
    api_key_configured: bool


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str