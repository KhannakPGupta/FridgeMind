"""API endpoints for recipe recommendations, details, and nutrition calculation."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.app.schemas.recipes import (
    RecommendRequest,
    RecommendResponse,
    RecipeResponse,
)
from backend.app.schemas.nutrition import NutritionSummary
from backend.app.services.recipe_service import (
    get_recipe_recommendations,
    fetch_recipe_detail,
)
from backend.app.services.nutrition_service import calculate_recipe_nutrition

router = APIRouter(prefix="/recipes", tags=["Recipes"])


@router.post("/recommend", response_model=RecommendResponse)
async def recommend_recipes(payload: RecommendRequest) -> RecommendResponse:
    """Recommend and rank recipes based on available pantry items and user preferences."""
    return await get_recipe_recommendations(
        pantry=payload.ingredients,
        preferences=payload.preferences,
        theme=payload.theme or "cozy",
        surprise=payload.surprise,
    )


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(recipe_id: int) -> RecipeResponse:
    """Retrieve full details of a specific recipe by ID."""
    recipe = fetch_recipe_detail(recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with ID {recipe_id} not found.",
        )
    return recipe


@router.get("/{recipe_id}/nutrition", response_model=NutritionSummary)
async def get_recipe_nutrition(
    recipe_id: int,
    servings: Optional[int] = Query(default=None, ge=1, le=12, description="Target serving size"),
) -> NutritionSummary:
    """Calculate aggregated nutritional breakdown for a recipe, scaled to specified servings."""
    recipe = fetch_recipe_detail(recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with ID {recipe_id} not found.",
        )

    target_servings = servings if servings is not None else recipe.servings
    return calculate_recipe_nutrition(recipe.ingredients, target_servings)
