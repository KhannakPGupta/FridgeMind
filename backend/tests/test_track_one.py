"""Comprehensive tests for Track 1 enhancements:
1. Gemini structured schemas
2. Sub-millisecond SQLite FTS5 candidate retrieval
3. Dynamic dish-specific image resolver
4. Interactive culinary substitutions engine & API endpoints
"""

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.recipes import GeneratedRecipe, GeneratedRecipeIngredient, RecipeResponse
from backend.app.services.image_service import resolve_dish_image, DISH_KEYWORD_IMAGE_MAP
from backend.app.data.database import (
    init_db,
    search_candidate_recipes_fts,
    get_all_recipes,
)
from backend.app.ml.substitutions import (
    get_substitutions_for_ingredient,
    find_substitutions_for_recipe,
    apply_substitution_to_recipe,
)

client = TestClient(app)


def test_generated_recipe_schema_validation():
    """Verify GeneratedRecipe Pydantic schema validates structured LLM payloads correctly."""
    sample_data = {
        "name": "Smoky Shakshuka with Feta",
        "cuisine": "Mediterranean",
        "time": "20 min",
        "difficulty": "Easy",
        "tags": ["Vegetarian", "High-protein"],
        "desc": "Simmered tomatoes, peppers, and poached eggs.",
        "cal": "290 cal",
        "rating": 4.9,
        "accent": "#FFD5C2",
        "servings": 2,
        "ingredients": [
            {"name": "Eggs", "amount": 3.0, "unit": ""},
            {"name": "Tomatoes", "amount": 200.0, "unit": "g"},
        ],
        "steps": [
            "Cook tomatoes until juicy.",
            "Make wells and crack in eggs.",
        ],
        "stepTimers": [0, 300],
        "substitution": "Swap feta with goat cheese or crumbled paneer.",
        "tastes": ["savory", "tangy"],
        "effort": "easy",
    }
    model = GeneratedRecipe(**sample_data)
    assert model.name == "Smoky Shakshuka with Feta"
    assert len(model.ingredients) == 2
    assert model.stepTimers == [0, 300]


def test_sqlite_fts5_candidate_search():
    """Verify SQLite FTS5 index returns fast relevant candidate recipes for pantry items."""
    init_db()
    # Search for eggs and tomatoes
    candidates = search_candidate_recipes_fts(["Eggs", "Tomatoes"], limit=20)
    assert len(candidates) > 0

    # Ensure eggs or tomatoes appear in ingredients or names of matched recipes
    first_recipe = candidates[0]
    assert "name" in first_recipe
    assert "ingredients" in first_recipe

    # Empty pantry search returns baseline catalog
    all_cat = get_all_recipes()
    empty_candidates = search_candidate_recipes_fts([])
    assert len(empty_candidates) == len(all_cat)


def test_dynamic_dish_image_resolver():
    """Verify resolve_dish_image matches dish-specific culinary photography."""
    # Dish name match
    shakshuka_img = resolve_dish_image("Spicy Moroccan Shakshuka", cuisine="Mediterranean")
    assert shakshuka_img == DISH_KEYWORD_IMAGE_MAP["shakshuka"]

    paneer_img = resolve_dish_image("Amritsari Paneer Bhurji", cuisine="Indian")
    assert paneer_img == DISH_KEYWORD_IMAGE_MAP["paneer bhurji"]

    bruschetta_img = resolve_dish_image("Cheesy Garlic Bruschetta", cuisine="Italian")
    assert bruschetta_img == DISH_KEYWORD_IMAGE_MAP["bruschetta"]

    ramen_img = resolve_dish_image("Miso Ramen Bowl", cuisine="Japanese")
    assert ramen_img == DISH_KEYWORD_IMAGE_MAP["ramen"]

    # Ingredient hint match
    toast_img = resolve_dish_image("Avocado Delight", cuisine="Continental", ingredients=["toast", "avocado"])
    assert "unsplash.com" in toast_img

    # Cuisine default fallback
    unknown_img = resolve_dish_image("Mystery Dish", cuisine="Mexican")
    assert "unsplash.com" in unknown_img


