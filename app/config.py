"""Centralized application configuration loaded from .env."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BioInternshipRadar"
    app_env: str = "local"

    database_url: str = "sqlite:///data/database.sqlite"

    scan_interval_minutes: int = 15
    max_companies_per_scan_batch: int = 10
    enable_playwright: bool = True
    headless_browser: bool = True

    min_notification_fit_score: int = 60

    email_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: str = ""

    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    slack_enabled: bool = False
    slack_webhook_url: str = ""

    llm_provider: str = "none"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    local_llm_url: str = ""

    base_resume_path: str = "resumes/base/base_resume.docx"
    generated_resume_dir: str = "resumes/generated"
    export_dir: str = "exports"
    log_dir: str = "logs"

    usajobs_api_key: str = ""
    usajobs_email: str = ""

    internship_only: bool = True

    dashboard_url: str = "http://localhost:8501"

    @property
    def companies_yaml_path(self) -> Path:
        return BASE_DIR / "data" / "companies.yaml"

    @property
    def keywords_yaml_path(self) -> Path:
        return BASE_DIR / "data" / "keywords.yaml"

    @property
    def ignored_keywords_yaml_path(self) -> Path:
        return BASE_DIR / "data" / "ignored_keywords.yaml"

    @property
    def locations_yaml_path(self) -> Path:
        return BASE_DIR / "data" / "locations.yaml"

    @property
    def student_profile_yaml_path(self) -> Path:
        return BASE_DIR / "data" / "student_profile.yaml"

    def resolved_path(self, relative: str) -> Path:
        p = Path(relative)
        return p if p.is_absolute() else BASE_DIR / p


settings = Settings()

for d in (settings.log_dir, settings.export_dir, settings.generated_resume_dir, "resumes/base", "resumes/archive", "data"):
    settings.resolved_path(d).mkdir(parents=True, exist_ok=True)
