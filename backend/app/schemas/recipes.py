"""Schemas for recipes, preferences, and recommendations matching frontend TypeScript types."""

from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.ingredients import IngredientItem


class RecipeIngredient(BaseModel):
    """Ingredient requirement within a recipe."""

    name: str
    amount: float
    unit: str = ""


class RecipeResponse(BaseModel):
    """Complete recipe object matching the frontend TypeScript Recipe type."""

    id: int
    name: str
    time: str
    difficulty: str
    tags: List[str] = Field(default_factory=list)
    desc: str
    image: str
    cal: str
    rating: float = 4.8
    match: int = Field(default=95, ge=0, le=100)
    accent: str = "#FFD5C2"
    servings: int = 2
    ingredients: List[RecipeIngredient]
    steps: List[str]
    stepTimers: List[int] = Field(default_factory=list, description="Step countdown durations in seconds")
    substitution: str = ""
    ai_reason: Optional[str] = None


class PreferencesInput(BaseModel):
    """User vibe and cooking preferences matching Preferences interface in App.tsx."""

    tastes: List[str] = Field(default_factory=list)
    effort: Optional[str] = None
    time: Optional[str] = None
    diets: List[str] = Field(default_factory=list)


class RecommendRequest(BaseModel):
    """Request payload to get recipe recommendations."""

    ingredients: List[IngredientItem] = Field(default_factory=list)
    preferences: PreferencesInput = Field(default_factory=PreferencesInput)
    theme: Optional[str] = "cozy"
    surprise: bool = False


class RecommendResponse(BaseModel):
    """Response returned for recipe searches."""

    recipes: List[RecipeResponse]
    total_found: int
    selected_theme: str
    source: str = Field(default="catalog", description="'catalog', 'gemini_adapted', or 'hybrid'")
