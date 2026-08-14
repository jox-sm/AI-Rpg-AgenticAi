from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
import operator

from .types import (
    CharacterStats,
    ContextSummary,
    GridCell,
    ImageData,
    InventoryItem,
    NodeDecision,
    Relationship,
    ReDescriptionData,
    Skill,
)


class GameState(TypedDict):
    uuid: str
    prompt: str
    input_data: Dict[str, Any]
    game_data: Dict[str, Any]
    images: Dict[str, ImageData]
    grid_data: Dict[str, List[GridCell]]
    re_description_data: Optional[ReDescriptionData]
    context_summary: Optional[ContextSummary]
    character_stats: Optional[CharacterStats]
    skills: Annotated[List[Skill], operator.add]
    inventory: Annotated[List[InventoryItem], operator.add]
    relationships: Annotated[List[Relationship], operator.add]
    story_output: str
    decision: Optional[NodeDecision]
    needs_search: bool
    needs_image_processing: bool
    needs_re_description: bool
    processed: bool
    error: Optional[str]
    search_results: str
    rag_context: str
    tool_results: Annotated[List[str], operator.add]
    game_output: Optional[Dict[str, Any]]
    conditional_passes: int
    remaining_steps: int
    __next__: str
