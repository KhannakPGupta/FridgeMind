"""Smart Culinary Substitutions Engine for FridgeMind.

Provides authentic culinary swaps for missing pantry items, dietary adaptations,
and on-the-fly recipe modifications with ratio scaling and cooking tips.
"""

from typing import List, Dict, Any, Optional, Tuple
import re

from backend.app.schemas.recipes import SubstitutionOption
from backend.app.ml.normalizer import normalize_ingredient_name


# Comprehensive culinary substitution dictionary
# Key: canonical / common ingredient name
CULINARY_SUBSTITUTION_DATA: Dict[str, List[Dict[str, Any]]] = {
    # Dairy & Alternatives
    "milk": [
        {
            "substitute": "Oat milk",
            "ratio": "1:1",
            "flavor_impact": "slightly sweet, creamy",
            "notes": "Excellent 1:1 substitute in both baking and savory cooking.",
            "dietary_tags": ["vegan", "dairy-free"],
        },
        {
            "substitute": "Almond milk",
            "ratio": "1:1",
            "flavor_impact": "subtle nutty",
            "notes": "Use unsweetened almond milk for savory dishes like curries and sauces.",
            "dietary_tags": ["vegan", "dairy-free"],
        },
        {
            "substitute": "Water + Butter",
            "ratio": "1 cup water + 1 tbsp melted butter",
            "flavor_impact": "neutral, rich",
            "notes": "Quick pantry trick for pan-frying or thinning sauces when milk is out.",
            "dietary_tags": ["vegetarian"],
        },
    ],
    "paneer": [
        {
            "substitute": "Extra-firm Tofu",
            "ratio": "1:1",
            "flavor_impact": "neutral, absorbs spices",
            "notes": "Press well to remove excess water. Golden pan-fry for authentic texture in bhurji or palak.",
            "dietary_tags": ["vegan", "dairy-free", "high-protein"],
        },
        {
            "substitute": "Halloumi",
            "ratio": "1:1",
            "flavor_impact": "salty, savory",
            "notes": "Holds shape excellently when grilled or pan-fried. Reduce added salt in the recipe.",
            "dietary_tags": ["vegetarian"],
        },
        {
            "substitute": "Ricotta",
            "ratio": "1:1",
            "flavor_impact": "creamy, mild",
            "notes": "Ideal for bhurji-style scrambles; drain lightly before tossing in skillet.",
            "dietary_tags": ["vegetarian"],
        },
    ],
    "heavy cream": [
        {
            "substitute": "Coconut cream",
            "ratio": "1:1",
            "flavor_impact": "rich, mild coconut aroma",
            "notes": "Great for curries, soups, and creamy sauces.",
            "dietary_tags": ["vegan", "dairy-free"],
        },
        {
            "substitute": "Cashew cream",
            "ratio": "1:1 (soaked cashews blended with water)",
            "flavor_impact": "luxuriously smooth, neutral",
            "notes": "Blend 1/2 cup raw cashews with 1/2 cup warm water until silky.",
            "dietary_tags": ["vegan", "dairy-free"],
        },
        {
            "substitute": "Milk + Butter",
            "ratio": "3/4 cup milk + 1/4 cup melted butter",
            "flavor_impact": "rich dairy",
            "notes": "Whisk thoroughly. Works for cooking and simmering (do not whip).",
            "dietary_tags": ["vegetarian"],
        },
    ],
    "sour cream": [
        {
            "substitute": "Greek yogurt",
            "ratio": "1:1",
            "flavor_impact": "tangy, creamy",
            "notes": "Direct 1:1 swap with higher protein and lower fat. Add off heat to prevent curdling.",
            "dietary_tags": ["vegetarian", "high-protein"],
        },
        {
            "substitute": "Hung curd",
            "ratio": "1:1",
            "flavor_impact": "rich, tangy",
            "notes": "Strain plain yogurt through cheesecloth for 20 mins for identical consistency.",
            "dietary_tags": ["vegetarian"],
        },
    ],
    "curd": [
        {
            "substitute": "Plain Greek yogurt",
            "ratio": "1:1",
            "flavor_impact": "rich, tart",
            "notes": "Whisk lightly with a splash of water for perfect marinade or raita texture.",
            "dietary_tags": ["vegetarian"],
        },
        {
            "substitute": "Coconut yogurt",
            "ratio": "1:1",
            "flavor_impact": "mild coconut tang",
            "notes": "Plant-based alternative that holds up well in spiced marinades.",
            "dietary_tags": ["vegan", "dairy-free"],
        },
    ],
    "cheese": [
        {
            "substitute": "Nutritional yeast",
            "ratio": "2 tbsp per 1/2 cup cheese",
            "flavor_impact": "cheesy, savory umami",
            "notes": "Sprinkle over pastas, scrambled eggs, or roasted vegetables for instant cheesy depth.",
            "dietary_tags": ["vegan", "dairy-free", "gluten-free"],
        },
        {
            "substitute": "Crumbled Paneer",
            "ratio": "1:1",
            "flavor_impact": "mild, fresh dairy",
            "notes": "Adds soft creaminess and protein to toppings and fillings.",
            "dietary_tags": ["vegetarian", "high-protein"],
        },
    ],
    "butter": [
        {
            "substitute": "Olive oil",
            "ratio": "3/4 tbsp oil per 1 tbsp butter",
            "flavor_impact": "fruity, savory",
            "notes": "Ideal for sautéing, pasta tossing, and pan roasting.",
            "dietary_tags": ["vegan", "dairy-free"],
        },
        {
            "substitute": "Ghee (Clarified butter)",
            "ratio": "1:1",
            "flavor_impact": "nutty, aromatic",
            "notes": "Higher smoke point, perfect for searing, tempering spices, and high-heat cooking.",
            "dietary_tags": ["vegetarian"],
        },
    ],

    # Eggs & Bindings
    "eggs": [
        {
            "substitute": "Flax egg",
            "ratio": "1 tbsp ground flaxseed + 2.5 tbsp water per egg",
            "flavor_impact": "mild nutty",
            "notes": "Let rest for 5 minutes until gelatinous. Perfect binder for patties, chillas, and baking.",
            "dietary_tags": ["vegan", "gluten-free"],
        },
        {
            "substitute": "Silken tofu",
            "ratio": "1/4 cup blended tofu per egg",
            "flavor_impact": "neutral, smooth",
            "notes": "Provides moisture and protein without altering flavor profile.",
            "dietary_tags": ["vegan", "dairy-free", "high-protein"],
        },
        {
            "substitute": "Chickpea flour (Besan) slurry",
            "ratio": "2 tbsp besan + 2 tbsp water per egg",
            "flavor_impact": "earthy, savory",
            "notes": "Golden binding batter ideal for pan-fried savory snacks and coatings.",
            "dietary_tags": ["vegan", "gluten-free"],
        },
    ],

    # Pantry Staples & Aromatics
    "soy sauce": [
        {
            "substitute": "Tamari",
            "ratio": "1:1",
            "flavor_impact": "deep umami, less salty",
            "notes": "Naturally gluten-free Japanese brewed alternative with rich umami.",
            "dietary_tags": ["gluten-free", "vegan"],
        },
        {
            "substitute": "Coconut aminos",
            "ratio": "1:1",
            "flavor_impact": "slightly sweet, savory",
            "notes": "Soy-free and lower sodium alternative.",
            "dietary_tags": ["soy-free", "vegan"],
        },
    ],
    "garlic": [
        {
            "substitute": "Garlic powder",
            "ratio": "1/8 tsp powder per clove",
            "flavor_impact": "concentrated garlic savory",
            "notes": "Whisk into liquids or rubs; doesn't burn as easily as fresh garlic.",
            "dietary_tags": ["vegan", "gluten-free"],
        },
        {
            "substitute": "Asafoetida (Hing)",
            "ratio": "1 pinch per 2 cloves garlic",
            "flavor_impact": "pungent onion-garlic aroma",
            "notes": "Bloom briefly in hot oil/ghee for authentic Ayurvedic digestive flavor.",
            "dietary_tags": ["vegetarian"],
        },
        {
            "substitute": "Shallots",
            "ratio": "1 small shallot per 2 cloves garlic",
            "flavor_impact": "sweet, subtle garlic-onion",
            "notes": "Mince finely and sauté gently.",
            "dietary_tags": ["vegan"],
        },
    ],
    "ginger": [
        {
            "substitute": "Ground ginger powder",
            "ratio": "1/4 tsp powder per 1 tbsp fresh minced ginger",
            "flavor_impact": "warm, peppery",
            "notes": "Add with dry spices rather than aromatics.",
            "dietary_tags": ["vegan", "gluten-free"],
        },
    ],
    "lemon": [
        {
            "substitute": "Apple cider vinegar",
            "ratio": "1/2 tbsp vinegar per 1 tbsp lemon juice",
            "flavor_impact": "bright, fruity acidity",
            "notes": "Provides the essential acidic lift in dressings, curries, and marinades.",
            "dietary_tags": ["vegan", "gluten-free"],
        },
        {
            "substitute": "Amchur (Dry mango powder)",
            "ratio": "1/2 tsp per 1 tbsp lemon juice",
            "flavor_impact": "sour, fruity tang",
            "notes": "Classic Indian pantry staple for dry tang without adding excess moisture.",
            "dietary_tags": ["vegan", "gluten-free"],
        },
    ],
    "tomatoes": [
        {
            "substitute": "Tomato paste + Water",
            "ratio": "2 tbsp paste + 1/4 cup water per medium tomato",
            "flavor_impact": "rich, concentrated umami",
            "notes": "Cook paste in hot oil first to caramelize natural sugars.",
            "dietary_tags": ["vegan", "gluten-free"],
        },
        {
            "substitute": "Red bell pepper puree",
            "ratio": "1:1",
            "flavor_impact": "sweet, vibrant, slightly smoky",
            "notes": "Wonderful nightshade-sensitive alternative with beautiful red color.",
            "dietary_tags": ["vegan", "gluten-free"],
        },
    ],
    "breadcrumbs": [
        {
            "substitute": "Rolled oats (crushed)",
            "ratio": "1:1",
            "flavor_impact": "nutty, wholesome",
            "notes": "Pulse in blender until coarse. Binds meatballs and burger patties firmly.",
            "dietary_tags": ["vegan", "high-fiber"],
        },
        {
            "substitute": "Crushed crackers or cornflakes",
            "ratio": "1:1",
            "flavor_impact": "extra crispy, salty",
            "notes": "Yields an extra-crispy pan-fried crust.",
            "dietary_tags": ["vegetarian"],
        },
    ],
    "spinach": [
        {
            "substitute": "Kale",
            "ratio": "1:1 (destemmed)",
            "flavor_impact": "earthy, hearty",
            "notes": "Cook for 2 minutes longer to tenderize hearty leaves.",
            "dietary_tags": ["vegan", "gluten-free"],
        },
        {
            "substitute": "Fenugreek leaves (Methi)",
            "ratio": "1/2 ratio (stronger flavor)",
            "flavor_impact": "aromatic, mildly bitter",
            "notes": "Adds deep authentic flavor to egg scrambles, dals, and paneer curries.",
            "dietary_tags": ["vegan", "gluten-free"],
        },
    ],
}


