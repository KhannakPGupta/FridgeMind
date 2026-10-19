"""Endpoints for ingredient photo recognition and manual entry normalization."""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from backend.app.schemas.ingredients import (
    IngredientItem,
    RecognizeResponse,
    ManualIngredientRequest,
    ManualIngredientResponse,
)
from backend.app.services.vision_service import recognize_ingredients_from_image
from backend.app.ml.normalizer import (
    normalize_ingredient_name,
    get_emoji_for_ingredient,
    parse_quantity_and_name,
    lookup_ingredient_def,
)


router = APIRouter(prefix="/ingredients", tags=["Ingredients"])


@router.post("/recognize", response_model=RecognizeResponse)
async def recognize_fridge_photo(file: UploadFile = File(...)) -> RecognizeResponse:
    """Accept an uploaded kitchen/fridge photo and return detected ingredients."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Uploaded file must be an image (JPEG, PNG, or WEBP).",
        )

    content = await file.read()
    return await recognize_ingredients_from_image(content, file.content_type)


@router.post("/normalize", response_model=ManualIngredientResponse)
async def normalize_manual_ingredients(payload: ManualIngredientRequest) -> ManualIngredientResponse:
    """Normalize, clean, deduplicate, and assign emojis to user-typed ingredients."""
    seen_names = set()
    ingredients = []
    duplicates_count = 0

    for idx, raw_item in enumerate(payload.items, start=1):
        if not raw_item.strip():
            continue

        raw_qty, raw_name = parse_quantity_and_name(raw_item)
        definition = lookup_ingredient_def(raw_name)
        canonical = definition.canonical

        if canonical.lower() in seen_names:
            duplicates_count += 1
            continue

        seen_names.add(canonical.lower())

        ingredients.append(
            IngredientItem(
                id=idx,
                name=canonical,
                qty=raw_qty,
                emoji=definition.emoji,
                confidence=1.0,
                category=definition.category,
                shelf=definition.shelf,
                cuisine=definition.cuisine,
            )
        )


    return ManualIngredientResponse(
        ingredients=ingredients,
        duplicates_removed=duplicates_count,
    )
