from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://mfg:mfg@localhost:5432/mfg"
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


settings = Settings()
