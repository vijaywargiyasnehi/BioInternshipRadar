"""Anthropic-backed resume tailoring. Only used when LLM_PROVIDER=anthropic and
ANTHROPIC_API_KEY is set. See README privacy notes before enabling."""
import json
import re

import requests

from app.config import settings
from app.llm.base_llm import BaseLLM, LLMTailorResult, RESUME_TAILORING_SYSTEM_PROMPT


class AnthropicLLM(BaseLLM):
    provider_name = "anthropic"

    def tailor_resume(self, resume_text: str, job_description: str, job_title: str, company_name: str) -> LLMTailorResult:
        if not settings.anthropic_api_key:
            return LLMTailorResult("", [], ["ANTHROPIC_API_KEY not set — skipped LLM tailoring."], [], "")

        user_prompt = (
            f"Company: {company_name}\nRole: {job_title}\n\n"
            f"Job description:\n{job_description}\n\n"
            f"Base resume text:\n{resume_text}\n\n"
            "Respond with ONLY a JSON object with keys: summary, revised_bullets (list), warnings (list), "
            "keywords_to_emphasize (list), networking_message. No prose outside the JSON."
        )

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 2000,
                    "system": RESUME_TAILORING_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
                timeout=30,
            )
            resp.raise_for_status()
            text = resp.json()["content"][0]["text"]
            match = re.search(r"\{.*\}", text, re.DOTALL)
            parsed = json.loads(match.group(0)) if match else {}
        except Exception as exc:
            return LLMTailorResult("", [], [f"Anthropic request failed: {exc}"], [], "")

        return LLMTailorResult(
            summary=parsed.get("summary", ""),
            revised_bullets=parsed.get("revised_bullets", []),
            warnings=parsed.get("warnings", []),
            keywords_to_emphasize=parsed.get("keywords_to_emphasize", []),
            networking_message=parsed.get("networking_message", ""),
        )
