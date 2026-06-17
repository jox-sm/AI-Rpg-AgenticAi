from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from nltk.corpus import stopwords
    _STOPWORDS = set(stopwords.words("english"))
except LookupError:
    import nltk
    nltk.download("stopwords", quiet=True)
    from nltk.corpus import stopwords
    _STOPWORDS = set(stopwords.words("english"))

_WORD_RE = re.compile(r"[a-zA-Z]{2,}")


def _char_bigrams(text: str, pad: int = 2) -> Counter:
    t = f"{' ' * pad}{text.lower().strip()}{' ' * pad}"
    return Counter(t[i:i+2] for i in range(len(t)-1))


def _cosine_sim(a: Counter, b: Counter) -> float:
    inter = set(a) & set(b)
    num = sum(a[k] * b[k] for k in inter)
    den = math.sqrt(sum(v*v for v in a.values())) * math.sqrt(sum(v*v for v in b.values()))
    return num / den if den else 0.0


def _damerau_levenshtein(s1: str, s2: str) -> int:
    """Damerau-Levenshtein distance with transpositions."""
    if s1 == s2:
        return 0
    len1, len2 = len(s1), len(s2)
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    d = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(len1 + 1):
        d[i][0] = i
    for j in range(len2 + 1):
        d[0][j] = j

    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i-1] == s2[j-1] else 1
            d[i][j] = min(
                d[i-1][j] + 1,        # deletion
                d[i][j-1] + 1,        # insertion
                d[i-1][j-1] + cost,   # substitution
            )
            if i > 1 and j > 1 and s1[i-1] == s2[j-2] and s1[i-2] == s2[j-1]:
                d[i][j] = min(d[i][j], d[i-2][j-2] + cost)  # transposition

    return d[len1][len2]


