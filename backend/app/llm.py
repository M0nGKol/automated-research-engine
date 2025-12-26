"""LLM provider factory for LLaMA 3 models.

Supports:
- Ollama: Local inference (recommended for development)
- vLLM: Hosted OpenAI-compatible endpoints (recommended for production)
"""

from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from app.config import get_settings


@lru_cache
def get_llm() -> BaseChatModel:
    """
    Factory function to get the configured LLaMA 3 LLM.

    Supports two providers:
    1. Ollama - Local inference via ollama serve
    2. vLLM - OpenAI-compatible API (self-hosted or cloud)

    Returns:
        BaseChatModel: Configured LangChain chat model
    """
    settings = get_settings()

    if settings.llm_provider == "ollama":
        return _create_ollama_llm(settings)
    elif settings.llm_provider == "vllm":
        return _create_vllm_llm(settings)
    else:
        raise ValueError(
            f"Unknown LLM provider: {settings.llm_provider}. "
            "Supported: 'ollama', 'vllm'"
        )


def _create_ollama_llm(settings) -> BaseChatModel:
    """Create Ollama-backed LLaMA model for local inference."""
    from langchain_community.chat_models import ChatOllama

    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        num_predict=settings.llm_max_tokens,
    )


def _create_vllm_llm(settings) -> BaseChatModel:
    """Create vLLM-backed LLaMA model via OpenAI-compatible API."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        base_url=settings.vllm_base_url,
        api_key=settings.vllm_api_key,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )


def check_llm_health() -> dict:
    """Check if the LLM provider is accessible."""
    settings = get_settings()

    try:
        llm = get_llm()
        # Quick test invocation
        response = llm.invoke("Say 'ok' if you're working.")
        return {
            "status": "healthy",
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "response_preview": str(response.content)[:50],
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "error": str(e),
        }
