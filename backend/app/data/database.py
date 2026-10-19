"""SQLite database connection, schema management, and query helpers for recipe catalog."""

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
    """Create recipe table and indexes if they do not exist, and migrate missing columns."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
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
                effort TEXT NOT NULL,
                source TEXT DEFAULT 'catalog'
            )
        """)
        # Migration: ensure 'source' column exists
        cursor.execute("PRAGMA table_info(recipes)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "source" not in columns:
            cursor.execute("ALTER TABLE recipes ADD COLUMN source TEXT DEFAULT 'catalog'")

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
        "tags": json.loads(row["tags"]) if isinstance(row["tags"], str) else row["tags"],
        "desc": row["desc"],
        "image": row["image"],
        "cal": row["cal"],
        "rating": float(row["rating"]),
        "match": 95,
        "accent": row["accent"],
        "servings": int(row["servings"]),
        "ingredients": json.loads(row["ingredients"]) if isinstance(row["ingredients"], str) else row["ingredients"],
        "steps": json.loads(row["steps"]) if isinstance(row["steps"], str) else row["steps"],
        "stepTimers": json.loads(row["step_timers"]) if isinstance(row["step_timers"], str) else row["step_timers"],
        "substitution": row["substitution"],
        "tastes": json.loads(row["tastes"]) if isinstance(row["tastes"], str) else row["tastes"],
        "effort": row["effort"],
    }


def get_all_recipes() -> List[Dict[str, Any]]:
    """Fetch all recipes from SQLite catalog."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recipes ORDER BY id ASC")
        rows = cursor.fetchall()
        return [row_to_recipe_dict(r) for r in rows]


def get_recipe_by_id(recipe_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve single recipe by ID."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
        row = cursor.fetchone()
        return row_to_recipe_dict(row) if row else None


def get_recipe_count() -> int:
    """Return total number of recipes stored in the catalog."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM recipes")
        return cursor.fetchone()[0]


def save_recipe(recipe: Dict[str, Any], source: str = "gemini") -> int:
    """Insert or update a recipe in the database, avoiding duplicates by name."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO recipes (
                name, cuisine, time, difficulty, tags, desc, image,
                cal, rating, accent, servings, ingredients, steps, step_timers,
                substitution, tastes, effort, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                time=excluded.time,
                difficulty=excluded.difficulty,
                tags=excluded.tags,
                desc=excluded.desc,
                image=excluded.image,
                cal=excluded.cal,
                rating=excluded.rating,
                ingredients=excluded.ingredients,
                steps=excluded.steps,
                step_timers=excluded.step_timers,
                substitution=excluded.substitution,
                tastes=excluded.tastes,
                effort=excluded.effort
        """, (
            recipe["name"],
            recipe.get("cuisine", "Global"),
            recipe.get("time", "20 min"),
            recipe.get("difficulty", "Easy"),
            json.dumps(recipe.get("tags", [])),
            recipe.get("desc", ""),
            recipe.get("image", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&h=380&fit=crop&auto=format"),
            recipe.get("cal", "300 cal"),
            float(recipe.get("rating", 4.8)),
            recipe.get("accent", "#FFD5C2"),
            int(recipe.get("servings", 2)),
            json.dumps(recipe.get("ingredients", [])),
            json.dumps(recipe.get("steps", [])),
            json.dumps(recipe.get("stepTimers", [0] * len(recipe.get("steps", [])))),
            recipe.get("substitution", ""),
            json.dumps(recipe.get("tastes", ["savory"])),
            recipe.get("effort", "easy"),
            source,
        ))
        conn.commit()
        return cursor.lastrowid or 0


def bulk_insert_recipes(recipes: List[Dict[str, Any]], source: str = "catalog") -> int:
    """Insert multiple recipes efficiently, ignoring duplicates."""
    init_db()
    inserted = 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for r in recipes:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO recipes (
                        name, cuisine, time, difficulty, tags, desc, image,
                        cal, rating, accent, servings, ingredients, steps, step_timers,
                        substitution, tastes, effort, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r["name"],
                    r.get("cuisine", "Global"),
                    r.get("time", "20 min"),
                    r.get("difficulty", "Easy"),
                    json.dumps(r.get("tags", [])),
                    r.get("desc", ""),
                    r.get("image", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&h=380&fit=crop&auto=format"),
                    r.get("cal", "300 cal"),
                    float(r.get("rating", 4.8)),
                    r.get("accent", "#FFD5C2"),
                    int(r.get("servings", 2)),
                    json.dumps(r.get("ingredients", [])),
                    json.dumps(r.get("steps", [])),
                    json.dumps(r.get("step_timers", r.get("stepTimers", [0] * len(r.get("steps", []))))),
                    r.get("substitution", ""),
                    json.dumps(r.get("tastes", ["savory"])),
                    r.get("effort", "easy"),
                    source,
                ))
                if cursor.rowcount > 0:
                    inserted += 1
            except Exception as exc:
                logger.warning("Could not insert recipe '%s': %s", r.get("name"), exc)
        conn.commit()
    return inserted


def get_catalog_stats() -> Dict[str, Any]:
    """Return database statistics: count by cuisine, count by source, total count."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM recipes")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT cuisine, COUNT(*) as count FROM recipes GROUP BY cuisine ORDER BY count DESC")
        by_cuisine = {row["cuisine"]: row["count"] for row in cursor.fetchall()}

        cursor.execute("SELECT source, COUNT(*) as count FROM recipes GROUP BY source ORDER BY count DESC")
        by_source = {row["source"]: row["count"] for row in cursor.fetchall()}

        return {
            "total_recipes": total,
            "by_cuisine": by_cuisine,
            "by_source": by_source,
        }