class ItemsDB:
    """In-memory RPG items database with semantic-ish search.

    Search: exact match → substring → bigram cosine sim → edit distance re-rank.
    Zero external dependencies, zero API calls.
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = str(Path(__file__).resolve().parent.parent.parent / "items-db")
        self.data_dir = Path(data_dir)
        self._items: Dict[str, list[Dict[str, Any]]] = {}
        self._flat: list[Dict[str, Any]] = []
        self._name_index: Dict[str, list[Dict[str, Any]]] = {}
        self._type_index: Dict[str, list[Dict[str, Any]]] = {}
        self._rarity_index: Dict[str, list[Dict[str, Any]]] = {}
        self._bigram_index: list[tuple[Counter, int]] = []
        self._name_bigram_index: list[tuple[Counter, int]] = []
        self._max_name_words: int = 1
        self._query_cache: Dict[str, list[Dict[str, Any]]] = {}
        self.load()

    def load(self) -> None:
        for path in sorted(self.data_dir.glob("*.json")):
            stem = path.stem
            try:
                with open(path, encoding="utf-8") as f:
                    items = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[ItemsDB] Skipping {path.name}: {e}")
                continue
            self._items[stem] = items
            for item in items:
                item["_file"] = stem
                self._flat.append(item)
                name = item.get("name", "").lower().strip()
                if name:
                    self._name_index.setdefault(name, []).append(item)

                for field, index in [("Type", self._type_index), ("Rarity", self._rarity_index)]:
                    val = item.get(field)
                    if val:
                        index.setdefault(str(val).lower(), []).append(item)

                search_text = f"{item.get('name', '')} {item.get('Description', '')} {item.get('Effect', '')} {item.get('Special Effect', '')}"
                bg = _char_bigrams(search_text)
                self._bigram_index.append((bg, len(self._flat) - 1))

                name_bg = _char_bigrams(item.get("name", ""), pad=1)
                self._name_bigram_index.append((name_bg, len(self._flat) - 1))

                name_word_count = len(item.get("name", "").split())
                if name_word_count > self._max_name_words:
                    self._max_name_words = name_word_count

    def search(self, query: str, limit: int = 10) -> list[Dict[str, Any]]:
        q = query.lower().strip()
        if not q:
            return []

        # cache hit
        if q in self._query_cache:
            return self._query_cache[q][:limit]

        # 1. exact match
        if q in self._name_index:
            return self._name_index[q][:limit]

        # 2. substring match
        substr = [item for item in self._flat if q in item.get("name", "").lower()]
        substr.sort(key=lambda x: x.get("name", "").lower().index(q))
        if substr:
            return substr[:limit]

        # 3. bigram cosine + edit distance re-rank
        q_bg = _char_bigrams(q)
        scored: list[tuple[float, int]] = []
        for bg, idx in self._bigram_index:
            sim = _cosine_sim(q_bg, bg)
            if sim > 0.05:
                scored.append((sim, idx))

        scored.sort(key=lambda x: -x[0])

        # re-rank top 50 by edit distance
        results: list[tuple[float, Dict[str, Any]]] = []
        for sim, idx in scored[:50]:
            item = self._flat[idx]
            item_name = item.get("name", "")
            words = item_name.lower().split()
            q_words = q.split()
            # best per-word edit distance
            edit_score = 0.0
            for qw in q_words:
                best = min(_damerau_levenshtein(qw, w) for w in words) if words else len(qw)
                edit_score += best
            avg_edit = edit_score / max(len(q_words), 1)
            # combined: higher bigram + lower edit distance = better
            combined = sim * 0.6 + (1.0 / (1.0 + avg_edit)) * 0.4
            results.append((combined, item))

        results.sort(key=lambda x: -x[0])

        final = [item for _, item in results[:limit]]
        self._query_cache[q] = final
        return final

    def extract_items(
        self,
        text: str,
        scope: Optional[list[str | Dict[str, Any]]] = None,
        threshold: float = 0.65,
    ) -> list[Dict[str, Any]]:
        if not text or not text.strip():
            return []

        raw = text.lower().strip()
        tokens = [w for w in _WORD_RE.findall(raw) if w not in _STOPWORDS]
        if not tokens:
            return []

        candidates: list[str] = []
        for n in range(1, min(self._max_name_words, len(tokens)) + 1):
            for i in range(len(tokens) - n + 1):
                candidates.append(" ".join(tokens[i:i+n]))

        if scope:
            name_bg_index: list[tuple[Counter, Dict[str, Any]]] = []
            for entry in scope:
                name = entry if isinstance(entry, str) else entry.get("name", "")
                if name:
                    item = entry if isinstance(entry, dict) else (self._name_index.get(name.lower(), [None])[0] or {"name": name})
                    name_bg_index.append((_char_bigrams(name, pad=1), item))
        else:
            name_bg_index = [(bg, self._flat[idx]) for bg, idx in self._name_bigram_index]

        matched: dict[str, tuple[float, Dict[str, Any]]] = {}
        for phrase in candidates:
            phrase_bg = _char_bigrams(phrase, pad=1)
            best_score = 0.0
            best_item = None
            for name_bg, item in name_bg_index:
                score = _cosine_sim(phrase_bg, name_bg)
                if score > best_score:
                    best_score = score
                    best_item = item

            if best_score >= threshold and best_item:
                item_name = best_item.get("name", "")
                phrase_chars = len(phrase.replace(" ", ""))
                item_chars = len(item_name.replace(" ", ""))
                if phrase_chars < item_chars * 0.4:
                    continue
                if item_name not in matched or best_score > matched[item_name][0]:
                    matched[item_name] = (best_score, best_item)

        return [item for _, item in sorted(matched.values(), key=lambda x: -x[0])]

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        results = self.search(name, limit=1)
        return results[0] if results else None

    def get_by_id(self, file_stem: str, item_id: int) -> Optional[Dict[str, Any]]:
        for item in self._items.get(file_stem, []):
            if item.get("id") == item_id:
                return item
        return None

    def filter(self, limit: int = 50, **kwargs) -> list[Dict[str, Any]]:
        results = self._flat
        for key, val in kwargs.items():
            results = [it for it in results if str(it.get(key, "")).lower() == str(val).lower()]
        return results[:limit]

    def by_type(self, type_name: str, limit: int = 50) -> list[Dict[str, Any]]:
        return self._type_index.get(type_name.lower(), [])[:limit]

    def by_rarity(self, rarity: str, limit: int = 50) -> list[Dict[str, Any]]:
        return self._rarity_index.get(rarity.lower(), [])[:limit]

    def random(self, count: int = 1) -> list[Dict[str, Any]]:
        import random
        return random.sample(self._flat, min(count, len(self._flat)))

    @property
    def categories(self) -> list[str]:
        return list(self._items.keys())

    def __len__(self) -> int:
        return len(self._flat)

    def __repr__(self) -> str:
        return f"<ItemsDB: {len(self._flat)} items across {len(self._items)} files>"
