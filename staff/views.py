"""社内アプリの各 view。自分でデータ取得と状態を持つ自己完結型(03_apps)。

DB 接続は view ごとに connect() → close()。業務ロジックは app.services 側。
"""

from typing import Any

import flet as ft

from app.core.db import connect
from app.services import inventory, ledger, qrlabel
from app.services import products as prod_svc
from app.services import staff as staff_svc
from app.services import users as users_svc
from app.services.ledger import STATUS_JA

BADGE = {
    "requested": ft.Colors.RED,
    "answered": ft.Colors.BLUE,
    "ordered": ft.Colors.GREEN,
    "closed": ft.Colors.GREY,
    "declined": ft.Colors.GREY,
    "cancelled": ft.Colors.GREY,
    "expired": ft.Colors.GREY,
}


def status_chip(status: str) -> ft.Control:
    return ft.Container(
        ft.Text(STATUS_JA.get(status, status), color=ft.Colors.WHITE, size=12),
        bgcolor=BADGE.get(status, ft.Colors.GREY),
        border_radius=10,
        padding=ft.padding.symmetric(2, 8),
    )


class View(ft.Column):
    """did_mount で load() を走らせる共通土台"""

    def __init__(self, user: dict[str, Any]):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO, spacing=16)
        self.user = user
        self.controls = [ft.ProgressRing()]

    def did_mount(self) -> None:
        self.page.run_task(self.load)

    async def load(self) -> None:  # pragma: no cover - 各viewで実装
        raise NotImplementedError

    def toast(self, msg: str) -> None:
        self.page.open(ft.SnackBar(ft.Text(msg)))

    def title(self, text: str) -> ft.Control:
        return ft.Text(text, size=20, weight=ft.FontWeight.BOLD)


