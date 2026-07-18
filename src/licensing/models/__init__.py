"""Import every model module so licensing.database.Base.metadata is complete
for Alembic autogenerate and for tests that call Base.metadata.create_all().
"""

from licensing.models.activation import ActivationRequest, RefreshChallenge
from licensing.models.audit import AuditEvent
from licensing.models.certificates import IssuedLicenseCertificate, SigningKey
from licensing.models.devices import DeviceActivation
from licensing.models.licenses import OrganizationLicense
from licensing.models.organizations import Organization, OrganizationMembership
from licensing.models.products import Edition, EditionFeature, Feature, Product
from licensing.models.users import User

__all__ = [
    "ActivationRequest",
    "RefreshChallenge",
    "AuditEvent",
    "IssuedLicenseCertificate",
    "SigningKey",
    "DeviceActivation",
    "OrganizationLicense",
    "Organization",
    "OrganizationMembership",
    "Edition",
    "EditionFeature",
    "Feature",
    "Product",
    "User",
]
