"""In-memory fakes for Upstash Redis / Search clients."""

import json
import re
import time
import zlib
from types import SimpleNamespace


def _content_tokens(content):
    text = str(content.get("text", ""))
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _score(query, content):
    query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    if not query_tokens:
        return 0.0
    overlap = query_tokens & _content_tokens(content)
    return len(overlap) / len(query_tokens)


def _sid_from_filter(filter_str):
    if not filter_str:
        return None
    m = re.search(r"@metadata\.sid\s*=\s*'([^']*)'", filter_str)
    return m.group(1) if m else None


class FakeSearchDoc:
    def __init__(self, id_, content, metadata=None):
        self.id = id_
        self.content = content or {}
        self.metadata = metadata or {}


class FakeSearchIndex:
    """Mirrors the subset of the upstash-search Index used by GameMemory.

    Relevance is a simple deterministic keyword-overlap score; filtering only
    supports the ``@metadata.sid = '<sid>'`` form GameMemory emits.
    """

    def __init__(self):
        self.data = {}
        self.deleted = []
        self.upsert_calls = 0

    def upsert(self, documents):
        self.upsert_calls += 1
        for d in documents:
            doc = d if hasattr(d, "id") else FakeSearchDoc(d["id"], d.get("content", {}), d.get("metadata") or {})
            self.data[doc.id] = doc

    def _matches(self, doc, filter_str=""):
        sid = _sid_from_filter(filter_str)
        if sid is not None and doc.metadata.get("sid") != sid:
            return False
        return True

    def search(self, query, *, limit=10, filter="", reranking=False, semantic_weight=0.75, input_enrichment=True):
        docs = [d for d in self.data.values() if self._matches(d, filter)]
        ids = list(self.data)
        scored = sorted(
            ((_score(query, d.content), d) for d in docs),
            key=lambda pair: (-pair[0], ids.index(pair[1].id)),
        )
        return [
            SimpleNamespace(id=d.id, score=s, content=dict(d.content), metadata=dict(d.metadata))
            for s, d in scored[:limit]
        ]

    def fetch(self, *, ids=None, prefix=None):
        if ids is not None:
            out = []
            for i in ids:
                d = self.data.get(i)
                out.append(
                    SimpleNamespace(id=i, content=dict(d.content), metadata=dict(d.metadata)) if d else None
                )
            return out
        prefix = prefix or ""
        docs = [d for d in self.data.values() if d.id.startswith(prefix)]
        return [SimpleNamespace(id=d.id, content=dict(d.content), metadata=dict(d.metadata)) for d in docs]

    def delete(self, *, ids=None, prefix=None, filter=None):
        if ids is not None:
            n = sum(1 for i in ids if i in self.data)
            for i in ids:
                self.data.pop(i, None)
            self.deleted.extend(ids)
            return n
        if filter is not None:
            sid = _sid_from_filter(filter)
            to_delete = [i for i, d in self.data.items() if d.metadata.get("sid") == sid]
            for i in to_delete:
                del self.data[i]
            self.deleted.extend(to_delete)
            return len(to_delete)
        if prefix:
            to_delete = [i for i in self.data if i.startswith(prefix)]
            for i in to_delete:
                del self.data[i]
            self.deleted.extend(to_delete)
            return len(to_delete)
        return 0


class FakeGamesClient:
    """In-memory GamesRedisClient substitute (hash/counter/lock semantics)."""

    def __init__(self):
        self.hashes = {}
        self.counters = {}
        self.locks = {}
        self.expires = []
        self.incr_calls = 0

    async def hset(self, uuid, field, value):
        self.hashes.setdefault(uuid, {})[field] = value
        return True

    async def hget(self, uuid, field):
        return self.hashes.get(uuid, {}).get(field)

    async def hgetall(self, uuid):
        h = self.hashes.get(uuid)
        return dict(h) if h else None

    async def hdel(self, uuid, field):
        if uuid in self.hashes and field in self.hashes[uuid]:
            del self.hashes[uuid][field]
            return True
        return False

    async def incr(self, uuid):
        self.incr_calls += 1
        self.counters[uuid] = self.counters.get(uuid, 0) + 1
        return self.counters[uuid]

    async def set_counter(self, uuid, value):
        self.counters[uuid] = value
        return True

    async def expire(self, uuid, ttl):
        self.expires.append((uuid, ttl))
        return True

    async def acquire_lock(self, uuid, worker_id, ttl=30):
        if uuid in self.locks:
            return False
        self.locks[uuid] = worker_id
        return True

    async def release_lock(self, uuid, worker_id):
        if self.locks.get(uuid) == worker_id:
            del self.locks[uuid]
            return True
        return False

    async def refresh_lock(self, uuid, worker_id, ttl=30):
        if self.locks.get(uuid) == worker_id:
            self.locks[uuid] = worker_id
            return True
        return False


class FakeInputClient:
    """In-memory InputRedisClient substitute (queue/delayed/dead semantics)."""

    def __init__(self):
        self.queue = []
        self.delayed = {}
        self.dead = {}
        self.heartbeats = []

    async def pop_request(self):
        if not self.queue:
            return None
        return json.loads(self.queue.pop(0))

    async def push_request(self, uuid, data):
        self.queue.append(json.dumps(data))
        return True

    async def queue_length(self):
        return len(self.queue)

    async def push_delayed(self, item, score):
        self.delayed[json.dumps(item, sort_keys=True)] = score
        return True

    async def pop_delayed_due(self, max_score):
        due = [k for k, s in self.delayed.items() if s <= max_score]
        items = []
        for k in due:
            del self.delayed[k]
            items.append(json.loads(k))
        return items

    async def push_dead(self, item):
        self.dead[json.dumps(item, sort_keys=True)] = time.time()

    async def set_heartbeat(self, worker_id, game_uuid, ttl=15):
        self.heartbeats.append((worker_id, game_uuid))
        return True


class FakeOutputClient:
    def __init__(self):
        self.data = {}

    async def get_json(self, key):
        return self.data.get(key)

    async def push_result(self, uuid, data):
        self.data[uuid] = data
        return True

    async def count(self):
        return len(self.data)

    async def dbsize(self):
        return len(self.data)
