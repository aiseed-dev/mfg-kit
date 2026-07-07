-- =====================================================================
-- 製造業向け 見積・受注アプリ スキーマ(mfg)
-- SQLite(WAL)/ シングルテナント(1社1式)
--
-- 原則:
--  - 在庫・価格の正は会社側の基幹システム。本DBは持たない(API参照)
--  - 決済を持たない。見積番号はDB全体の通し番号(年+連番)
--  - 認証は PocketBase(顧客・社内スタッフとも個人別アカウント)
--  - データは1ファイル(data/mfg.db)。バックアップはファイルコピー
--  - 接続ごとに PRAGMA foreign_keys=ON を設定すること(アプリ側)
--  - UUID・日時(ISO 8601 UTC)はアプリが生成して渡す
-- =====================================================================

-- ユーザー(PocketBase の身元に対応)。顧客(取引先担当者)と社内スタッフ
CREATE TABLE IF NOT EXISTS app_users (
    id            TEXT PRIMARY KEY,          -- PocketBase record id
    display_name  TEXT NOT NULL,
    email         TEXT,                      -- 通知先(認証時に PocketBase から取込)
    company_name  TEXT,                      -- 顧客の所属会社
    contact_label TEXT,                      -- 社内スタッフの担当部門/担当者名
    role          TEXT NOT NULL DEFAULT 'customer'
                  CHECK (role IN ('customer', 'staff', 'admin')),
    is_suspended  INTEGER NOT NULL DEFAULT 0 CHECK (is_suspended IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS categories (
    id         INTEGER PRIMARY KEY,
    slug       TEXT NOT NULL UNIQUE,
    name       TEXT NOT NULL,                -- 例: 玄関ドア / 省力機械 / 保守部品
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- 製品(カタログ)。公開分は静的JSONとして R2 へ配信される
CREATE TABLE IF NOT EXISTS products (
    id           TEXT PRIMARY KEY,           -- UUID(アプリ生成)
    code         TEXT NOT NULL UNIQUE,       -- 製品コード(基幹と共通のキー。
                                             -- QR・基幹API照合に使う)
    name         TEXT NOT NULL,
    category_id  INTEGER NOT NULL REFERENCES categories(id),
    summary      TEXT,                       -- カード用の一言
    description  TEXT,
    specs        TEXT NOT NULL DEFAULT '{}', -- 仕様(キー:値)。JSON文字列
    price_note   TEXT,                       -- 「参考価格」「要見積」等の表示。
                                             -- 実価格は基幹APIから(本DBは持たない)
    is_public    INTEGER NOT NULL DEFAULT 1 CHECK (is_public IN (0, 1)),
    is_active    INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_products_cat ON products (category_id)
    WHERE is_public AND is_active;

CREATE TABLE IF NOT EXISTS product_photos (
    id         TEXT PRIMARY KEY,             -- UUID(アプリ生成)
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    path       TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- 見積依頼。取引の単位・経理の記録単位
CREATE TABLE IF NOT EXISTS quotes (
    id           TEXT PRIMARY KEY,           -- UUID(アプリ生成)
    customer_id  TEXT NOT NULL REFERENCES app_users(id),
    -- 見積番号: DB全体の通し番号(年+連番。例 2026-00042)。
    -- 会社の基幹・会計の伝票番号との照合キー。QRにも載せる。
    -- 採番は BEGIN IMMEDIATE で直列化して MAX(quote_seq)+1(アプリ側)。
    -- quote_no の UNIQUE と複合 UNIQUE が安全網
    quote_no     TEXT UNIQUE NOT NULL,
    quote_year   INTEGER NOT NULL,
    quote_seq    INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'requested'
                 CHECK (status IN ('requested',  -- 依頼受付
                                   'answered',   -- 見積回答済み
                                   'ordered',    -- 受注(顧客が発注)
                                   'declined',   -- 辞退(見積不可/失注)
                                   'cancelled',  -- 顧客取下げ
                                   'closed',     -- 完了(納品等の後)
                                   'expired')),  -- 放置の自動クローズ
    note         TEXT,                       -- 依頼時の要望(用途・数量・納期等)
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    answered_at  TEXT,                       -- 回答日時
    answered_by  TEXT REFERENCES app_users(id),  -- 回答した担当者
    ordered_at   TEXT,                       -- 受注日時(台帳の計上基準)
    updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (quote_year, quote_seq)
);

CREATE INDEX IF NOT EXISTS idx_quotes_customer
    ON quotes (customer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quotes_open ON quotes (created_at)
    WHERE status = 'requested';

CREATE TABLE IF NOT EXISTS quote_items (
    quote_id   TEXT NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(id),
    quantity   INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    spec_note  TEXT,                         -- 個別仕様(色・寸法指定等)
    PRIMARY KEY (quote_id, product_id)
);

-- 見積カート(依頼前の選択。サーバー保持で端末をまたぐ)
CREATE TABLE IF NOT EXISTS cart_items (
    user_id    TEXT NOT NULL REFERENCES app_users(id),
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity   INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    spec_note  TEXT,
    added_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (user_id, product_id)
);

-- メッセージ(見積単位のスレッド。仕様のやり取り・回答・納期調整)
CREATE TABLE IF NOT EXISTS messages (
    id        TEXT PRIMARY KEY,              -- UUID(アプリ生成)
    quote_id  TEXT NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    sender_id TEXT NOT NULL REFERENCES app_users(id),
    body      TEXT NOT NULL,
    file_path TEXT,                          -- 図面・仕様書PDF等の添付
    sent_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    read_at   TEXT
);

CREATE INDEX IF NOT EXISTS idx_messages_quote ON messages (quote_id, sent_at);

-- updated_at トリガ
CREATE TRIGGER IF NOT EXISTS trg_users_touch AFTER UPDATE ON app_users
BEGIN
    UPDATE app_users SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
     WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_products_touch AFTER UPDATE ON products
BEGIN
    UPDATE products SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
     WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_quotes_touch AFTER UPDATE ON quotes
BEGIN
    UPDATE quotes SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
     WHERE id = NEW.id;
END;

-- 在庫・価格テーブルは意図的に存在しない(基幹APIの責務)
