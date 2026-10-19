"""Service for structured LLM recipe generation and adaptation using Gemini 2.0 Flash."""

import json
import re
from typing import List, Dict, Any, Optional
from google import genai

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.ingredients import IngredientItem
from backend.app.schemas.recipes import PreferencesInput


ACCENT_PALETTES = ["#FFD5C2", "#F5D66F", "#C9DCC5", "#F6C8D0"]


async def generate_custom_recipe_with_llm(
    pantry: List[IngredientItem],
    preferences: PreferencesInput,
    theme: str = "cozy",
) -> Optional[Dict[str, Any]]:
    """Generate a tailored recipe using Google Gemini with strict schema enforcement."""
    if not settings.GEMINI_API_KEY.strip() or not pantry:
        return None

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        pantry_list = ", ".join(f"{i.name} ({i.qty})" for i in pantry)
        tastes_str = ", ".join(preferences.tastes) if preferences.tastes else "any"
        effort_str = preferences.effort or "easy"
        diets_str = ", ".join(preferences.diets) if preferences.diets else "none"

        prompt = f"""
You are an expert chef creating a delicious meal.
Available ingredients: {pantry_list}
Taste preference: {tastes_str}
Cooking effort: {effort_str}
Dietary constraints: {diets_str}
Vibe theme: {theme}

Design a practical, flavorful recipe that prioritizes the user's available ingredients.
You may include standard kitchen basics (salt, cooking oil, water).

Return ONLY a valid JSON object matching this schema:
{{
  "name": "Recipe Title",
  "time": "15 min",
  "difficulty": "Easy",
  "tags": ["Vegetarian", "High-protein"],
  "desc": "One-sentence appetizing description.",
  "image": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&h=380&fit=crop&auto=format",
  "cal": "320 cal",
  "rating": 4.9,
  "accent": "#FFD5C2",
  "servings": 2,
  "ingredients": [
    {{"name": "Ingredient Name", "amount": 2.0, "unit": "slices"}},
    {{"name": "Another Ingredient", "amount": 100.0, "unit": "g"}}
  ],
  "steps": [
    "Step 1 instruction...",
    "Step 2 instruction...",
    "Step 3 instruction..."
  ],
  "stepTimers": [0, 180, 240],
  "substitution": "Easy swap suggestion if an ingredient is missing."
}}

Output ONLY the raw JSON object with NO markdown quotes or commentary.
"""

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
        )

        text = response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n", "", text)
            text = re.sub(r"\n```$", "", text).strip()

        recipe_data = json.loads(text)
        recipe_data["id"] = 999  # dynamic AI recipe ID
        recipe_data["accent"] = recipe_data.get("accent") or ACCENT_PALETTES[0]
        recipe_data["stepTimers"] = recipe_data.get("stepTimers") or [0] * len(recipe_data.get("steps", []))
        return recipe_data

    except Exception as exc:
        logger.warning("LLM recipe generation failed or skipped: %s", exc)
        return None
