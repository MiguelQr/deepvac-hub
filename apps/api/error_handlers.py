"""Maps domain exceptions (src/licensing/exceptions.py) to HTTP responses.

Centralized here so routers raise plain domain exceptions -- consistent
with "no business logic in routes" -- rather than each router hand-rolling
HTTPException with a guessed status code.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from licensing.exceptions import LicensingError, status_for


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(LicensingError)
    async def _handle_licensing_error(request: Request, exc: LicensingError) -> JSONResponse:
        return JSONResponse(status_code=status_for(exc), content={"detail": str(exc)})
