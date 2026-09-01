"""Aplikasi FastAPI PREDIKSI PRESISI.

Urutan lapisan mengikuti CLAUDE.md §21:
Authentication → Authorization → Input Validation → Business Logic → Database → Response.

Endpoint domain baru ditambahkan setelah otorisasi dan audit hidup — itu sebabnya
TASK 050–053 dikerjakan sebelum TASK 031–040 (docs/08 PHASE 4).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api.errors import register_error_handlers
from .api.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from .api.routers import auth, catalog, dashboard, evaluation, health, intelligence
from .config import get_settings

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app = FastAPI(
        title="PREDIKSI PRESISI API",
        version=__version__,
        description=(
            "Sistem pendukung keputusan Kamtibmas. "
            "Seluruh endpoint sensitif memerlukan authentication dan authorization."
        ),
        docs_url=None if settings.app_env == "production" else "/docs",
        redoc_url=None,
        openapi_url=None if settings.app_env == "production" else "/openapi.json",
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    register_error_handlers(app)

    api = APIRouter(prefix=API_PREFIX)
    api.include_router(health.router)
    api.include_router(auth.router)
    api.include_router(catalog.router)
    api.include_router(intelligence.router)
    api.include_router(dashboard.router)
    api.include_router(evaluation.router)
    app.include_router(api)

    return app


app = create_app()
