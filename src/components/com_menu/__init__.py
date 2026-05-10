from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.registry import ComponentRegistry

_COMPONENT_DIR = Path(__file__).parent
_manifest: dict = {}


def _load_manifest() -> dict:
    global _manifest
    if not _manifest:
        try:
            _manifest = json.loads((_COMPONENT_DIR / "manifest.json").read_text(encoding="utf-8"))
        except Exception:
            _manifest = {}
    return _manifest


def setup(reg: "ComponentRegistry") -> None:
    from src.components.com_menu import admin
    from src.i18n.translator import translator

    manifest = _load_manifest()

    reg.register("com_menu", "src.components.com_menu")
    reg.register_display_name("com_menu", manifest.get("display_name_key", "extensions.name.com_menu"))
    reg.register_admin_url("com_menu", manifest.get("admin_url", "/admin/com_menu"))
    reg.register_router(admin.router)

    translator.load_domain("com_menu", _COMPONENT_DIR / "i18n")


async def uninstall_schema(engine: object) -> None:
    from src.components.com_menu.models import Menu, MenuItem

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: MenuItem.__table__.drop(sync_conn, checkfirst=True))
        await conn.run_sync(lambda sync_conn: Menu.__table__.drop(sync_conn, checkfirst=True))
