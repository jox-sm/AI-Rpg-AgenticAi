from __future__ import annotations

import time
from typing import Any, Dict, Optional

from langgraph.graph import StateGraph

from ..agents.node4_tool_agent.tools import json_data_maker_and_tracker
from ..redis.game_state import GameStateManager
from ..redis.output_cache import OutputCache
from ..schemas.state import GameState
from ..schemas.types import CharacterStats, GameRequest, Skill
from ..scripts.world_generator import generate_world, world_to_grid_data, world_to_meta
from ..utils.logger import logger
from .graph_builder import build_game_graph


class GameOrchestrator:
    def __init__(self, output_cache: OutputCache, game_state_mgr: GameStateManager, worker_id: str = ""):
        self.output_cache = output_cache
        self.game_state_mgr = game_state_mgr
        self.worker_id = worker_id or f"orch-{id(self)}"
        self.graph: Optional[StateGraph] = None
        self.compiled_graph = None

    async def initialize(self):
        logger.info("Initializing game orchestrator...")
        workflow = build_game_graph(self.output_cache)
        self.graph = workflow
        self.compiled_graph = workflow.compile()
        logger.info("Game orchestrator initialized")

    def _build_initial_state(self, request: GameRequest) -> GameState:
        stats = CharacterStats()

        world = generate_world(seed=request.uuid)
        grid_data = world_to_grid_data(world)
        world_meta = world_to_meta(world)

        initial_state: GameState = {
            "uuid": request.uuid,
            "prompt": request.prompt,
            "input_data": request.data or {},
            "game_data": request.data or {"world": world_meta, "grid": world["grid"]},
            "images": {},
            "grid_data": grid_data,
            "re_description_data": None,
            "context_summary": None,
            "character_stats": stats,
            "skills": [
                Skill(
                    name="Basic Attack",
                    skill_type="attack",
                    cooldown=0,
                    max_cooldown=1,
                    level=1,
                    description="A basic melee or ranged attack",
                ),
                Skill(
                    name="Dodge",
                    skill_type="defense",
                    cooldown=0,
                    max_cooldown=2,
                    level=1,
                    description="Dodge incoming attack",
                    is_passive=False,
                ),
            ],
            "inventory": [],
            "relationships": [],
            "story_output": "",
            "decision": None,
            "needs_search": False,
            "needs_image_processing": False,
            "needs_re_description": False,
            "processed": False,
            "error": None,
            "search_results": "",
            "tool_results": [],
            "game_output": None,
            "__next__": "node4_tool_agent",
        }

        if request.images:
            from uuid import uuid4
            from ..schemas.types import ImageData
            import time
            for img in request.images:
                img_uuid = str(uuid4())
                initial_state["images"][img_uuid] = ImageData(
                    image_uuid=img_uuid,
                    game_uuid=request.uuid,
                    url=img.get("url", ""),
                    format=img.get("format", "webp"),
                    timestamp=time.time(),
                )
            initial_state["needs_image_processing"] = True

        return initial_state

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
                for k, v in existing.items():
                    if k in initial_state:
                        initial_state[k] = v
            else:
                initial_state = self._build_initial_state(request)
                await self.game_state_mgr.save_initial_state(
                    request.uuid,
                    request.data or {},
                    initial_state.get("story_output", ""),
                )
                logger.info(f"Saved initial game state for {request.uuid}")

            result = await self.compiled_graph.ainvoke(initial_state)

            output = result.get("game_output")
            if output:
                story = output.get("story", "") or result.get("story_output", "")
                await self.game_state_mgr.save_state(
                    request.uuid,
                    {"game_data": output.get("game_data", {}),
                     "story": story,
                     "character_stats": output.get("game_data", {}).get("character_stats", {})},
                    ["game_data", "story", "character_stats"],
                )
                await self.game_state_mgr.try_drain(request.uuid, story)
                logger.info(f"Request {request.uuid} completed successfully")
            else:
                logger.warning(f"Request {request.uuid} completed but no output generated")

            return output

        except Exception as e:
            logger.error(f"Failed to process request {request.uuid}: {e}")
            return {
                "uuid": request.uuid,
                "error": str(e),
                "game_data": request.data,
                "story": f"The adventure encountered an error: {e}",
            }
        finally:
            await self.game_state_mgr.release_lock(request.uuid, self.worker_id)
