"""Integration tests for recipe and recommendation API endpoints."""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_recommend_recipes_endpoint():
    """Verify POST /api/recipes/recommend returns ranked recipes with match scores."""
    payload = {
        "ingredients": [
            {"id": 1, "name": "Eggs", "qty": "4", "emoji": "🥚"},
            {"id": 2, "name": "Tomatoes", "qty": "2", "emoji": "🍅"},
            {"id": 3, "name": "Spinach", "qty": "1 bunch", "emoji": "🥬"},
        ],
        "preferences": {
            "tastes": ["savory"],
            "effort": "easy",
            "time": "20 min",
            "diets": ["veg"],
        },
        "theme": "cozy",
        "surprise": False,
    }
    response = client.post("/api/recipes/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "recipes" in data
    assert len(data["recipes"]) > 0
    assert data["total_found"] > 0

    first = data["recipes"][0]
    assert "name" in first
    assert "match" in first
    assert "ai_reason" in first
    assert "stepTimers" in first
    assert isinstance(first["stepTimers"], list)


def test_recommend_recipes_surprise_mode():
    """Verify surprise option returns valid randomized recommendation."""
    payload = {
        "ingredients": [
            {"id": 1, "name": "Bread", "qty": "4", "emoji": "🍞"},
            {"id": 2, "name": "Cheese", "qty": "100g", "emoji": "🧀"},
        ],
        "preferences": {
            "tastes": [],
            "effort": None,
            "time": None,
            "diets": [],
        },
        "theme": "spicy",
        "surprise": True,
    }
    response = client.post("/api/recipes/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["recipes"]) > 0
    assert data["source"] == "surprise_sampler"


def test_get_recipe_by_id():
    """Verify GET /api/recipes/{id} returns recipe details."""
    response = client.get("/api/recipes/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Creamy Tomato Scrambled Eggs"

    # Non-existent ID
    response_404 = client.get("/api/recipes/999999")
    assert response_404.status_code == 404


def test_get_recipe_nutrition():
    """Verify GET /api/recipes/{id}/nutrition returns calculated macros."""
    response = client.get("/api/recipes/1/nutrition?servings=2")
    assert response.status_code == 200
    data = response.json()
    assert data["servings"] == 2
    assert data["calories"] > 0
    assert data["protein_g"] > 0
    assert "USDA" in data["basis"]


def test_catalog_stats_endpoint():
    """Verify GET /api/recipes/catalog/stats returns database size and cuisine distribution."""
    response = client.get("/api/recipes/catalog/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_recipes" in data
    assert data["total_recipes"] >= 100
    assert "by_cuisine" in data
    assert "Indian" in data["by_cuisine"]
    assert "Italian" in data["by_cuisine"]


def test_expand_catalog_endpoint_safe_fallback():
    """Verify POST /api/recipes/expand-catalog runs safely even without API key."""
    response = client.post("/api/recipes/expand-catalog?cuisines=Italian&count_per_cuisine=1")
    assert response.status_code == 200
    data = response.json()
    assert "added_count" in data
    assert "total_catalog_size" in data

