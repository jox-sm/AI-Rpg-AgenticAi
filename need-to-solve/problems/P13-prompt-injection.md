# P13 — Prompt Injection: No Boundaries, Poisoned Lore to Story

Status: OPEN. Severity P1 (security).

## Description
No sanitization/delimiters/role hierarchy. User prompt + web + RAG concatenated raw: `node1:61 {"role":"user","content":query}` where `query=prompt or decision.search_query :44-46` (attacker-influenced). `agent.py:184-210` interpolates `prompt`, `search_results[:2000]`, `rag memories`, grid note, `Web search ...[:500]`; system prompt duplicated as `messages[0] :196` despite `system_prompt= :172`. `node5:56-66` dumps `prompt/input_data/game_data` + `search[:200]`. `node6:94,104-116` templates `search[:300]/tool_results/rag/inventory/skills` to narrative. `agent.py:137-145` joins `text[:1500]` with weak `[memory i|...]` headers — stored jailbreak persists. `node6:88-91` blocklist `if "error" not in r.lower()` drops legit "terror" prose, keeps hallucinations without substring.

## Evidence
- `rpg_ai_server/agents/node1_web_search.py:44-64`, `node4_tool_agent/agent.py:124-210`, `node5_context_injector.py:56-77`, `node6_story_generator.py:88-126`

## Impact
Web-poisoned lore flows to player story, stored memory jailbreak persists across turns, benign tool output filtered.

## Repro
Seed search result with `Ignore previous...` -> appears verbatim in story. Store jailbreak chunk -> retrieved every turn.

## Related
S13, D13, P11, P12.
