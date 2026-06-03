"""Limit/offset pagination primitives.

Usage in a router:

    @router.get("", response_model=Page[JobPostingOut])
    def list_jobs(params: PageParams = Depends(), db: Session = Depends(get_db)):
        items, total = crud.list_with_filters(db, limit=params.limit, offset=params.offset)
        return Page.build(items, total, params)
"""
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


class PageParams:
    """Query-param dependency. Reads ?limit=&offset= with sane bounds."""

    def __init__(
        self,
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ) -> None:
        self.limit = limit
        self.offset = offset


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int

    @classmethod
    def build(cls, items: list[T], total: int, params: PageParams) -> "Page[T]":
        return cls(items=items, total=total, limit=params.limit, offset=params.offset)
