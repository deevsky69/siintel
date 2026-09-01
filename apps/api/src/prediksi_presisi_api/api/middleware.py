"""Middleware permintaan (TASK 030)."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("prediksi_presisi.api")

#: Header yang membuat satu permintaan dapat ditelusuri dari klien sampai audit trail.
REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Memberi setiap permintaan satu identitas dan mencatat lamanya."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id

        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000

        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "%s %s %s %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            extra={"request_id": request_id},
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Header keamanan dasar (CLAUDE.md §28).

    HSTS sengaja tidak dipasang di sini: nilainya ditentukan reverse proxy yang
    memegang sertifikat, dan memasangnya dari aplikasi pada demo non-HTTPS justru
    mengunci peramban ke skema yang belum tersedia.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        return response
