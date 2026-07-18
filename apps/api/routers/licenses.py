"""Public signing keys (GET /licensing/public-keys).

This is the only license-related endpoint on this API. Licenses in this
product are lifetime grants issued once at activation (see
apps/api/routers/activation.py) -- there is no refresh/renewal endpoint,
deliberately: see README.md's Phase D notes.
"""

from __future__ import annotations

import base64

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from licensing.schemas.license import PublicSigningKey, PublicSigningKeysResponse
from licensing.services import signing_keys as signing_keys_service

router = APIRouter(tags=["licenses"])


@router.get("/licensing/public-keys", response_model=PublicSigningKeysResponse)
def get_public_keys(db: Session = Depends(get_db)) -> PublicSigningKeysResponse:
    keys = signing_keys_service.list_public_keys(db)
    return PublicSigningKeysResponse(
        keys=[
            PublicSigningKey(
                key_id=key.key_id,
                algorithm=key.algorithm,
                public_key=base64.urlsafe_b64encode(key.public_key).decode("ascii"),
                status=key.status.value,
                activated_at=key.activated_at,
                retired_at=key.retired_at,
            )
            for key in keys
        ]
    )
