"""Compatibility facade — orchestration helpers moved into engine/orchestration/.

The GameOrchestrator class (and its method names, which tests monkeypatch on
instances) stays here; heavy pure helpers live in small focused modules.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from langgraph.graph import StateGraph

from ..config.settings import settings
from ..redis.game_state import GameStateManager
from ..redis.output_cache import OutputCache
from ..schemas.state import GameState
from ..schemas.types import GameRequest
from ..utils.coerce import model_list
from ..utils.logger import logger
from .graph_v2 import build_game_graph_v2
from .orchestration.constants import GRACEFUL_ERROR_STORY
from .orchestration.graph_run import run_graph
from .orchestration.state import build_initial_state, hydrate_models

__all__ = ["GameOrchestrator", "GRACEFUL_ERROR_STORY"]


class GameOrchestrator:
    def __init__(self, output_cache: OutputCache, game_state_mgr: GameStateManager, worker_id: str = ""):
        import uuid as _uuid
        self.output_cache = output_cache
        self.game_state_mgr = game_state_mgr
        # Stable process-lifetime worker id (was f"orch-{id(self)}", collided across restarts)
        self.worker_id = worker_id or settings.app.worker_id or f"worker-{_uuid.uuid4().hex[:8]}"
        self.graph: Optional[StateGraph] = None
        self.compiled_graph = None

    async def initialize(self):
        logger.info("Initializing game orchestrator...")
        workflow = build_game_graph_v2(self.output_cache)
        self.graph = workflow
        self.compiled_graph = workflow.compile()
        logger.info("Game orchestrator initialized")

    @staticmethod
    def _hydrate_models(initial_state: GameState) -> None:
        hydrate_models(initial_state)

    def _build_initial_state(self, request: GameRequest) -> GameState:
        return build_initial_state(request)

    async def process_request(self, request: GameRequest) -> Optional[Dict[str, Any]]:
        logger.info(f"Processing request UUID {request.uuid}")

        if self.compiled_graph is None:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")

        locked = await self.game_state_mgr.acquire_lock(request.uuid, self.worker_id)
        if not locked:
            logger.warning(f"Could not acquire lock for {request.uuid}, another worker is processing")
            return None

        try:
            existing = await self.game_state_mgr.load_state(request.uuid)
            if existing:
                logger.info(f"Loaded existing game state for {request.uuid}")
                initial_state = self._build_initial_state(request)
                # Allowlist merge (was full overwrite incl. stale budgets/flags).
                # Only long-lived fields come from persisted state; fresh request
                # fields (prompt/images/budget/turn/flags) always win.
                for k in ("character_stats", "skills", "inventory", "relationships",
                          "game_data", "context", "chat_log", "context_summary", "decision"):
                    if k in existing:
                        initial_state[k] = existing[k]
                self._hydrate_models(initial_state)
                # Append this turn's prompt to rolling chat log (cap generous local 40)
                try:
                    log = list(initial_state.get("chat_log", []) or [])
                    log.append({"role": "user", "text": request.prompt, "turn": len(log)})
                    initial_state["chat_log"] = log[-settings.app.chat_log_max_turns:]
                except Exception:
                    pass
            else:
                initial_state = self._build_initial_state(request)
                await self.game_state_mgr.save_initial_state(
                    request.uuid,
                    initial_state.get("game_data", {}),
                    initial_state.get("story_output", ""),
                    chat_log=initial_state.get("chat_log"),
                    context=initial_state.get("context", ""),
                )
                logger.info(f"Saved initial game state for {request.uuid}")

            result = await self._run_graph(initial_state, request.uuid)

            output = result.get("game_output")
            if output:
                story = output.get("story", "") or result.get("story_output", "")
                await self.game_state_mgr.save_state(
                    request.uuid,
                    {"game_data": output.get("game_data", {}),
                     "story": story,
                     "character_stats": output.get("game_data", {}).get("character_stats", {}),
                     # Top-level live fields (node4/node6 read these, not the
                     # game_data-embedded copies node7 writes). Without these,
                     # resumed games silently reset inventory/skills to [].
                     "inventory": model_list(result.get("inventory")),
                     "skills": model_list(result.get("skills")),
                     "relationships": model_list(result.get("relationships")),
                     "context_summary": result.get("context_summary"),
                     "decision": result.get("decision"),
                     "chat_log": initial_state.get("chat_log"),
                     "context": result.get("context", "")},
                    ["game_data", "story", "character_stats", "inventory", "skills",
                     "relationships", "context_summary", "decision",
                     "chat_log", "context"],
                )
                await self.game_state_mgr.try_drain(request.uuid, story)
                logger.info(f"Request {request.uuid} completed successfully")
            else:
                logger.warning(f"Request {request.uuid} completed but no output generated")

            return output

        except Exception as e:
            logger.error(
                f"Failed to process request {request.uuid}: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return {
                "uuid": request.uuid,
                "error": type(e).__name__,
                "game_data": request.data,
                "story": GRACEFUL_ERROR_STORY,
            }
        finally:
            await self.game_state_mgr.release_lock(request.uuid, self.worker_id)

    async def _run_graph(self, state: GameState, uuid: str) -> Dict[str, Any]:
        return await run_graph(
            self.compiled_graph, self.game_state_mgr, state, uuid, self.worker_id
        )
