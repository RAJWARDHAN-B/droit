"""FastAPI application factory for Droit."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.responses import JSONResponse

from .api.v1.router import api_router
from .config import Settings, get_settings
from .core.embedding import QdrantVectorIndexer, VectorIndexer
from .core.generation import AnswerGenerator, LLMGenerator
from .core.retrieval import (
    CrossEncoderReranker,
    HybridRetriever,
    QdrantVectorSearcher,
)
from .core.risk import LLMRiskEnricher
from .database import create_engine, create_session_factory

logger = logging.getLogger("droit.api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_failed request_id=%s path=%s", request_id, request.url.path)
            raise
        duration_ms = (perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


def create_app(
    settings: Settings | None = None,
    vector_indexer: VectorIndexer | None = None,
    retriever: HybridRetriever | None = None,
    generator: AnswerGenerator | None = None,
) -> FastAPI:
    """Create and configure an isolated FastAPI application instance."""
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app_settings.upload_directory.mkdir(parents=True, exist_ok=True)
        engine = create_engine(app_settings)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.vector_indexer = vector_indexer or QdrantVectorIndexer(app_settings)
        app.state.retriever = retriever or HybridRetriever(
            QdrantVectorSearcher(app_settings),
            app_settings,
            reranker=CrossEncoderReranker(app_settings.retrieval_reranker_model),
        )
        app.state.generator = generator or LLMGenerator(app_settings)
        app.state.risk_enricher = LLMRiskEnricher(app.state.generator)
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(
        title=app_settings.app_name,
        debug=app_settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, _exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception("unhandled_exception request_id=%s path=%s", request_id, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected server error occurred",
                    "request_id": request_id,
                }
            },
            headers={"X-Request-ID": request_id},
        )
    app.state.settings = app_settings
    app.state.health_client = None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(api_router, prefix=app_settings.api_v1_prefix)
    return app


app = create_app()