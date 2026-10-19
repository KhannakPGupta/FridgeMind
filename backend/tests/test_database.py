"""Unit tests for SQLite recipe catalog."""

from backend.app.data.database import get_all_recipes, get_recipe_by_id
from backend.app.data.seed_data import seed_database


def test_database_contains_recipes():
    """Verify database contains seeded recipes with required fields."""
    seed_database()
    recipes = get_all_recipes()
    assert len(recipes) >= 16

    first = recipes[0]
    assert "id" in first
    assert "name" in first
    assert "time" in first
    assert "difficulty" in first
    assert "tags" in first
    assert "ingredients" in first
    assert "steps" in first
    assert "stepTimers" in first
    assert isinstance(first["stepTimers"], list)
    assert len(first["ingredients"]) > 0


def test_recipe_by_id():
    """Verify single recipe retrieval by ID."""
    recipe = get_recipe_by_id(1)
    assert recipe is not None
    assert recipe["name"] == "Creamy Tomato Scrambled Eggs"

    indian_recipe = get_recipe_by_id(5)
    assert indian_recipe is not None
    assert indian_recipe["cuisine"] == "Indian"
    assert "Paneer" in indian_recipe["name"]
