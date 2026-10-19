"""Service for processing fridge photos and recognizing ingredients."""

import io
import json
import re
from typing import List
from PIL import Image
from fastapi import HTTPException, status
from google import genai
from google.genai import types

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.ingredients import IngredientItem, RecognizeResponse
from backend.app.ml.normalizer import normalize_ingredient_name, get_emoji_for_ingredient


FALLBACK_INGREDIENTS = [
    {"name": "Eggs", "qty": "6", "emoji": "🥚", "confidence": 0.95},
    {"name": "Milk", "qty": "500ml", "emoji": "🥛", "confidence": 0.92},
    {"name": "Cheese", "qty": "200g", "emoji": "🧀", "confidence": 0.90},
    {"name": "Tomatoes", "qty": "3", "emoji": "🍅", "confidence": 0.88},
    {"name": "Spinach", "qty": "1 bunch", "emoji": "🥬", "confidence": 0.85},
    {"name": "Garlic", "qty": "4 cloves", "emoji": "🧄", "confidence": 0.91},
    {"name": "Onion", "qty": "1", "emoji": "🧅", "confidence": 0.89},
    {"name": "Bread", "qty": "½ loaf", "emoji": "🍞", "confidence": 0.94},
    {"name": "Carrots", "qty": "3", "emoji": "🥕", "confidence": 0.87},
    {"name": "Butter", "qty": "100g", "emoji": "🧈", "confidence": 0.93},
    {"name": "Mushrooms", "qty": "200g", "emoji": "🍄", "confidence": 0.86},
    {"name": "Lemon", "qty": "1", "emoji": "🍋", "confidence": 0.89},
]


def validate_image_bytes(image_bytes: bytes, mime_type: str) -> Image.Image:
    """Validate uploaded image file bytes, format, and dimension limits."""
    if len(image_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image size exceeds {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB limit.",
        )

    if mime_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type: {mime_type}. Allowed types: {', '.join(settings.ALLOWED_IMAGE_TYPES)}",
        )

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
        # Re-open after verify as per PIL documentation
        img = Image.open(io.BytesIO(image_bytes))
        return img
    except Exception as exc:
        logger.warning("Corrupted or invalid image uploaded: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid or readable image.",
        )


async def recognize_ingredients_from_image(image_bytes: bytes, mime_type: str) -> RecognizeResponse:
    """Detect food ingredients from image bytes using Gemini 2.0 Flash with safe fallback."""
    # 1. Validate image
    validate_image_bytes(image_bytes, mime_type)

    # 2. Check if Gemini API is available
    if settings.GEMINI_API_KEY.strip():
        try:
            logger.info("Invoking Gemini Vision model (%s) for ingredient recognition...", settings.GEMINI_MODEL)
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            prompt = (
                "You are an expert culinary vision assistant. Inspect this kitchen/fridge photo and identify "
                "all visible food ingredients. Be accurate and do not invent items hidden inside opaque containers.\n\n"
                "Return a JSON array of objects with keys:\n"
                "- 'name': standard common name of the food ingredient\n"
                "- 'qty': estimated count or pack quantity (e.g. '3', '500ml', '1 bunch', '200g', '1')\n"
                "- 'confidence': float between 0.0 and 1.0\n\n"
                "Example format:\n"
                '[{"name": "Tomatoes", "qty": "3", "confidence": 0.95}, {"name": "Eggs", "qty": "6", "confidence": 0.98}]\n\n'
                "Output ONLY the raw JSON array without markdown formatting or code blocks."
            )

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
            )

            text_output = response.text.strip()
            # Clean markdown code blocks if model wrapped it
            if text_output.startswith("```"):
                text_output = re.sub(r"^```(?:json)?\n", "", text_output)
                text_output = re.sub(r"\n```$", "", text_output).strip()

            raw_items = json.loads(text_output)
            ingredients: List[IngredientItem] = []
            
            for index, item in enumerate(raw_items, start=1):
                raw_name = str(item.get("name", "")).strip()
                if not raw_name:
                    continue
                canonical_name = normalize_ingredient_name(raw_name)
                qty = str(item.get("qty", "1")).strip() or "1"
                conf = float(item.get("confidence", 0.9))
                emoji = get_emoji_for_ingredient(canonical_name)

                ingredients.append(
                    IngredientItem(
                        id=index,
                        name=canonical_name,
                        qty=qty,
                        emoji=emoji,
                        confidence=round(conf, 2),
                    )
                )

            if ingredients:
                avg_conf = sum(i.confidence or 0.9 for i in ingredients) / len(ingredients)
                return RecognizeResponse(
                    ingredients=ingredients,
                    detected_count=len(ingredients),
                    confidence_avg=round(avg_conf, 2),
                    source="gemini_vision",
                    notes="Successfully detected ingredients via Gemini Vision.",
                )

        except Exception as exc:
            logger.error("Gemini Vision detection encountered error: %s. Reverting to curated fallback.", exc)

    # 3. Fallback when API key is missing or fails
    logger.info("Using curated fridge starter ingredients fallback.")
    fallback_items = [
        IngredientItem(
            id=idx,
            name=item["name"],
            qty=item["qty"],
            emoji=item["emoji"],
            confidence=item["confidence"],
        )
        for idx, item in enumerate(FALLBACK_INGREDIENTS, start=1)
    ]
    return RecognizeResponse(
        ingredients=fallback_items,
        detected_count=len(fallback_items),
        confidence_avg=0.90,
        source="curated_fallback",
        notes="Loaded starter ingredients for user review. Configure GEMINI_API_KEY in .env for live AI vision recognition.",
    )
