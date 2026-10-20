"""SQLite database connection, schema management, and query helpers for recipe catalog."""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger


import re


def get_db_connection() -> sqlite3.Connection:
    """Return an open SQLite database connection with row factory."""
    db_path = settings.DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create recipe table, FTS5 virtual table, and indexes if they do not exist."""
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
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_recipes_name_unique ON recipes(lower(name))")

        # Sub-millisecond candidate retrieval via SQLite FTS5
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS recipes_fts USING fts5(
                recipe_id UNINDEXED,
                name,
                cuisine,
                tags,
                ingredients_text,
                tastes
            )
        """)

        # Sync FTS table if empty but main table has data
        cursor.execute("SELECT COUNT(*) FROM recipes_fts")
        fts_count = cursor.fetchone()[0]
        if fts_count == 0:
            cursor.execute("""
                INSERT INTO recipes_fts (recipe_id, name, cuisine, tags, ingredients_text, tastes)
                SELECT id, name, cuisine, tags, ingredients, tastes FROM recipes
            """)

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
        recipe_id = cursor.lastrowid or 0
        if recipe_id == 0:
            cursor.execute("SELECT id FROM recipes WHERE name = ?", (recipe["name"],))
            row = cursor.fetchone()
            if row:
                recipe_id = row["id"]

        # Sync into FTS
        try:
            cursor.execute("DELETE FROM recipes_fts WHERE recipe_id = ?", (recipe_id,))
            cursor.execute("""
                INSERT INTO recipes_fts (recipe_id, name, cuisine, tags, ingredients_text, tastes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                recipe_id,
                recipe["name"],
                recipe.get("cuisine", "Global"),
                json.dumps(recipe.get("tags", [])),
                json.dumps(recipe.get("ingredients", [])),
                json.dumps(recipe.get("tastes", ["savory"])),
            ))
        except Exception as fts_exc:
            logger.warning("Could not sync FTS for recipe %s: %s", recipe.get("name"), fts_exc)

        conn.commit()
        return recipe_id


def bulk_insert_recipes(recipes: List[Dict[str, Any]], source: str = "catalog") -> int:
    """Insert multiple recipes efficiently and sync them into FTS index."""
    init_db()
    inserted = 0

    # Defensive in-memory deduplication of the incoming batch
    unique_batch = []
    seen = set()
    for r in recipes:
        clean_name = r.get("name", "").strip().lower()
        if clean_name and clean_name not in seen:
            seen.add(clean_name)
            unique_batch.append(r)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        for r in unique_batch:
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

        # Refresh FTS virtual index
        try:
            cursor.execute("DELETE FROM recipes_fts")
            cursor.execute("""
                INSERT INTO recipes_fts (recipe_id, name, cuisine, tags, ingredients_text, tastes)
                SELECT id, name, cuisine, tags, ingredients, tastes FROM recipes
            """)
        except Exception as fts_exc:
            logger.warning("Could not refresh FTS after bulk insert: %s", fts_exc)

        conn.commit()
    return inserted


def search_candidate_recipes_fts(pantry_terms: List[str], limit: int = 60) -> List[Dict[str, Any]]:
    """Sub-millisecond candidate retrieval using SQLite FTS5 index.

    Matches recipes containing any of the normalized pantry terms across their
    ingredients, recipe name, tags, or taste profile.
    """
    init_db()
    clean_terms = []
    for t in pantry_terms:
        cleaned = re.sub(r"[^\w\s]", "", t).strip()
        if cleaned and len(cleaned) > 1:
            clean_terms.append(f'"{cleaned}"')

    if not clean_terms:
        return get_all_recipes()

    fts_query = " OR ".join(clean_terms)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT r.* FROM recipes r
                JOIN recipes_fts fts ON r.id = fts.recipe_id
                WHERE recipes_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (fts_query, limit))
            rows = cursor.fetchall()
            
            # Deduplicate by name
            results: List[Dict[str, Any]] = []
            seen_names = set()
            for r in rows:
                recipe_dict = row_to_recipe_dict(r)
                name_key = recipe_dict["name"].strip().lower()
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    results.append(recipe_dict)

            # If FTS matched fewer than 15 recipes, supplement from catalog to ensure broad recommendation pool
            if len(results) < 15:
                all_recipes = get_all_recipes()
                for ar in all_recipes:
                    name_key = ar["name"].strip().lower()
                    if name_key not in seen_names:
                        results.append(ar)
                        seen_names.add(name_key)
                    if len(results) >= limit:
                        break

            return results
        except Exception as exc:
            logger.warning("FTS search failed for query '%s' (%s), using full catalog fallback", fts_query, exc)
            return get_all_recipes()



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

