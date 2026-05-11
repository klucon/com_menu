from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.admin.deps import CurrentAdminUser
from src.api.admin.render import admin_render
from src.core.hooks import hooks
from src.core.system_settings import get_runtime_settings
from src.core.templates import make_t
from src.database.base import get_db_session

from .service import (
    MenuError,
    build_item_payload,
    build_menu_payload,
    create_item,
    create_menu,
    delete_item as delete_item_record,
    delete_menu as delete_menu_record,
    get_item,
    get_menu,
    list_items,
    list_menus,
    update_item,
    update_menu,
)

router = APIRouter(prefix="/admin/com_menu", tags=["com_menu"])


async def _component_t(db: AsyncSession):
    runtime = await get_runtime_settings(db)
    return make_t(runtime.locale, "com_menu")


def _set_flash(request: Request, flash_type: str, text: str) -> None:
    request.session["flash"] = {"type": flash_type, "text": text}


def _normalize_type(raw: object) -> str:
    return str(raw or "").strip()


async def _menu_item_types(request: Request, db: AsyncSession) -> list[dict[str, object]]:
    ct = await _component_t(db)
    results = await hooks.fire("menu.item.types", request=request, db=db)
    types: list[dict[str, object]] = []
    for result in results:
        if isinstance(result, list):
            types.extend(item for item in result if isinstance(item, dict))
        elif isinstance(result, dict):
            types.append(result)
    types.append(
        {
            "key": "system.url",
            "group": ct("com_menu.type.group.system"),
            "label": ct("com_menu.type.url"),
            "description": ct("com_menu.type.url_description"),
            "empty": "",
            "options": [],
            "manual_url": True,
        }
    )
    return sorted(types, key=lambda item: str(item.get("group", "")) + str(item.get("label", "")))


def _find_type(types: list[dict[str, object]], key: str) -> dict[str, object] | None:
    for item_type in types:
        if item_type.get("key") == key:
            return item_type
    return None


def _find_option(item_type: dict[str, object] | None, value: str) -> dict[str, object] | None:
    if item_type is None:
        return None
    options = item_type.get("options")
    if not isinstance(options, list):
        return None
    for option in options:
        if isinstance(option, dict) and str(option.get("value", "")) == value:
            return option
    return None


def _infer_type_from_url(
    types: list[dict[str, object]],
    url: str,
) -> tuple[str, str]:
    for item_type in types:
        options = item_type.get("options")
        if not isinstance(options, list):
            continue
        for option in options:
            if isinstance(option, dict) and option.get("url") == url:
                return str(item_type.get("key") or "system.url"), str(option.get("value") or "")
    return "system.url", ""


async def _item_payload(form: object, request: Request, db: AsyncSession):
    item_types = await _menu_item_types(request, db)
    item_type_key = _normalize_type(form.get("item_type")) or "system.url"
    item_type = _find_type(item_types, item_type_key)
    selected_value = str(form.get("item_ref", "") or "")
    selected_option = _find_option(item_type, selected_value)

    raw_title = str(form.get("title", "") or "").strip()
    if item_type and item_type.get("manual_url") is True:
        title = raw_title
        url = str(form.get("url", "") or "").strip()
    elif selected_option is not None:
        title = raw_title or str(selected_option.get("title") or "")
        url = str(selected_option.get("url") or "").strip()
    else:
        title = raw_title
        url = ""

    return build_item_payload(
        menu_id=form.get("menu_id"),
        title=title,
        url=url,
        target=str(form.get("target", "_self")),
        status=str(form.get("status", "published")),
        ordering=form.get("ordering"),
    )


