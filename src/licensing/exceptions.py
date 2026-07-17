"""Domain exceptions. Routers/views translate these to HTTP responses; the
service layer never raises framework-specific exceptions.
"""


class LicensingError(Exception):
    """Base class for all domain errors raised by src/licensing."""


class NotFoundError(LicensingError):
    pass


class ConflictError(LicensingError):
    """E.g. duplicate device key, duplicate active membership, seat already assigned."""


class SeatLimitExceededError(LicensingError):
    pass


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
