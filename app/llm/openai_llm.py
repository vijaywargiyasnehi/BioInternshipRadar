"""OpenAI-backed resume tailoring. Only used when LLM_PROVIDER=openai and OPENAI_API_KEY is set.

NOTE: enabling this sends resume text and job descriptions to OpenAI's API. See README
privacy notes. Kept deliberately simple (single chat completion call) since this is a
review-before-use assistant, not an autonomous agent.
"""
import json

import requests

from app.config import settings
from app.llm.base_llm import BaseLLM, LLMTailorResult, RESUME_TAILORING_SYSTEM_PROMPT


class OpenAILLM(BaseLLM):
    provider_name = "openai"

    def tailor_resume(self, resume_text: str, job_description: str, job_title: str, company_name: str) -> LLMTailorResult:
        if not settings.openai_api_key:
            return LLMTailorResult("", [], ["OPENAI_API_KEY not set — skipped LLM tailoring."], [], "")

        user_prompt = (
            f"Company: {company_name}\nRole: {job_title}\n\n"
            f"Job description:\n{job_description}\n\n"
            f"Base resume text:\n{resume_text}\n\n"
            "Respond as strict JSON with keys: summary, revised_bullets (list), warnings (list), "
            "keywords_to_emphasize (list), networking_message."
        )

        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": RESUME_TAILORING_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                },
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except Exception as exc:
            return LLMTailorResult("", [], [f"OpenAI request failed: {exc}"], [], "")

        return LLMTailorResult(
            summary=parsed.get("summary", ""),
            revised_bullets=parsed.get("revised_bullets", []),
            warnings=parsed.get("warnings", []),
            keywords_to_emphasize=parsed.get("keywords_to_emphasize", []),
            networking_message=parsed.get("networking_message", ""),
        )
