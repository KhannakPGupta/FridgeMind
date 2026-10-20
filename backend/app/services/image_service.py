"""Service for dynamic, dish-specific culinary image resolution.

Maps dish names, key ingredients, and culinary types to curated, appetizing,
high-resolution food photography, eliminating generic fallback duplicates.
"""

from typing import List, Optional
import re

# High-resolution, authentic culinary photo library keyed by dish concepts
DISH_KEYWORD_IMAGE_MAP = {
    # ── Bruschetta, Toasts & Sandwiches ──
    "cheesy garlic bruschetta": "https://images.unsplash.com/photo-1572695157366-5e585ab2b69f?w=600&h=380&fit=crop&auto=format",
    "bruschetta": "https://images.unsplash.com/photo-1572695157366-5e585ab2b69f?w=600&h=380&fit=crop&auto=format",
    "garlic butter mushroom toast": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&h=380&fit=crop&auto=format",
    "mushroom toast": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&h=380&fit=crop&auto=format",
    "avocado toast": "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=600&h=380&fit=crop&auto=format",
    "masala toast sandwich": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600&h=380&fit=crop&auto=format",
    "grilled sourdough": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600&h=380&fit=crop&auto=format",
    "grilled cheese": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600&h=380&fit=crop&auto=format",
    "sandwich": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600&h=380&fit=crop&auto=format",
    "toast": "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=600&h=380&fit=crop&auto=format",

    # ── Eggs & Breakfast ──
    "creamy tomato scrambled eggs": "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=600&h=380&fit=crop&auto=format",
    "scrambled egg": "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=600&h=380&fit=crop&auto=format",
    "spinach & cheese omelette": "https://images.unsplash.com/photo-1510693206972-df098062cb71?w=600&h=380&fit=crop&auto=format",
    "french herb omelette": "https://images.unsplash.com/photo-1510693206972-df098062cb71?w=600&h=380&fit=crop&auto=format",
    "omelette": "https://images.unsplash.com/photo-1510693206972-df098062cb71?w=600&h=380&fit=crop&auto=format",
    "tamagoyaki": "https://images.unsplash.com/photo-1510693206972-df098062cb71?w=600&h=380&fit=crop&auto=format",
    "shakshuka": "https://images.unsplash.com/photo-1590412200988-a436970781fa?w=600&h=380&fit=crop&auto=format",
    "huevos rancheros": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&h=380&fit=crop&auto=format",
    "huevos a la mexicana": "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=600&h=380&fit=crop&auto=format",
    "menemen": "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=600&h=380&fit=crop&auto=format",
    "akuri": "https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=600&h=380&fit=crop&auto=format",
    "egg curry": "https://images.unsplash.com/photo-1628294895950-9805252327bc?w=600&h=380&fit=crop&auto=format",
    "hotcakes": "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=600&h=380&fit=crop&auto=format",
    "pancake": "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=600&h=380&fit=crop&auto=format",
    "hashbrown": "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=600&h=380&fit=crop&auto=format",
    "egg": "https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=600&h=380&fit=crop&auto=format",

    # ── Indian Classics ──
    "amritsari paneer bhurji": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=600&h=380&fit=crop&auto=format",
    "paneer bhurji": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=600&h=380&fit=crop&auto=format",
    "palak paneer": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&h=380&fit=crop&auto=format",
    "paneer butter masala": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=600&h=380&fit=crop&auto=format",
    "matar paneer": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&h=380&fit=crop&auto=format",
    "paneer": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=600&h=380&fit=crop&auto=format",
    "dal makhani": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=600&h=380&fit=crop&auto=format",
    "tadka dal": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=600&h=380&fit=crop&auto=format",
    "dal": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=600&h=380&fit=crop&auto=format",
    "chana masala": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600&h=380&fit=crop&auto=format",
    "aloo jeera": "https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=600&h=380&fit=crop&auto=format",
    "baingan bharta": "https://images.unsplash.com/photo-1628294895950-9805252327bc?w=600&h=380&fit=crop&auto=format",
    "poha": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=600&h=380&fit=crop&auto=format",
    "besan chilla": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=600&h=380&fit=crop&auto=format",
    "chilla": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=600&h=380&fit=crop&auto=format",
    "samosa": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=600&h=380&fit=crop&auto=format",
    "curd rice": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=600&h=380&fit=crop&auto=format",
    "pulao": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&h=380&fit=crop&auto=format",
    "biryani": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&h=380&fit=crop&auto=format",
    "rasam": "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=600&h=380&fit=crop&auto=format",
    "curry": "https://images.unsplash.com/photo-1628294895950-9805252327bc?w=600&h=380&fit=crop&auto=format",

    # ── Italian & Pasta ──
    "margherita skillet flatbread": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&h=380&fit=crop&auto=format",
    "flatbread": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&h=380&fit=crop&auto=format",
    "pizza": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&h=380&fit=crop&auto=format",
    "aglio e olio": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=600&h=380&fit=crop&auto=format",
    "spaghetti": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=600&h=380&fit=crop&auto=format",
    "pesto pasta": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=600&h=380&fit=crop&auto=format",
    "penne all'arrabbiata": "https://images.unsplash.com/photo-1621996346565-e3d5d6281048?w=600&h=380&fit=crop&auto=format",
    "pasta": "https://images.unsplash.com/photo-1621996346565-e3d5d6281048?w=600&h=380&fit=crop&auto=format",
    "penne": "https://images.unsplash.com/photo-1621996346565-e3d5d6281048?w=600&h=380&fit=crop&auto=format",
    "mushroom risotto": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&h=380&fit=crop&auto=format",
    "risotto": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&h=380&fit=crop&auto=format",

    # ── Asian & Noodles ──
    "pad thai": "https://images.unsplash.com/photo-1559847844-5315695dadae?w=600&h=380&fit=crop&auto=format",
    "thai green coconut curry": "https://images.unsplash.com/photo-1559847844-5315695dadae?w=600&h=380&fit=crop&auto=format",
    "pad krapow": "https://images.unsplash.com/photo-1559847844-5315695dadae?w=600&h=380&fit=crop&auto=format",
    "miso ramen": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=600&h=380&fit=crop&auto=format",
    "ramen": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=600&h=380&fit=crop&auto=format",
    "yakisoba": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=600&h=380&fit=crop&auto=format",
    "noodle": "https://images.unsplash.com/photo-1585032226651-759b368d7246?w=600&h=380&fit=crop&auto=format",
    "kimchi fried rice": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&h=380&fit=crop&auto=format",
    "fried rice": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&h=380&fit=crop&auto=format",
    "kimchi jeon": "https://images.unsplash.com/photo-1590301157890-4810ed352733?w=600&h=380&fit=crop&auto=format",
    "bibimbap": "https://images.unsplash.com/photo-1590301157890-4810ed352733?w=600&h=380&fit=crop&auto=format",
    "dubu jorim": "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600&h=380&fit=crop&auto=format",
    "agedashi tofu": "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600&h=380&fit=crop&auto=format",
    "bok choy": "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600&h=380&fit=crop&auto=format",
    "stir-fry": "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600&h=380&fit=crop&auto=format",
    "spring roll": "https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?w=600&h=380&fit=crop&auto=format",
    "fideo": "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=600&h=380&fit=crop&auto=format",

    # ── Mexican & Latin ──
    "quesadilla": "https://images.unsplash.com/photo-1618040996337-56904b7850b9?w=600&h=380&fit=crop&auto=format",
    "chilaquiles": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&h=380&fit=crop&auto=format",
    "guacamole": "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=600&h=380&fit=crop&auto=format",
    "burrito": "https://images.unsplash.com/photo-1543339308-43e59d6b73a6?w=600&h=380&fit=crop&auto=format",
    "enchilada": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&h=380&fit=crop&auto=format",
    "esquites": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&h=380&fit=crop&auto=format",
    "taco": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&h=380&fit=crop&auto=format",

    # ── Mediterranean & Salads ──
    "hummus": "https://images.unsplash.com/photo-1577906096429-f73c2c312435?w=600&h=380&fit=crop&auto=format",
    "falafel": "https://images.unsplash.com/photo-1590301157890-4810ed352733?w=600&h=380&fit=crop&auto=format",
    "spanakopita": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&h=380&fit=crop&auto=format",
    "tortilla de patatas": "https://images.unsplash.com/photo-1534080564583-6be75777b70a?w=600&h=380&fit=crop&auto=format",
    "greek salad": "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=600&h=380&fit=crop&auto=format",
    "chickpea salad": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600&h=380&fit=crop&auto=format",
    "mujadara": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&h=380&fit=crop&auto=format",
    "salad": "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=600&h=380&fit=crop&auto=format",
    "soup": "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=600&h=380&fit=crop&auto=format",
}

