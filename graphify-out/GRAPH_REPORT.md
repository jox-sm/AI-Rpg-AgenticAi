# Graph Report - rpg_ai_server  (2026-10-05)

## Corpus Check
- 43 files · ~27,357 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 696 nodes · 1952 edges · 71 communities (44 shown, 27 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 247 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Flee Pack Combat|Flee Pack Combat]]
- [[_COMMUNITY_Redis Clients|Redis Clients]]
- [[_COMMUNITY_Context Injector|Context Injector]]
- [[_COMMUNITY_World Generation|World Generation]]
- [[_COMMUNITY_Combat Formulas|Combat Formulas]]
- [[_COMMUNITY_Game State Manager|Game State Manager]]
- [[_COMMUNITY_Combat System|Combat System]]
- [[_COMMUNITY_Classifier Routing|Classifier Routing]]
- [[_COMMUNITY_Worldgen Web Search|Worldgen Web Search]]
- [[_COMMUNITY_Items DB Loader|Items DB Loader]]
- [[_COMMUNITY_Classifier Node|Classifier Node]]
- [[_COMMUNITY_Input Queue|Input Queue]]
- [[_COMMUNITY_Config Entry Points|Config Entry Points]]
- [[_COMMUNITY_Memory API|Memory API]]
- [[_COMMUNITY_Multi-Task Engine|Multi-Task Engine]]
- [[_COMMUNITY_Distributed Locks|Distributed Locks]]
- [[_COMMUNITY_Story Graph Build|Story Graph Build]]
- [[_COMMUNITY_Image Redescriptor|Image Redescriptor]]
- [[_COMMUNITY_Queue Operations|Queue Operations]]
- [[_COMMUNITY_Web Search Node|Web Search Node]]
- [[_COMMUNITY_State Persistence|State Persistence]]
- [[_COMMUNITY_Delayed Dead-Letter Queue|Delayed Dead-Letter Queue]]
- [[_COMMUNITY_Orchestrator Core|Orchestrator Core]]
- [[_COMMUNITY_Output Cache|Output Cache]]
- [[_COMMUNITY_Legacy TLS Patch|Legacy TLS Patch]]
- [[_COMMUNITY_Trigger Guard|Trigger Guard]]
- [[_COMMUNITY_Redis Config|Redis Config]]
- [[_COMMUNITY_Game Output|Game Output]]
- [[_COMMUNITY_LLM Client Setup|LLM Client Setup]]
- [[_COMMUNITY_Logging|Logging]]
- [[_COMMUNITY_Worker Heartbeat|Worker Heartbeat]]
- [[_COMMUNITY_Rolling Memory|Rolling Memory]]
- [[_COMMUNITY_Decision Routing|Decision Routing]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]

## God Nodes (most connected - your core abstractions)
1. `GamesRedisClient` - 34 edges
2. `InputRedisClient` - 33 edges
3. `str` - 30 edges
4. `GameMemory` - 30 edges
5. `to_int()` - 26 edges
6. `GameState` - 25 edges
7. `OutputRedisClient` - 23 edges
8. `resolve_flee()` - 22 edges
9. `str` - 21 edges
10. `Terrain` - 21 edges

## Surprising Connections (you probably didn't know these)
- `MemoryQueryRequest` --uses--> `InputRedisClient`  [INFERRED]
  redis_api.py → redis/client.py
- `MemoryRestoreRequest` --uses--> `InputRedisClient`  [INFERRED]
  redis_api.py → redis/client.py
- `MemoryUpsertRequest` --uses--> `InputRedisClient`  [INFERRED]
  redis_api.py → redis/client.py
- `int` --uses--> `InputRedisClient`  [INFERRED]
  redis_api.py → redis/client.py
- `str` --uses--> `InputRedisClient`  [INFERRED]
  redis_api.py → redis/client.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **full_turn_pipeline** — node0_worldgen_node0_worldgen, node1_web_search_node1_web_search, node2_image_processor_node2_image_processor, node3_redescriptor_node3_redescriptor, node4_parallel_node4_parallel, node5_context_injector_node5_context_injector, node6_story_generator_node6_story_generator, node7_output_pusher_node7_output_pusher [INFERRED]
