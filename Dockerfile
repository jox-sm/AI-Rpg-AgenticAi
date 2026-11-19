# RPG AI server — gameplay API + LangGraph engine as ONE process.
#   docker build -t rpg-ai-server .
#   docker run --env-file rpg_ai_server/.env -p 8000:8000 rpg-ai-server
# (or use docker-compose.yml in this folder, which wires up the web app too)
#
# Secrets are NOT baked into the image: pass UPSTASH_* / OPENROUTER_API_KEY at
# runtime (env_file / -e / compose). The app also reads rpg_ai_server/.env via
# python-dotenv if you mount it — compose-provided env vars always win.
#
# For the memory/saves endpoints also set:
#   UPSTASH_SEARCH_REST_URL / UPSTASH_SEARCH_REST_TOKEN
# (without them those endpoints answer 503 and gameplay still works — see
# REDIS_API.md → "Memory configuration note").

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

# nltk corpus used by utils/items_db.py (stopwords) — bake it in so the
# container doesn't download it on first run.
RUN python -c "import nltk; nltk.download('stopwords', quiet=True)"

# The engine reads the bundled game-item database at <repo>/items-db
# (utils/items_db.py: parents[2] of rpg_ai_server/utils/items_db.py = /app).
COPY rpg_ai_server ./rpg_ai_server
COPY items-db ./items-db

EXPOSE 8000

# Combined service: gameplay API + in-process engine (exactly ONE engine).
CMD ["uvicorn", "rpg_ai_server.api:app", "--host", "0.0.0.0", "--port", "8000"]
