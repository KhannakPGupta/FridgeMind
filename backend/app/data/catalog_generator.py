"""Gemini-powered World Recipe Catalog Generator & Database Expander.

Generates structured, authentic multi-cuisine recipes and persists them into SQLite.
Can be executed as a CLI script or triggered via the API to scale the catalog to 100s or 1000s of recipes.
"""

import argparse
import asyncio
import json
import re
from typing import List, Dict, Any, Optional
from google import genai

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.data.database import bulk_insert_recipes, get_recipe_count, get_catalog_stats


CUISINES_LIST = [
    "Indian", "Italian", "Mexican", "Japanese", "Chinese", "Thai",
    "Korean", "Mediterranean", "Lebanese", "French", "Spanish", "Greek",
    "American", "Vietnamese", "Turkish"
]

CUISINE_IMAGE_MAP = {
    "Indian": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=600&h=380&fit=crop&auto=format",
    "Italian": "https://images.unsplash.com/photo-1621996346565-e3d5d6281048?w=600&h=380&fit=crop&auto=format",
    "Mexican": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&h=380&fit=crop&auto=format",
    "Japanese": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=600&h=380&fit=crop&auto=format",
    "Chinese": "https://images.unsplash.com/photo-1541696432-82c6da8ce7bf?w=600&h=380&fit=crop&auto=format",
    "Thai": "https://images.unsplash.com/photo-1559847844-5315695dadae?w=600&h=380&fit=crop&auto=format",
    "Korean": "https://images.unsplash.com/photo-1590301157890-4810ed352733?w=600&h=380&fit=crop&auto=format",
    "Mediterranean": "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=600&h=380&fit=crop&auto=format",
    "French": "https://images.unsplash.com/photo-1510693206972-df098062cb71?w=600&h=380&fit=crop&auto=format",
    "American": "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=600&h=380&fit=crop&auto=format",
}

DEFAULT_IMAGE = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&h=380&fit=crop&auto=format"
ACCENT_PALETTES = ["#FFD5C2", "#F5D66F", "#C9DCC5", "#F6C8D0"]


async def generate_recipes_batch_with_gemini(
    cuisine: str,
    count: int = 5,
    theme: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Use Gemini 2.0 Flash to generate authentic, structured recipes for a specific cuisine."""
    if not settings.GEMINI_API_KEY.strip():
        logger.warning("GEMINI_API_KEY is not set. Cannot run automated recipe generator.")
        return []

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        theme_clause = f" with a focus on '{theme}' vibe" if theme else ""
        logger.info("Requesting Gemini to generate %d authentic %s recipes%s...", count, cuisine, theme_clause)

        prompt = f"""
You are an executive master chef specializing in global culinary arts.
Generate {count} distinct, authentic, highly rated {cuisine} recipes{theme_clause}.
Ensure a balanced mix of quick weekday favorites, hearty comfort foods, and diverse dietary options (vegetarian, high-protein, vegan).

For each recipe, return a JSON object adhering exactly to this schema:
{{
  "name": "Distinct Authentic Recipe Name",
  "cuisine": "{cuisine}",
  "time": "e.g. 15 min",
  "difficulty": "Easy" or "Medium",
  "tags": ["Vegetarian", "High-protein", etc.],
  "desc": "One mouthwatering sentence describing the dish.",
  "image": "{CUISINE_IMAGE_MAP.get(cuisine, DEFAULT_IMAGE)}",
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
  "tastes": ["savory", "spicy" or other tastes from: spicy, savory, sweet, tangy, creamy, fresh, comfort],
  "effort": "lazy" or "easy" or "chef"
}}

Return ONLY a valid JSON array of {count} recipe objects: [{{...}}, {{...}}].
Output raw JSON only with NO markdown code fences or commentary.
"""

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
        )

        text = response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n", "", text)
            text = re.sub(r"\n```$", "", text).strip()

        recipes = json.loads(text)
        valid_recipes = []
        for r in recipes:
            if "name" in r and "ingredients" in r and "steps" in r:
                r["step_timers"] = r.get("stepTimers", [0] * len(r.get("steps", [])))
                r["accent"] = r.get("accent", ACCENT_PALETTES[len(valid_recipes) % len(ACCENT_PALETTES)])
                if not r.get("image") or r["image"] == DEFAULT_IMAGE:
                    r["image"] = CUISINE_IMAGE_MAP.get(cuisine, DEFAULT_IMAGE)
                valid_recipes.append(r)

        return valid_recipes

    except Exception as exc:
        logger.error("Failed to generate recipes with Gemini for %s: %s", cuisine, exc)
        return []


async def expand_catalog_async(
    cuisines: Optional[List[str]] = None,
    count_per_cuisine: int = 5,
    theme: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate and insert recipes across specified cuisines using Gemini."""
    target_cuisines = cuisines or CUISINES_LIST
    total_added = 0
    results_by_cuisine = {}

    for cuisine in target_cuisines:
        recipes = await generate_recipes_batch_with_gemini(cuisine, count=count_per_cuisine, theme=theme)
        if recipes:
            inserted = bulk_insert_recipes(recipes, source="gemini_catalog")
            total_added += inserted
            results_by_cuisine[cuisine] = inserted
            logger.info("Added %d recipes for %s. Total in catalog: %d", inserted, cuisine, get_recipe_count())
        else:
            results_by_cuisine[cuisine] = 0

    return {
        "added_count": total_added,
        "results_by_cuisine": results_by_cuisine,
        "total_catalog_size": get_recipe_count(),
    }


def main():
    """CLI runner for expanding the database using Gemini."""
    parser = argparse.ArgumentParser(description="FridgeMind Gemini Recipe Catalog Expander")
    parser.add_argument(
        "--cuisines",
        nargs="+",
        default=None,
        help="Specific cuisines to generate recipes for (e.g. Indian Italian Mexican)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of recipes to generate per cuisine (default: 5)",
    )
    parser.add_argument(
        "--theme",
        type=str,
        default=None,
        help="Optional culinary theme (e.g. quick, comfort, street_food, healthy)",
    )
    args = parser.parse_args()

    print(f"Starting Gemini Catalog Expander (Count per cuisine: {args.count})...")
    res = asyncio.run(expand_catalog_async(cuisines=args.cuisines, count_per_cuisine=args.count, theme=args.theme))
    print(f"Done! Added {res['added_count']} recipes. Total catalog: {res['total_catalog_size']}")
    print("Catalog stats:", json.dumps(get_catalog_stats(), indent=2))


if __name__ == "__main__":
    main()
