from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---
    ANTHROPIC_API_KEY: str = Field(default="")
    LLM_MODEL: str = Field(default="claude-sonnet-5")
    LLM_MODEL_FAST: str = Field(default="claude-haiku-4-5-20251001")
    LLM_MAX_TOKENS: int = Field(default=2000)
    AGENT_MAX_STEPS: int = Field(default=6)
    TOOL_OUTPUT_MAX_CHARS: int = Field(default=12000)

    # --- Embeddings ---
    EMBED_PROVIDER: Literal["local", "voyage", "openai", "gemini"] = Field(default="local")
    EMBED_MODEL: str = Field(default="BAAI/bge-small-en-v1.5")
    EMBED_DIM: int = Field(default=384)

    # --- Postgres / Redis ---
    DATABASE_URL: str = Field(default="postgresql://incident:incident@localhost:5432/incident")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # --- Slack (Socket Mode) ---
    SLACK_BOT_TOKEN: str = Field(default="")
    SLACK_APP_TOKEN: str = Field(default="")
    SLACK_INCIDENT_CHANNEL: str = Field(default="")

    # --- API ---
    API_KEY: str = Field(default="change-me")
    PUBLIC_BASE_URL: str = Field(default="http://localhost:8000")

    # --- Adapters ---
    ADAPTER_MODE: Literal["mock", "real"] = Field(default="mock")
    MOCK_SCENARIO: str = Field(default="A_pool_exhaustion")
    PROMETHEUS_URL: str = Field(default="")
    LOKI_URL: str = Field(default="")
    GITHUB_TOKEN: str = Field(default="")

    # --- Retrieval tuning ---
    RETRIEVAL_TOP_K: int = Field(default=3)
    RETRIEVAL_CANDIDATES: int = Field(default=20)
    W_VEC: float = Field(default=0.35)
    W_FTS: float = Field(default=0.15)
    W_FP: float = Field(default=0.20)
    W_SVC: float = Field(default=0.15)
    W_CODE: float = Field(default=0.15)
    DECAY_HALF_LIFE_DAYS: int = Field(default=365)
    PATTERN_MIN_CLUSTER: int = Field(default=3)
    PATTERN_DISTANCE_THRESHOLD: float = Field(default=0.25)

    # --- Safety ---
    ALLOW_ACTIONS: bool = Field(default=False)

    # --- Logging ---
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: Literal["json", "console"] = Field(default="console")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
