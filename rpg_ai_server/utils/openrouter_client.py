from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from ..config.settings import settings
from ..utils.logger import logger


class OpenRouterDirectClient:
    def __init__(self):
        self.api_key = settings.app.openrouter_api_key
        self.base_url = settings.app.openrouter_base_url
        self._http: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=120.0,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://rpg-ai-server.local",
                    "X-Title": "RPG AI Server",
                },
            )
        return self._http

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        response_format: Optional[Dict[str, str]] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        client = await self._get_client()
        body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            body["response_format"] = response_format

        # NOTE: no leading slash — httpx replaces base_url path on absolute paths,
        # which dropped /api/v1 and caused 404s on every direct call.
        response = await client.post("chat/completions", json=body)
        response.raise_for_status()
        data = response.json()
        # Flaky free-tier providers sometimes return 200 with no usable choice
        # (overload envelopes). Fail loudly so node fallbacks trigger.
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"empty/unparseable LLM envelope: {str(data)[:200]}") from e
        if not content:
            raise RuntimeError("empty LLM content")
        return data

    async def extract_json(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        result = await self.chat_completion(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = result["choices"][0]["message"]["content"]
        import json
        return json.loads(content)

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()


_openrouter_client: Optional[OpenRouterDirectClient] = None


def get_openrouter_direct() -> OpenRouterDirectClient:
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = OpenRouterDirectClient()
    return _openrouter_client
