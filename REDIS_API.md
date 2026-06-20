# RPG AI Server — Redis API Usage Guide

Single FastAPI server (`rpg_ai_server/redis_api.py`) exposing Redis operations over HTTP.
No agent/skill/engine imports — just Redis CRUD.

---

## Run

```bash
python -m uvicorn rpg_ai_server.redis_api:app --port 8000
```

---

## 1. Health

```bash
curl http://127.0.0.1:8000/health
# → {"status":"ok"}
```

---

## 2. Queue (input:) — game request queue

### Push a request

```bash
curl -X POST "http://127.0.0.1:8000/queue/push?uuid=abc123&data=%7B%22prompt%22%3A%22hello%22%7D"
# data = URL-encoded JSON: {"prompt":"hello"}
# → {"ok":true,"uuid":"abc123"}
```

**Real example** (no encoding needed with curl `--data-urlencode`):

```bash
curl -X POST "http://127.0.0.1:8000/queue/push" \
  -G \
  --data-urlencode "uuid=game-001" \
  --data-urlencode "data={\"prompt\":\"attack goblin\",\"player_level\":5}"
# → {"ok":true,"uuid":"game-001"}
```

### Pop a request

```bash
curl "http://127.0.0.1:8000/queue/pop"
# → {"ok":true,"item":{...}}
# → {"ok":false,"item":null}  (queue empty)
```

### Queue length

```bash
curl "http://127.0.0.1:8000/queue/length"
# → {"length":3}
```

### Delayed queue (retry with backoff)

```bash
# push with score = timestamp when it should retry
curl -X POST "http://127.0.0.1:8000/queue/delayed/push" \
  -H "Content-Type: application/json" \
  -d "{\"uuid\":\"game-001\",\"retry_count\":1}" \
  -G --data-urlencode "score=1718000000"
# → {"ok":true}

# pop items whose score <= now (due for retry)
curl "http://127.0.0.1:8000/queue/delayed/pop?max_score=1718000000"
# → {"count":1,"items":[{...}]}
```

### Dead letter queue

```bash
curl -X POST "http://127.0.0.1:8000/queue/dead/push" \
  -H "Content-Type: application/json" \
  -d "{\"uuid\":\"game-001\",\"error\":\"max retries exceeded\"}"
# → {"ok":true}
```

---

## 3. Game State (games:) — per-player persistent state

### Get entire game state

```bash
curl "http://127.0.0.1:8000/games/abc123/state"
# → {"character_stats":{...},"inventory":[...],"skills":[...],"grid":[...],"story":"..."}
```

### Get single field

```bash
curl "http://127.0.0.1:8000/games/abc123/state/character_stats"
# → {"level":3,"health":80,"max_health":100,"mana":50,...}
```

### Set a field

```bash
curl -X PUT "http://127.0.0.1:8000/games/abc123/state/story" \
  -G --data-urlencode "value=You slay the goblin and find 5 gold."
# → {"ok":true}
```

### Delete a field

```bash
curl -X DELETE "http://127.0.0.1:8000/games/abc123/state/temp_field"
# → {"ok":true}
```

### Counter (action count for drain trigger)

```bash
# increment
curl -X POST "http://127.0.0.1:8000/games/abc123/counter/incr"
# → {"counter":7}

# set to specific value
curl -X PUT "http://127.0.0.1:8000/games/abc123/counter?value=0"
# → {"ok":true}
```

### Distributed lock

```bash
# acquire (TTL default 30s)
curl "http://127.0.0.1:8000/games/abc123/lock?worker_id=worker1&ttl=30"
# → {"acquired":true}
# → {"acquired":false}  (already locked)

# release
curl -X DELETE "http://127.0.0.1:8000/games/abc123/lock?worker_id=worker1"
# → {"released":true}
```

### Set TTL / expire

```bash
curl -X POST "http://127.0.0.1:8000/games/abc123/expire?ttl=3600"
# → {"ok":true}
```

