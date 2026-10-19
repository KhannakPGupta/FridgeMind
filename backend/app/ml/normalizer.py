"""Canonical ingredient normalization and emoji mapping."""

import re
import difflib
from typing import Tuple, Optional, Dict

# Standard emoji map mirroring src/App.tsx plus Indian and global staples
EMOJI_MAP = [
    ('egg', '🥚'), ('milk', '🥛'), ('cheese', '🧀'), ('paneer', '🧀'),
    ('tomato', '🍅'), ('spinach', '🥬'), ('palak', '🥬'), ('garlic', '🧄'),
    ('onion', '🧅'), ('bread', '🍞'), ('butter', '🧈'), ('ghee', '🧈'),
    ('carrot', '🥕'), ('broccoli', '🥦'), ('mushroom', '🍄'), ('lemon', '🍋'),
    ('lime', '🍋'), ('apple', '🍎'), ('banana', '🍌'), ('avocado', '🥑'),
    ('pepper', '🫑'), ('capsicum', '🫑'), ('chili', '🌶️'), ('mirchi', '🌶️'),
    ('cucumber', '🥒'), ('chicken', '🍗'), ('beef', '🥩'), ('mutton', '🥩'),
    ('pasta', '🍝'), ('rice', '🍚'), ('poha', '🍚'), ('potato', '🥔'),
    ('aloo', '🥔'), ('salmon', '🐟'), ('fish', '🐟'), ('shrimp', '🍤'),
    ('prawn', '🍤'), ('corn', '🌽'), ('pea', '🫛'), ('matar', '🫛'),
    ('bean', '🫘'), ('dal', '🫘'), ('lentil', '🫘'), ('chickpea', '🫘'),
    ('chana', '🫘'), ('olive', '🫒'), ('herb', '🌿'), ('basil', '🌿'),
    ('parsley', '🌿'), ('coriander', '🌿'), ('cilantro', '🌿'), ('methi', '🌿'),
    ('ginger', '🫚'), ('adrak', '🫚'), ('flour', '🌾'), ('atta', '🌾'),
    ('besan', '🌾'), ('maida', '🌾'), ('sugar', '🍬'), ('chocolate', '🍫'),
    ('yogurt', '🥣'), ('curd', '🥣'), ('dahi', '🥣'), ('tofu', '🧈'),
    ('noodle', '🍜'), ('sauce', '🥫'), ('oil', '🫒'), ('spices', '🧂'),
]