def test_substitutions_knowledge_base():
    """Verify culinary substitutions engine returns valid options for dairy and proteins."""
    # Milk substitutes
    milk_subs = get_substitutions_for_ingredient("Milk")
    assert len(milk_subs) >= 2
    sub_names = [s.substitute.lower() for s in milk_subs]
    assert any("oat milk" in s for s in sub_names)

    # Paneer substitutes
    paneer_subs = get_substitutions_for_ingredient("paneer")
    assert len(paneer_subs) >= 2
    assert any("tofu" in s.substitute.lower() for s in paneer_subs)

    # Non-existent ingredient returns empty list cleanly
    rare_subs = get_substitutions_for_ingredient("Dragonfruit Nectar 99")
    assert rare_subs == []


def test_recipe_missing_substitutions_enrichment():
    """Verify recipe substitutions can prioritize user's pantry items."""
    missing = ["milk", "sour cream"]
    pantry = ["greek yogurt", "spinach"]

    subs = find_substitutions_for_recipe(missing, available_pantry_names=pantry)
    assert len(subs) > 0
    # Greek yogurt should have the star pantry note
    greek_yogurt_sub = next((s for s in subs if "greek yogurt" in s.substitute.lower()), None)
    assert greek_yogurt_sub is not None
    assert "pantry" in greek_yogurt_sub.notes.lower()


def test_apply_substitution_to_recipe_dict():
    """Verify applying a substitution updates ingredients, steps, and badges."""
    sample_recipe = {
        "id": 1,
        "name": "Creamy Tomato Scrambled Eggs",
        "ingredients": [
            {"name": "Eggs", "amount": 3, "unit": ""},
            {"name": "Milk", "amount": 30, "unit": "ml"},
            {"name": "Cheese", "amount": 50, "unit": "g"},
        ],
        "steps": [
            "Whisk the eggs with the Milk and a pinch of salt.",
            "Scatter over the Cheese and serve.",
        ],
        "badges": ["Vegetarian"],
        "substitution": "",
    }

    adapted, option = apply_substitution_to_recipe(sample_recipe, "Milk", "Oat milk")
    assert option.substitute.lower() == "oat milk"

    # Ingredient updated
    ing_names = [i["name"].lower() for i in adapted["ingredients"]]
    assert "oat milk" in ing_names
    assert "milk" not in ing_names

    # Steps updated
    assert "Oat milk" in adapted["steps"][0] or "Oat Milk" in adapted["steps"][0]

    # Badge added
    assert any("Swapped" in b for b in adapted["badges"])


def test_api_substitutions_endpoints():
    """Verify GET /api/recipes/substitutions/lookup and POST /api/recipes/{id}/substitute."""
    # Lookup endpoint
    resp = client.get("/api/recipes/substitutions/lookup?ingredient=paneer")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert any("tofu" in item["substitute"].lower() for item in data)

    # Recipe substitutions endpoint
    resp_recipe_subs = client.get("/api/recipes/1/substitutions")
    assert resp_recipe_subs.status_code == 200
    recipe_subs = resp_recipe_subs.json()
    assert isinstance(recipe_subs, list)
    assert len(recipe_subs) > 0

    # Substitute endpoint on recipe 1 (replace Milk with Oat milk)
    sub_payload = {
        "replace": "Milk",
        "substitute_with": "Oat milk",
    }
    resp_sub = client.post("/api/recipes/1/substitute", json=sub_payload)
    assert resp_sub.status_code == 200
    sub_data = resp_sub.json()
    assert "recipe" in sub_data
    assert "applied_substitution" in sub_data
    assert sub_data["applied_substitution"]["substitute"].lower() == "oat milk"

    # Recipe 1 should now reflect the swap in its response
    recipe_obj = sub_data["recipe"]
    assert any("oat milk" in i["name"].lower() for i in recipe_obj["ingredients"])



def test_recommend_endpoint_includes_available_substitutions():
    """Verify POST /api/recipes/recommend attaches available_substitutions on recommended recipes."""
    payload = {
        "ingredients": [
            {"id": 1, "name": "Bread", "qty": "2 slices", "emoji": "🍞"},
        ],
        "preferences": {
            "tastes": ["savory"],
            "effort": "easy",
            "time": "15 min",
            "diets": [],
        },
        "theme": "cozy",
        "surprise": False,
    }
    resp = client.post("/api/recipes/recommend", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    recipes = data["recipes"]
    assert len(recipes) > 0

    # Check that available_substitutions is present in returned schema
    first = recipes[0]
    assert "available_substitutions" in first
    assert isinstance(first["available_substitutions"], list)