def find_canonical_key(name: str) -> Optional[str]:
    """Match an ingredient name to our substitution database keys."""
    clean = normalize_ingredient_name(name).lower()
    if clean in CULINARY_SUBSTITUTION_DATA:
        return clean

    # Partial/token matching
    tokens = clean.split()
    for token in tokens:
        if token in CULINARY_SUBSTITUTION_DATA:
            return token

    # Check plural / alias mappings
    singular = clean.rstrip("s")
    if singular in CULINARY_SUBSTITUTION_DATA:
        return singular

    return None


def get_substitutions_for_ingredient(ingredient_name: str) -> List[SubstitutionOption]:
    """Retrieve all feasible culinary substitution options for a given ingredient."""
    key = find_canonical_key(ingredient_name)
    if not key:
        return []

    options = []
    for item in CULINARY_SUBSTITUTION_DATA[key]:
        options.append(
            SubstitutionOption(
                original=ingredient_name.strip().title(),
                substitute=item["substitute"],
                ratio=item["ratio"],
                flavor_impact=item["flavor_impact"],
                notes=item["notes"],
                dietary_tags=item.get("dietary_tags", []),
            )
        )
    return options


def find_substitutions_for_recipe(
    missing_ingredients: List[str],
    available_pantry_names: Optional[List[str]] = None,
) -> List[SubstitutionOption]:
    """Find smart substitutions for ingredients missing from the recipe."""
    results: List[SubstitutionOption] = []
    pantry_set = {p.lower() for p in (available_pantry_names or [])}

    for missing in missing_ingredients:
        subs = get_substitutions_for_ingredient(missing)
        for s in subs:
            # Prioritize substitutions already present in the user's pantry
            if s.substitute.lower() in pantry_set:
                s.notes = f"⭐ You have this in your pantry! {s.notes}"
            results.append(s)

    return results