---

## 4. RAG Staging (rag:) — memory pipeline

### Push story chunk to RAG queue

```bash
curl -X POST "http://127.0.0.1:8000/rag/staging/push" \
  -H "Content-Type: application/json" \
  -d "{\"uuid\":\"abc123\",\"text\":\"compressed+gzipped+base64...\",\"chunk_count\":1}"
# → {"ok":true}
```

### Pop from RAG queue (for Chroma worker)

```bash
curl "http://127.0.0.1:8000/rag/staging/pop"
# → {"ok":true,"item":{...}}
# → {"ok":false,"item":null}
```

### RAG queue count

```bash
curl "http://127.0.0.1:8000/rag/staging/count"
# → {"count":5}
```

### Get stored chunk

```bash
curl "http://127.0.0.1:8000/rag/chunk/abc123/0"
# → {"text":"...","metadata":{...}}
```

---

## 5. Output Cache (output:) — LLM result storage

### Get output

```bash
curl "http://127.0.0.1:8000/output/abc123"
# → {"story":"...","game_data":{...},"character_stats":{...}}
```

### Set output

```bash
curl -X PUT "http://127.0.0.1:8000/output/abc123" \
  -H "Content-Type: application/json" \
  -d "{\"story\":\"You enter the dungeon...\",\"game_data\":{}}"
# → {"ok":true}
```

### Output count

```bash
curl "http://127.0.0.1:8000/output/count"
# → {"count":12}
```

---

## 6. General / Admin

### List keys by prefix

```bash
curl "http://127.0.0.1:8000/keys?pattern=*&prefix=input"
# → ["queue","queue:delayed","queue:dead"]

curl "http://127.0.0.1:8000/keys?pattern=abc*&prefix=games"
# → ["abc123:state","abc123:counter","abc123:lock"]
```

### DB size (key count)

```bash
curl "http://127.0.0.1:8000/dbsize?prefix=output"
# → {"dbsize":12}

# sum across all prefixes
curl "http://127.0.0.1:8000/dbsize"
# → {"dbsize":47}
```

### Delete a key

```bash
curl -X DELETE "http://127.0.0.1:8000/keys/abc123:state?prefix=games"
# → {"ok":true}
```

---

## Typical Web Server Flow

```
1. Player performs action

2. GET /games/{uuid}/state            ← load current game state
   GET /games/abc123/state

3. POST /queue/push                   ← push action to AI queue
   ?uuid=abc123
   &data={"prompt":"I attack the goblin with my sword","player_level":3}

4. Wait... AI processes... poll or webhook

5. GET /output/{uuid}                 ← read AI response
   GET /output/abc123

6. PUT /games/{uuid}/state/{field}    ← update game state
   PUT /games/abc123/state/character_stats?value={"health":85,...}

7. POST /games/{uuid}/counter/incr    ← increment action counter
```

---

## Redis Data Layout (for reference)

```
input:queue                → List    (RPUSH/LPOP FIFO)
input:queue:delayed        → Sorted Set (ZADD + ZRANGEBYSCORE)
input:queue:dead           → Sorted Set (failed after 3 retries)
input:workers:{id}:heartbeat → String (TTL)

games:{uuid}:state         → Hash (HGETALL, HSET, HDEL)
games:{uuid}:counter       → String (INCR, GETSET)
games:{uuid}:lock          → String (SET NX EX, GET + DEL)

rag:queue                  → List (RPUSH/LPOP)
rag:{uuid}:{index}         → String (GET)

output:{uuid}              → String (GET/SET with EX)
```

---

## Error Responses

```json
// 404 — key/chunk/field not found
{"detail":"Game not found"}
{"detail":"Field 'story' not found"}
{"detail":"Chunk not found"}

// 400 — missing required param
{"detail":"prefix required (input/games/rag/output)"}

// 500 — Redis connection error or serialization error
```
