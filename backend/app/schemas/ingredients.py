"""Schemas for ingredients and recognition."""

from typing import List, Optional
from pydantic import BaseModel, Field


class IngredientItem(BaseModel):
    """Ingredient item model matching the frontend Ingredient interface."""

    id: int
    name: str
    qty: str = "1"
    emoji: str = "🥗"
    confidence: Optional[float] = Field(default=None, description="Detection confidence between 0 and 1")


class RecognizeResponse(BaseModel):
    """Response returned after image or photo recognition."""

    ingredients: List[IngredientItem]
    detected_count: int
    confidence_avg: float = Field(default=0.9, ge=0.0, le=1.0)
    source: str = Field(default="gemini_vision", description="'gemini_vision' or 'curated_fallback'")
    notes: Optional[str] = None


class ManualIngredientRequest(BaseModel):
    """Request payload for manual ingredient entries."""

    items: List[str] = Field(..., min_length=1, description="List of raw ingredient strings entered by user")


class NormalizedIngredient(BaseModel):
    """Single normalized ingredient response."""

    original: str
    canonical: str
    qty: str
    emoji: str
    category: str


class ManualIngredientResponse(BaseModel):
    """Normalized response for manual entries."""

    ingredients: List[IngredientItem]
    duplicates_removed: int
