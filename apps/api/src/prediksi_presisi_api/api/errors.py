"""Format kesalahan baku (TASK 030, docs/05 §1).

Seluruh kesalahan keluar dalam satu bentuk:

```json
{"error": {"code": "...", "message": "...", "details": [...], "request_id": "..."}}
```

`request_id` selalu ikut, sehingga keluhan pengguna dapat ditelusuri ke baris log
dan ke audit trail tanpa menebak.

Pesan kesalahan **tidak pernah** memuat query, stack trace, maupun struktur internal
(CLAUDE.md §28, docs/05 §3).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("prediksi_presisi.api")

#: Pemetaan status HTTP ke kode kesalahan pada kontrak API (docs/05 §1).
STATUS_CODES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "VALIDATION_ERROR",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHENTICATED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_409_CONFLICT: "CONFLICT",
    422: "BUSINESS_RULE_VIOLATION",  # nama konstanta Starlette berubah antar versi
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
}


class ApiError(Exception):
    """Kesalahan yang sudah dipahami aplikasi dan aman ditampilkan ke klien."""

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        code: str | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.code = code or STATUS_CODES.get(status_code, "INTERNAL_ERROR")
        self.details = details or []


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": getattr(request.state, "request_id", ""),
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
        return error_response(request, exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = STATUS_CODES.get(exc.status_code, "INTERNAL_ERROR")
        return error_response(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Kontrak memakai 400 VALIDATION_ERROR, bukan 422 bawaan FastAPI (docs/05 §1);
        # 422 disediakan untuk pelanggaran aturan bisnis.
        details = [
            {"field": ".".join(str(part) for part in error["loc"][1:]), "issue": error["msg"]}
            for error in exc.errors()
        ]
        return error_response(
            request,
            status.HTTP_400_BAD_REQUEST,
            "VALIDATION_ERROR",
            "Permintaan tidak valid.",
            details,
        )

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Detail dicatat ke log, bukan dikirim ke klien.
        logger.exception(
            "kesalahan tak terduga", extra={"request_id": getattr(request.state, "request_id", "")}
        )
        return error_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "Terjadi kesalahan pada server.",
        )