def apply_substitution_to_recipe(
    recipe: Dict[str, Any],
    replace_ingredient: str,
    with_substitute: str,
) -> Tuple[Dict[str, Any], Optional[SubstitutionOption]]:
    """Adapt a recipe by replacing an ingredient in ingredients, steps, and tags."""
    adapted = dict(recipe)
    target_clean = replace_ingredient.strip().lower()
    sub_clean = with_substitute.strip().title()

    applied_option = None
    subs = get_substitutions_for_ingredient(replace_ingredient)
    for s in subs:
        if s.substitute.lower() == with_substitute.lower():
            applied_option = s
            break

    if not applied_option:
        applied_option = SubstitutionOption(
            original=replace_ingredient.title(),
            substitute=sub_clean,
            ratio="1:1",
            flavor_impact="adapted",
            notes=f"Substituted {replace_ingredient} with {sub_clean}.",
            dietary_tags=[],
        )

    # 1. Update ingredients list
    new_ingredients = []
    for ing in adapted.get("ingredients", []):
        ing_dict = dict(ing) if isinstance(ing, dict) else ing.model_dump()
        if target_clean in ing_dict.get("name", "").lower():
            ing_dict["name"] = sub_clean
        new_ingredients.append(ing_dict)
    adapted["ingredients"] = new_ingredients

    # 2. Update steps text
    new_steps = []
    pattern = re.compile(rf"\b{re.escape(replace_ingredient)}\b", re.IGNORECASE)
    for step in adapted.get("steps", []):
        updated_step = pattern.sub(sub_clean, step)
        new_steps.append(updated_step)
    adapted["steps"] = new_steps

    # 3. Add visual adaptation badge
    badges = list(adapted.get("badges", []))
    swap_badge = f"Swapped: {sub_clean}"
    if swap_badge not in badges:
        badges.insert(0, swap_badge)
    adapted["badges"] = badges[:4]

    # 4. Update substitution note
    adapted["substitution"] = f"Using {sub_clean} in place of {replace_ingredient.title()} ({applied_option.ratio}). {applied_option.notes}"

    return adapted, applied_option
