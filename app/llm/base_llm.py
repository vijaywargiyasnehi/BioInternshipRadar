"""Abstraction layer for optional LLM-assisted resume tailoring.

All providers must implement tailor_resume() with the same signature so resume_tailor.py
doesn't need to know which provider is active. The default provider is NoLLM, which
performs no API calls — the app works fully without any LLM configured.
"""
from abc import ABC, abstractmethod


class LLMTailorResult:
    def __init__(self, summary: str, revised_bullets: list[str], warnings: list[str], keywords_to_emphasize: list[str], networking_message: str):
        self.summary = summary
        self.revised_bullets = revised_bullets
        self.warnings = warnings
        self.keywords_to_emphasize = keywords_to_emphasize
        self.networking_message = networking_message


RESUME_TAILORING_SYSTEM_PROMPT = """You are tailoring a resume for an internship opportunity.
Do not invent experience.
Only use facts present in the base resume.
You may rewrite bullets for clarity and relevance.
You may reorder content.
You may create a concise professional summary.
You must output:
1. Suggested resume changes
2. Revised resume text
3. Warnings about missing qualifications
4. Keywords to emphasize
5. A short networking message"""


class BaseLLM(ABC):
    provider_name: str = "base"

    @abstractmethod
    def tailor_resume(self, resume_text: str, job_description: str, job_title: str, company_name: str) -> LLMTailorResult:
        raise NotImplementedError
