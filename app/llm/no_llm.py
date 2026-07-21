"""Default no-op LLM provider. Used when LLM_PROVIDER=none (the default)."""
from app.llm.base_llm import BaseLLM, LLMTailorResult


class NoLLM(BaseLLM):
    provider_name = "none"

    def tailor_resume(self, resume_text: str, job_description: str, job_title: str, company_name: str) -> LLMTailorResult:
        return LLMTailorResult(
            summary="",
            revised_bullets=[],
            warnings=["LLM provider is set to 'none' — only rule-based tailoring was applied."],
            keywords_to_emphasize=[],
            networking_message="",
        )
