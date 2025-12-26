"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Provider: "ollama" (local) or "vllm" (hosted OpenAI-compatible)
    llm_provider: Literal["ollama", "vllm"] = "ollama"

    # Ollama Configuration (local inference)
    ollama_base_url: str = "http://localhost:11434"

    # vLLM / OpenAI-compatible Configuration (hosted inference)
    vllm_base_url: str = "http://localhost:8080/v1"
    vllm_api_key: str = "EMPTY"  # vLLM doesn't require auth by default

    # Model Configuration - LLaMA 3 variants
    # For Ollama: "llama3", "llama3:8b", "llama3:70b"
    # For vLLM: "meta-llama/Meta-Llama-3-8B-Instruct", etc.
    llm_model: str = "llama3:8b"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096

    # Google Custom Search API Configuration
    google_api_key: str = ""
    google_cse_id: str = ""

    # Clerk Authentication Configuration
    clerk_secret_key: str = ""  # From Clerk dashboard
    clerk_publishable_key: str = ""  # From Clerk dashboard

    # Search Configuration
    max_search_results: int = 10
    max_sources_to_process: int = 5

    # Server Configuration
    api_host: str = "0.0.0.0"
    api_port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
