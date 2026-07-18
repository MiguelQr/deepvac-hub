"""Authorization checks shared by every management-portal service.

Framework-agnostic on purpose (no Flask/FastAPI imports) so it can be
unit-tested directly and reused from apps/api once device management grows
a "management session" dependency (see apps/api/dependencies.py). Two
independent role axes exist in the schema and nothing else: User.vendor_role
(vendor back-office staff, not org-scoped) and OrganizationMembership.role
(org-scoped, only for ACTIVE memberships). There is no third role table --
see docs/database-erd.md and models/enums.py.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from licensing.exceptions import PermissionDeniedError
from licensing.models.enums import MembershipRole, MembershipStatus, VendorRole
from licensing.models.organizations import OrganizationMembership
from licensing.models.users import User


def is_vendor(user: User) -> bool:
    return user.vendor_role is not None


def require_vendor(user: User, *, write: bool = False) -> None:
    """Gate the vendor console. VENDOR_SUPPORT is read-only: it satisfies
    write=False but not write=True."""
    if user.vendor_role is None:
        raise PermissionDeniedError("This area is restricted to vendor staff.")
    if write and user.vendor_role != VendorRole.VENDOR_SUPER_ADMIN:
        raise PermissionDeniedError("This action requires a vendor super admin.")


def get_active_membership(
    session: Session, *, user_id: uuid.UUID, organization_id: uuid.UUID
) -> OrganizationMembership | None:
    return session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status == MembershipStatus.ACTIVE,
        )
    ).scalar_one_or_none()


def require_org_view(
    session: Session, user: User, organization_id: uuid.UUID
) -> OrganizationMembership | None:
    """Vendor staff may view any organization (returns None, meaning "not
    scoped by a membership"). Otherwise the caller must hold an active
    membership in this org; returns it."""
    if is_vendor(user):
        return None
    membership = get_active_membership(session, user_id=user.id, organization_id=organization_id)
    if membership is None:
        raise PermissionDeniedError("You do not have access to this organization.")
    return membership


def require_org_admin(session: Session, user: User, organization_id: uuid.UUID) -> None:
    """Write access to an org's self-service actions (memberships, seats):
    vendor_super_admin, or an active organization_admin membership in that
    specific org."""
    if user.vendor_role == VendorRole.VENDOR_SUPER_ADMIN:
        return
    membership = get_active_membership(session, user_id=user.id, organization_id=organization_id)
    if membership is None or membership.role != MembershipRole.ORGANIZATION_ADMIN:
        raise PermissionDeniedError("You do not have admin access to this organization.")


def can_vendor_write(user: User) -> bool:
    """Non-raising check for template rendering (show/hide write controls).
    The actual write endpoints still call require_vendor(write=True) --
    this only decides what to display."""
    return user.vendor_role == VendorRole.VENDOR_SUPER_ADMIN


def can_org_admin(session: Session, user: User, organization_id: uuid.UUID) -> bool:
    """Non-raising counterpart to require_org_admin, for template rendering."""
    try:
        require_org_admin(session, user, organization_id)
        return True
    except PermissionDeniedError:
        return False
