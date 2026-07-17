"""Pydantic schemas for the desktop-facing activation endpoints.

Field set here is deliberately minimal -- see docs/privacy.md: activation
never carries experiment-shaped data, only product/edition codes and
licensing identifiers.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ActivationStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_code: str = Field(max_length=100)
    edition_code: str | None = Field(default=None, max_length=100)


class ActivationStartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activation_id: uuid.UUID
    user_code: str
    verification_url: str
    expires_at: datetime
    polling_interval_seconds: int


class ActivationStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    expires_at: datetime


class ActivationCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_public_key: str = Field(description="base64url-encoded raw Ed25519 public key")
    display_name: str | None = Field(default=None, max_length=200)
