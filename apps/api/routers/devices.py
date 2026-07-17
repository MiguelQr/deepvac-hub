"""Management-authenticated device inventory/revoke/replace endpoints.

Not implemented in Phase A (foundation). Lands in Phase D/E alongside device
activation and revocation services — see README.md phase plan.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["devices"])
