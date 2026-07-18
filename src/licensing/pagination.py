"""Simple offset/limit pagination shared by list-view service functions.

Framework-agnostic (pure SQLAlchemy) so it can live in src/licensing and be
used directly by service functions rather than duplicated per Flask route.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


@dataclass
class Page[T]:
    items: list[T]
    total: int
    page: int
    per_page: int

    @property
    def has_next(self) -> bool:
        return self.page * self.per_page < self.total

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.per_page))


def paginate[T](
    session: Session, stmt: Select[tuple[T]], *, page: int, per_page: int = 25
) -> Page[T]:
    page = max(1, page)
    total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = list(session.execute(stmt.limit(per_page).offset((page - 1) * per_page)).scalars())
    return Page(items=items, total=total, page=page, per_page=per_page)
