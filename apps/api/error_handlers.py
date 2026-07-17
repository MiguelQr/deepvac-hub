"""Maps domain exceptions (src/licensing/exceptions.py) to HTTP responses.

Centralized here so routers raise plain domain exceptions -- consistent
with "no business logic in routes" -- rather than each router hand-rolling
HTTPException with a guessed status code.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from licensing.exceptions import (
    AccountDisabledError,
    ActivationAlreadyConsumedError,
    ActivationExpiredError,
    ActivationNotApprovedError,
    ChallengeAlreadyConsumedError,
    ChallengeExpiredError,
    ConflictError,
    DeviceLimitExceededError,
    DeviceRevokedError,
    EntitlementError,
    InvalidCredentialsError,
    InvalidSignatureError,
    LicensingError,
    NotFoundError,
    PermissionDeniedError,
    SeatLimitExceededError,
)

_STATUS_BY_EXCEPTION: dict[type[LicensingError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    SeatLimitExceededError: 409,
    DeviceLimitExceededError: 409,
    InvalidCredentialsError: 401,
    AccountDisabledError: 403,
    ActivationExpiredError: 410,
    ActivationAlreadyConsumedError: 409,
    ActivationNotApprovedError: 409,
    EntitlementError: 403,
    ChallengeExpiredError: 410,
    ChallengeAlreadyConsumedError: 409,
    InvalidSignatureError: 401,
    DeviceRevokedError: 403,
    PermissionDeniedError: 403,
}


def _status_for(exc: LicensingError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION.items():
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(LicensingError)
    async def _handle_licensing_error(request: Request, exc: LicensingError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"detail": str(exc)})
