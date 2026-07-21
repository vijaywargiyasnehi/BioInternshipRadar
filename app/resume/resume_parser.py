"""Extracts text/sections from a base .docx resume for tailoring and LLM context."""
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document

SECTION_HEADERS = ("summary", "objective", "skills", "experience", "education", "projects", "research", "certifications")


@dataclass
class ResumeSection:
    title: str
    lines: list[str] = field(default_factory=list)


@dataclass
class ParsedResume:
    raw_paragraphs: list[str]
    sections: list[ResumeSection]
    full_text: str


def parse_resume(docx_path: Path) -> ParsedResume:
    if not docx_path.exists():
        raise FileNotFoundError(f"Base resume not found at {docx_path}")

    document = Document(str(docx_path))
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]

    sections: list[ResumeSection] = []
    current: ResumeSection | None = None
    for line in paragraphs:
        lowered = line.lower().strip(":")
        if lowered in SECTION_HEADERS or any(lowered.startswith(h) for h in SECTION_HEADERS):
            current = ResumeSection(title=line)
            sections.append(current)
        elif current is not None:
            current.lines.append(line)
        else:
            # Content before any recognized header (e.g. name/contact block).
            if not sections:
                sections.append(ResumeSection(title="Header"))
                current = sections[0]
            current.lines.append(line)

    return ParsedResume(raw_paragraphs=paragraphs, sections=sections, full_text="\n".join(paragraphs))


def find_section(parsed: ParsedResume, keyword: str) -> ResumeSection | None:
    keyword = keyword.lower()
    for section in parsed.sections:
        if keyword in section.title.lower():
            return section
    return None
