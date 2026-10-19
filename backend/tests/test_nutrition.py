"""Unit tests for nutrition service."""

from backend.app.schemas.recipes import RecipeIngredient
from backend.app.services.nutrition_service import (
    calculate_recipe_nutrition,
    convert_ingredient_to_grams,
)


def test_convert_ingredient_to_grams():
    """Verify culinary unit conversion to approximate gram weights."""
    assert convert_ingredient_to_grams("Eggs", 2, "") == 100.0
    assert convert_ingredient_to_grams("Milk", 200, "ml") == 200.0
    assert convert_ingredient_to_grams("Bread", 2, "slices") == 70.0
    assert convert_ingredient_to_grams("Garlic", 2, "cloves") == 8.0
    assert convert_ingredient_to_grams("Paneer", 150, "g") == 150.0


def test_calculate_recipe_nutrition():
    """Verify nutrition aggregation divides properly by servings and returns transparency data."""
    ingredients = [
        RecipeIngredient(name="Eggs", amount=4, unit=""),
        RecipeIngredient(name="Spinach", amount=100, unit="g"),
        RecipeIngredient(name="Butter", amount=15, unit="g"),
    ]
    summary = calculate_recipe_nutrition(ingredients, servings=2)
    assert summary.servings == 2
    assert summary.calories > 100
    assert summary.protein_g > 5.0
    assert "USDA" in summary.basis
    assert len(summary.details) >= 4
    assert summary.macro_ratios is not None
    assert "protein_pct" in summary.macro_ratios
    assert "carbs_pct" in summary.macro_ratios
    assert "fat_pct" in summary.macro_ratios
    assert isinstance(summary.badges, list)
