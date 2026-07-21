"""Orchestrates resume tailoring: parse base resume -> build plan -> optionally consult
LLM -> generate .docx -> save metadata.json -> record GeneratedDocument + update opportunity."""
from datetime import datetime

import yaml
from sqlalchemy.orm import Session

from app.config import settings
from app.llm import get_llm_provider
from app.models import GeneratedDocument, Opportunity
from app.resume.docx_generator import generate_tailored_docx
from app.resume.resume_parser import parse_resume
from app.resume.resume_tailor import build_tailoring_plan, TailoringPlan
from app.services.opportunity_service import mark_resume_generated
from app.utils.file_utils import generated_metadata_path, generated_resume_path, write_metadata


def load_student_profile() -> dict:
    if not settings.student_profile_yaml_path.exists():
        return {}
    with open(settings.student_profile_yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def preview_tailoring(opportunity: Opportunity, use_llm: bool = False) -> tuple[TailoringPlan, dict]:
    """Builds the tailoring plan without writing any files, for the dashboard preview step."""
    base_path = settings.resolved_path(settings.base_resume_path)
    parsed = parse_resume(base_path)
    plan = build_tailoring_plan(parsed, opportunity.job_title, opportunity.description, opportunity.company_name)

    llm_result = None
    if use_llm and settings.llm_provider != "none":
        provider = get_llm_provider()
        llm_output = provider.tailor_resume(parsed.full_text, opportunity.description, opportunity.job_title, opportunity.company_name)
        llm_result = {
            "summary": llm_output.summary,
            "revised_bullets": llm_output.revised_bullets,
            "warnings": llm_output.warnings,
            "keywords_to_emphasize": llm_output.keywords_to_emphasize,
            "networking_message": llm_output.networking_message,
        }
        if llm_output.summary:
            plan.suggested_summary = llm_output.summary
        plan.warnings.extend(llm_output.warnings)

    return plan, (llm_result or {})


def generate_resume_for_opportunity(session: Session, opportunity: Opportunity, plan: TailoringPlan) -> tuple[str, str]:
    """Generates the tailored .docx + metadata.json and records it. Returns (resume_path, metadata_path)."""
    base_path = settings.resolved_path(settings.base_resume_path)
    output_path = generated_resume_path(opportunity.company_name, opportunity.job_title)

    generate_tailored_docx(base_path, plan, output_path, opportunity.job_title, opportunity.company_name)

    metadata_path = generated_metadata_path(output_path)
    metadata = {
        "company": opportunity.company_name,
        "role_title": opportunity.job_title,
        "job_url": opportunity.job_url,
        "generated_at": datetime.utcnow().isoformat(),
        "base_resume_used": str(base_path),
        "matched_keywords": plan.matched_keywords,
        "changes_made": plan.changes_made,
        "warnings": plan.warnings,
    }
    write_metadata(metadata_path, metadata)

    doc_record = GeneratedDocument(
        opportunity_id=opportunity.id,
        company_name=opportunity.company_name,
        job_title=opportunity.job_title,
        document_type="resume",
        file_path=str(output_path),
        metadata_path=str(metadata_path),
        base_resume_path=str(base_path),
    )
    session.add(doc_record)
    mark_resume_generated(session, opportunity.id, str(output_path))
    session.flush()

    return str(output_path), str(metadata_path)