# Canonical alias lookup mapping raw terms to standardized names
CANONICAL_ALIASES: Dict[str, str] = {
    # Vegetables & Greens
    'tomatoes': 'Tomato', 'tomato': 'Tomato',
    'potatoes': 'Potato', 'potato': 'Potato', 'aloo': 'Potato',
    'onions': 'Onion', 'onion': 'Onion', 'pyaz': 'Onion',
    'garlic': 'Garlic', 'garlic cloves': 'Garlic', 'lahsun': 'Garlic',
    'ginger': 'Ginger', 'adrak': 'Ginger',
    'spinach': 'Spinach', 'palak': 'Spinach',
    'carrots': 'Carrot', 'carrot': 'Carrot', 'gajar': 'Carrot',
    'bell pepper': 'Bell Pepper', 'capsicum': 'Bell Pepper', 'peppers': 'Bell Pepper',
    'chili': 'Green Chili', 'chillies': 'Green Chili', 'green chilies': 'Green Chili', 'mirchi': 'Green Chili',
    'coriander': 'Coriander', 'cilantro': 'Coriander', 'dhania': 'Coriander',
    'mushrooms': 'Mushroom', 'mushroom': 'Mushroom',
    'green peas': 'Green Peas', 'peas': 'Green Peas', 'matar': 'Green Peas',
    'cucumber': 'Cucumber', 'kheera': 'Cucumber',
    'lemon': 'Lemon', 'lemons': 'Lemon', 'nimbu': 'Lemon',
    'lime': 'Lime',

    # Dairy & Proteins
    'eggs': 'Eggs', 'egg': 'Eggs', 'anda': 'Eggs',
    'milk': 'Milk', 'doodh': 'Milk',
    'cheese': 'Cheese', 'cheddar': 'Cheese', 'mozzarella': 'Cheese',
    'paneer': 'Paneer', 'cottage cheese': 'Paneer',
    'curd': 'Yogurt', 'dahi': 'Yogurt', 'yogurt': 'Yogurt',
    'butter': 'Butter', 'makkhan': 'Butter',
    'ghee': 'Ghee', 'clarified butter': 'Ghee',
    'chicken': 'Chicken', 'chicken breast': 'Chicken',
    'tofu': 'Tofu',

    # Grains, Flours & Carbs
    'bread': 'Bread', 'bread slices': 'Bread',
    'rice': 'Rice', 'chawal': 'Rice', 'basmati rice': 'Rice',
    'poha': 'Poha', 'flattened rice': 'Poha',
    'pasta': 'Pasta', 'spaghetti': 'Pasta', 'penne': 'Pasta',
    'wheat flour': 'Wheat Flour', 'atta': 'Wheat Flour',
    'gram flour': 'Besan', 'besan': 'Besan',
    'all purpose flour': 'All-Purpose Flour', 'maida': 'All-Purpose Flour',
    'oats': 'Oats',

    # Legumes & Pulses
    'lentils': 'Lentils', 'dal': 'Lentils', 'yellow dal': 'Lentils',
    'toor dal': 'Toor Dal', 'moong dal': 'Moong Dal',
    'chickpeas': 'Chickpeas', 'chana': 'Chickpeas', 'chole': 'Chickpeas',
    'black beans': 'Black Beans', 'kidney beans': 'Kidney Beans', 'rajma': 'Kidney Beans',

    # Condiments & Pantry
    'olive oil': 'Olive Oil', 'vegetable oil': 'Cooking Oil', 'oil': 'Cooking Oil',
    'mustard seeds': 'Mustard Seeds', 'rai': 'Mustard Seeds',
    'cumin seeds': 'Cumin Seeds', 'jeera': 'Cumin Seeds',
    'turmeric': 'Turmeric', 'haldi': 'Turmeric',
    'salt': 'Salt', 'black pepper': 'Black Pepper',
    'soy sauce': 'Soy Sauce', 'tomato sauce': 'Tomato Sauce', 'tomato ketchup': 'Tomato Ketchup',
}


def get_emoji_for_ingredient(name: str) -> str:
    """Return appropriate emoji based on substring lookup, matching frontend logic."""
    lower = name.lower()
    for key, emoji in EMOJI_MAP:
        if key in lower:
            return emoji
    return '🥗'


def parse_quantity_and_name(raw_text: str) -> Tuple[str, str]:
    """Extract quantity/units and clean name from raw user strings like '3 eggs' or '200g paneer'."""
    text = raw_text.strip()
    # Match patterns like "3", "500ml", "1/2 loaf", "4 cloves", "200g", "1 bunch"
    qty_pattern = r'^(\d+(?:[./]\d+)?\s*(?:g|kg|ml|l|cloves?|slices?|bunch|cups?|tbsp|tsp|loaf|can|pcs?|pieces?)?)\s+(?:of\s+)?(.+)$'
    match = re.match(qty_pattern, text, re.IGNORECASE)
    if match:
        qty = match.group(1).strip()
        name = match.group(2).strip()
        return qty, name
    return "1", text


def normalize_ingredient_name(raw_name: str) -> str:
    """Map raw name to canonical name, handling plurals, aliases, and fuzzy cleanup safely."""
    cleaned = raw_name.strip().lower()
    # Remove punctuation
    cleaned = re.sub(r'[^\w\s-]', '', cleaned).strip()

    # Exact alias match
    if cleaned in CANONICAL_ALIASES:
        return CANONICAL_ALIASES[cleaned]

    # Plural strip: check without trailing 's' or 'es'
    if cleaned.endswith('es') and cleaned[:-2] in CANONICAL_ALIASES:
        return CANONICAL_ALIASES[cleaned[:-2]]
    if cleaned.endswith('s') and cleaned[:-1] in CANONICAL_ALIASES:
        return CANONICAL_ALIASES[cleaned[:-1]]

    # Fuzzy match against known aliases with high confidence threshold (0.84)
    matches = difflib.get_close_matches(cleaned, CANONICAL_ALIASES.keys(), n=1, cutoff=0.84)
    if matches:
        return CANONICAL_ALIASES[matches[0]]

    # Capitalize title words if unknown
    return cleaned.title()
