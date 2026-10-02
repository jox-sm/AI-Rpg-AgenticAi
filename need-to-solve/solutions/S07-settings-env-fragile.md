# S07 — Settings: Pydantic-Settings Fail-Fast

Best practice:
```python
class Settings(BaseSettings):
  model_config = SettingsConfigDict(env_file=("rpg_ai_server/.env",".env"), extra="ignore")
  redis_url: RedisDsn; upstash_token: SecretStr; ...
  @field_validator("redis_port") ...
settings = Settings()  # single aggregated ValidationError
```
- One `.env` path list, log which file loaded.
- Delete dead `host/port/db` OR implement local `redis.asyncio` client when `use_upstash=False`.
- Factories `create_*` raise `ValueError("missing GOOGLE/OPENROUTER key")` at startup, not 401 deep.
- `NEXTJS_WEBHOOK: HttpUrl|None` in Settings, not `os.getenv` in route. No `sys.path` hack, consistent relative imports, `__init__.__all__`.
