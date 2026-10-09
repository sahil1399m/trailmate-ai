"""
TrailMate AI - Application Configuration

Centralises all configuration values. Settings are loaded from environment
variables (or a .env file at the project root) via pydantic-settings.

Unknown environment variables (e.g. HF_TOKEN) are silently ignored so that
the .env file can hold model-management tokens without breaking app startup.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Silently ignore env vars not declared as fields (e.g. HF_TOKEN)
        extra="ignore",
        # Allow field names that start with 'model_' without a Pydantic warning
        protected_namespaces=(),
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_name: str = "TrailMate AI"
    app_version: str = "0.1.0"
    debug: bool = False

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Model ─────────────────────────────────────────────────────────────────
    # Local GGUF path (used when the file is present on disk).
    model_path: str = "models/smollm2-1.7b-instruct-q4_k_m.gguf"

    # ── LLM runtime (llama-cli via llama.cpp) ────────────────────────────────
    # HuggingFace repo + file — llama-cli will serve from its local HF cache
    # after the first download, so no re-download occurs on every request.
    llm_hf_repo: str = "HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF"
    llm_hf_file: str = "smollm2-1.7b-instruct-q4_k_m.gguf"

    # Maximum tokens to generate per request
    llm_max_tokens: int = 256

    # Subprocess wall-clock timeout in seconds
    llm_timeout: int = 120


# Singleton instance used throughout the application
settings = Settings()
