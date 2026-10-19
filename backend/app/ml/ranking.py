"""Transparent hybrid recipe ranking engine with perishability-aware scoring and explainable AI."""

import math
from typing import List, Dict, Any, Set, Tuple, Optional
from backend.app.schemas.recipes import PreferencesInput
from backend.app.schemas.ingredients import IngredientItem


WEIGHT_COVERAGE = 0.45
WEIGHT_TASTE = 0.25
WEIGHT_EFFORT = 0.20
WEIGHT_PRACTICALITY = 0.10

EFFORT_LEVELS = {"lazy": 1, "easy": 2, "chef": 3}
LIGHT_GARNISHES = {
    "salt", "black pepper", "turmeric", "water", "coriander leaves",
    "basil leaves", "chili flakes", "cumin seeds", "oil", "cooking oil"
}


def calculate_detailed_coverage(
    recipe_ingredients: List[Dict[str, Any]],
    pantry_names: Set[str],
    use_first_names: Optional[Set[str]] = None,
) -> Tuple[float, int, int, List[str], List[str], List[str]]:
    """Calculate weighted coverage with perishability boost and ingredient lists.

    Returns:
        (coverage_ratio, matched_count, total_count, matched_names, missing_names, rescued_use_first)
    """
    if not recipe_ingredients:
        return 0.0, 0, 0, [], [], []

    use_first = use_first_names or set()
    total_weight = 0.0
    matched_weight = 0.0
    matched_names: List[str] = []
    missing_names: List[str] = []
    rescued_use_first: List[str] = []

    for item in recipe_ingredients:
        raw_name = str(item.get("name", "")).strip()
        ing_name = raw_name.lower()
        is_light = any(g in ing_name for g in LIGHT_GARNISHES)
        base_weight = 0.5 if is_light else 1.0

        # Check if user has this ingredient or a close alias in pantry
        matched_pantry_item = None
        for p_name in pantry_names:
            if p_name in ing_name or ing_name in p_name:
                matched_pantry_item = p_name
                break

        # Check perishability boost
        is_perishable = bool(matched_pantry_item and matched_pantry_item in use_first)
        weight = base_weight * (1.5 if is_perishable else 1.0)
        total_weight += base_weight

        if matched_pantry_item:
            matched_weight += weight
            matched_names.append(raw_name)
            if is_perishable:
                rescued_use_first.append(raw_name)
        else:
            missing_names.append(raw_name)

    coverage_ratio = min(1.0, matched_weight / total_weight) if total_weight > 0 else 0.0
    return (
        round(coverage_ratio, 3),
        len(matched_names),
        len(recipe_ingredients),
        matched_names,
        missing_names,
        rescued_use_first,
    )


def calculate_ingredient_coverage(
    recipe_ingredients: List[Dict[str, Any]],
    pantry_names: Set[str],
    use_first_names: Optional[Set[str]] = None,
) -> Tuple[float, int, int]:
    """Calculate weighted coverage of available pantry items.

    Returns:
        (coverage_ratio, matched_count, total_count)
    """
    cov, matched_cnt, total_cnt, _, _, _ = calculate_detailed_coverage(
        recipe_ingredients, pantry_names, use_first_names
    )
    return cov, matched_cnt, total_cnt


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


def calculate_effort_match(recipe_effort: str, user_effort: Optional[str]) -> float:
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
    missing_ratio = (total_count - matched_count) / max(1, total_count)
    ingredient_feasibility = 1.0 - (0.7 * missing_ratio)

    time_str = recipe.get("time", "20 min")
    try:
        minutes = int("".join(filter(str.isdigit, time_str)) or 20)
    except Exception:
        minutes = 20

    time_factor = 1.0 if minutes <= 15 else 0.85 if minutes <= 30 else 0.70
    return round(0.6 * ingredient_feasibility + 0.4 * time_factor, 3)


