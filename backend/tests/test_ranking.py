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
