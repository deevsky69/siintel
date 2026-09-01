"""Pagination baku untuk seluruh endpoint daftar (docs/05 §1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Query
from pydantic import BaseModel

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_params(
    page: int = Query(1, ge=1, description="Halaman, dimulai dari 1"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Jumlah baris per halaman"
    ),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


class Pagination(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class Page[T](BaseModel):
    """Amplop daftar: `{"data": [...], "pagination": {...}}`."""

    data: list[T]
    pagination: Pagination


def paginate(items: list[Any], total: int, params: PageParams) -> dict[str, Any]:
    total_pages = (total + params.page_size - 1) // params.page_size if total else 0
    return {
        "data": items,
        "pagination": {
            "page": params.page,
            "page_size": params.page_size,
            "total_items": total,
            "total_pages": total_pages,
        },
    }