class Dash(View):
    """ダッシュボード: 未回答件数(赤バッジ)・直近の依頼"""

    async def load(self) -> None:
        db = await connect()
        try:
            d = await staff_svc.dashboard(db)
        finally:
            await db.close()
        self.controls = [
            self.title("ダッシュボード"),
            ft.Row(
                [
                    ft.Text("未回答", size=16),
                    ft.CircleAvatar(
                        content=ft.Text(str(d["open_count"]), color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.RED if d["open_count"] else ft.Colors.GREY,
                        radius=16,
                    ),
                ]
            ),
            ft.Text("直近の依頼", size=16),
            *[
                ft.ListTile(
                    leading=status_chip(q["status"]),
                    title=ft.Text(
                        f"{q['quote_no']}  {q['company_name'] or ''}"
                        f" {q['customer_name']}"
                    ),
                    subtitle=ft.Text(q["created_at"][:16].replace("T", " ")),
                )
                for q in d["recent"]
            ],
        ]
        self.update()


class Quotes(View):
    """見積対応(S-01/S-02): requested を上に。詳細で回答・受注・完了"""

    async def load(self) -> None:
        db = await connect()
        try:
            rows = await staff_svc.list_quotes(db)
        finally:
            await db.close()
        tiles = [
            ft.ListTile(
                leading=status_chip(q["status"]),
                title=ft.Text(
                    f"{q['quote_no']}  {q['company_name'] or ''} {q['customer_name']}"
                    + (f"  📩{q['unread']}" if q["unread"] else "")
                ),
                subtitle=ft.Text((q["note"] or "")[:40]),
                data=q["id"],
                on_click=lambda e: self.page.run_task(self.open_detail, e.control.data),
            )
            for q in rows
        ]
        self.controls = [
            self.title("見積対応"),
            *(tiles or [ft.Text("依頼はまだありません")]),
        ]
        self.update()

    async def open_detail(self, quote_id: str) -> None:
        db = await connect()
        try:
            d = await staff_svc.quote_detail(db, quote_id, self.user)
        finally:
            await db.close()
        if d is None:
            return

        reply = ft.TextField(
            label="回答・返信(金額・納期など)", multiline=True, min_lines=2
        )

        async def do_answer(_: Any) -> None:
            if not reply.value:
                return
            db = await connect()
            try:
                await staff_svc.answer(db, quote_id, self.user, reply.value)
            finally:
                await db.close()
            self.page.close(dlg)
            self.toast("回答を送信しました(顧客へメール通知)")
            await self.load()

        async def do_status(status: str) -> None:
            db = await connect()
            try:
                await staff_svc.set_status(db, quote_id, status)
            finally:
                await db.close()
            self.page.close(dlg)
            self.toast(f"{STATUS_JA[status]} にしました")
            await self.load()

        msgs = [
            ft.Text(
                f"{'▶' if m['sender_id'] != d['customer_id'] else '◀'}"
                f" {m['sender_name']} {m['sent_at'][:16].replace('T', ' ')}\n"
                f"{m['body']}"
            )
            for m in d["messages"]
        ]
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Text(d["quote_no"]), status_chip(d["status"])]),
            content=ft.Column(
                [
                    ft.Text(f"{d['company_name'] or ''} {d['customer_name']}"),
                    ft.Text(f"要望: {d['note'] or '(なし)'}"),
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("型番")),
                            ft.DataColumn(ft.Text("品目")),
                            ft.DataColumn(ft.Text("数量"), numeric=True),
                            ft.DataColumn(ft.Text("個別仕様")),
                        ],
                        rows=[
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(i["code"])),
                                    ft.DataCell(ft.Text(i["name"])),
                                    ft.DataCell(ft.Text(str(i["quantity"]))),
                                    ft.DataCell(ft.Text(i["spec_note"] or "")),
                                ]
                            )
                            for i in d["items"]
                        ],
                    ),
                    ft.Divider(),
                    *msgs,
                    reply,
                ],
                scroll=ft.ScrollMode.AUTO,
                width=640,
                height=480,
            ),
            actions=[
                ft.TextButton(
                    "受注", on_click=lambda e: self.page.run_task(do_status, "ordered")
                ),
                ft.TextButton(
                    "完了", on_click=lambda e: self.page.run_task(do_status, "closed")
                ),
                ft.TextButton(
                    "辞退", on_click=lambda e: self.page.run_task(do_status, "declined")
                ),
                ft.FilledButton("回答する", on_click=do_answer),
                ft.TextButton("閉じる", on_click=lambda e: self.page.close(dlg)),
            ],
        )
        self.page.open(dlg)


def parse_specs(text: str) -> dict[str, str]:
    """「キー: 値」の行を dict に(仕様のキー:値フォーム)"""
    specs = {}
    for line in text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            if k.strip():
                specs[k.strip()] = v.strip()
    return specs


