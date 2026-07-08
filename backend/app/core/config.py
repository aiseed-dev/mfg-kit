from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_path: str = "data/mfg.db"
    files_dir: str = "data/files"  # メッセージ添付の保存先
    pb_url: str = "http://localhost:8090"
    app_base_url: str = "https://app.example.jp"  # 顧客アプリ。QRの飛び先

    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    mail_from: str = "noreply@example.jp"
    company_mail_to: str = "eigyo@example.jp"
    mail_backend: str = "smtp"  # smtp / console(dev・テスト)

    expire_days: int = 14
    kikan_url: str = ""  # 会社の基幹API。空なら未接続=「要見積」表示
    export_dir: str = "data/exports"  # 台帳 xlsx・QRラベル PDF の出力先


settings = Settings()
