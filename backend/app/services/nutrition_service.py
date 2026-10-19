"""Nutritional calculation service using standard food composition values."""

import re
from typing import List, Dict, Any, Tuple
from backend.app.schemas.recipes import RecipeIngredient
from backend.app.schemas.nutrition import NutritionSummary, NutrientBreakdown

# Standard nutrient profiles per 100g (USDA FoodData Central baseline averages)
# Values: (Calories, Protein_g, Carbs_g, Fat_g, Fiber_g)
NUTRIENT_TABLE: Dict[str, Tuple[float, float, float, float, float]] = {
    # Dairy & Eggs
    "eggs": (143, 12.6, 0.7, 9.5, 0.0),
    "egg": (143, 12.6, 0.7, 9.5, 0.0),
    "milk": (61, 3.2, 4.8, 3.3, 0.0),
    "cheese": (350, 25.0, 1.3, 28.0, 0.0),
    "paneer": (296, 18.3, 3.4, 23.0, 0.0),
    "butter": (717, 0.9, 0.1, 81.0, 0.0),
    "ghee": (884, 0.0, 0.0, 99.5, 0.0),
    "yogurt": (59, 3.5, 4.7, 3.3, 0.0),
    "curd": (59, 3.5, 4.7, 3.3, 0.0),

    # Vegetables & Produce
    "tomatoes": (18, 0.9, 3.9, 0.2, 1.2),
    "tomato": (18, 0.9, 3.9, 0.2, 1.2),
    "spinach": (23, 2.9, 3.6, 0.4, 2.2),
    "garlic": (149, 6.4, 33.1, 0.5, 2.1),
    "onion": (40, 1.1, 9.3, 0.1, 1.7),
    "potato": (77, 2.0, 17.5, 0.1, 2.2),
    "carrot": (41, 0.9, 9.6, 0.2, 2.8),
    "mushroom": (22, 3.1, 3.3, 0.3, 1.0),
    "cucumber": (15, 0.7, 3.6, 0.1, 0.5),
    "bell pepper": (26, 1.0, 6.0, 0.3, 2.1),
    "lemon": (29, 1.1, 9.3, 0.3, 2.8),
    "avocado": (160, 2.0, 8.5, 14.7, 6.7),
    "green peas": (81, 5.4, 14.5, 0.4, 5.7),
    "coriander": (23, 2.1, 3.7, 0.5, 2.8),

    # Grains & Legumes
    "bread": (265, 9.0, 49.0, 3.2, 2.7),
    "pasta": (371, 13.0, 74.0, 1.5, 3.2),
    "spaghetti": (158, 5.8, 30.9, 0.9, 1.8),
    "penne": (158, 5.8, 30.9, 0.9, 1.8),
    "rice": (130, 2.7, 28.0, 0.3, 0.4),
    "poha": (350, 6.8, 77.0, 1.2, 1.5),
    "lentils": (116, 9.0, 20.0, 0.4, 7.9),
    "chickpeas": (164, 8.9, 27.4, 2.6, 7.6),
    "black beans": (132, 8.9, 23.7, 0.5, 8.7),
    "besan": (387, 22.0, 58.0, 6.7, 10.8),
    "oats": (389, 16.9, 66.3, 6.9, 10.6),
    "noodles": (138, 4.5, 25.0, 2.1, 1.2),
    "ramen": (138, 4.5, 25.0, 2.1, 1.2),
    "tortilla": (218, 5.7, 44.6, 2.8, 4.0),
    "corn": (86, 3.2, 19.0, 1.2, 2.0),

    # Asian & Plant Proteins
    "tofu": (76, 8.0, 1.9, 4.8, 0.3),
    "kimchi": (15, 1.1, 2.4, 0.5, 1.6),
    "miso": (199, 11.8, 26.5, 6.0, 5.4),
    "tahini": (595, 17.0, 21.2, 53.8, 9.3),
    "bok choy": (13, 1.5, 2.2, 0.2, 1.0),
    "eggplant": (25, 1.0, 6.0, 0.2, 3.0),
    "zucchini": (17, 1.2, 3.1, 0.3, 1.0),
    "scallion": (32, 1.8, 7.3, 0.2, 2.6),
    "scallions": (32, 1.8, 7.3, 0.2, 2.6),

    # Cheeses
    "feta": (264, 14.2, 4.1, 21.3, 0.0),
    "mozzarella": (280, 22.0, 2.2, 21.0, 0.0),
    "cheddar": (403, 24.9, 1.3, 33.1, 0.0),

    # Oils & Basics
    "olive oil": (884, 0.0, 0.0, 100.0, 0.0),
    "cooking oil": (884, 0.0, 0.0, 100.0, 0.0),
    "sesame oil": (884, 0.0, 0.0, 100.0, 0.0),
    "soy sauce": (53, 8.1, 4.9, 0.6, 0.8),
}


