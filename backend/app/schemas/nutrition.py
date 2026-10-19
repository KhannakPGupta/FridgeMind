"""Schemas for nutritional summaries and estimates."""

from typing import List, Optional
from pydantic import BaseModel, Field


class NutrientBreakdown(BaseModel):
    """Nutrient name, value, and unit."""

    name: str
    amount: float
    unit: str


class NutritionSummary(BaseModel):
    """Nutritional calculation and transparency details."""

    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: Optional[float] = None
    servings: int = 2
    basis: str = Field(default="Standard USDA Food Composition tables", description="Source of nutrition estimation")
    assumptions: str = Field(
        default="Values calculated from raw ingredient weights divided by recipe servings; cooking absorption may vary.",
        description="Explicit estimation disclosure",
    )
    details: List[NutrientBreakdown] = Field(default_factory=list)
    badges: List[str] = Field(default_factory=list)
    macro_ratios: Optional[dict] = None
