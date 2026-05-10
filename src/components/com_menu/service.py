from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Menu, MenuItem

STATUS_PUBLISHED = "published"
STATUS_UNPUBLISHED = "unpublished"
VALID_STATUSES = {STATUS_PUBLISHED, STATUS_UNPUBLISHED}
VALID_TARGETS = {"_self", "_blank"}

_ALIAS_INVALID_RE = re.compile(r"[^a-z0-9\s-]")
_ALIAS_SEPARATOR_RE = re.compile(r"[\s_-]+")


class MenuError(ValueError):
    def __init__(self, key: str, **kwargs: object) -> None:
        super().__init__(key)
        self.key = key
        self.kwargs = kwargs


@dataclass(frozen=True)
class MenuPayload:
    title: str
    alias: str
    description: str


@dataclass(frozen=True)
class MenuItemPayload:
    menu_id: int
    title: str
    url: str
    target: str
    status: str
    ordering: int


def aliasify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = _ALIAS_INVALID_RE.sub("", ascii_text.lower().strip())
    return _ALIAS_SEPARATOR_RE.sub("-", cleaned).strip("-")


def _int_value(value: object, default: int = 0) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return default


def _status(value: str | None) -> str:
    candidate = (value or STATUS_PUBLISHED).strip().lower()
    return candidate if candidate in VALID_STATUSES else STATUS_PUBLISHED


def _target(value: str | None) -> str:
    candidate = (value or "_self").strip()
    return candidate if candidate in VALID_TARGETS else "_self"


def build_menu_payload(*, title: str, alias: str | None, description: str | None) -> MenuPayload:
    clean_title = title.strip()
    if not clean_title:
        raise MenuError("com_menu.error.title_required")
    clean_alias = aliasify(alias or clean_title)
    if not clean_alias:
        raise MenuError("com_menu.error.alias_required")
    return MenuPayload(title=clean_title, alias=clean_alias, description=(description or "").strip())


def build_item_payload(
    *,
    menu_id: object,
    title: str,
    url: str,
    target: str | None,
    status: str | None,
    ordering: object,
) -> MenuItemPayload:
    clean_title = title.strip()
    clean_url = url.strip()
    if not clean_title:
        raise MenuError("com_menu.error.item_title_required")
    if not clean_url:
        raise MenuError("com_menu.error.item_url_required")
    return MenuItemPayload(
        menu_id=_int_value(menu_id),
        title=clean_title,
        url=clean_url,
        target=_target(target),
        status=_status(status),
        ordering=_int_value(ordering),
    )


async def list_menus(db: AsyncSession) -> list[Menu]:
    return (await db.execute(select(Menu).order_by(Menu.title.asc(), Menu.id.asc()))).scalars().all()


async def get_menu(db: AsyncSession, menu_id: int) -> Menu | None:
    return (await db.execute(select(Menu).where(Menu.id == menu_id))).scalar_one_or_none()


async def get_menu_by_alias(db: AsyncSession, alias: str) -> Menu | None:
    return (await db.execute(select(Menu).where(Menu.alias == alias))).scalar_one_or_none()


async def _alias_exists(db: AsyncSession, alias: str, *, exclude_id: int | None = None) -> bool:
    query = select(Menu).where(Menu.alias == alias)
    if exclude_id is not None:
        query = query.where(Menu.id != exclude_id)
    return (await db.execute(query)).scalar_one_or_none() is not None


async def create_menu(db: AsyncSession, payload: MenuPayload) -> Menu:
    if await _alias_exists(db, payload.alias):
        raise MenuError("com_menu.error.alias_exists", alias=payload.alias)
    menu = Menu(title=payload.title, alias=payload.alias, description=payload.description)
    db.add(menu)
    await db.commit()
    await db.refresh(menu)
    return menu


async def update_menu(db: AsyncSession, menu: Menu, payload: MenuPayload) -> Menu:
    if await _alias_exists(db, payload.alias, exclude_id=menu.id):
        raise MenuError("com_menu.error.alias_exists", alias=payload.alias)
    menu.title = payload.title
    menu.alias = payload.alias
    menu.description = payload.description
    await db.commit()
    await db.refresh(menu)
    return menu


async def delete_menu(db: AsyncSession, menu_id: int) -> None:
    await db.execute(delete(MenuItem).where(MenuItem.menu_id == menu_id))
    await db.execute(delete(Menu).where(Menu.id == menu_id))
    await db.commit()


async def list_items(db: AsyncSession, menu_id: int | None = None) -> list[MenuItem]:
    query = select(MenuItem)
    if menu_id is not None:
        query = query.where(MenuItem.menu_id == menu_id)
    query = query.order_by(MenuItem.menu_id.asc(), MenuItem.ordering.asc(), MenuItem.title.asc())
    return (await db.execute(query)).scalars().all()


async def get_item(db: AsyncSession, item_id: int) -> MenuItem | None:
    return (await db.execute(select(MenuItem).where(MenuItem.id == item_id))).scalar_one_or_none()


async def create_item(db: AsyncSession, payload: MenuItemPayload) -> MenuItem:
    item = MenuItem(**payload.__dict__)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_item(db: AsyncSession, item: MenuItem, payload: MenuItemPayload) -> MenuItem:
    item.menu_id = payload.menu_id
    item.title = payload.title
    item.url = payload.url
    item.target = payload.target
    item.status = payload.status
    item.ordering = payload.ordering
    await db.commit()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item_id: int) -> None:
    await db.execute(delete(MenuItem).where(MenuItem.id == item_id))
    await db.commit()