# Regional cuisine default photography
CUISINE_DEFAULT_IMAGE_MAP = {
    "Indian": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=600&h=380&fit=crop&auto=format",
    "Italian": "https://images.unsplash.com/photo-1621996346565-e3d5d6281048?w=600&h=380&fit=crop&auto=format",
    "Mexican": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&h=380&fit=crop&auto=format",
    "Japanese": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=600&h=380&fit=crop&auto=format",
    "Chinese": "https://images.unsplash.com/photo-1541696432-82c6da8ce7bf?w=600&h=380&fit=crop&auto=format",
    "Thai": "https://images.unsplash.com/photo-1559847844-5315695dadae?w=600&h=380&fit=crop&auto=format",
    "Korean": "https://images.unsplash.com/photo-1590301157890-4810ed352733?w=600&h=380&fit=crop&auto=format",
    "Mediterranean": "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=600&h=380&fit=crop&auto=format",
    "French": "https://images.unsplash.com/photo-1510693206972-df098062cb71?w=600&h=380&fit=crop&auto=format",
    "American": "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=600&h=380&fit=crop&auto=format",
    "Spanish": "https://images.unsplash.com/photo-1534080564583-6be75777b70a?w=600&h=380&fit=crop&auto=format",
    "Greek": "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=600&h=380&fit=crop&auto=format",
    "Lebanese": "https://images.unsplash.com/photo-1577906096429-f73c2c312435?w=600&h=380&fit=crop&auto=format",
    "Turkish": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=600&h=380&fit=crop&auto=format",
    "Vietnamese": "https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?w=600&h=380&fit=crop&auto=format",
}

