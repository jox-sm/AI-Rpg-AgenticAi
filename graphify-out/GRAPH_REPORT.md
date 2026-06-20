# Graph Report - D:/AI agent  (2026-06-20)

## Corpus Check
- 120 files · ~99,999 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 703 nodes · 1319 edges · 103 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_bool  RedisConfig  ._auth_part()|bool / RedisConfig / ._auth_part()]]
- [[_COMMUNITY_google_web_search()  Search the web for real-time information.     Use this tool when the game requir  AppConfig|google_web_search() / Search the web for real-time information.     Use this tool when the game requir / AppConfig]]
- [[_COMMUNITY_BaseModel  combat_tools.py  common.py|BaseModel / combat_tools.py / common.py]]
- [[_COMMUNITY_node1_web_search()  _create_cell_key()  _generate_empty_grid()|node1_web_search() / _create_cell_key() / _generate_empty_grid()]]
- [[_COMMUNITY_combat_system.py  dice_engine.py  incident_learning.py|combat_system.py / dice_engine.py / incident_learning.py]]
- [[_COMMUNITY_GameOrchestrator  ._build_initial_state()  .__init__()|GameOrchestrator / ._build_initial_state() / .__init__()]]
- [[_COMMUNITY_configurations  default_iteration  description|configurations / default_iteration / description]]
- [[_COMMUNITY_context  skill_name  suite_name|context / skill_name / suite_name]]
- [[_COMMUNITY_author  email  name|author / email / name]]
- [[_COMMUNITY_node7_output_pusher()  build_game_graph()  make_router_node()|node7_output_pusher() / build_game_graph() / make_router_node()]]
- [[_COMMUNITY_world_generator.py  GridCell  Random|world_generator.py / GridCell / Random]]
- [[_COMMUNITY_lastSelectedAgents|lastSelectedAgents]]
- [[_COMMUNITY_baseline_name  eval_suite  included_files|baseline_name / eval_suite / included_files]]
- [[_COMMUNITY_ChatGoogleGenerativeAI  ChatOpenAI  create_gemini_model()|ChatGoogleGenerativeAI / ChatOpenAI / create_gemini_model()]]
- [[_COMMUNITY_enums.py  Enum  DamageType|enums.py / Enum / DamageType]]
- [[_COMMUNITY_combat_defense.py  __init__.py  _block()|combat_defense.py / __init__.py / _block()]]
- [[_COMMUNITY_base.py  stealth.py  damage_formula()|base.py / stealth.py / damage_formula()]]
- [[_COMMUNITY_AsyncClient  get_openrouter_direct()  OpenRouterDirectClient|AsyncClient / get_openrouter_direct() / OpenRouterDirectClient]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_installedAt  skillFolderHash  skillPath|installedAt / skillFolderHash / skillPath]]
- [[_COMMUNITY_swarm  installedAt  skillFolderHash|swarm / installedAt / skillFolderHash]]
- [[_COMMUNITY_GameOutput  OutputRedisClient  OutputCache|GameOutput / OutputRedisClient / OutputCache]]
- [[_COMMUNITY_evals.json  description  eval_suite|evals.json / description / eval_suite]]
- [[_COMMUNITY_.skill-lock.json  dismissed  findSkillsPrompt|.skill-lock.json / dismissed / findSkillsPrompt]]

## God Nodes (most connected - your core abstractions)
1. `str` - 127 edges
2. `int` - 70 edges
3. `Any` - 47 edges
4. `bool` - 40 edges
5. `float` - 36 edges
6. `RedisClient` - 19 edges
7. `Random` - 17 edges
8. `skills` - 17 edges
9. `ItemsDB` - 15 edges
10. `lastSelectedAgents` - 14 edges

## Surprising Connections (you probably didn't know these)
- `str` --references--> `compress_text()`  [EXTRACTED]
  D:\AI agent\rpg_ai_server\utils\items_db.py → D:\AI agent\rpg_ai_server\utils\compression.py
- `str` --references--> `decompress_text()`  [EXTRACTED]
  D:\AI agent\rpg_ai_server\utils\items_db.py → D:\AI agent\rpg_ai_server\utils\compression.py
- `str` --references--> `get_skill()`  [EXTRACTED]
  D:\AI agent\rpg_ai_server\utils\items_db.py → D:\AI agent\rpg_ai_server\skills\__init__.py
- `str` --references--> `list_skills()`  [EXTRACTED]
  D:\AI agent\rpg_ai_server\utils\items_db.py → D:\AI agent\rpg_ai_server\skills\__init__.py
