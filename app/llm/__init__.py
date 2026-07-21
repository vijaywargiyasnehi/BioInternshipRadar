"""LLM provider factory."""
from app.config import settings
from app.llm.base_llm import BaseLLM


def get_llm_provider() -> BaseLLM:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        from app.llm.openai_llm import OpenAILLM
        return OpenAILLM()
    if provider == "anthropic":
        from app.llm.anthropic_llm import AnthropicLLM
        return AnthropicLLM()
    if provider == "local":
        from app.llm.local_llm import LocalLLM
        return LocalLLM()
    from app.llm.no_llm import NoLLM
    return NoLLM()
