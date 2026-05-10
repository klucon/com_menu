from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Menu(Base):
    __tablename__ = "com_menu_menus"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    alias: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class MenuItem(Base):
    __tablename__ = "com_menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    menu_id: Mapped[int] = mapped_column(ForeignKey("com_menu_menus.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(500))
    target: Mapped[str] = mapped_column(String(20), default="_self")
    status: Mapped[str] = mapped_column(String(20), default="published")
    ordering: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
