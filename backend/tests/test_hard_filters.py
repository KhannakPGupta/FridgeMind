"""Unit tests for dietary and allergy hard filters."""

from backend.app.ml.hard_filters import is_recipe_diet_compliant, filter_recipes_by_diet


def test_vegetarian_hard_filter():
    """Verify meat ingredients are excluded for vegetarian requests."""
    veg_recipe = {
        "name": "Paneer Bhurji",
        "tags": ["Vegetarian"],
        "ingredients": [{"name": "Paneer"}, {"name": "Onion"}, {"name": "Tomato"}],
    }
    non_veg_recipe = {
        "name": "Chicken Curry",
        "tags": ["Non-Veg"],
        "ingredients": [{"name": "Chicken"}, {"name": "Onion"}],
    }

    assert is_recipe_diet_compliant(veg_recipe, ["veg"]) is True
    assert is_recipe_diet_compliant(non_veg_recipe, ["veg"]) is False


def test_dairy_free_hard_filter():
    """Verify dairy items like milk, cheese, paneer, and butter are excluded."""
    dairy_recipe = {
        "name": "Cheesy Bruschetta",
        "tags": ["Vegetarian"],
        "ingredients": [{"name": "Bread"}, {"name": "Cheese"}, {"name": "Butter"}],
    }
    dairy_free_recipe = {
        "name": "Tomato Rasam",
        "tags": ["Vegan"],
        "ingredients": [{"name": "Tomato"}, {"name": "Garlic"}, {"name": "Cooking Oil"}],
    }

    assert is_recipe_diet_compliant(dairy_recipe, ["df"]) is False
    assert is_recipe_diet_compliant(dairy_free_recipe, ["df"]) is True


def test_gluten_free_hard_filter():
    """Verify wheat, bread, and pasta are excluded for gluten-free requests."""
    pasta_recipe = {
        "name": "Garlic Pasta",
        "tags": ["Vegetarian"],
        "ingredients": [{"name": "Pasta"}, {"name": "Garlic"}, {"name": "Olive Oil"}],
    }
    rice_recipe = {
        "name": "Aloo Jeera",
        "tags": ["Gluten-free"],
        "ingredients": [{"name": "Potato"}, {"name": "Cumin Seeds"}],
    }

    assert is_recipe_diet_compliant(pasta_recipe, ["gf"]) is False
    assert is_recipe_diet_compliant(rice_recipe, ["gf"]) is True