- **mechanics_fanout** — node4_parallel_snapshot, node4_parallel_dice_patch, node4_parallel_damage_patch, node4_parallel_stats_patch, node4_parallel_skill_patch, node4_parallel_inventory_patch, node4_parallel_json_patch, node4_parallel_node4_parallel [INFERRED]
- **grid_perception_flow** — node0_worldgen_node0_worldgen, node2_image_processor_node2_image_processor, node3_redescriptor_node3_redescriptor, node5_context_injector_node5_context_injector, node6_story_generator_node6_story_generator [INFERRED]
- **react_routing_loop** — graph_v2_react_router_node, graph_v2_route_react, graph_v2_budget_exhausted, graph_v2_build_game_graph_v2, graph_v2_context_refresh_node [INFERRED]
- **engine_entry_to_graph** — main_main, multi_tasker_run, multi_tasker_process_single_request, orchestrator_process_request, orchestrator_run_graph, orchestrator_initialize, graph_v2_build_game_graph_v2 [INFERRED]
- **classifier_flee_branch** — classifier_classifier_node, classifier_deterministic_pass, classifier_extract_flee_method, flee_resolve_flee, flee_adjudicate_trick, flee_flee_chance, flee_monster_strike [INFERRED]
- **Game persist/load roundtrip (hash + counter TTL)** — game_state_save_state, game_state_load_state, game_state_save_initial_state, client_hset, client_hgetall, client_touch_game_keys, client_set_counter, client_expire, hash_game_state, key_game_counter [EXTRACTED 0.90]
- **Input queue retry cycle (main/delayed/dead/mover)** — queue_manager_next_request, queue_manager_handle_failure, queue_manager_mover_loop, client_push_request, client_pop_request, client_push_delayed, client_pop_delayed_due, client_push_dead, queue_input, queue_delayed, queue_dead [EXTRACTED 0.90]
- **Story drain to vector memory** — game_state_try_drain, client_incr, client_hdel, vector_memory_upsert_chunks, vector_memory_upsert, vector_memory_query, hash_game_state, key_game_counter, vector_index_search [EXTRACTED 0.85]
- **Combat resolution flow** — combat_system_resolve_attack, combat_system_calculate_base_damage, combat_system_apply_damage_multipliers, combat_system_full_combat_turn, dice_engine_roll, dice_engine_advantage [INFERRED 0.80]
- **Infinite world plus adaptive difficulty loop** — world_generator_generate_cell, world_generator_ensure_world, world_generator_expand_world, world_generator_move_player, xp_loot_difficulty_scalar, xp_loot_track_fight [INFERRED 0.75]

## Communities (71 total, 27 thin omitted)

### Community 0 - "Flee Pack Combat"
Cohesion: 0.09
Nodes (78): adjudicate_trick(), currently_engaged(), engage_pack(), _fallback_trick(), flee_chance(), has_trick_item(), live_hostiles(), monster_strike() (+70 more)

### Community 1 - "Redis Clients"
Cohesion: 0.13
Nodes (15): float, GameMemory, GamesRedisClient, InputRedisClient, OutputRedisClient, GamesRedisClient, InputRedisClient, OutputRedisClient (+7 more)

### Community 2 - "Context Injector"
Cohesion: 0.35
Nodes (33): node5_context_injector(), Any, GameState, str, BaseModel, Enum, DamageType, DiceType (+25 more)

### Community 3 - "World Generation"
Cohesion: 0.20
Nodes (35): node0_worldgen(), Any, GameState, str, _seed_for(), GridCell, Random, _biome_adjacency() (+27 more)

### Community 4 - "Combat Formulas"
Cohesion: 0.07
Nodes (37): to_int / clamp_int, apply_damage_multipliers, calculate_base_damage, full_combat_turn, resolve_attack, status effects (apply/process), advantage / disadvantage rolls, attack_roll (+29 more)

### Community 5 - "Game State Manager"
Cohesion: 0.13
Nodes (17): GameStateManager, Any, bool, GameMemory, GamesRedisClient, int, str, estimate_tokens() (+9 more)

### Community 6 - "Combat System"
Cohesion: 0.21
Nodes (32): Dice, apply_damage_multipliers(), apply_status_effect(), calculate_base_damage(), _damage_type_to_effect(), full_combat_turn(), process_status_effects(), bool (+24 more)

### Community 7 - "Classifier Routing"
Cohesion: 0.10
Nodes (32): classifier_node, deterministic_pass, _extract_flee_method, _extract_target, adjudicate_trick, currently_engaged, engage_pack, _fallback_trick (+24 more)

### Community 8 - "Worldgen Web Search"
Cohesion: 0.11
Nodes (28): node0_worldgen, _seed_for, _fetch_and_extract, _fetch_html, google_web_search, html_to_text, node1_web_search, _parse_ddg_results (+20 more)

### Community 9 - "Items DB Loader"
Cohesion: 0.22
Nodes (9): Counter, _char_bigrams(), _cosine_sim(), _damerau_levenshtein(), ItemsDB, Any, float, int (+1 more)

### Community 10 - "Classifier Node"
Cohesion: 0.17
Nodes (16): classifier_node(), deterministic_pass(), _extract_flee_method(), _extract_target(), Any, bool, GameState, str (+8 more)

### Community 11 - "Input Queue"
Cohesion: 0.14
Nodes (9): backoff_delay(), InputQueue, Any, float, GameRequest, InputRedisClient, int, str (+1 more)

### Community 12 - "Config Entry Points"
Cohesion: 0.26
Nodes (6): AppConfig, ModelConfig, Settings, OutputCache, int, OutputRedisClient

### Community 13 - "Memory API"
Cohesion: 0.18
Nodes (15): _get_memory(), memory_clear(), memory_export(), memory_query(), memory_restore(), memory_upsert(), MemoryQueryRequest, MemoryRestoreRequest (+7 more)