def build_ai_reason(
    matched_cnt: int,
    total_cnt: int,
    missing_names: List[str],
    rescued_use_first: List[str],
    substitution: str,
    theme: str,
) -> str:
    """Generate dynamic, explainable reasoning for why this recipe was recommended."""
    if matched_cnt == total_cnt and total_cnt > 0:
        if rescued_use_first:
            rescued_str = ", ".join(rescued_use_first[:2])
            return f"100% fridge match! Rescues your {rescued_str} from the 'Use First' shelf for a low-waste {theme} meal."
        return f"100% fridge match! You already have all {total_cnt} ingredients ready for a low-waste {theme} meal."

    if len(missing_names) == 1:
        missing_item = missing_names[0]
        if substitution:
            return f"You have {matched_cnt} of {total_cnt} items for a low-waste match! Only missing {missing_item} (Swap: {substitution})."
        return f"You have {matched_cnt} of {total_cnt} items for a low-waste match! Only missing {missing_item}."

    if rescued_use_first:
        rescued_str = rescued_use_first[0]
        return f"Uses {matched_cnt} of {total_cnt} items and rescues {rescued_str} for a low-waste {theme} meal."

    return f"You have {matched_cnt} of {total_cnt} ingredients already for a low-waste {theme} meal."


def generate_recipe_badges(
    recipe: Dict[str, Any],
    missing_names: List[str],
    rescued_use_first: List[str],
) -> List[str]:
    """Derive visual classification badges based on recipe attributes and match state."""
    badges = []

    # Perishability / Zero Waste Badge
    if len(missing_names) == 0 and rescued_use_first:
        badges.append("Zero Waste")
    elif len(missing_names) == 0:
        badges.append("Pantry Ready")

    # Time badge
    time_str = recipe.get("time", "20 min")
    try:
        minutes = int("".join(filter(str.isdigit, time_str)) or 20)
        if minutes <= 15:
            badges.append("Quick & Easy")
    except Exception:
        pass

    # Effort badge
    if recipe.get("effort") == "lazy":
        badges.append("Low Effort")

    # Dietary tags
    tags = recipe.get("tags", [])
    for tag in tags:
        if tag in ("High-protein", "Vegetarian", "Vegan", "Gluten-free") and tag not in badges:
            badges.append(tag)

    # Cuisine
    cuisine = recipe.get("cuisine")
    if cuisine and cuisine != "Global" and cuisine not in badges:
        badges.append(cuisine)

    return badges[:4]


def rank_recipes(
    recipes: List[Dict[str, Any]],
    pantry: List[IngredientItem],
    preferences: PreferencesInput,
    theme: str = "cozy",
) -> List[Dict[str, Any]]:
    """Rank candidate recipes using the transparent 4-signal hybrid formula with perishability prioritization."""
    pantry_names = {item.name.lower() for item in pantry}
    use_first_names = {item.name.lower() for item in pantry if getattr(item, "shelf", None) == "use_first"}
    scored_recipes = []

    for r in recipes:
        recipe_ing = r.get("ingredients", [])
        (
            coverage,
            matched_cnt,
            total_cnt,
            matched_names,
            missing_names,
            rescued_use_first,
        ) = calculate_detailed_coverage(recipe_ing, pantry_names, use_first_names)

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

        # Match percentage scaled between 60 and 99
        match_pct = int(min(99, max(60, round(composite * 100))))

        # Copy and attach metadata
        entry = dict(r)
        entry["match"] = match_pct
        entry["matched_count"] = matched_cnt
        entry["total_ingredients"] = total_cnt
        entry["matched_ingredients"] = matched_names
        entry["missing_ingredients"] = missing_names
        entry["rescued_use_first"] = rescued_use_first
        entry["composite_score"] = composite
        entry["ai_reason"] = build_ai_reason(
            matched_cnt, total_cnt, missing_names, rescued_use_first, r.get("substitution", ""), theme
        )
        entry["badges"] = generate_recipe_badges(r, missing_names, rescued_use_first)

        scored_recipes.append(entry)

    # Sort descending by composite score, then rating
    scored_recipes.sort(key=lambda x: (x["composite_score"], x["rating"]), reverse=True)
    return scored_recipes
