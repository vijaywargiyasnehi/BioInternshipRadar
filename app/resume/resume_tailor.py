"""Rule-based resume tailoring: never invents experience, only reorders/emphasizes
truthful content from the base resume and flags missing keywords separately."""
from dataclasses import dataclass, field

from app.resume.resume_parser import ParsedResume, find_section
from app.services.keyword_service import match_all_categories
from app.utils.text_cleaning import normalize_text


@dataclass
class TailoringPlan:
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    suggested_summary: str = ""
    relevant_skills_section: list[str] = field(default_factory=list)
    bullet_suggestions: list[str] = field(default_factory=list)
    changes_made: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def build_tailoring_plan(parsed: ParsedResume, job_title: str, job_description: str, company_name: str) -> TailoringPlan:
    plan = TailoringPlan()

    jd_text = f"{job_title} {job_description}"
    jd_keyword_matches = match_all_categories(jd_text)
    jd_keywords = sorted({kw for kws in jd_keyword_matches.values() for kw in kws})

    resume_norm = normalize_text(parsed.full_text)
    matched = [kw for kw in jd_keywords if normalize_text(kw) in resume_norm]
    missing = [kw for kw in jd_keywords if kw not in matched]

    plan.matched_keywords = matched
    plan.missing_keywords = missing

    skills_section = find_section(parsed, "skill")
    existing_skills = skills_section.lines if skills_section else []

    # Only reorder/emphasize skills that already exist on the resume — never add new ones here.
    emphasized = [s for s in existing_skills if any(normalize_text(kw) in normalize_text(s) for kw in matched)]
    rest = [s for s in existing_skills if s not in emphasized]
    plan.relevant_skills_section = emphasized + rest
    if emphasized:
        plan.changes_made.append(f"Reordered Skills section to emphasize: {', '.join(emphasized[:6])}")

    if matched:
        plan.suggested_summary = (
            f"Bioengineering student with hands-on experience in "
            f"{', '.join(matched[:4])}, applying for the {job_title} role at {company_name}."
        )
        plan.changes_made.append("Generated tailored professional summary using only matched, existing skills")
    else:
        plan.warnings.append("No overlapping keywords found between resume and job description — review manually before applying.")

    if missing:
        plan.warnings.append(
            f"Job mentions keywords not found on your resume (do NOT add unless truthful): {', '.join(missing[:10])}"
        )

    experience_section = find_section(parsed, "experience") or find_section(parsed, "research")
    if experience_section:
        for line in experience_section.lines:
            if any(normalize_text(kw) in normalize_text(line) for kw in matched):
                plan.bullet_suggestions.append(line)
        if plan.bullet_suggestions:
            plan.changes_made.append("Identified existing experience bullets most relevant to this role for emphasis")

    return plan
