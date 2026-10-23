"""Comprehensive integration tests for culinary substitution and recipe adaptation flows."""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_lookup_substitutions_dairy():
    """Verify looking up substitutions for Milk returns valid alternatives."""
    resp = client.get("/api/recipes/substitutions/lookup?ingredient=milk")
    assert resp.status_code == 200
    options = resp.json()
    assert isinstance(options, list)
    assert len(options) >= 2
    sub_names = [o["substitute"].lower() for o in options]
    assert any("oat milk" in name for name in sub_names)
    assert any("almond milk" in name for name in sub_names)


def test_lookup_substitutions_paneer_and_tofu():
    """Verify paneer substitutes include extra-firm tofu with ratios and notes."""
    resp = client.get("/api/recipes/substitutions/lookup?ingredient=paneer")
    assert resp.status_code == 200
    options = resp.json()
    assert len(options) >= 2
    tofu_opt = next((o for o in options if "tofu" in o["substitute"].lower()), None)
    assert tofu_opt is not None
    assert tofu_opt["ratio"] == "1:1"
    assert "vegan" in tofu_opt.get("dietary_tags", [])


def test_lookup_substitutions_greens():
    """Verify spinach substitutions return leafy alternatives."""
    resp = client.get("/api/recipes/substitutions/lookup?ingredient=spinach")
    assert resp.status_code == 200
    options = resp.json()
    assert len(options) >= 1
    sub_names = [o["substitute"].lower() for o in options]
    assert any("kale" in name or "chard" in name or "peas" in name for name in sub_names)


def test_recipe_substitutions_list():
    """Verify GET /api/recipes/{id}/substitutions returns available swaps for recipe ingredients."""
    resp = client.get("/api/recipes/1/substitutions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_recipe_substitute_execution_and_step_adaptation():
    """Verify POST /api/recipes/{id}/substitute rewrites steps and attaches Swapped badge."""
    payload = {
        "replace": "Milk",
        "substitute_with": "Oat milk",
    }
    resp = client.post("/api/recipes/1/substitute", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "recipe" in data
    assert "applied_substitution" in data
    assert "message" in data

    recipe = data["recipe"]
    # Verify ingredient updated
    ing_names = [i["name"].lower() for i in recipe["ingredients"]]
    assert "oat milk" in ing_names
    assert "milk" not in ing_names

    # Verify Swapped badge is present
    badges = recipe.get("badges", [])
    assert any("Swapped" in b for b in badges)

    # Verify nutrition is calculable on the adapted recipe
    nutr_resp = client.get(f"/api/recipes/{recipe['id']}/nutrition?servings=2")
    assert nutr_resp.status_code == 200
    assert nutr_resp.json()["calories"] > 0


def test_substitute_nonexistent_recipe():
    """Verify substituting on a non-existent recipe returns 404."""
    payload = {
        "replace": "Milk",
        "substitute_with": "Oat milk",
    }
    resp = client.post("/api/recipes/999999/substitute", json=payload)
    assert resp.status_code == 404
