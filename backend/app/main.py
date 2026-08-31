"""FastAPI application factory for Droit."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.v1.router import api_router
from .config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure an isolated FastAPI application instance."""
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        app_settings.upload_directory.mkdir(parents=True, exist_ok=True)
        yield

    app = FastAPI(
        title=app_settings.app_name,
        debug=app_settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.include_router(api_router, prefix=app_settings.api_v1_prefix)
    return app


app = create_app()