DEFAULT_CULINARY_IMAGE = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&h=380&fit=crop&auto=format"


def resolve_dish_image(
    recipe_name: str,
    cuisine: str = "Global",
    ingredients: Optional[List[str]] = None,
) -> str:
    """Resolve an appetizing, context-specific photograph URL for a recipe.

    Checks:
    1. Exact or partial keyword match in recipe name (longest specific match first)
    2. Primary ingredient matches (e.g., eggs, paneer, pasta, mushrooms)
    3. Regional cuisine default
    4. General vibrant culinary fallback
    """
    if not recipe_name:
        return CUISINE_DEFAULT_IMAGE_MAP.get(cuisine, DEFAULT_CULINARY_IMAGE)

    clean_name = recipe_name.lower()

    # 1. Match against dish keyword library (longest key first for maximum specificity)
    for keyword in sorted(DISH_KEYWORD_IMAGE_MAP.keys(), key=len, reverse=True):
        if keyword in clean_name:
            return DISH_KEYWORD_IMAGE_MAP[keyword]

    # 2. Check ingredient hints if provided
    if ingredients:
        for ing in ingredients:
            ing_lower = ing.lower()
            for keyword in sorted(DISH_KEYWORD_IMAGE_MAP.keys(), key=len, reverse=True):
                if keyword in ing_lower:
                    return DISH_KEYWORD_IMAGE_MAP[keyword]

    # 3. Match cuisine default
    if cuisine in CUISINE_DEFAULT_IMAGE_MAP:
        return CUISINE_DEFAULT_IMAGE_MAP[cuisine]

    # 4. Fallback
    return DEFAULT_CULINARY_IMAGE
