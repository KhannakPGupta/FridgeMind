"""Service coordinating multi-cuisine recipe retrieval, dietary filtering, ranking, and surprise generation."""

import random
from typing import List, Dict, Any, Optional
from backend.app.data.database import get_all_recipes, get_recipe_by_id
from backend.app.ml.hard_filters import filter_recipes_by_diet
from backend.app.ml.ranking import rank_recipes
from backend.app.services.llm_recipe_adapter import generate_dynamic_recipes
from backend.app.schemas.ingredients import IngredientItem
from backend.app.schemas.recipes import (
    PreferencesInput,
    RecipeResponse,
    RecommendResponse,
)
from backend.app.core.logging import logger


async def get_recipe_recommendations(
    pantry: List[IngredientItem],
    preferences: PreferencesInput,
    theme: str = "cozy",
    surprise: bool = False,
) -> RecommendResponse:
    """Retrieve, filter, rank, and adapt recipes based on user pantry and vibe."""
    # 1. Fetch catalog candidate pool
    candidates = get_all_recipes()

    # 2. Apply dietary & allergy hard filters first
    filtered_candidates = filter_recipes_by_diet(candidates, preferences.diets)
    if not filtered_candidates:
        logger.warning("No recipes matched strict dietary filters %s. Using all candidates with warning.", preferences.diets)
        filtered_candidates = candidates

    # 3. Dynamic LLM multi-cuisine recipe synthesis
    ai_recipes = []
    if not surprise and pantry:
        ai_recipes = await generate_dynamic_recipes(pantry, preferences, theme, count=2)
        for ar in ai_recipes:
            filtered_candidates.insert(0, ar)

    # 4. Hybrid ML Ranking (0.45 coverage + 0.25 taste + 0.20 effort + 0.10 practicality)
    ranked = rank_recipes(filtered_candidates, pantry, preferences, theme)

    # 5. Handle Surprise Mode
    selected_theme = theme
    source = "hybrid" if ai_recipes else "catalog"

    if surprise:
        source = "surprise_sampler"
        themes = ["cozy", "spicy", "fresh", "chef"]
        selected_theme = random.choice(themes)

        # Sample from the top 5 feasible candidates to ensure quality while adding variety
        top_pool = ranked[:min(5, len(ranked))]
        if top_pool:
            chosen = random.choice(top_pool)
            # Put chosen recipe first
            ranked = [chosen] + [r for r in ranked if r["id"] != chosen["id"]]

    # Convert to response objects
    recipe_responses = [RecipeResponse(**r) for r in ranked]

    return RecommendResponse(
        recipes=recipe_responses,
        total_found=len(recipe_responses),
        selected_theme=selected_theme,
        source=source,
    )


def fetch_recipe_detail(recipe_id: int) -> Optional[RecipeResponse]:
    """Retrieve full details of a single recipe."""
    r = get_recipe_by_id(recipe_id)
    return RecipeResponse(**r) if r else None
