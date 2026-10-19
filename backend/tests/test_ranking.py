"""Unit tests for hybrid ranking engine."""

from backend.app.ml.ranking import (
    calculate_ingredient_coverage,
    calculate_taste_match,
    calculate_effort_match,
    rank_recipes,
)
from backend.app.schemas.ingredients import IngredientItem
from backend.app.schemas.recipes import PreferencesInput


def test_coverage_calculation():
    """Verify coverage increases as more ingredients match."""
    ingredients = [
        {"name": "Eggs", "amount": 3, "unit": ""},
        {"name": "Tomatoes", "amount": 100, "unit": "g"},
        {"name": "Spinach", "amount": 50, "unit": "g"},
        {"name": "Salt", "amount": 1, "unit": "pinch"},
    ]
    pantry = {"eggs", "tomatoes"}

    ratio, matched_cnt, total_cnt = calculate_ingredient_coverage(ingredients, pantry)
    assert matched_cnt == 2
    assert total_cnt == 4
    assert 0.5 <= ratio <= 0.75


def test_taste_match():
    """Verify taste alignment matches user preferences."""
    recipe_tastes = ["spicy", "savory"]
    assert calculate_taste_match(recipe_tastes, ["spicy"]) >= 0.8
    assert calculate_taste_match(recipe_tastes, ["sweet"]) == 0.25
    assert calculate_taste_match(recipe_tastes, []) == 0.75  # neutral baseline


def test_effort_match():
    """Verify effort alignment matches user effort choices."""
    assert calculate_effort_match("lazy", "lazy") == 1.0
    assert calculate_effort_match("easy", "lazy") == 0.65
    assert calculate_effort_match("chef", "lazy") == 0.30


def test_rank_recipes_ordering():
    """Verify top ranked recipe has higher ingredient overlap and preference alignment."""
    recipes = [
        {
            "id": 1,
            "name": "Paneer Dish",
            "ingredients": [{"name": "Paneer"}, {"name": "Onion"}],
            "tastes": ["spicy"],
            "effort": "easy",
            "rating": 4.8,
            "time": "15 min",
        },
        {
            "id": 2,
            "name": "Mushroom Soup",
            "ingredients": [{"name": "Mushroom"}, {"name": "Cream"}],
            "tastes": ["comfort"],
            "effort": "easy",
            "rating": 4.5,
            "time": "25 min",
        },
    ]
    pantry = [
        IngredientItem(id=1, name="Paneer", qty="200g", emoji="🧀"),
        IngredientItem(id=2, name="Onion", qty="1", emoji="🧅"),
    ]
    pref = PreferencesInput(tastes=["spicy"], effort="easy")

    ranked = rank_recipes(recipes, pantry, pref)
    assert len(ranked) == 2
    assert ranked[0]["name"] == "Paneer Dish"
    assert ranked[0]["match"] >= ranked[1]["match"]
    assert "low-waste" in ranked[0]["ai_reason"]


def test_perishability_shelf_boost():
    """Verify ingredients in 'use_first' shelf boost recipe rank over stable pantry items."""
    recipes = [
        {
            "id": 1,
            "name": "Spinach Sauté",
            "ingredients": [{"name": "Spinach"}],
            "tastes": ["savory"],
            "effort": "easy",
            "rating": 4.5,
            "time": "10 min",
        },
        {
            "id": 2,
            "name": "Potato Roast",
            "ingredients": [{"name": "Potato"}],
            "tastes": ["savory"],
            "effort": "easy",
            "rating": 4.5,
            "time": "10 min",
        },
    ]
    # Spinach is expiring on the use_first shelf, Potato is shelf-stable
    pantry = [
        IngredientItem(id=1, name="Spinach", qty="100g", emoji="🥬", shelf="use_first"),
        IngredientItem(id=2, name="Potato", qty="2", emoji="🥔", shelf="fresh_finds"),
    ]
    pref = PreferencesInput(tastes=["savory"], effort="easy")

    ranked = rank_recipes(recipes, pantry, pref)
    # The spinach recipe must rank first because it rescues an expiring ingredient
    assert ranked[0]["name"] == "Spinach Sauté"
    assert "Spinach" in ranked[0]["rescued_use_first"]
    assert "Zero Waste" in ranked[0]["badges"]
    assert "Spinach" in ranked[0]["ai_reason"]


def test_missing_and_matched_ingredients_breakdown():
    """Verify matched and missing ingredient lists and badges are cleanly populated."""
    recipes = [
        {
            "id": 1,
            "name": "Avocado Toast",
            "ingredients": [{"name": "Bread"}, {"name": "Avocado"}, {"name": "Eggs"}],
            "tastes": ["fresh"],
            "effort": "easy",
            "rating": 4.9,
            "time": "10 min",
            "tags": ["Vegetarian", "High-protein"],
            "cuisine": "American",
            "substitution": "Sunny fried eggs work as well as poached eggs.",
        }
    ]
    pantry = [
        IngredientItem(id=1, name="Bread", qty="2 slices", emoji="🍞"),
        IngredientItem(id=2, name="Avocado", qty="1", emoji="🥑"),
    ]
    pref = PreferencesInput(tastes=["fresh"], effort="easy")

    ranked = rank_recipes(recipes, pantry, pref)
    recipe = ranked[0]
    assert "Bread" in recipe["matched_ingredients"]
    assert "Avocado" in recipe["matched_ingredients"]
    assert "Eggs" in recipe["missing_ingredients"]
    assert recipe["matched_count"] == 2
    assert recipe["total_ingredients"] == 3
    assert "Eggs" in recipe["ai_reason"]
    assert "Quick & Easy" in recipe["badges"]
    assert "High-protein" in recipe["badges"]

