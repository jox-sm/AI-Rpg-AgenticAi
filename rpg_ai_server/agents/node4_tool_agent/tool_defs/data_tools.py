from __future__ import annotations

import json

from langchain_core.tools import tool

from ....schemas.types import Relationship


@tool
async def json_data_maker_and_tracker(
    action: str = "get",
    data_type: str = "",
    data_name: str = "",
    existing_data_json: str = "{}",
    new_data_json: str = "",
    relationship_entity: str = "",
    relationship_disposition: float = 0.0,
    relationship_description: str = "",
) -> str:
    """Track relationships, items, and game data in structured JSON format.

    Args:
        action: Action - 'get', 'set', 'update_relationship', 'list_all'
        data_type: Type of data (inventory, relationships, quests, locations, notes)
        data_name: Name/key of the specific data entry
        existing_data_json: JSON string of existing data store
        new_data_json: JSON string of new data to set
        relationship_entity: Entity name for relationship update
        relationship_disposition: Disposition value (-100 to 100)
        relationship_description: Description of the relationship
    """
    try:
        data_store = json.loads(existing_data_json) if isinstance(existing_data_json, str) else existing_data_json
    except (json.JSONDecodeError, TypeError):
        data_store = {}

    if not isinstance(data_store, dict):
        raise ValueError("existing data corrupt")

    if data_type not in data_store:
        data_store[data_type] = {}

    if action == "get":
        entry = data_store.get(data_type, {}).get(data_name, None)
        return json.dumps({"data_type": data_type, "name": data_name, "data": entry}, indent=2)

    elif action == "set":
        try:
            new_data = json.loads(new_data_json) if isinstance(new_data_json, str) else new_data_json
            data_store[data_type][data_name] = new_data
            return json.dumps({"success": True, "data_type": data_type, "name": data_name, "data": new_data}, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to set data: {e}"}, indent=2)

    elif action == "update_relationship":
        if relationship_entity:
            rel = Relationship(
                entity_name=relationship_entity,
                disposition=relationship_disposition,
                description=relationship_description,
            )
            if "relationships" not in data_store:
                data_store["relationships"] = {}
            if relationship_entity in data_store["relationships"]:
                existing = data_store["relationships"][relationship_entity]
                new_disp = existing.get("disposition", 0) + relationship_disposition
                new_disp = max(-100, min(100, new_disp))
                rel.disposition = new_disp
            data_store["relationships"][relationship_entity] = rel.model_dump()
            return json.dumps({"success": True, "relationship": rel.model_dump()}, indent=2)
        return json.dumps({"error": "relationship_entity is required"}, indent=2)

    elif action == "list_all":
        return json.dumps(data_store, indent=2)

    return json.dumps({"error": f"Unknown action: {action}"}, indent=2)
