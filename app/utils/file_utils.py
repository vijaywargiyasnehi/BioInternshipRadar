"""Filesystem helpers for resume/document storage paths."""
import json
import re
from datetime import datetime
from pathlib import Path

from app.config import settings


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[\s_-]+", "_", value)


def generated_resume_dir_for(company_name: str) -> Path:
    base = settings.resolved_path(settings.generated_resume_dir) / slugify(company_name)
    base.mkdir(parents=True, exist_ok=True)
    return base


def generated_resume_path(company_name: str, role_title: str, extension: str = "docx") -> Path:
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{date_str}_{slugify(company_name)}_{slugify(role_title)}_resume.{extension}"
    return generated_resume_dir_for(company_name) / filename


def generated_metadata_path(resume_path: Path) -> Path:
    return resume_path.with_name(resume_path.stem.replace("_resume", "_metadata") + ".json")


def write_metadata(metadata_path: Path, data: dict) -> None:
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
