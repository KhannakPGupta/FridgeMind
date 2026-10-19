"""SQLite database connection and query helpers for recipe catalog."""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger


def get_db_connection() -> sqlite3.Connection:
    """Return an open SQLite database connection with row factory."""
    db_path = settings.DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create recipe table if it doesn't already exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cuisine TEXT NOT NULL,
                time TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                tags TEXT NOT NULL,
                desc TEXT NOT NULL,
                image TEXT NOT NULL,
                cal TEXT NOT NULL,
                rating REAL NOT NULL,
                accent TEXT NOT NULL,
                servings INTEGER NOT NULL,
                ingredients TEXT NOT NULL,
                steps TEXT NOT NULL,
                step_timers TEXT NOT NULL,
                substitution TEXT NOT NULL,
                tastes TEXT NOT NULL,
                effort TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipes_cuisine ON recipes(cuisine)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipes_effort ON recipes(effort)")
        conn.commit()


def row_to_recipe_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert an SQLite row to a recipe dictionary matching RecipeResponse schema."""
    return {
        "id": row["id"],
        "name": row["name"],
        "cuisine": row["cuisine"],
        "time": row["time"],
        "difficulty": row["difficulty"],
        "tags": json.loads(row["tags"]),
        "desc": row["desc"],
        "image": row["image"],
        "cal": row["cal"],
        "rating": float(row["rating"]),
        "match": 95,
        "accent": row["accent"],
        "servings": int(row["servings"]),
        "ingredients": json.loads(row["ingredients"]),
        "steps": json.loads(row["steps"]),
        "stepTimers": json.loads(row["step_timers"]),
        "substitution": row["substitution"],
        "tastes": json.loads(row["tastes"]),
        "effort": row["effort"],
    }


def get_all_recipes() -> List[Dict[str, Any]]:
    """Fetch all recipes from SQLite catalog."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recipes")
        rows = cursor.fetchall()
        return [row_to_recipe_dict(r) for r in rows]


def get_recipe_by_id(recipe_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve single recipe by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
        row = cursor.fetchone()
        return row_to_recipe_dict(row) if row else None
