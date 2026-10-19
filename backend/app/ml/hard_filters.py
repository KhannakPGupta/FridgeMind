"""Hard constraint filtering for dietary restrictions and food allergies."""

from typing import List, Dict, Any, Set

# Non-compliant ingredients for strict diets
DAIRY_INGREDIENTS = {"milk", "cheese", "paneer", "butter", "ghee", "curd", "yogurt", "cream"}
EGG_INGREDIENTS = {"egg", "eggs"}
GLUTEN_INGREDIENTS = {"bread", "flour", "pasta", "wheat flour", "atta", "maida", "all-purpose flour"}
MEAT_INGREDIENTS = {"chicken", "beef", "mutton", "fish", "salmon", "shrimp", "prawn", "pork"}


def is_recipe_diet_compliant(recipe: Dict[str, Any], selected_diets: List[str]) -> bool:
    """Check whether a recipe satisfies all user-selected dietary constraints."""
    if not selected_diets:
        return True

    tags_lower: Set[str] = {t.lower() for t in recipe.get("tags", [])}
    ingredients_lower: Set[str] = {
        item.get("name", "").lower() for item in recipe.get("ingredients", [])
    }

    for diet in selected_diets:
        d = diet.lower()

        # Vegetarian filter
        if d in ("veg", "vegetarian"):
            if any(meat in ing for meat in MEAT_INGREDIENTS for ing in ingredients_lower):
                return False

        # Vegan filter
        elif d in ("vegan",):
            if "vegan" not in tags_lower:
                if any(non_veg in ing for non_veg in (MEAT_INGREDIENTS | DAIRY_INGREDIENTS | EGG_INGREDIENTS) for ing in ingredients_lower):
                    return False

        # Dairy-free filter
        elif d in ("df", "dairy-free", "dairy_free"):
            if any(dairy in ing for dairy in DAIRY_INGREDIENTS for ing in ingredients_lower):
                return False

        # Egg-free filter
        elif d in ("ef", "egg-free", "egg_free"):
            if any(egg in ing for egg in EGG_INGREDIENTS for ing in ingredients_lower):
                return False

        # Gluten-free filter
        elif d in ("gf", "gluten-free", "gluten_free"):
            if "gluten-free" not in tags_lower:
                if any(gluten in ing for gluten in GLUTEN_INGREDIENTS for ing in ingredients_lower):
                    return False

    return True


def filter_recipes_by_diet(recipes: List[Dict[str, Any]], selected_diets: List[str]) -> List[Dict[str, Any]]:
    """Return only recipes that comply with all dietary constraints."""
    return [r for r in recipes if is_recipe_diet_compliant(r, selected_diets)]