def convert_ingredient_to_grams(name: str, amount: float, unit: str) -> float:
    """Approximate weight in grams based on standard culinary unit conversions."""
    unit_clean = unit.strip().lower()
    name_clean = name.strip().lower()

    if unit_clean in ("g", "grams"):
        return amount
    if unit_clean in ("kg",):
        return amount * 1000.0
    if unit_clean in ("ml", "milliliters"):
        return amount  # density approx 1g/ml
    if unit_clean in ("l", "liter"):
        return amount * 1000.0
    if unit_clean in ("slices", "slice"):
        return amount * 35.0  # standard bread slice ~35g
    if unit_clean in ("cloves", "clove"):
        return amount * 4.0   # garlic clove ~4g
    if unit_clean in ("tbsp", "tablespoon"):
        return amount * 15.0
    if unit_clean in ("tsp", "teaspoon"):
        return amount * 5.0
    if unit_clean in ("cup", "cups"):
        return amount * 240.0
    if unit_clean in ("bunch",):
        return amount * 50.0

    # Piece counts
    if "egg" in name_clean:
        return amount * 50.0   # medium egg ~50g
    if "tomato" in name_clean:
        return amount * 80.0   # medium tomato ~80g
    if "onion" in name_clean:
        return amount * 110.0  # medium onion ~110g
    if "potato" in name_clean:
        return amount * 150.0  # medium potato ~150g
    if "lemon" in name_clean:
        return amount * 50.0

    return amount * 50.0  # default baseline per unit


def calculate_recipe_nutrition(
    ingredients: List[RecipeIngredient],
    servings: int = 2,
) -> NutritionSummary:
    """Aggregate total recipe nutrition and divide across specified servings."""
    total_cal = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0
    total_fiber = 0.0

    for item in ingredients:
        name_lower = item.name.lower()
        grams = convert_ingredient_to_grams(item.name, item.amount, item.unit)

        # Lookup in table or find substring match
        profile = None
        for key, vals in NUTRIENT_TABLE.items():
            if key in name_lower:
                profile = vals
                break

        if profile is None:
            # Conservative average estimate for miscellaneous produce/spices
            profile = (50.0, 1.0, 10.0, 0.5, 1.0)

        factor = grams / 100.0
        total_cal += profile[0] * factor
        total_protein += profile[1] * factor
        total_carbs += profile[2] * factor
        total_fat += profile[3] * factor
        total_fiber += profile[4] * factor

    servings_count = max(1, servings)
    per_serving_cal = int(round(total_cal / servings_count))
    per_serving_protein = round(total_protein / servings_count, 1)
    per_serving_carbs = round(total_carbs / servings_count, 1)
    per_serving_fat = round(total_fat / servings_count, 1)
    per_serving_fiber = round(total_fiber / servings_count, 1)

    details = [
        NutrientBreakdown(name="Calories", amount=float(per_serving_cal), unit="kcal"),
        NutrientBreakdown(name="Protein", amount=per_serving_protein, unit="g"),
        NutrientBreakdown(name="Carbohydrates", amount=per_serving_carbs, unit="g"),
        NutrientBreakdown(name="Fat", amount=per_serving_fat, unit="g"),
        NutrientBreakdown(name="Fiber", amount=per_serving_fiber, unit="g"),
    ]

    # Calculate Macro Energy Ratios
    macro_cal = (per_serving_protein * 4.0) + (per_serving_carbs * 4.0) + (per_serving_fat * 9.0)
    if macro_cal > 0:
        protein_pct = round((per_serving_protein * 4.0 / macro_cal) * 100, 1)
        carbs_pct = round((per_serving_carbs * 4.0 / macro_cal) * 100, 1)
        fat_pct = round((per_serving_fat * 9.0 / macro_cal) * 100, 1)
    else:
        protein_pct, carbs_pct, fat_pct = 0.0, 0.0, 0.0

    macro_ratios = {
        "protein_pct": protein_pct,
        "carbs_pct": carbs_pct,
        "fat_pct": fat_pct,
    }

    # Generate Dynamic Nutrition Badges
    badges = []
    if per_serving_protein >= 20.0 or protein_pct >= 25.0:
        badges.append(f"High Protein ({int(per_serving_protein)}g)")
    if per_serving_cal <= 300:
        badges.append("Low Calorie (<300 kcal)")
    if per_serving_fiber >= 4.0:
        badges.append("High Fiber")
    if per_serving_carbs <= 15.0 and per_serving_fat >= 12.0:
        badges.append("Keto Friendly")

    return NutritionSummary(
        calories=per_serving_cal,
        protein_g=per_serving_protein,
        carbs_g=per_serving_carbs,
        fat_g=per_serving_fat,
        fiber_g=per_serving_fiber,
        servings=servings_count,
        basis="Standard USDA FoodData Central composition tables",
        assumptions=f"Nutritional values calculated from raw ingredient weights divided by {servings_count} servings; cooking absorption and oil uptake may vary.",
        details=details,
        badges=badges,
        macro_ratios=macro_ratios,
    )