- `str` --references--> `list_categories()`  [EXTRACTED]
  D:\AI agent\rpg_ai_server\utils\items_db.py → D:\AI agent\rpg_ai_server\skills\__init__.py

## Import Cycles
- None detected.

## Communities (103 total, 0 thin omitted)

### Community 0 - "bool / RedisConfig / ._auth_part()"
Cohesion: 0.08
Nodes (15): bool, RedisConfig, GamesRedisClient, InputRedisClient, OutputRedisClient, RagRedisClient, RedisClient, GameStateManager (+7 more)

### Community 1 - "google_web_search() / Search the web for real-time information.     Use this tool when the game requir / AppConfig"
Cohesion: 0.09
Nodes (32): google_web_search(), Search the web for real-time information.     Use this tool when the game requir, asyncio, base64, AppConfig, ModelConfig, Settings, d_ai_agent_rpg_ai_server_agents_node4_tool_agent_py (+24 more)

### Community 2 - "BaseModel / combat_tools.py / common.py"
Cohesion: 0.08
Nodes (37): BaseModel, langchain_core_tools, math, pydantic, CharacterStats, ContextSummary, DamageCalculation, DiceRoll (+29 more)

### Community 3 - "node1_web_search() / _create_cell_key() / _generate_empty_grid()"
Cohesion: 0.06
Nodes (27): node1_web_search(), _create_cell_key(), _generate_empty_grid(), node2_image_processor(), node3_redescriptor(), node5_context_injector(), node6_story_generator(), Any (+19 more)

### Community 4 - "combat_system.py / dice_engine.py / incident_learning.py"
Cohesion: 0.13
Nodes (37): Dice, float, int, backoff_delay(), apply_damage_multipliers(), apply_status_effect(), calculate_base_damage(), _damage_type_to_effect() (+29 more)

### Community 5 - "GameOrchestrator / ._build_initial_state() / .__init__()"
Cohesion: 0.12
Nodes (6): GameOrchestrator, GameRequest, GameStateManager, InputRedisClient, InputQueue, QueueManager

### Community 6 - "configurations / default_iteration / description"
Cohesion: 0.11
Nodes (19): configurations, default_iteration, description, eval_suite, judge_model, models, repetitions, configurations (+11 more)

### Community 7 - "context / skill_name / suite_name"
Cohesion: 0.10
Nodes (19): context, skill_name, suite_name, evals, generated_at, input_root, models, overall (+11 more)

### Community 8 - "author / email / name"
Cohesion: 0.11
Nodes (17): author, email, name, description, homepage, keywords, license, logo (+9 more)

### Community 9 - "node7_output_pusher() / build_game_graph() / make_router_node()"
Cohesion: 0.17
Nodes (10): node7_output_pusher(), build_game_graph(), make_router_node(), MultiTaskEngine, GameOrchestrator, InputQueue, OutputCache, QueueManager (+2 more)

### Community 10 - "world_generator.py / GridCell / Random"
Cohesion: 0.22
Nodes (14): GridCell, hashlib, Random, _biome_adjacency(), _biome_to_terrain(), _cell_to_gridcell(), coord_to_key(), generate_world() (+6 more)

### Community 11 - "lastSelectedAgents"
Cohesion: 0.14
Nodes (14): ref_amp, ref_antigravity, ref_cline, ref_codex, ref_cursor, ref_deepagents, ref_dexto, ref_firebender (+6 more)

### Community 12 - "baseline_name / eval_suite / included_files"
Cohesion: 0.15
Nodes (12): baseline_name, eval_suite, included_files, input_root, iteration, skill_name, updated_at, ref_aggregate_benchmark_json (+4 more)

### Community 13 - "ChatGoogleGenerativeAI / ChatOpenAI / create_gemini_model()"
Cohesion: 0.24
Nodes (11): ChatGoogleGenerativeAI, ChatOpenAI, create_gemini_model(), create_openrouter_model(), get_context_injector_model(), get_image_model(), get_redescription_model(), get_story_model() (+3 more)

### Community 14 - "enums.py / Enum / DamageType"
Cohesion: 0.38
Nodes (9): Enum, DamageType, DiceType, EntityType, ItemCategory, OreType, SkillType, Terrain (+1 more)

### Community 15 - "combat_defense.py / __init__.py / _block()"
Cohesion: 0.22
Nodes (3): get_skill(), list_categories(), list_skills()

### Community 16 - "base.py / stealth.py / damage_formula()"
Cohesion: 0.22
Nodes (3): damage_formula(), make_result(), success_check()

### Community 17 - "AsyncClient / get_openrouter_direct() / OpenRouterDirectClient"
Cohesion: 0.32
Nodes (3): AsyncClient, get_openrouter_direct(), OpenRouterDirectClient

