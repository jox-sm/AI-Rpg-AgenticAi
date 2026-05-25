from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class RedisConfig:
    host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    input_db: int = field(default_factory=lambda: int(os.getenv("REDIS_INPUT_DB", "0")))
    output_db: int = field(default_factory=lambda: int(os.getenv("REDIS_OUTPUT_DB", "1")))
    password: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_PASSWORD", None))
    ttl_seconds: int = field(default_factory=lambda: int(os.getenv("REDIS_TTL_SECONDS", "3600")))

    @property
    def input_url(self) -> str:
        return f"redis://{self._auth_part}{self.host}:{self.port}/{self.input_db}"

    @property
    def output_url(self) -> str:
        return f"redis://{self._auth_part}{self.host}:{self.port}/{self.output_db}"

    @property
    def _auth_part(self) -> str:
        return f":{self.password}@" if self.password else ""


@dataclass
class ModelConfig:
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
    image_model: str = field(default_factory=lambda: os.getenv("IMAGE_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"))
    redescription_model: str = field(default_factory=lambda: os.getenv("REDESCRIPTION_MODEL", "openrouter/owl-alpha"))
    tool_agent_model: str = field(default_factory=lambda: os.getenv("TOOL_AGENT_MODEL", "qwen/qwen3-coder:free"))
    context_injector_model: str = field(default_factory=lambda: os.getenv("CONTEXT_INJECTOR_MODEL", "nvidia/nemotron-3-super-120b-a12b:free"))
    story_model: str = field(default_factory=lambda: os.getenv("STORY_MODEL", "qwen/qwen3-coder:free"))


@dataclass
class AppConfig:
    max_concurrent_requests: int = field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_REQUESTS", "100")))
    output_memory_threshold: float = field(default_factory=lambda: float(os.getenv("OUTPUT_MEMORY_THRESHOLD", "90.0")))
    backoff_seconds: float = field(default_factory=lambda: float(os.getenv("BACKOFF_SECONDS", "3.0")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    openrouter_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", None))
    openrouter_base_url: str = field(default_factory=lambda: os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))
    google_api_key: Optional[str] = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", None))


@dataclass
class Settings:
    redis: RedisConfig = field(default_factory=RedisConfig)
    models: ModelConfig = field(default_factory=ModelConfig)
    app: AppConfig = field(default_factory=AppConfig)


settings = Settings()
