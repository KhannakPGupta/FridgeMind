import math
import random
from typing import List, Dict, Any, Optional, Tuple
from backend.app.data.database import (
    get_all_recipes,
    get_recipe_by_id,
    search_candidate_recipes_fts,
)
from backend.app.ml.hard_filters import filter_recipes_by_diet
from backend.app.ml.ranking import rank_recipes
from backend.app.ml.substitutions import (
    find_substitutions_for_recipe,
    apply_substitution_to_recipe,
    SubstitutionOption,
)
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
    # 1. Sub-millisecond candidate retrieval via SQLite FTS5 index
    pantry_terms = [i.name for i in pantry] if pantry else []
    if pantry_terms:
        candidates = search_candidate_recipes_fts(pantry_terms, limit=80)
    else:
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

    # In-memory candidate deduplication by name
    seen_cand_names = set()
    deduped_candidates = []
    for cand in filtered_candidates:
        cand_name = cand.get("name", "").strip().lower()
        if cand_name and cand_name not in seen_cand_names:
            seen_cand_names.add(cand_name)
            deduped_candidates.append(cand)
    filtered_candidates = deduped_candidates

    # 4. Hybrid ML Ranking (0.45 coverage + 0.25 taste + 0.20 effort + 0.10 practicality)
    ranked = rank_recipes(filtered_candidates, pantry, preferences, theme)

    # Defensive deduplication of ranked results
    seen_ranked_names = set()
    deduped_ranked = []
    for r in ranked:
        r_name = r.get("name", "").strip().lower()
        if r_name and r_name not in seen_ranked_names:
            seen_ranked_names.add(r_name)
            deduped_ranked.append(r)
    ranked = deduped_ranked

    # 5. Handle Temperature-Controlled Surprise Mode
    selected_theme = theme
    source = "hybrid" if ai_recipes else "catalog"

    if surprise:
        source = "surprise_sampler"
        themes = ["cozy", "spicy", "fresh", "chef"]
        selected_theme = random.choice(themes)

        # Softmax temperature sampling over top candidates (temperature T = 0.7)
        top_pool = ranked[:min(8, len(ranked))]
        if top_pool:
            scores = [r.get("composite_score", 0.5) for r in top_pool]
            exp_scores = [math.exp(s / 0.7) for s in scores]
            sum_exp = sum(exp_scores)
            weights = [e / sum_exp for e in exp_scores]

            chosen = random.choices(top_pool, weights=weights, k=1)[0]
            # Prioritize chosen surprise recipe at top of list
            ranked = [chosen] + [r for r in ranked if r["id"] != chosen["id"] and r.get("name", "").strip().lower() != chosen.get("name", "").strip().lower()]

    # 6. Enrich recipes with smart pantry substitutions
    pantry_names = [i.name for i in pantry]
    for r in ranked:
        missing = r.get("missing_ingredients", [])
        if missing:
            r["available_substitutions"] = find_substitutions_for_recipe(missing, pantry_names)
        else:
            r["available_substitutions"] = []

    # Convert to response objects
    recipe_responses = [RecipeResponse(**r) for r in ranked]

    return RecommendResponse(
        recipes=recipe_responses,
        total_found=len(recipe_responses),
        selected_theme=selected_theme,
        source=source,
    )


def fetch_recipe_detail(recipe_id: int) -> Optional[RecipeResponse]:
    """Retrieve full details of a single recipe enriched with substitutions."""
    r = get_recipe_by_id(recipe_id)
    if not r:
        return None
    r.setdefault("matched_ingredients", [])
    r.setdefault("missing_ingredients", [])
    r.setdefault("badges", [r.get("cuisine", "Global")])

    # Find substitutions for any ingredients in the recipe
    ing_names = [
        ing.get("name") if isinstance(ing, dict) else getattr(ing, "name", "")
        for ing in r.get("ingredients", [])
    ]
    r["available_substitutions"] = find_substitutions_for_recipe(ing_names)
    return RecipeResponse(**r)


def apply_recipe_substitution(
    recipe_id: int,
    replace_ingredient: str,
    with_substitute: str,
) -> Optional[Tuple[RecipeResponse, SubstitutionOption]]:
    """Apply an ingredient substitution to a recipe and return the updated response."""
    r = get_recipe_by_id(recipe_id)
    if not r:
        return None

    adapted_dict, option = apply_substitution_to_recipe(r, replace_ingredient, with_substitute)
    adapted_dict.setdefault("matched_ingredients", [])
    adapted_dict.setdefault("missing_ingredients", [])

    # Refresh remaining substitutions
    all_ing = [
        ing.get("name") if isinstance(ing, dict) else getattr(ing, "name", "")
        for ing in adapted_dict.get("ingredients", [])
    ]
    adapted_dict["available_substitutions"] = find_substitutions_for_recipe(all_ing)

    return RecipeResponse(**adapted_dict), option

