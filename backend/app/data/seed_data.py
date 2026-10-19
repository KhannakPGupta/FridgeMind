"""Database seeder loading multi-cuisine world recipes from external JSON dataset into SQLite.

Eliminates hardcoded recipe dictionaries from source code, decoupling data from logic.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

from backend.app.core.logging import logger
from backend.app.data.database import init_db, bulk_insert_recipes, get_recipe_count

BASELINE_JSON_PATH = Path(__file__).resolve().parent / "recipes_baseline.json"


def load_baseline_recipes() -> List[Dict[str, Any]]:
    """Load baseline recipes from external JSON dataset."""
    if not BASELINE_JSON_PATH.exists():
        logger.warning("Baseline recipes JSON file not found at %s", BASELINE_JSON_PATH)
        return []
    try:
        with open(BASELINE_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.error("Failed to load baseline recipes from JSON: %s", exc)
        return []


# Maintain module-level accessor for backward compatibility
WORLD_CURATED_RECIPES: List[Dict[str, Any]] = load_baseline_recipes()


def seed_database():
    """Seed SQLite database with external multi-cuisine recipe baseline."""
    init_db()
    recipes = load_baseline_recipes()
    if recipes:
        logger.info("Syncing SQLite database with %d baseline recipes from %s...", len(recipes), BASELINE_JSON_PATH.name)
        inserted = bulk_insert_recipes(recipes, source="catalog")
        logger.info("Database sync complete. Total recipes in catalog: %d (New: %d)", get_recipe_count(), inserted)
    else:
        logger.warning("No recipes loaded from baseline dataset.")


if __name__ == "__main__":
    seed_database()
