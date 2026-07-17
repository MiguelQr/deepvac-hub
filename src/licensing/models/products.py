from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from licensing.database import Base
from licensing.models.enums import EditionStatus, ProductStatus
from licensing.models.mixins import UUIDPrimaryKeyMixin, pg_enum


class Product(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "products"

    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[ProductStatus] = mapped_column(
        pg_enum(ProductStatus, name="product_status"),
        nullable=False,
        default=ProductStatus.ACTIVE,
    )

    editions: Mapped[list[Edition]] = relationship(back_populates="product")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Product {self.code!r}>"


class Edition(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "editions"
    __table_args__ = (UniqueConstraint("product_id", "code", name="uq_edition_product_code"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[EditionStatus] = mapped_column(
        pg_enum(EditionStatus, name="edition_status"),
        nullable=False,
        default=EditionStatus.ACTIVE,
    )

    product: Mapped[Product] = relationship(back_populates="editions")
    edition_features: Mapped[list[EditionFeature]] = relationship(back_populates="edition")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Edition {self.product_id}/{self.code!r}>"


class Feature(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "features"

    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Feature {self.code!r}>"


class EditionFeature(Base):
    """Association between an edition and a feature it grants, with
    optional per-edition limits/config (e.g. {"max_channels": 64}).
    """

    __tablename__ = "edition_features"

    edition_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("editions.id"), primary_key=True
    )
    feature_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("features.id"), primary_key=True
    )
    config: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)

    edition: Mapped[Edition] = relationship(back_populates="edition_features")
    feature: Mapped[Feature] = relationship()