class Products(View):
    """製品管理(S-03): 一覧・編集・公開/非公開。保存で静的カタログ再生成"""

    async def load(self) -> None:
        db = await connect()
        try:
            rows = await prod_svc.list_products(db)
            self.categories = await prod_svc.list_categories(db)
        finally:
            await db.close()

        async def toggle(e: Any) -> None:
            db = await connect()
            try:
                await prod_svc.set_public(db, e.control.data, e.control.value)
            finally:
                await db.close()
            self.toast("公開状態を変更し、カタログを再生成しました")

        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(h))
                for h in ("型番", "製品名", "分類", "価格表記", "公開", "")
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(p["code"])),
                        ft.DataCell(ft.Text(p["name"])),
                        ft.DataCell(ft.Text(p["category_name"])),
                        ft.DataCell(ft.Text(p["price_note"] or "")),
                        ft.DataCell(
                            ft.Switch(
                                value=bool(p["is_public"]),
                                data=p["code"],
                                on_change=toggle,
                            )
                        ),
                        ft.DataCell(
                            ft.TextButton(
                                "編集",
                                data=p["code"],
                                on_click=lambda e: self.page.run_task(
                                    self.edit, e.control.data
                                ),
                            )
                        ),
                    ]
                )
                for p in rows
            ],
        )
        self.controls = [
            ft.Row(
                [
                    self.title("製品管理"),
                    ft.FilledButton(
                        "新規追加",
                        icon=ft.Icons.ADD,
                        on_click=lambda e: self.page.run_task(self.edit, None),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            table,
        ]
        self.update()

    async def edit(self, code: str | None) -> None:
        p: dict[str, Any] = {}
        if code:
            db = await connect()
            try:
                p = await prod_svc.get_product(db, code) or {}
            finally:
                await db.close()

        f_code = ft.TextField(
            label="型番(基幹と共通)", value=p.get("code", ""), disabled=bool(code)
        )
        f_name = ft.TextField(label="製品名", value=p.get("name", ""))
        f_cat = ft.Dropdown(
            label="分類",
            options=[ft.dropdown.Option(c["slug"], c["name"]) for c in self.categories],
            value=p.get("category_slug", self.categories[0]["slug"]),
        )
        f_summary = ft.TextField(label="一言(カード用)", value=p.get("summary") or "")
        f_desc = ft.TextField(
            label="説明", value=p.get("description") or "", multiline=True
        )
        f_specs = ft.TextField(
            label="仕様(1行に「キー: 値」)",
            value="\n".join(f"{k}: {v}" for k, v in p.get("specs", {}).items()),
            multiline=True,
            min_lines=3,
        )
        f_price = ft.TextField(
            label="価格表記(要見積 等)", value=p.get("price_note") or ""
        )

        async def save(_: Any) -> None:
            if not f_code.value or not f_name.value:
                self.toast("型番と製品名は必須です")
                return
            db = await connect()
            try:
                await prod_svc.save_product(
                    db,
                    {
                        "code": f_code.value.strip(),
                        "name": f_name.value.strip(),
                        "category_slug": f_cat.value,
                        "summary": f_summary.value or None,
                        "description": f_desc.value or None,
                        "specs": parse_specs(f_specs.value),
                        "price_note": f_price.value or None,
                        "is_public": p.get("is_public", True),
                        "is_active": p.get("is_active", True),
                    },
                )
            finally:
                await db.close()
            self.page.close(dlg)
            self.toast("保存し、静的カタログを再生成しました")
            await self.load()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("製品の編集" if code else "製品の追加"),
            content=ft.Column(
                [f_code, f_name, f_cat, f_summary, f_desc, f_specs, f_price],
                scroll=ft.ScrollMode.AUTO,
                width=520,
                height=480,
            ),
            actions=[
                ft.TextButton("キャンセル", on_click=lambda e: self.page.close(dlg)),
                ft.FilledButton("保存", on_click=save),
            ],
        )
        self.page.open(dlg)


class Inventory(View):
    """在庫・価格(S-04): 基幹API中継の表示のみ。未接続なら「要見積」"""

    async def load(self) -> None:
        db = await connect()
        try:
            products = await prod_svc.list_products(db)
        finally:
            await db.close()
        inv = await inventory.fetch()
        if inv is None:
            body: list[ft.Control] = [
                ft.Text(
                    "基幹API 未接続です。顧客画面・カタログは「要見積」表示で"
                    "運用されます(基幹APIができたら .env の KIKAN_URL を設定)。"
                )
            ]
        else:
            body = [
                ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text(h))
                        for h in ("型番", "製品名", "在庫", "価格")
                    ],
                    rows=[
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(p["code"])),
                                ft.DataCell(ft.Text(p["name"])),
                                ft.DataCell(
                                    ft.Text(str(inv.get(p["code"], {}).get("qty", "—")))
                                ),
                                ft.DataCell(
                                    ft.Text(
                                        str(inv.get(p["code"], {}).get("price", "—"))
                                    )
                                ),
                            ]
                        )
                        for p in products
                    ],
                )
            ]
        self.controls = [self.title("在庫・価格(基幹API)"), *body]
        self.update()


