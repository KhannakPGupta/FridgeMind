"""Schemas for recipes, preferences, and recommendations matching frontend TypeScript types."""

from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.ingredients import IngredientItem


class RecipeIngredient(BaseModel):
    """Ingredient requirement within a recipe."""

    name: str
    amount: float
    unit: str = ""


class SubstitutionOption(BaseModel):
    """Feasible ingredient substitution with ratio and practical cooking notes."""

    original: str
    substitute: str
    ratio: str = "1:1"
    flavor_impact: str = "neutral"
    notes: str = ""
    dietary_tags: List[str] = Field(default_factory=list)


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
    cuisine: Optional[str] = "Global"
    matched_ingredients: List[str] = Field(default_factory=list)
    missing_ingredients: List[str] = Field(default_factory=list)
    badges: List[str] = Field(default_factory=list)
    available_substitutions: List[SubstitutionOption] = Field(
        default_factory=list,
        description="Feasible pantry swaps for missing or alternative ingredients",
    )


class SubstituteRequest(BaseModel):
    """Request payload to adapt a recipe with an ingredient substitution."""

    replace: str
    substitute_with: str


class SubstituteResponse(BaseModel):
    """Response payload after applying an ingredient substitution to a recipe."""

    recipe: RecipeResponse
    applied_substitution: SubstitutionOption
    message: str


class GeneratedRecipeIngredient(BaseModel):
    """Ingredient item for Gemini structured recipe generation."""

    name: str
    amount: float
    unit: str = ""


class GeneratedRecipe(BaseModel):
    """Pydantic model for Gemini 2.0 Flash structured JSON schema generation."""

    name: str
    cuisine: str = "Global"
    time: str = "20 min"
    difficulty: str = "Easy"
    tags: List[str] = Field(default_factory=list)
    desc: str
    image: Optional[str] = None
    cal: str = "320 cal"
    rating: float = 4.8
    accent: Optional[str] = "#FFD5C2"
    servings: int = 2
    ingredients: List[GeneratedRecipeIngredient]
    steps: List[str]
    stepTimers: List[int] = Field(default_factory=list)
    substitution: str = ""
    tastes: List[str] = Field(default_factory=list)
    effort: str = "easy"


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

