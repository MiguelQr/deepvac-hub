"""Domain exceptions. Routers/views translate these to HTTP responses; the
service layer never raises framework-specific exceptions.
"""


class LicensingError(Exception):
    """Base class for all domain errors raised by src/licensing."""


class NotFoundError(LicensingError):
    pass


class ConflictError(LicensingError):
    """E.g. duplicate device key, duplicate active membership."""


class DeviceLimitExceededError(LicensingError):
    pass


class InvalidCredentialsError(LicensingError):
    """Deliberately generic — never distinguishes "wrong password" from
    "unknown user" to the caller.
    """


class AccountDisabledError(LicensingError):
    pass


class ActivationExpiredError(LicensingError):
    pass


class ActivationAlreadyConsumedError(LicensingError):
    pass


class ActivationNotApprovedError(LicensingError):
    pass


class EntitlementError(LicensingError):
    """Organization license missing, inactive, or expired for the requested product/edition."""


class ChallengeExpiredError(LicensingError):
    pass


class ChallengeAlreadyConsumedError(LicensingError):
    pass


class InvalidSignatureError(LicensingError):
    pass


class DeviceRevokedError(LicensingError):
    pass


class PermissionDeniedError(LicensingError):
    pass


class ProhibitedFieldError(LicensingError):
    """Raised by the audit allow-list guard when a caller attempts to log a
    field name outside the licensing-metadata allow-list — see
    licensing/audit/allowlist.py and docs/privacy.md.
    """


EXCEPTION_STATUS_MAP: dict[type[LicensingError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
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
"""Shared HTTP-status mapping used by both apps/api/error_handlers.py and
apps/web/errors.py, so the two surfaces don't drift out of sync."""


def status_for(exc: LicensingError) -> int:
    for exc_type, status_code in EXCEPTION_STATUS_MAP.items():
        if isinstance(exc, exc_type):
            return status_code
    return 400
