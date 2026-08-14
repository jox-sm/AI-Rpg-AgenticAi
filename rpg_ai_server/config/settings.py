from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_ENV_FILE)


@dataclass
class RedisConfig:
    host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    input_db: int = field(default_factory=lambda: int(os.getenv("REDIS_INPUT_DB", "0")))
    output_db: int = field(default_factory=lambda: int(os.getenv("REDIS_OUTPUT_DB", "1")))
    password: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_PASSWORD", None))
    ttl_seconds: int = field(default_factory=lambda: int(os.getenv("REDIS_TTL_SECONDS", "3600")))
    upstash_rest_url: Optional[str] = field(default_factory=lambda: os.getenv("UPSTASH_REDIS_REST_URL", None))
    upstash_rest_token: Optional[str] = field(default_factory=lambda: os.getenv("UPSTASH_REDIS_REST_TOKEN", None))

    @property
    def use_upstash(self) -> bool:
        return bool(self.upstash_rest_url and self.upstash_rest_token)


@dataclass
class SearchConfig:
    upstash_search_url: Optional[str] = field(default_factory=lambda: os.getenv("UPSTASH_SEARCH_REST_URL", None))
    upstash_search_token: Optional[str] = field(default_factory=lambda: os.getenv("UPSTASH_SEARCH_REST_TOKEN", None))
    index_name: str = field(default_factory=lambda: os.getenv("SEARCH_INDEX_NAME", "game-memory"))
    top_k: int = field(default_factory=lambda: int(os.getenv("SEARCH_TOP_K", "3")))
    reranking: bool = field(default_factory=lambda: os.getenv("SEARCH_RERANKING", "false").lower() == "true")
    semantic_weight: float = field(default_factory=lambda: float(os.getenv("SEARCH_SEMANTIC_WEIGHT", "0.75")))
    input_enrichment: bool = field(default_factory=lambda: os.getenv("SEARCH_INPUT_ENRICHMENT", "true").lower() != "false")
    chunk_max_tokens: int = field(default_factory=lambda: int(os.getenv("SEARCH_CHUNK_MAX_TOKENS", "512")))
    chunk_overlap_tokens: int = field(default_factory=lambda: int(os.getenv("SEARCH_CHUNK_OVERLAP_TOKENS", "32")))

    @property
    def configured(self) -> bool:
        return bool(self.upstash_search_url and self.upstash_search_token)


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
    loop_recursion_limit: int = field(default_factory=lambda: int(os.getenv("LOOP_RECURSION_LIMIT", "60")))
    router_max_passes: int = field(default_factory=lambda: int(os.getenv("ROUTER_MAX_PASSES", "4")))
    max_tool_calls: int = field(default_factory=lambda: int(os.getenv("MAX_TOOL_CALLS", "15")))
    request_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("REQUEST_TIMEOUT_SECONDS", "120.0")))
    remaining_steps_min: int = field(default_factory=lambda: int(os.getenv("REMAINING_STEPS_MIN", "10")))
    lock_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("LOCK_TTL_SECONDS", "30")))
    lock_refresh_interval: float = field(default_factory=lambda: float(os.getenv("LOCK_REFRESH_INTERVAL", "10.0")))


@dataclass
class Settings:
    redis: RedisConfig = field(default_factory=RedisConfig)
    models: ModelConfig = field(default_factory=ModelConfig)
    app: AppConfig = field(default_factory=AppConfig)
    search: SearchConfig = field(default_factory=SearchConfig)


settings = Settings()