@router.get("", response_class=HTMLResponse)
async def index(
    request: Request,
    user: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    return await admin_render(
        "admin/com_menu/index.html",
        request=request,
        db=db,
        user=user,
        ct=await _component_t(db),
        menus=await list_menus(db),
        items=await list_items(db),
        flash=request.session.pop("flash", None),
    )


@router.get("/menus/new", response_class=HTMLResponse)
async def menu_new_form(
    request: Request,
    user: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    return await admin_render(
        "admin/com_menu/menu_form.html",
        request=request,
        db=db,
        user=user,
        ct=await _component_t(db),
        menu=None,
        flash=request.session.pop("flash", None),
    )


@router.post("/menus/new")
async def menu_new_submit(
    request: Request,
    user: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    ct = await _component_t(db)
    form = await request.form()
    try:
        menu = await create_menu(db, build_menu_payload(
            title=str(form.get("title", "")),
            alias=str(form.get("alias", "")),
            description=str(form.get("description", "")),
        ))
    except MenuError as exc:
        _set_flash(request, "danger", ct(exc.key, **exc.kwargs))
        return RedirectResponse("/admin/com_menu/menus/new", status_code=303)
    _set_flash(request, "success", ct("com_menu.success.menu_created", title=menu.title))
    return RedirectResponse("/admin/com_menu", status_code=303)


@router.get("/menus/{menu_id}/edit", response_class=HTMLResponse)
async def menu_edit_form(
    menu_id: int,
    request: Request,
    user: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    menu = await get_menu(db, menu_id)
    if menu is None:
        return RedirectResponse("/admin/com_menu", status_code=303)
    return await admin_render(
        "admin/com_menu/menu_form.html",
        request=request,
        db=db,
        user=user,
        ct=await _component_t(db),
        menu=menu,
        flash=request.session.pop("flash", None),
    )


@router.post("/menus/{menu_id}/edit")
async def menu_edit_submit(
    menu_id: int,
    request: Request,
    user: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    menu = await get_menu(db, menu_id)
    if menu is None:
        return RedirectResponse("/admin/com_menu", status_code=303)
    ct = await _component_t(db)
    form = await request.form()
    try:
        await update_menu(db, menu, build_menu_payload(
            title=str(form.get("title", "")),
            alias=str(form.get("alias", "")),
            description=str(form.get("description", "")),
        ))
    except MenuError as exc:
        _set_flash(request, "danger", ct(exc.key, **exc.kwargs))
        return RedirectResponse(f"/admin/com_menu/menus/{menu_id}/edit", status_code=303)
    _set_flash(request, "success", ct("com_menu.success.menu_updated"))
    return RedirectResponse("/admin/com_menu", status_code=303)


@router.post("/menus/{menu_id}/delete")
async def menu_delete_submit(
    menu_id: int,
    request: Request,
    user: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    await delete_menu_record(db, menu_id)
    ct = await _component_t(db)
    _set_flash(request, "success", ct("com_menu.success.menu_deleted"))
    return RedirectResponse("/admin/com_menu", status_code=303)


@router.get("/items/new", response_class=HTMLResponse)
async def item_new_form(
    request: Request,
    user: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    item_types = await _menu_item_types(request, db)
    selected_type = _normalize_type(request.query_params.get("item_type"))
    if not selected_type:
        return await admin_render(
            "admin/com_menu/item_type.html",
            request=request,
            db=db,
            user=user,
            ct=await _component_t(db),
            item_types=item_types,
            flash=request.session.pop("flash", None),
        )
    selected_item_type = _find_type(item_types, selected_type) or _find_type(item_types, "system.url")
    return await admin_render(
        "admin/com_menu/item_form.html",
        request=request,
        db=db,
        user=user,
        ct=await _component_t(db),
        item=None,
        menus=await list_menus(db),
        item_types=item_types,
        selected_type=selected_item_type,
        selected_type_key=selected_item_type.get("key") if selected_item_type else "system.url",
        selected_ref="",
        flash=request.session.pop("flash", None),
    )


@router.post("/items/new")
async def item_new_submit(
    request: Request,
    user: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    ct = await _component_t(db)
    form = await request.form()
    try:
        item = await create_item(db, await _item_payload(form, request, db))
    except MenuError as exc:
        _set_flash(request, "danger", ct(exc.key, **exc.kwargs))
        return RedirectResponse("/admin/com_menu/items/new", status_code=303)
    _set_flash(request, "success", ct("com_menu.success.item_created", title=item.title))
    return RedirectResponse("/admin/com_menu", status_code=303)


@router.get("/items/{item_id}/edit", response_class=HTMLResponse)
async def item_edit_form(
    item_id: int,
    request: Request,
    user: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    item = await get_item(db, item_id)
    if item is None:
        return RedirectResponse("/admin/com_menu", status_code=303)
    item_types = await _menu_item_types(request, db)
    selected_type_key = _normalize_type(request.query_params.get("item_type"))
    selected_ref = ""
    if not selected_type_key:
        selected_type_key, selected_ref = _infer_type_from_url(item_types, item.url)
    selected_item_type = _find_type(item_types, selected_type_key) or _find_type(item_types, "system.url")
    if selected_item_type and not selected_ref:
        selected_ref = _infer_type_from_url([selected_item_type], item.url)[1]
    return await admin_render(
        "admin/com_menu/item_form.html",
        request=request,
        db=db,
        user=user,
        ct=await _component_t(db),
        item=item,
        menus=await list_menus(db),
        item_types=item_types,
        selected_type=selected_item_type,
        selected_type_key=selected_item_type.get("key") if selected_item_type else "system.url",
        selected_ref=selected_ref,
        flash=request.session.pop("flash", None),
    )


@router.post("/items/{item_id}/edit")
async def item_edit_submit(
    item_id: int,
    request: Request,
    user: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    item = await get_item(db, item_id)
    if item is None:
        return RedirectResponse("/admin/com_menu", status_code=303)
    ct = await _component_t(db)
    form = await request.form()
    try:
        await update_item(db, item, await _item_payload(form, request, db))
    except MenuError as exc:
        _set_flash(request, "danger", ct(exc.key, **exc.kwargs))
        return RedirectResponse(f"/admin/com_menu/items/{item_id}/edit", status_code=303)
    _set_flash(request, "success", ct("com_menu.success.item_updated"))
    return RedirectResponse("/admin/com_menu", status_code=303)


@router.post("/items/{item_id}/delete")
async def item_delete_submit(
    item_id: int,
    request: Request,
    user: CurrentAdminUser,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    await delete_item_record(db, item_id)
    ct = await _component_t(db)
    _set_flash(request, "success", ct("com_menu.success.item_deleted"))
    return RedirectResponse("/admin/com_menu", status_code=303)