class Export(View):
    """エクスポート(S-05): 台帳 xlsx。OnlyOffice でそのまま開ける"""

    async def load(self) -> None:
        async def run(kind: str) -> None:
            db = await connect()
            try:
                path = await ledger.export(db, kind)
            finally:
                await db.close()
            self.toast(f"出力しました: {path}")

        self.controls = [
            self.title("エクスポート"),
            ft.FilledButton(
                "見積台帳 xlsx",
                icon=ft.Icons.TABLE_VIEW,
                on_click=lambda e: self.page.run_task(run, "quotes"),
            ),
            ft.FilledButton(
                "受注台帳 xlsx",
                icon=ft.Icons.TABLE_VIEW,
                on_click=lambda e: self.page.run_task(run, "orders"),
            ),
            ft.Text("出力先: data/exports/(OnlyOffice でそのまま開けます)"),
        ]
        self.update()


class QrLabel(View):
    """QRラベル(S-06): 選択した製品のQR面付けPDF(銘板・紙カタログ用)"""

    async def load(self) -> None:
        db = await connect()
        try:
            products = await prod_svc.list_products(db)
        finally:
            await db.close()
        checks = [
            ft.Checkbox(label=f"{p['code']}  {p['name']}", data=p, value=False)
            for p in products
        ]

        def make(_: Any) -> None:
            selected = [c.data for c in checks if c.value]
            if not selected:
                self.toast("製品を選択してください")
                return
            path = qrlabel.build_pdf(
                [{"code": p["code"], "name": p["name"]} for p in selected]
            )
            self.toast(f"出力しました: {path}")

        self.controls = [
            self.title("QRラベル"),
            ft.Text("選択した製品のQRを面付けしたPDFを出力します(A4・4×6)"),
            *checks,
            ft.FilledButton("PDF生成", icon=ft.Icons.QR_CODE_2, on_click=make),
        ]
        self.update()


class Users(View):
    """ユーザー管理(S-07・admin): 顧客の凍結、スタッフの担当名・役割"""

    async def load(self) -> None:
        if self.user["role"] != "admin":
            self.controls = [
                self.title("ユーザー管理"),
                ft.Text("admin のみ操作できます"),
            ]
            self.update()
            return
        db = await connect()
        try:
            rows = await users_svc.list_users(db)
        finally:
            await db.close()

        async def toggle(e: Any) -> None:
            db = await connect()
            try:
                await users_svc.set_suspended(db, e.control.data, e.control.value)
            finally:
                await db.close()
            self.toast("凍結状態を変更しました")

        self.controls = [
            self.title("ユーザー管理"),
            ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text(h))
                    for h in ("名前", "会社", "メール", "役割", "依頼数", "凍結")
                ],
                rows=[
                    ft.DataRow(
                        cells=[
                            ft.DataCell(
                                ft.Text(
                                    u["display_name"]
                                    + (
                                        f"({u['contact_label']})"
                                        if u["contact_label"]
                                        else ""
                                    )
                                )
                            ),
                            ft.DataCell(ft.Text(u["company_name"] or "")),
                            ft.DataCell(ft.Text(u["email"] or "")),
                            ft.DataCell(ft.Text(u["role"])),
                            ft.DataCell(ft.Text(str(u["quote_count"]))),
                            ft.DataCell(
                                ft.Switch(
                                    value=bool(u["is_suspended"]),
                                    data=u["id"],
                                    on_change=toggle,
                                )
                            ),
                        ]
                    )
                    for u in rows
                ],
            ),
        ]
        self.update()


VIEWS: list[tuple[str, type[View]]] = [
    ("ダッシュボード", Dash),
    ("見積対応", Quotes),
    ("製品管理", Products),
    ("在庫・価格", Inventory),
    ("エクスポート", Export),
    ("QRラベル", QrLabel),
    ("ユーザー管理", Users),
]
