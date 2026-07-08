"""社内アプリ(Flet)。backend の services を import し DB 直結(03_apps)。

実行: 会社サーバー上で `flet run --web staff/main.py`(社内LAN / SSHトンネル)
開発: scripts/staff

ログイン: 本番は PocketBase(answered_by の本人記録のため)。
PocketBase 疎通確認まで、開発用にスタッフ選択で代替(pick_staff を差し替える)。
"""

import asyncio

import flet as ft

from app.core.db import connect
from views import VIEWS

ICONS = [
    ft.Icons.DASHBOARD,
    ft.Icons.REQUEST_QUOTE,
    ft.Icons.INVENTORY_2,
    ft.Icons.PRICE_CHECK,
    ft.Icons.TABLE_VIEW,
    ft.Icons.QR_CODE_2,
    ft.Icons.PEOPLE,
]


async def _staff_users() -> list[dict]:
    db = await connect()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM app_users WHERE role IN ('staff', 'admin')"
            " ORDER BY display_name"
        )
        if not rows:
            # 初回起動: スタッフ未登録なら管理者を1人作る
            await db.execute(
                "INSERT INTO app_users (id, display_name, role, contact_label)"
                " VALUES ('admin', '管理者', 'admin', '管理')"
            )
            rows = await db.execute_fetchall(
                "SELECT * FROM app_users WHERE role IN ('staff', 'admin')"
            )
    finally:
        await db.close()
    return [dict(r) for r in rows]


async def pick_staff(page: ft.Page) -> dict:
    """開発用ログイン: staff/admin から担当者を選ぶ。
    TODO: PocketBase の auth-with-password に差し替え(PB疎通確認後)"""
    staff_list = await _staff_users()
    picked: asyncio.Future[dict] = asyncio.get_running_loop().create_future()

    dd = ft.Dropdown(
        label="担当者",
        options=[
            ft.dropdown.Option(
                u["id"], f"{u['display_name']}({u['contact_label'] or u['role']})"
            )
            for u in staff_list
        ],
        value=staff_list[0]["id"],
        width=280,
    )

    def ok(_: object) -> None:
        page.close(dlg)
        picked.set_result(next(u for u in staff_list if u["id"] == dd.value))

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("担当者を選択(開発モード)"),
        content=dd,
        actions=[ft.FilledButton("開始", on_click=ok)],
    )
    page.open(dlg)
    return await picked


async def main(page: ft.Page) -> None:
    page.title = "mfg 社内"
    page.theme_mode = ft.ThemeMode.LIGHT

    staff_user: dict | None = None
    content = ft.Container(expand=True, padding=16)

    def switch(i: int) -> None:
        if staff_user is None:
            return
        content.content = VIEWS[i][1](staff_user)
        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        destinations=[
            ft.NavigationRailDestination(icon=icon, label=label)
            for (label, _), icon in zip(VIEWS, ICONS, strict=True)
        ],
        on_change=lambda e: switch(e.control.selected_index),
    )

    # ダイアログ(オーバーレイ)はページ初期化後でないと開けないので先に組む
    page.add(ft.Row([rail, ft.VerticalDivider(width=1), content], expand=True))
    staff_user = await pick_staff(page)
    switch(0)


ft.app(main)
