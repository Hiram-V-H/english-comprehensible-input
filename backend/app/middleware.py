from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from .exceptions import AppException


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "detail": exc.detail, "code": exc.code},
    )
