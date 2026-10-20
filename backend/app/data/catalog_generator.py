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
from google.genai import types

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.data.database import bulk_insert_recipes, get_recipe_count, get_catalog_stats
from backend.app.schemas.recipes import GeneratedRecipe
from backend.app.services.image_service import resolve_dish_image


CUISINES_LIST = [
    "Indian", "Italian", "Mexican", "Japanese", "Chinese", "Thai",
    "Korean", "Mediterranean", "Lebanese", "French", "Spanish", "Greek",
    "American", "Vietnamese", "Turkish"
]

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
Provide authentic dishes with practical ingredients and accurate cooking step timers.
"""

        # Gemini 2.0 structured output configuration
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=list[GeneratedRecipe],
            temperature=0.7,
        )

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=config,
        )

        text = response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n", "", text)
            text = re.sub(r"\n```$", "", text).strip()

        recipes_raw = json.loads(text)
        valid_recipes = []
        for r in recipes_raw:
            if isinstance(r, dict) and "name" in r and "ingredients" in r and "steps" in r:
                r["cuisine"] = r.get("cuisine") or cuisine
                r["step_timers"] = r.get("stepTimers", [0] * len(r.get("steps", [])))
                r["accent"] = r.get("accent") or ACCENT_PALETTES[len(valid_recipes) % len(ACCENT_PALETTES)]

                # Dynamic dish-specific image resolution
                ing_names = [i.get("name", "") if isinstance(i, dict) else getattr(i, "name", "") for i in r.get("ingredients", [])]
                if not r.get("image") or "unsplash.com" not in r.get("image", ""):
                    r["image"] = resolve_dish_image(r["name"], cuisine, ing_names)

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