### Community 18 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, deep-agents-core

### Community 19 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, find-skills

### Community 20 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, framework-selection

### Community 21 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, langchain-middleware

### Community 22 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, langgraph-human-in-the-loop

### Community 23 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, deep-agents-memory

### Community 24 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, deep-agents-orchestration

### Community 25 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, langchain-dependencies

### Community 26 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, langchain-fundamentals

### Community 27 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, langchain-rag

### Community 28 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, langgraph-cli

### Community 29 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, langgraph-fundamentals

### Community 30 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, langgraph-persistence

### Community 31 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, managed-deep-agents

### Community 32 - "installedAt / skillFolderHash / skillPath"
Cohesion: 0.25
Nodes (8): installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt, redis-development

### Community 33 - "swarm / installedAt / skillFolderHash"
Cohesion: 0.25
Nodes (8): swarm, installedAt, skillFolderHash, skillPath, source, sourceType, sourceUrl, updatedAt

### Community 35 - "GameOutput / OutputRedisClient / OutputCache"
Cohesion: 0.29
Nodes (3): GameOutput, OutputRedisClient, OutputCache

### Community 44 - "evals.json / description / eval_suite"
Cohesion: 0.40
Nodes (4): description, eval_suite, evals, skill_name

### Community 45 - ".skill-lock.json / dismissed / findSkillsPrompt"
Cohesion: 0.40
Nodes (4): dismissed, findSkillsPrompt, skills, version

## Knowledge Gaps
- **177 isolated node(s):** `ModelConfig`, `AppConfig`, `Settings`, `Logger`, `GamesRedisClient` (+172 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `str` connect `bool / RedisConfig / ._auth_part()` to `google_web_search() / Search the web for real-time information.     Use this tool when the game requir / AppConfig`, `BaseModel / combat_tools.py / common.py`, `node1_web_search() / _create_cell_key() / _generate_empty_grid()`, `combat_system.py / dice_engine.py / incident_learning.py`, `GameOrchestrator / ._build_initial_state() / .__init__()`, `node7_output_pusher() / build_game_graph() / make_router_node()`, `world_generator.py / GridCell / Random`, `ChatGoogleGenerativeAI / ChatOpenAI / create_gemini_model()`, `enums.py / Enum / DamageType`, `combat_defense.py / __init__.py / _block()`, `base.py / stealth.py / damage_formula()`, `AsyncClient / get_openrouter_direct() / OpenRouterDirectClient`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Why does `skills` connect `.skill-lock.json / dismissed / findSkillsPrompt` to `installedAt / skillFolderHash / skillPath`, `swarm / installedAt / skillFolderHash`, `installedAt / skillFolderHash / skillPath`, `installedAt / skillFolderHash / skillPath`, `installedAt / skillFolderHash / skillPath`, `installedAt / skillFolderHash / skillPath`, `installedAt / skillFolderHash / skillPath`, `installedAt / skillFolderHash / skillPath`, `installedAt / skillFolderHash / skillPath`, `installedAt / skillFolderHash / skillPath`, `installedAt / skillFolderHash / skillPath`, `installedAt / skillFolderHash / skillPath`, `installedAt / skillFolderHash / skillPath`, `installedAt / skillFolderHash / skillPath`, `installedAt / skillFolderHash / skillPath`, `installedAt / skillFolderHash / skillPath`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `int` connect `combat_system.py / dice_engine.py / incident_learning.py` to `bool / RedisConfig / ._auth_part()`, `BaseModel / combat_tools.py / common.py`, `node1_web_search() / _create_cell_key() / _generate_empty_grid()`, `GameOutput / OutputRedisClient / OutputCache`, `GameOrchestrator / ._build_initial_state() / .__init__()`, `world_generator.py / GridCell / Random`, `ChatGoogleGenerativeAI / ChatOpenAI / create_gemini_model()`, `base.py / stealth.py / damage_formula()`, `AsyncClient / get_openrouter_direct() / OpenRouterDirectClient`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **What connects `Damerau-Levenshtein distance with transpositions.`, `In-memory RPG items database with semantic-ish search.      Search: exact match`, `ModelConfig` to the rest of the system?**
  _189 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `bool / RedisConfig / ._auth_part()` be split into smaller, more focused modules?**
  _Cohesion score 0.08281573498964803 - nodes in this community are weakly interconnected._
- **Should `google_web_search() / Search the web for real-time information.     Use this tool when the game requir / AppConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.08961038961038961 - nodes in this community are weakly interconnected._
- **Should `BaseModel / combat_tools.py / common.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07535460992907801 - nodes in this community are weakly interconnected._