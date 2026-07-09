"""社内アプリ(Flet)。backend の services を import し DB 直結(03_apps)。

実行: 会社サーバー上で `flet run --web staff/main.py`(社内LAN / SSHトンネル)
開発: scripts/staff

ログイン: PocketBase auth-with-password(answered_by の本人記録のため)。
スタッフかどうかの正は app_users.role(付与はユーザー管理 view)。
初回セットアップのみ、staff/admin が一人もいなければ最初にログインした
PB ユーザーを admin にする(それ以外の未登録ユーザーは拒否)。
"""

import asyncio
import os

import flet as ft
import httpx

from app.core.db import connect
from views import VIEWS

PB_URL = os.environ.get("PB_URL", "http://localhost:8090")

ICONS = [
    ft.Icons.DASHBOARD,
    ft.Icons.REQUEST_QUOTE,
    ft.Icons.INVENTORY_2,
    ft.Icons.PRICE_CHECK,
    ft.Icons.TABLE_VIEW,
    ft.Icons.QR_CODE_2,
    ft.Icons.PEOPLE,
]


async def _pb_login(email: str, password: str) -> dict:
    """PocketBase で認証し record を返す。失敗は ValueError(表示用日本語)。"""
    try:
        async with httpx.AsyncClient(base_url=PB_URL, timeout=10) as c:
            r = await c.post(
                "/api/collections/users/auth-with-password",
                json={"identity": email, "password": password},
            )
    except httpx.HTTPError as e:
        raise ValueError("認証サーバーに接続できません") from e
    if r.status_code != 200:
        raise ValueError("メールまたはパスワードが違います")
    return r.json()["record"]


async def _staff_row(rec: dict) -> dict:
    """PB record に対応する app_users の staff/admin 行を返す。

    行が無い場合、staff/admin が一人もいなければ初回セットアップとして
    admin を作る。それ以外は拒否(付与はユーザー管理 view で行う)。
    """
    uid = rec["id"]
    display = rec.get("name") or rec.get("email", "").split("@")[0] or uid
    db = await connect()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM app_users WHERE id = ?", (uid,)
        )
        row = dict(rows[0]) if rows else None
        if row is None:
            n = (
                await db.execute_fetchall(
                    "SELECT COUNT(*) AS n FROM app_users"
                    " WHERE role IN ('staff', 'admin')"
                )
            )[0]["n"]
            if n:
                raise ValueError("スタッフ登録がありません(管理者に依頼してください)")
            await db.execute(
                "INSERT INTO app_users (id, display_name, email, role, contact_label)"
                " VALUES (?, ?, ?, 'admin', '管理')",
                (uid, display, rec.get("email")),
            )
            row = dict(
                (
                    await db.execute_fetchall(
                        "SELECT * FROM app_users WHERE id = ?", (uid,)
                    )
                )[0]
            )
        elif row["role"] not in ("staff", "admin"):
            raise ValueError("スタッフ権限がありません(管理者に依頼してください)")
        if row["is_suspended"]:
            raise ValueError("アカウントが凍結されています")
        return row
    finally:
        await db.close()


async def pick_staff(page: ft.Page) -> dict:
    """PocketBase ログイン。answered_by に PB の user id が入る。"""
    picked: asyncio.Future[dict] = asyncio.get_running_loop().create_future()

    email = ft.TextField(label="メール", width=280, autofocus=True)
    pw = ft.TextField(label="パスワード", width=280, password=True,
                      can_reveal_password=True)
    msg = ft.Text("", color=ft.Colors.RED)

    async def login(_: object) -> None:
        msg.value = ""
        page.update()
        try:
            row = await _staff_row(await _pb_login(email.value, pw.value))
        except ValueError as e:
            msg.value = str(e)
            page.update()
            return
        page.close(dlg)
        picked.set_result(row)

    pw.on_submit = login
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("スタッフログイン"),
        content=ft.Column([email, pw, msg], tight=True),
        actions=[ft.FilledButton("ログイン", on_click=login)],
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


if __name__ == "__main__":
    ft.app(main)
