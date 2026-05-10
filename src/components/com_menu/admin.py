from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.admin.deps import CurrentAdminUser
from src.api.admin.render import admin_render
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
) -> HTMLResponse | Response:
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
    return await admin_render(
        "admin/com_menu/item_form.html",
        request=request,
        db=db,
        user=user,
        ct=await _component_t(db),
        item=None,
        menus=await list_menus(db),
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
        item = await create_item(db, _item_payload(form))
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
) -> HTMLResponse | Response:
    item = await get_item(db, item_id)
    if item is None:
        return RedirectResponse("/admin/com_menu", status_code=303)
    return await admin_render(
        "admin/com_menu/item_form.html",
        request=request,
        db=db,
        user=user,
        ct=await _component_t(db),
        item=item,
        menus=await list_menus(db),
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
        await update_item(db, item, _item_payload(form))
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


def _item_payload(form: object):
    return build_item_payload(
        menu_id=form.get("menu_id"),
        title=str(form.get("title", "")),
        url=str(form.get("url", "")),
        target=str(form.get("target", "_self")),
        status=str(form.get("status", "published")),
        ordering=form.get("ordering"),
    )
