# 残タスク(2026-07-08 時点)

Phase 0〜6 は実装済み(テスト51件+Flutter analyze/test/build 通過)。
残りは結線・確認系と、意図的に保留した項目。

## 次にやる(結線・確認)

1. **PocketBase 実機疎通+ログイン差し替え**
   - バイナリは `pb/` 配置済み(git 管理外)。`pb/pocketbase serve` で起動
   - staff/ のログインを開発用スタッフ選択 → PB auth-with-password に差し替え
     (`staff/main.py` の `pick_staff()` に差し替えポイントを明記済み)
   - 顧客アプリのログイン/登録(実装済み)を実機で確認
   - PB の users コレクションに `company` フィールドを足すか判断
     (`core/auth.py` が `rec.company` を読む。無ければ NULL のまま)
2. **ブラウザ E2E**: Flutter web ⇔ API ⇔ 静的JSON(CATALOG_URL)を通しで。
   依頼→staff 回答→発注の一巡

## 保留(採用判断が要る)

3. 顧客側の添付**ダウンロード**(認可ヘッダー付き取得。Web は blob 保存が必要)
4. トークン**永続化**(shared_preferences の追加確認。現状リロードで再ログイン)
5. 顧客側の **PDF 添付送信**(file_picker の追加確認。現状は画像のみ)

## 導入時(会社ごと・ユーザー操作)

6. cf-publish で site/dist を Pages/R2 へ公開(外部接続はユーザー操作)
7. Cloudflare 設定(DNS・Full Strict・Origin CA・nftables の CF レンジ許可)
8. 実サーバー構築: deploy/ の unit 配置・restore.md の実地確認・
   メール専用機(Stalwart+DKIM/SPF/DMARC/PTR)
9. `site/company.json`・`.env`(COMPANY_MAIL_TO / APP_BASE_URL / KIKAN_URL 等)を
   導入先の値に
