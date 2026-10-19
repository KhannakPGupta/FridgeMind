"""Service for dynamic, multi-cuisine LLM recipe synthesis using Gemini 2.0 Flash.

Synthesizes tailored recipes across diverse global cuisines matching the user's
specific pantry ingredients, dietary constraints, taste profile, and vibe theme.
Automatically indexes and caches every synthesized recipe in SQLite.
"""

import json
import re
from typing import List, Dict, Any, Optional
from google import genai

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.data.database import save_recipe
from backend.app.schemas.ingredients import IngredientItem
from backend.app.schemas.recipes import PreferencesInput


ACCENT_PALETTES = ["#FFD5C2", "#F5D66F", "#C9DCC5", "#F6C8D0"]

CUISINE_IMAGE_FALLBACKS = {
    "Italian": "https://images.unsplash.com/photo-1621996346565-e3d5d6281048?w=600&h=380&fit=crop&auto=format",
    "Mexican": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&h=380&fit=crop&auto=format",
    "Japanese": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=600&h=380&fit=crop&auto=format",
    "Chinese": "https://images.unsplash.com/photo-1541696432-82c6da8ce7bf?w=600&h=380&fit=crop&auto=format",
    "Thai": "https://images.unsplash.com/photo-1559847844-5315695dadae?w=600&h=380&fit=crop&auto=format",
    "Korean": "https://images.unsplash.com/photo-1590301157890-4810ed352733?w=600&h=380&fit=crop&auto=format",
    "Mediterranean": "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=600&h=380&fit=crop&auto=format",
    "French": "https://images.unsplash.com/photo-1510693206972-df098062cb71?w=600&h=380&fit=crop&auto=format",
    "American": "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=600&h=380&fit=crop&auto=format",
    "Indian": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=600&h=380&fit=crop&auto=format",
}

DEFAULT_IMAGE = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&h=380&fit=crop&auto=format"


async def generate_dynamic_recipes(
    pantry: List[IngredientItem],
    preferences: PreferencesInput,
    theme: str = "cozy",
    count: int = 2,
) -> List[Dict[str, Any]]:
    """Dynamically synthesize diverse, multi-cuisine recipes using Gemini based on available fridge items."""
    if not settings.GEMINI_API_KEY.strip() or not pantry:
        return []

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        pantry_list = ", ".join(f"{i.name} ({i.qty})" for i in pantry)
        tastes_str = ", ".join(preferences.tastes) if preferences.tastes else "balanced, savory"
        effort_str = preferences.effort or "easy"
        diets_str = ", ".join(preferences.diets) if preferences.diets else "none"

        prompt = f"""
You are an executive master chef and culinary AI.
Available ingredients in the user's fridge/pantry: {pantry_list}
Taste preference: {tastes_str}
Cooking effort level: {effort_str}
Dietary constraints: {diets_str}
Vibe theme: {theme}

Generate {count} distinct, authentic, highly rated recipes across DIFFERENT global cuisines (e.g. Italian, Mexican, East Asian, Mediterranean, Indian, Japanese, Continental).
Ensure maximum utilization of the user's available ingredients while keeping recipes practical and delicious.
You may include standard kitchen basics (cooking oil, salt, pepper, water).

Return ONLY a valid JSON array of {count} recipe objects: [{{...}}, {{...}}].
Each object must adhere strictly to this schema:
{{
  "name": "Distinct Authentic Recipe Name",
  "cuisine": "Cuisine Name (e.g. Italian, Mexican, Japanese, etc.)",
  "time": "e.g. 15 min",
  "difficulty": "Easy" or "Medium",
  "tags": ["Vegetarian", "High-protein", etc.],
  "desc": "One mouthwatering sentence describing the dish.",
  "cal": "e.g. 320 cal",
  "rating": 4.8,
  "accent": "#FFD5C2" or "#F5D66F" or "#C9DCC5" or "#F6C8D0",
  "servings": 2,
  "ingredients": [
    {{"name": "Ingredient 1", "amount": 2.0, "unit": "slices or g or ml or cloves"}},
    {{"name": "Ingredient 2", "amount": 100.0, "unit": "g"}}
  ],
  "steps": [
    "Step 1 instruction...",
    "Step 2 instruction...",
    "Step 3 instruction..."
  ],
  "stepTimers": [0, 180, 240],
  "substitution": "Easy swap suggestion if a key ingredient is missing.",
  "tastes": ["savory", "spicy" or tastes from: savory, spicy, sweet, tangy, creamy, fresh, comfort],
  "effort": "lazy" or "easy" or "chef"
}}

Output ONLY the raw JSON array with NO markdown quotes or commentary.
"""

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
        )

        text = response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n", "", text)
            text = re.sub(r"\n```$", "", text).strip()

        parsed = json.loads(text)
        recipe_list = parsed if isinstance(parsed, list) else [parsed]
        synthesized_recipes = []

        for idx, recipe_data in enumerate(recipe_list):
            if not isinstance(recipe_data, dict) or "name" not in recipe_data or "ingredients" not in recipe_data:
                continue

            cuisine = recipe_data.get("cuisine", "Global Fusion")
            recipe_data["cuisine"] = cuisine
            recipe_data["effort"] = recipe_data.get("effort", preferences.effort or "easy")
            recipe_data["tastes"] = recipe_data.get("tastes", preferences.tastes or ["savory"])
            recipe_data["accent"] = recipe_data.get("accent") or ACCENT_PALETTES[idx % len(ACCENT_PALETTES)]
            recipe_data["image"] = recipe_data.get("image") or CUISINE_IMAGE_FALLBACKS.get(cuisine, DEFAULT_IMAGE)
            recipe_data["stepTimers"] = recipe_data.get("stepTimers") or [0] * len(recipe_data.get("steps", []))
            recipe_data["step_timers"] = recipe_data["stepTimers"]

            # Automatically persist into SQLite catalog
            try:
                persisted_id = save_recipe(recipe_data, source="gemini_dynamic")
                recipe_data["id"] = persisted_id if persisted_id > 0 else (900 + idx)
                logger.info("Persisted dynamic Gemini recipe '%s' (ID %d) to SQLite catalog", recipe_data["name"], recipe_data["id"])
            except Exception as db_exc:
                logger.warning("Could not persist dynamic recipe to database: %s", db_exc)
                recipe_data["id"] = 900 + idx

            synthesized_recipes.append(recipe_data)

        return synthesized_recipes

    except Exception as exc:
        logger.warning("Dynamic LLM recipe generation failed or skipped: %s", exc)
        return []


async def generate_custom_recipe_with_llm(
    pantry: List[IngredientItem],
    preferences: PreferencesInput,
    theme: str = "cozy",
) -> Optional[Dict[str, Any]]:
    """Backward-compatible single recipe synthesis wrapper."""
    recipes = await generate_dynamic_recipes(pantry, preferences, theme, count=1)
    return recipes[0] if recipes else None
