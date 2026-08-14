from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..config.settings import settings
from ..utils.logger import logger


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def split_into_chunks(text: str, max_tokens: int | None = None, overlap_tokens: int | None = None) -> List[str]:
    """Split text into overlapping chunks bounded by an estimated token budget.

    First splits on sentence/line boundaries, then hard-splits any sentence that
    still exceeds the budget. Uses a small tail overlap so context survives
    chunk boundaries.
    """
    max_tokens = max_tokens or settings.search.chunk_max_tokens
    overlap_tokens = min(overlap_tokens or settings.search.chunk_overlap_tokens, max_tokens // 2)
    text = text.strip()
    if not text:
        return []
    if estimate_tokens(text) <= max_tokens:
        return [text]

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
    chunks: List[str] = []
    current: List[str] = []
    current_tokens = 0

    def flush():
        nonlocal current, current_tokens
        if not current:
            return
        chunks.append(" ".join(current))
        tail: List[str] = []
        tail_tokens = 0
        for s in reversed(current):
            t = estimate_tokens(s)
            if tail_tokens + t > overlap_tokens:
                break
            tail.insert(0, s)
            tail_tokens += t
        current = tail
        current_tokens = tail_tokens

    def hard_split(sentence: str):
        nonlocal current
        flush()
        words = sentence.split()
        buf: List[str] = []
        buf_tokens = 0
        for word in words:
            wt = estimate_tokens(word) + 1
            if wt > max_tokens:
                if buf:
                    chunks.append(" ".join(buf))
                    buf = []
                    buf_tokens = 0
                chars_per_chunk = max(1, max_tokens * 4 - 1)
                for i in range(0, len(word), chars_per_chunk):
                    chunks.append(word[i : i + chars_per_chunk])
                continue
            if buf and buf_tokens + wt > max_tokens:
                chunks.append(" ".join(buf))
                buf = []
                buf_tokens = 0
            buf.append(word)
            buf_tokens += wt
        if buf:
            chunks.append(" ".join(buf))

    for sentence in sentences:
        t = estimate_tokens(sentence)
        if t > max_tokens:
            hard_split(sentence)
            continue
        if current_tokens + t > max_tokens:
            flush()
        current.append(sentence)
        current_tokens += t
    flush()

    return [c for c in chunks if c]


class GameMemory:
    """Long-term game memory backed by Upstash Search (one shared index).

    There is no namespace concept in Upstash Search, so games are separated by
    the ``sid`` field (kept in both content and metadata) plus an id prefix of
    ``{sid}:``. All calls run in a thread so the synchronous SDK never blocks
    the event loop.
    """

    def __init__(self, index: Any = None):
        self._index = index
        self._thread_lock = asyncio.Lock()

    def _connect(self) -> Any:
        if self._index is not None:
            return self._index
        if not settings.search.configured:
            raise RuntimeError(
                "UPSTASH_SEARCH_REST_URL / UPSTASH_SEARCH_REST_TOKEN not configured"
            )
        from upstash_search import Search

        search = Search(settings.search.upstash_search_url, settings.search.upstash_search_token)
        self._index = search.index(settings.search.index_name)
        logger.info(f"Connected to Upstash Search index '{settings.search.index_name}'")
        return self._index

    async def _run(self, fn) -> Any:
        index = self._connect()
        async with self._thread_lock:
            try:
                return await asyncio.to_thread(fn, index)
            except Exception as e:
                logger.error(f"Upstash Search call failed: {e}")
                raise

    async def upsert_chunks(
        self,
        namespace: str,
        texts: List[str],
        turn: int = 0,
        is_incident: bool = False,
    ) -> int:
        """Upsert a batch of story texts as search documents (server-side embedding)."""
        if not texts:
            return 0
        documents: List[Dict[str, Any]] = []
        for i, text in enumerate(texts):
            documents.append(
                {
                    "id": f"{namespace}:{turn}:{i}:{uuid4().hex[:8]}",
                    "content": {"sid": namespace, "text": text[:4000]},
                    "metadata": {
                        "sid": namespace,
                        "turn": turn,
                        "index": i,
                        "is_incident": bool(is_incident),
                        "ts": int(time.time()),
                    },
                }
            )
        return await self.upsert(namespace, documents)

    async def upsert(self, namespace: str, documents: List[Dict[str, Any]]) -> int:
        """Upsert documents: each must have ``content`` (dict or str); optional
        ``id`` and ``metadata``. Strings are wrapped into ``{"text": ...}`` and
        the ``sid`` is always stamped so per-game filtering works."""
        if not documents:
            return 0
        prepared: List[Dict[str, Any]] = []
        for doc in documents:
            content = doc.get("content")
            if isinstance(content, str):
                content = {"sid": namespace, "text": content[:4000]}
            elif isinstance(content, dict):
                content = dict(content)
                content.setdefault("sid", namespace)
            else:
                text = doc.get("text")
                if not isinstance(text, str):
                    continue
                content = {"sid": namespace, "text": text[:4000]}
            metadata = dict(doc.get("metadata") or {})
            metadata["sid"] = namespace
            prepared.append(
                {
                    "id": doc.get("id") or f"{namespace}:{uuid4().hex[:12]}",
                    "content": content,
                    "metadata": metadata,
                }
            )
        if not prepared:
            return 0

        def _do(index):
            index.upsert(prepared)

        await self._run(_do)
        return len(prepared)

    async def query(
        self, namespace: str, query_text: str, top_k: int | None = None
    ) -> List[Dict[str, Any]]:
        """Hybrid (semantic + full-text) search scoped to one game's sid."""
        query_text = query_text.strip()
        if not query_text:
            return []
        top_k = top_k or settings.search.top_k

        def _do(index):
            return index.search(
                query=query_text,
                limit=top_k,
                filter=f"@metadata.sid = '{namespace}'",
                reranking=settings.search.reranking,
                semantic_weight=settings.search.semantic_weight,
                input_enrichment=settings.search.input_enrichment,
            )

        results = await self._run(_do)
        return [
            {
                "id": r.id,
                "score": float(r.score),
                "content": r.content or {},
                "metadata": r.metadata or {},
            }
            for r in results
        ]

    async def export(self, namespace: str) -> List[Dict[str, Any]]:
        """Dump every document for the game (id prefix ``{sid}:``)."""
        def _do(index):
            return index.fetch(prefix=f"{namespace}:") or []

        docs = await self._run(_do)
        return [
            {
                "id": d.id,
                "content": d.content or {},
                "metadata": d.metadata or {},
            }
            for d in docs
            if d is not None
        ]

    async def restore(self, namespace: str, chunks: List[Dict[str, Any]]) -> int:
        """Upsert previously exported documents back (no re-embedding needed)."""
        if not chunks:
            return 0
        return await self.upsert(namespace, chunks)

    async def clear(self, namespace: str) -> bool:
        def _do(index):
            return index.delete(filter=f"@metadata.sid = '{namespace}'")

        try:
            await self._run(_do)
            return True
        except Exception as e:
            logger.error(f"Upstash Search delete failed for {namespace}: {e}")
            raise