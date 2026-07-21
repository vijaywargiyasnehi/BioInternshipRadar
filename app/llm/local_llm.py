"""Local LLM provider (e.g. Ollama/LM Studio exposing an OpenAI-compatible endpoint).

Only used when LLM_PROVIDER=local and LOCAL_LLM_URL is set. No data leaves the machine
since the endpoint is expected to be localhost.
"""
import json
import re

import requests

from app.config import settings
from app.llm.base_llm import BaseLLM, LLMTailorResult, RESUME_TAILORING_SYSTEM_PROMPT


class LocalLLM(BaseLLM):
    provider_name = "local"

    def tailor_resume(self, resume_text: str, job_description: str, job_title: str, company_name: str) -> LLMTailorResult:
        if not settings.local_llm_url:
            return LLMTailorResult("", [], ["LOCAL_LLM_URL not set — skipped LLM tailoring."], [], "")

        user_prompt = (
            f"Company: {company_name}\nRole: {job_title}\n\n"
            f"Job description:\n{job_description}\n\n"
            f"Base resume text:\n{resume_text}\n\n"
            "Respond with ONLY a JSON object with keys: summary, revised_bullets (list), warnings (list), "
            "keywords_to_emphasize (list), networking_message."
        )

        try:
            resp = requests.post(
                settings.local_llm_url,
                json={
                    "messages": [
                        {"role": "system", "content": RESUME_TAILORING_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=60,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            match = re.search(r"\{.*\}", text, re.DOTALL)
            parsed = json.loads(match.group(0)) if match else {}
        except Exception as exc:
            return LLMTailorResult("", [], [f"Local LLM request failed: {exc}"], [], "")

        return LLMTailorResult(
            summary=parsed.get("summary", ""),
            revised_bullets=parsed.get("revised_bullets", []),
            warnings=parsed.get("warnings", []),
            keywords_to_emphasize=parsed.get("keywords_to_emphasize", []),
            networking_message=parsed.get("networking_message", ""),
        )
