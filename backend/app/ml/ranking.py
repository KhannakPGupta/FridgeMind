"""Transparent hybrid recipe ranking engine."""

from typing import List, Dict, Any, Set, Tuple
from backend.app.schemas.recipes import PreferencesInput
from backend.app.schemas.ingredients import IngredientItem


WEIGHT_COVERAGE = 0.45
WEIGHT_TASTE = 0.25
WEIGHT_EFFORT = 0.20
WEIGHT_PRACTICALITY = 0.10

EFFORT_LEVELS = {"lazy": 1, "easy": 2, "chef": 3}


def calculate_ingredient_coverage(
    recipe_ingredients: List[Dict[str, Any]],
    pantry_names: Set[str],
) -> Tuple[float, int, int]:
    """Calculate weighted coverage of available pantry items for a given recipe.

    Returns:
        (coverage_ratio, matched_count, total_count)
    """
    if not recipe_ingredients:
        return 0.0, 0, 0

    total_weight = 0.0
    matched_weight = 0.0
    matched_count = 0

    # Minor seasonings and garnishes receive lower weight than main proteins/produce
    light_garnishes = {"salt", "black pepper", "turmeric", "water", "coriander leaves", "basil leaves"}

    for item in recipe_ingredients:
        ing_name = str(item.get("name", "")).strip().lower()
        is_light = ing_name in light_garnishes
        weight = 0.5 if is_light else 1.0
        total_weight += weight

        # Check if pantry contains this ingredient or a close alias
        if any(pantry_item in ing_name or ing_name in pantry_item for pantry_item in pantry_names):
            matched_weight += weight
            matched_count += 1

    coverage_ratio = matched_weight / total_weight if total_weight > 0 else 0.0
    return round(coverage_ratio, 3), matched_count, len(recipe_ingredients)


def calculate_taste_match(recipe_tastes: List[str], user_tastes: List[str]) -> float:
    """Calculate taste alignment between user preferences and recipe taste profile."""
    if not user_tastes:
        return 0.75  # Neutral baseline when user didn't specify taste

    r_set = {t.lower() for t in recipe_tastes}
    u_set = {t.lower() for t in user_tastes}

    overlap = len(r_set.intersection(u_set))
    if overlap > 0:
        return min(1.0, 0.6 + (0.4 * (overlap / len(u_set))))
    return 0.25


def calculate_effort_match(recipe_effort: str, user_effort: str | None) -> float:
    """Calculate cooking effort alignment."""
    if not user_effort:
        return 0.8

    r_level = EFFORT_LEVELS.get(recipe_effort.lower(), 2)
    u_level = EFFORT_LEVELS.get(user_effort.lower(), 2)
    diff = abs(r_level - u_level)

    if diff == 0:
        return 1.0
    if diff == 1:
        return 0.65
    return 0.30


def calculate_practicality(recipe: Dict[str, Any], matched_count: int, total_count: int) -> float:
    """Estimate practicality based on prep time and missing ingredients burden."""
    # Fewer missing ingredients = higher practicality
    missing_ratio = (total_count - matched_count) / max(1, total_count)
    ingredient_feasibility = 1.0 - (0.7 * missing_ratio)

    # Shorter cook time is slightly more practical
    time_str = recipe.get("time", "20 min")
    try:
        minutes = int("".join(filter(str.isdigit, time_str)) or 20)
    except Exception:
        minutes = 20

    time_factor = 1.0 if minutes <= 15 else 0.85 if minutes <= 30 else 0.70
    return round(0.6 * ingredient_feasibility + 0.4 * time_factor, 3)


def rank_recipes(
    recipes: List[Dict[str, Any]],
    pantry: List[IngredientItem],
    preferences: PreferencesInput,
    theme: str = "cozy",
) -> List[Dict[str, Any]]:
    """Rank candidate recipes using the transparent 4-signal hybrid formula."""
    pantry_names = {item.name.lower() for item in pantry}
    scored_recipes = []

    for r in recipes:
        recipe_ing = r.get("ingredients", [])
        coverage, matched_cnt, total_cnt = calculate_ingredient_coverage(recipe_ing, pantry_names)
        taste_score = calculate_taste_match(r.get("tastes", []), preferences.tastes)
        effort_score = calculate_effort_match(r.get("effort", "easy"), preferences.effort)
        practicality = calculate_practicality(r, matched_cnt, total_cnt)

        # Weighted composite score
        composite = (
            WEIGHT_COVERAGE * coverage
            + WEIGHT_TASTE * taste_score
            + WEIGHT_EFFORT * effort_score
            + WEIGHT_PRACTICALITY * practicality
        )

        # Match percentage scaled between 60 and 99 for friendly UI display
        match_pct = int(min(99, max(60, round(composite * 100))))

        # Copy and attach metadata
        entry = dict(r)
        entry["match"] = match_pct
        entry["matched_count"] = matched_cnt
        entry["total_ingredients"] = total_cnt
        entry["composite_score"] = composite
        entry["ai_reason"] = (
            f"You have {matched_cnt} of {total_cnt} ingredients already, so this is a low-waste {theme} match."
        )

        scored_recipes.append(entry)

    # Sort descending by composite score, then rating
    scored_recipes.sort(key=lambda x: (x["composite_score"], x["rating"]), reverse=True)
    return scored_recipes
