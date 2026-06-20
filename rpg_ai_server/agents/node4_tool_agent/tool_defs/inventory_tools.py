from __future__ import annotations

import json

from langchain_core.tools import tool

from ....schemas.types import InventoryItem
from .common import _ITEMS_DB, calc_load, item_weight, load_status


@tool
async def inventory_checker_and_updater(
    current_inventory_json: str,
    action: str = "check",
    item_name: str = "",
    quantity: int = 1,
    item_json: str = "",
    currency_amount: int = 0,
    currency_action: str = "",
    carry_capacity: float = 50.0,
) -> str:
    """Check and update character inventory, including weight/encumbrance.

    Args:
        current_inventory_json: JSON string of current inventory items
        action: Action - 'check', 'add', 'remove', 'store', 'retrieve', 'use', 'check_currency', 'spend_currency', 'load_status'
        item_name: Name of the item to check/use/remove/store/retrieve
        quantity: Quantity for add/remove
        item_json: JSON string of item to add (for add action) OR container name (for store action)
        currency_amount: Amount of currency
        currency_action: 'add' or 'spend'
        carry_capacity: Max carry weight in lbs (usually STR * 5)
    """
    try:
        inv_data = json.loads(current_inventory_json) if isinstance(current_inventory_json, str) else current_inventory_json
    except (json.JSONDecodeError, TypeError):
        inv_data = []

    inventory = [InventoryItem(**i) if isinstance(i, dict) else i for i in inv_data]

    if action == "load_status":
        return json.dumps(load_status(inventory, carry_capacity), indent=2)

    if action == "container_status":
        if not item_name:
            return json.dumps({"error": "container_status requires item_name (container name)"}, indent=2)
        container = None
        for item in inventory:
            if item.name.lower() == item_name.lower() and item.properties.get("is_container"):
                container = item
                break
        if not container:
            return json.dumps({"error": f"Container '{item_name}' not found"}, indent=2)
        stored = [
            {"name": i.name, "quantity": i.quantity, "weight": i.weight}
            for i in inventory if i.stored_in == container.name
        ]
        props = container.properties
        used_lbs = sum(i.weight * i.quantity for i in inventory if i.stored_in == container.name)
        used_units = sum(i.quantity for i in inventory if i.stored_in == container.name)
        max_lbs = props.get("max_capacity_lbs", 0)
        max_units = props.get("max_capacity_units", 0)
        return json.dumps({
            "container": container.name,
            "contents": stored,
            "weight": f"{round(used_lbs,1)}/{max_lbs if max_lbs > 0 else 'unlimited'} lbs",
            "slots": f"{used_units}/{max_units if max_units > 0 else 'unlimited'}",
            "item_count": len(stored),
        }, indent=2)

    if action == "check":
        item_found = None
        for item in inventory:
            if item.name.lower() == item_name.lower():
                item_found = item
                break
        if item_found:
            result = item_found.model_dump() if hasattr(item_found, 'model_dump') else item_found
            db_item = _ITEMS_DB.get_by_name(item_name)
            if db_item:
                result["db_stats"] = db_item
            result["load"] = load_status(inventory, carry_capacity)
            return json.dumps({
                "found": True,
                "item": result,
                "quantity": item_found.quantity,
            }, indent=2)
        return json.dumps({"found": False, "message": f"Item '{item_name}' not in inventory"}, indent=2)

    elif action == "add":
        try:
            if item_json:
                new_item_data = json.loads(item_json) if isinstance(item_json, str) else json.loads(item_json)
            elif item_name:
                db_item = _ITEMS_DB.get_by_name(item_name)
                if db_item:
                    new_item_data = db_item
                else:
                    return json.dumps({"error": f"Item '{item_name}' not found in database"}, indent=2)
            else:
                return json.dumps({"error": "Provide item_name or item_json"}, indent=2)

            new_item_data["weight"] = new_item_data.get("weight", item_weight(new_item_data))

            if new_item_data.get("Type", "").lower() == "container":
                wr = new_item_data.get("Weight Reduction", "0.1")
                try:
                    frac = float(wr.split("/")[1].strip()) if "/" in wr else 0.1
                except (ValueError, IndexError, AttributeError):
                    frac = 0.1
                if "no weight" in wr.lower() or "nothing" in wr.lower() or "0 weight" in wr.lower():
                    frac = 0.0
                props = new_item_data.setdefault("properties", {})
                if isinstance(props, str):
                    props = {}
                props["is_container"] = True
                props["weight_reduction"] = frac
                props["max_capacity_lbs"] = new_item_data.get("max_capacity_lbs", 0)
                props["max_capacity_units"] = new_item_data.get("max_capacity_units", 0)

            existing = None
            for item in inventory:
                if item.name.lower() == new_item_data.get("name", "").lower():
                    existing = item
                    break

            will_add_weight = new_item_data.get("weight", 1.0)
            load = calc_load(inventory)
            additional = will_add_weight * quantity
            if load + additional > carry_capacity:
                ls = load_status(inventory, carry_capacity)
                return json.dumps({
                    "error": f"Not enough carry capacity! Need {additional} lbs, have {round(carry_capacity - load, 1)} lbs free.",
                    "load": ls,
                }, indent=2)

            if existing:
                existing.quantity += quantity
            else:
                new_item = InventoryItem(**new_item_data)
                new_item.quantity = quantity
                inventory.append(new_item)

            ls = load_status(inventory, carry_capacity)
            return json.dumps({
                "success": True,
                "load": ls,
                "inventory": [i.model_dump() if hasattr(i, 'model_dump') else i for i in inventory],
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to add item: {e}"}, indent=2)

    elif action == "store":
        if not item_name or not item_json:
            return json.dumps({"error": "store requires item_name (item to store) and item_json (container name)"}, indent=2)
        container_name = item_json
        container_found = None
        for item in inventory:
            if item.name.lower() == container_name.lower() and item.properties.get("is_container"):
                container_found = item
                break
        if not container_found:
            return json.dumps({"error": f"Container '{container_name}' not found in inventory"}, indent=2)
        item_to_store = None
        for item in inventory:
            if item.name.lower() == item_name.lower() and not item.stored_in:
                item_to_store = item
                break
        if not item_to_store:
            return json.dumps({"error": f"'{item_name}' not found or already stored"}, indent=2)

        props = container_found.properties
        max_lbs = props.get("max_capacity_lbs", 0)
        max_units = props.get("max_capacity_units", 0)

        stored_items = [i for i in inventory if i.stored_in == container_found.name]
        current_stored_weight = sum(i.weight * i.quantity for i in stored_items)
        current_stored_units = sum(i.quantity for i in stored_items)
        add_weight = item_to_store.weight * item_to_store.quantity
        add_units = item_to_store.quantity

        if max_lbs > 0 and current_stored_weight + add_weight > max_lbs:
            free = round(max_lbs - current_stored_weight, 1)
            return json.dumps({"error": f"{container_found.name} full! Has {round(current_stored_weight,1)}/{max_lbs} lbs, need {round(add_weight,1)} more, only {free} free."}, indent=2)
        if max_units > 0 and current_stored_units + add_units > max_units:
            free = max_units - current_stored_units
            return json.dumps({"error": f"{container_found.name} full! Has {current_stored_units}/{max_units} slots, need {add_units} more, only {free} free."}, indent=2)

        item_to_store.stored_in = container_found.name
        ls = load_status(inventory, carry_capacity)
        return json.dumps({
            "success": True,
            "message": f"Stored {item_to_store.name} x{item_to_store.quantity} in {container_found.name}",
            "load": ls,
            "inventory": [i.model_dump() if hasattr(i, 'model_dump') else i for i in inventory],
        }, indent=2)

    elif action == "retrieve":
        if not item_name:
            return json.dumps({"error": "retrieve requires item_name"}, indent=2)
        item_to_retrieve = None
        for item in inventory:
            if item.name.lower() == item_name.lower() and item.stored_in:
                item_to_retrieve = item
                break
        if not item_to_retrieve:
            return json.dumps({"error": f"'{item_name}' not found in any container"}, indent=2)
        item_to_retrieve.stored_in = None
        ls = load_status(inventory, carry_capacity)
        return json.dumps({
            "success": True,
            "message": f"Retrieved {item_to_retrieve.name} x{item_to_retrieve.quantity} from storage",
            "load": ls,
            "inventory": [i.model_dump() if hasattr(i, 'model_dump') else i for i in inventory],
        }, indent=2)

    elif action == "remove":
        for item in inventory:
            if item.name.lower() == item_name.lower():
                if item.quantity < quantity:
                    return json.dumps({"error": f"Not enough '{item_name}': have {item.quantity}, need {quantity}"}, indent=2)
                item.quantity -= quantity
                if item.quantity <= 0:
                    inventory = [i for i in inventory if i.name.lower() != item_name.lower()]
                ls = load_status(inventory, carry_capacity)
                return json.dumps({
                    "success": True,
                    "removed": quantity,
                    "load": ls,
                    "inventory": [i.model_dump() if hasattr(i, 'model_dump') else i for i in inventory],
                }, indent=2)
        return json.dumps({"error": f"Item '{item_name}' not found"}, indent=2)

    elif action == "check_currency":
        total_coins = sum(i.quantity for i in inventory if i.name.lower() in ["gold coin", "silver coin", "copper coin", "platinum coin"])
        return json.dumps({"total_currency": total_coins, "load": load_status(inventory, carry_capacity)}, indent=2)

    elif action == "spend_currency":
        for item in inventory:
            if item.name.lower() in ["gold coin", "silver coin", "copper coin", "platinum coin"]:
                if item.quantity >= currency_amount:
                    item.quantity -= currency_amount
                    if item.quantity <= 0:
                        inventory = [i for i in inventory if i.name.lower() != item.name.lower()]
                    return json.dumps({"success": True, "spent": currency_amount, "load": load_status(inventory, carry_capacity)}, indent=2)
                currency_amount -= item.quantity
                item.quantity = 0
                inventory = [i for i in inventory if i.quantity > 0]
        return json.dumps({"error": "Insufficient currency"}, indent=2)

    return json.dumps({"error": f"Unknown action: {action}"}, indent=2)
