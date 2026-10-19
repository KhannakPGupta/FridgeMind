"""Unit tests for ingredient normalization and emoji mapping."""

from backend.app.ml.normalizer import (
    normalize_ingredient_name,
    get_emoji_for_ingredient,
    parse_quantity_and_name,
)


def test_normalize_exact_aliases():
    """Verify known singular and plural terms map to canonical names."""
    assert normalize_ingredient_name("tomatoes") == "Tomato"
    assert normalize_ingredient_name("tomato") == "Tomato"
    assert normalize_ingredient_name("eggs") == "Eggs"
    assert normalize_ingredient_name("egg") == "Eggs"
    assert normalize_ingredient_name("onions") == "Onion"
    assert normalize_ingredient_name("garlic cloves") == "Garlic"


def test_normalize_indian_ingredients():
    """Verify regional and Indian pantry terms are recognized."""
    assert normalize_ingredient_name("paneer") == "Paneer"
    assert normalize_ingredient_name("palak") == "Spinach"
    assert normalize_ingredient_name("adrak") == "Ginger"
    assert normalize_ingredient_name("besan") == "Besan"
    assert normalize_ingredient_name("dahi") == "Yogurt"
    assert normalize_ingredient_name("poha") == "Poha"
    assert normalize_ingredient_name("chana") == "Chickpeas"
    assert normalize_ingredient_name("aloo") == "Potato"


def test_emoji_mapping():
    """Verify emoji matching matches the frontend expectations."""
    assert get_emoji_for_ingredient("Eggs") == "🥚"
    assert get_emoji_for_ingredient("Milk") == "🥛"
    assert get_emoji_for_ingredient("Paneer") == "🧀"
    assert get_emoji_for_ingredient("Spinach") == "🥬"
    assert get_emoji_for_ingredient("Tomato") == "🍅"
    assert get_emoji_for_ingredient("UnknownFoodXYZ") == "🥗"


def test_parse_quantity_and_name():
    """Verify splitting of quantity prefix from ingredient name."""
    qty, name = parse_quantity_and_name("3 eggs")
    assert qty == "3"
    assert name == "eggs"

    qty, name = parse_quantity_and_name("200g paneer")
    assert qty == "200g"
    assert name == "paneer"

    qty, name = parse_quantity_and_name("4 cloves garlic")
    assert qty == "4 cloves"
    assert name == "garlic"

    qty, name = parse_quantity_and_name("spinach")
    assert qty == "1"
    assert name == "spinach"