### Community 14 - "Multi-Task Engine"
Cohesion: 0.19
Nodes (12): MultiTaskEngine, Any, bool, OutputCache, str, GameOrchestrator, GameOrchestrator, InputQueue (+4 more)

### Community 15 - "Distributed Locks"
Cohesion: 0.17
Nodes (16): GamesRedisClient.acquire_lock(), GamesRedisClient.release_lock(), games:{uuid}:lock STRING NX, dbsize(), delete_key(), game_counter_set(), game_expire(), game_lock_acquire() (+8 more)

### Community 16 - "Story Graph Build"
Cohesion: 0.20
Nodes (14): node6_story_generator(), Any, GameState, str, _budget_exhausted(), build_game_graph_v2(), context_refresh_node(), Any (+6 more)

### Community 17 - "Image Redescriptor"
Cohesion: 0.21
Nodes (12): _create_cell_key(), _generate_empty_grid(), node2_image_processor(), Any, GameState, int, str, node3_redescriptor() (+4 more)

### Community 18 - "Queue Operations"
Cohesion: 0.17
Nodes (15): InputRedisClient.pop_request(), InputRedisClient.push_request(), InputRedisClient.queue_length(), InputQueue.enqueue(), input:queue LIST, QueueManager.next_request(), _get_input(), _get_output() (+7 more)

### Community 19 - "Web Search Node"
Cohesion: 0.33
Nodes (12): _fetch_and_extract(), _fetch_html(), google_web_search(), html_to_text(), node1_web_search(), _parse_ddg_results(), Any, float (+4 more)

### Community 20 - "State Persistence"
Cohesion: 0.26
Nodes (13): GamesRedisClient.expire(), GamesRedisClient.hdel(), GamesRedisClient.hset(), GamesRedisClient.incr(), GamesRedisClient.set_counter(), GamesRedisClient.touch_game_keys(), GameStateManager.save_initial_state(), GameStateManager.save_state() (+5 more)

### Community 21 - "Delayed Dead-Letter Queue"
Cohesion: 0.24
Nodes (10): InputRedisClient.pop_delayed_due(), InputRedisClient.push_dead(), InputRedisClient.push_delayed(), input:queue:dead ZSET (DLQ), input:queue:delayed ZSET, QueueManager.handle_failure(), QueueManager._mover_loop(), queue_dead_push() (+2 more)

### Community 22 - "Orchestrator Core"
Cohesion: 0.29
Nodes (6): Any, GameRequest, GameState, OutputCache, str, GameStateManager

### Community 23 - "Output Cache"
Cohesion: 0.33
Nodes (7): RedisClient.get_json(), OutputRedisClient.push_result(), output:{uuid} JSON TTL, OutputCache.store_result(), output_get(), output_set(), OutputRedisClient (prefix=output)

### Community 24 - "Legacy TLS Patch"
Cohesion: 0.33
Nodes (4): _legacy_ssl_context(), _LegacyTLSAsyncClient, _LegacyTLSClient, SSLContext

### Community 25 - "Trigger Guard"
Cohesion: 0.33
Nodes (6): GamesRedisClient.hgetall(), GameStateManager.load_state(), trigger:busy guard STRING, input:queue:processing transient LIST, game_state_get(), trigger()

### Community 26 - "Redis Config"
Cohesion: 0.40
Nodes (3): bool, RedisConfig, SearchConfig

### Community 28 - "LLM Client Setup"
Cohesion: 0.50
Nodes (4): setup_logger, OpenRouterDirectClient, chat_json strict-JSON helper, AppConfig budgets

### Community 29 - "Logging"
Cohesion: 0.67
Nodes (3): Logger, str, setup_logger()

### Community 31 - "Rolling Memory"
Cohesion: 0.67
Nodes (3): TimeOfDay enum, GameState rolling memory (context/chat_log), ContextSummary model

## Knowledge Gaps
- **104 isolated node(s):** `bool`, `GameState`, `float`, `GameState`, `Any` (+99 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `Multi-Task Engine` to `Redis Clients`, `Game State Manager`, `Classifier Routing`, `Input Queue`, `Config Entry Points`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Why does `str` connect `Distributed Locks` to `Redis Clients`, `Game State Manager`, `Memory API`, `Queue Operations`, `State Persistence`, `Output Cache`, `Trigger Guard`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `InputRedisClient` connect `Redis Clients` to `Input Queue`, `Config Entry Points`, `Memory API`, `Multi-Task Engine`, `Distributed Locks`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `GamesRedisClient` (e.g. with `MemoryQueryRequest` and `MemoryRestoreRequest`) actually correct?**
  _`GamesRedisClient` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `InputRedisClient` (e.g. with `MemoryQueryRequest` and `MemoryRestoreRequest`) actually correct?**
  _`InputRedisClient` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `GameMemory` (e.g. with `MemoryQueryRequest` and `MemoryRestoreRequest`) actually correct?**
  _`GameMemory` has 17 INFERRED edges - model-reasoned connections that need verification._
- **What connects `bool`, `GameState`, `float` to the rest of the system?**
  _104 weakly-connected nodes found - possible documentation gaps or missing edges._