-- =====================================================================
-- 製造業向け 見積・受注アプリ スキーマ(mfg)
-- PostgreSQL 15+ / シングルテナント(1社1式)
--
-- 原則:
--  - 在庫・価格の正は会社側の基幹システム。本DBは持たない(API参照)
--  - 決済を持たない。見積番号はDB全体の通し番号(年+連番)
--  - 認証は PocketBase(顧客・社内スタッフとも個人別アカウント)
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS mfg;

-- ユーザー(PocketBase の身元に対応)。顧客(取引先担当者)と社内スタッフ
CREATE TABLE mfg.app_users (
    id            TEXT PRIMARY KEY,          -- PocketBase record id
    display_name  TEXT NOT NULL,
    company_name  TEXT,                      -- 顧客の所属会社
    contact_label TEXT,                      -- 社内スタッフの担当部門/担当者名
    role          TEXT NOT NULL DEFAULT 'customer'
                  CHECK (role IN ('customer', 'staff', 'admin')),
    is_suspended  BOOLEAN NOT NULL DEFAULT false,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE mfg.categories (
    id         SERIAL PRIMARY KEY,
    slug       TEXT NOT NULL UNIQUE,
    name       TEXT NOT NULL,                -- 例: 玄関ドア / 省力機械 / 保守部品
    sort_order INT NOT NULL DEFAULT 0
);

-- 製品(カタログ)。公開分は静的JSONとして R2 へ配信される
CREATE TABLE mfg.products (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code         TEXT NOT NULL UNIQUE,       -- 製品コード(基幹と共通のキー。
                                             -- QR・基幹API照合に使う)
    name         TEXT NOT NULL,
    category_id  INT NOT NULL REFERENCES mfg.categories(id),
    summary      TEXT,                       -- カード用の一言
    description  TEXT,
    specs        JSONB NOT NULL DEFAULT '{}'::jsonb,
                                             -- 仕様(寸法・材質・性能等の キー:値)
    price_note   TEXT,                       -- 「参考価格」「要見積」等の表示。
                                             -- 実価格は基幹APIから(本DBは持たない)
    is_public    BOOLEAN NOT NULL DEFAULT true,   -- 公開カタログに載せるか
    is_active    BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_products_cat ON mfg.products (category_id)
    WHERE is_public AND is_active;

CREATE TABLE mfg.product_photos (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES mfg.products(id) ON DELETE CASCADE,
    path       TEXT NOT NULL,
    sort_order INT NOT NULL DEFAULT 0
);

-- 見積依頼(seed の requests に対応)。取引の単位・経理の記録単位
CREATE TABLE mfg.quotes (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id  TEXT NOT NULL REFERENCES mfg.app_users(id),
    -- 見積番号: DB全体の通し番号(年+連番。例 2026-00042)。
    -- 会社の基幹・会計の伝票番号との照合キー。QRにも載せる
    quote_no     TEXT UNIQUE NOT NULL,       -- 挿入時にアプリが採番して渡す
                                             -- (既定値なし。空文字挿入禁止)
    -- 採番は pg_advisory_xact_lock で直列化して MAX(quote_seq)+1。
    -- quote_no の UNIQUE と下の複合 UNIQUE が安全網
    quote_year   INT NOT NULL,
    quote_seq    INT NOT NULL,
    UNIQUE (quote_year, quote_seq),
    status       TEXT NOT NULL DEFAULT 'requested'
                 CHECK (status IN ('requested',  -- 依頼受付
                                   'answered',   -- 見積回答済み
                                   'ordered',    -- 受注(顧客が発注)
                                   'declined',   -- 辞退(見積不可/失注)
                                   'cancelled',  -- 顧客取下げ
                                   'closed',     -- 完了(納品等の後)
                                   'expired')),  -- 放置の自動クローズ
    note         TEXT,                       -- 依頼時の要望(用途・数量・納期等)
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),  -- 受付日時
    answered_at  TIMESTAMPTZ,                -- 回答日時
    answered_by  TEXT REFERENCES mfg.app_users(id),   -- 回答した担当者
    ordered_at   TIMESTAMPTZ,                -- 受注日時(台帳の計上基準)
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_quotes_customer ON mfg.quotes (customer_id, created_at DESC);
CREATE INDEX idx_quotes_open ON mfg.quotes (created_at)
    WHERE status = 'requested';

CREATE TABLE mfg.quote_items (
    quote_id   UUID NOT NULL REFERENCES mfg.quotes(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES mfg.products(id),
    quantity   INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    spec_note  TEXT,                         -- 個別仕様(色・寸法指定等)
    PRIMARY KEY (quote_id, product_id)
);

-- 見積カート(依頼前の選択。サーバー保持で端末をまたぐ)
CREATE TABLE mfg.cart_items (
    user_id    TEXT NOT NULL REFERENCES mfg.app_users(id),
    product_id UUID NOT NULL REFERENCES mfg.products(id) ON DELETE CASCADE,
    quantity   INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    spec_note  TEXT,
    added_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, product_id)
);

-- メッセージ(見積単位のスレッド。仕様のやり取り・回答・納期調整)
CREATE TABLE mfg.messages (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id  UUID NOT NULL REFERENCES mfg.quotes(id) ON DELETE CASCADE,
    sender_id TEXT NOT NULL REFERENCES mfg.app_users(id),
    body      TEXT NOT NULL,
    file_path TEXT,                          -- 図面・仕様書PDF等の添付
    sent_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at   TIMESTAMPTZ
);

CREATE INDEX idx_messages_quote ON mfg.messages (quote_id, sent_at);

-- updated_at トリガ
CREATE OR REPLACE FUNCTION mfg.touch_updated_at()
RETURNS trigger AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_touch BEFORE UPDATE ON mfg.app_users
    FOR EACH ROW EXECUTE FUNCTION mfg.touch_updated_at();
CREATE TRIGGER trg_products_touch BEFORE UPDATE ON mfg.products
    FOR EACH ROW EXECUTE FUNCTION mfg.touch_updated_at();
CREATE TRIGGER trg_quotes_touch BEFORE UPDATE ON mfg.quotes
    FOR EACH ROW EXECUTE FUNCTION mfg.touch_updated_at();

-- 在庫・価格テーブルは意図的に存在しない(基幹APIの責務)
