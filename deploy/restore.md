# リストア手順(目標復旧: 半日)

データは「SQLite ファイル2つ+画像・添付フォルダ」だけ。
置き戻せば戻る、が基本方針。

## 前提

- サーバー再構築は「セットアップ手順」(このディレクトリの unit ファイル
  配置と `git clone`+venv 作成)を先に済ませる
- バックアップは R2 の `mfg-backup/` に毎晩(保持14日)

## 手順

1. サービスを止める
   ```bash
   sudo systemctl stop mfg-api mfg-staff pocketbase
   ```
2. バックアップを取得して展開
   ```bash
   rclone copy r2:mfg-backup/db/db-YYYYMMDD.tar.gz /tmp/
   tar -xzf /tmp/db-YYYYMMDD.tar.gz -C /tmp/
   ```
3. 置き戻す
   ```bash
   cp /tmp/mfg.db /srv/mfg/data/mfg.db
   rm -rf /srv/mfg/pb/pb_data && cp -r /tmp/pb_data /srv/mfg/pb/pb_data
   rclone sync r2:mfg-backup/images/ /srv/mfg/data/images/
   rclone sync r2:mfg-backup/files/  /srv/mfg/data/files/
   ```
4. サービスを起動して確認
   ```bash
   sudo systemctl start pocketbase mfg-api mfg-staff
   curl -s localhost:8000/healthz        # {"status":"ok"}
   ```
5. 静的カタログを再生成して公開(必要なら)
   ```bash
   cd /srv/mfg && .venv/bin/python -m app.services.staticgen
   # cf-publish で Pages/R2 へ(公開操作は会社の担当者が実行)
   ```

## 注意

- 見積番号の連番は DB の中身から復元されるので、追加作業は不要
- バックアップ以降のデータ(最大24時間分)は失われる。顧客に影響する
  見積依頼はメール通知が残っているので、会社のメールボックスと突き合わせる
