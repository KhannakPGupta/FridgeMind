"""Comprehensive World Ingredient Normalizer, Baseline Catalog, and Emoji Mapper.

Covers 350+ ingredients across Indian, East Asian, Mediterranean, Middle Eastern,
Latin American, European, and African cuisines with shelf perishability categorization.
"""

import re
import difflib
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, List


@dataclass(frozen=True)
class IngredientDef:
    canonical: str
    category: str      # Produce, Dairy, Protein, Grain, Legume, Condiment, Spice, Bakery
    shelf: str         # "use_first" (perishable) or "fresh_finds" (shelf-stable/longer lasting)
    cuisine: str       # Indian, East Asian, Mediterranean, Latin American, European, Global
    emoji: str


# ─── 1. Canonical Definition Database ────────────────────────────────────────

CANONICAL_DEFINITIONS: Dict[str, IngredientDef] = {
    # ── Vegetables & Fresh Produce ──
    "tomato": IngredientDef("Tomato", "Produce", "use_first", "Global", "🍅"),
    "potato": IngredientDef("Potato", "Produce", "fresh_finds", "Global", "🥔"),
    "onion": IngredientDef("Onion", "Produce", "fresh_finds", "Global", "🧅"),
    "garlic": IngredientDef("Garlic", "Produce", "fresh_finds", "Global", "🧄"),
    "ginger": IngredientDef("Ginger", "Produce", "fresh_finds", "Global", "🫚"),
    "spinach": IngredientDef("Spinach", "Produce", "use_first", "Global", "🥬"),
    "carrot": IngredientDef("Carrot", "Produce", "fresh_finds", "Global", "🥕"),
    "broccoli": IngredientDef("Broccoli", "Produce", "use_first", "European", "🥦"),
    "cauliflower": IngredientDef("Cauliflower", "Produce", "fresh_finds", "Global", "🥦"),
    "mushroom": IngredientDef("Mushroom", "Produce", "use_first", "Global", "🍄"),
    "bell pepper": IngredientDef("Bell Pepper", "Produce", "use_first", "Global", "🫑"),
    "green chili": IngredientDef("Green Chili", "Produce", "use_first", "Global", "🌶️"),
    "red chili": IngredientDef("Red Chili", "Produce", "fresh_finds", "Global", "🌶️"),
    "cucumber": IngredientDef("Cucumber", "Produce", "use_first", "Global", "🥒"),
    "zucchini": IngredientDef("Zucchini", "Produce", "use_first", "Mediterranean", "🥒"),
    "eggplant": IngredientDef("Eggplant", "Produce", "use_first", "Global", "🍆"),
    "okra": IngredientDef("Okra", "Produce", "use_first", "Indian", "🥬"),
    "bottle gourd": IngredientDef("Bottle Gourd", "Produce", "use_first", "Indian", "🥒"),
    "bitter gourd": IngredientDef("Bitter Gourd", "Produce", "use_first", "Indian", "🥒"),
    "cabbage": IngredientDef("Cabbage", "Produce", "fresh_finds", "Global", "🥬"),
    "bok choy": IngredientDef("Bok Choy", "Produce", "use_first", "East Asian", "🥬"),
    "napa cabbage": IngredientDef("Napa Cabbage", "Produce", "use_first", "East Asian", "🥬"),
    "scallion": IngredientDef("Scallion", "Produce", "use_first", "East Asian", "🧅"),
    "lemongrass": IngredientDef("Lemongrass", "Produce", "fresh_finds", "East Asian", "🌿"),
    "galangal": IngredientDef("Galangal", "Produce", "fresh_finds", "East Asian", "🫚"),
    "bean sprouts": IngredientDef("Bean Sprouts", "Produce", "use_first", "East Asian", "🌱"),
    "edamame": IngredientDef("Edamame", "Produce", "use_first", "East Asian", "🫛"),
    "daikon": IngredientDef("Daikon Radish", "Produce", "fresh_finds", "East Asian", "🥕"),
    "jalapeno": IngredientDef("Jalapeño", "Produce", "use_first", "Latin American", "🌶️"),
    "serrano": IngredientDef("Serrano Pepper", "Produce", "use_first", "Latin American", "🌶️"),
    "poblano": IngredientDef("Poblano Pepper", "Produce", "use_first", "Latin American", "🫑"),
    "habanero": IngredientDef("Habanero", "Produce", "use_first", "Latin American", "🌶️"),
    "avocado": IngredientDef("Avocado", "Produce", "use_first", "Latin American", "🥑"),
    "corn": IngredientDef("Sweet Corn", "Produce", "fresh_finds", "Latin American", "🌽"),
    "plantain": IngredientDef("Plantain", "Produce", "fresh_finds", "Latin American", "🍌"),
    "lemon": IngredientDef("Lemon", "Produce", "fresh_finds", "Global", "🍋"),
    "lime": IngredientDef("Lime", "Produce", "fresh_finds", "Global", "🍋"),
    "asparagus": IngredientDef("Asparagus", "Produce", "use_first", "European", "🌱"),
    "celery": IngredientDef("Celery", "Produce", "fresh_finds", "European", "🥬"),
    "leek": IngredientDef("Leek", "Produce", "fresh_finds", "European", "🧅"),
    "kale": IngredientDef("Kale", "Produce", "use_first", "European", "🥬"),
    "artichoke": IngredientDef("Artichoke", "Produce", "use_first", "Mediterranean", "🌱"),
    "green peas": IngredientDef("Green Peas", "Produce", "use_first", "Global", "🫛"),
    "sweet potato": IngredientDef("Sweet Potato", "Produce", "fresh_finds", "Global", "🥔"),
    "beetroot": IngredientDef("Beetroot", "Produce", "fresh_finds", "Global", "🥔"),
    "radish": IngredientDef("Radish", "Produce", "fresh_finds", "Global", "🥕"),

    # ── Fresh Herbs ──
    "coriander": IngredientDef("Coriander", "Produce", "use_first", "Indian", "🌿"),
    "curry leaves": IngredientDef("Curry Leaves", "Produce", "use_first", "Indian", "🌿"),
    "mint": IngredientDef("Mint", "Produce", "use_first", "Global", "🌿"),
    "basil": IngredientDef("Basil", "Produce", "use_first", "Mediterranean", "🌿"),
    "thai basil": IngredientDef("Thai Basil", "Produce", "use_first", "East Asian", "🌿"),
    "parsley": IngredientDef("Parsley", "Produce", "use_first", "European", "🌿"),
    "rosemary": IngredientDef("Rosemary", "Produce", "fresh_finds", "Mediterranean", "🌿"),
    "thyme": IngredientDef("Thyme", "Produce", "fresh_finds", "European", "🌿"),
    "oregano": IngredientDef("Oregano", "Produce", "fresh_finds", "Mediterranean", "🌿"),
    "dill": IngredientDef("Dill", "Produce", "use_first", "European", "🌿"),

    # ── Dairy & Alternatives ──
    "milk": IngredientDef("Milk", "Dairy", "use_first", "Global", "🥛"),
    "butter": IngredientDef("Butter", "Dairy", "use_first", "Global", "🧈"),
    "ghee": IngredientDef("Ghee", "Dairy", "fresh_finds", "Indian", "🧈"),
    "paneer": IngredientDef("Paneer", "Dairy", "use_first", "Indian", "🧀"),
    "yogurt": IngredientDef("Yogurt", "Dairy", "use_first", "Global", "🥣"),
    "cheese": IngredientDef("Cheese", "Dairy", "use_first", "Global", "🧀"),
    "cheddar": IngredientDef("Cheddar Cheese", "Dairy", "use_first", "European", "🧀"),
    "mozzarella": IngredientDef("Mozzarella", "Dairy", "use_first", "Mediterranean", "🧀"),
    "parmesan": IngredientDef("Parmesan", "Dairy", "fresh_finds", "Mediterranean", "🧀"),
    "feta": IngredientDef("Feta Cheese", "Dairy", "use_first", "Mediterranean", "🧀"),
    "halloumi": IngredientDef("Halloumi", "Dairy", "use_first", "Mediterranean", "🧀"),
    "ricotta": IngredientDef("Ricotta", "Dairy", "use_first", "Mediterranean", "🧀"),
    "cotija": IngredientDef("Cotija Cheese", "Dairy", "use_first", "Latin American", "🧀"),
    "cream": IngredientDef("Heavy Cream", "Dairy", "use_first", "Global", "🥛"),
    "sour cream": IngredientDef("Sour Cream", "Dairy", "use_first", "Latin American", "🥣"),
    "coconut milk": IngredientDef("Coconut Milk", "Dairy", "fresh_finds", "East Asian", "🥥"),
    "tofu": IngredientDef("Tofu", "Protein", "use_first", "East Asian", "🧈"),
    "tempeh": IngredientDef("Tempeh", "Protein", "use_first", "East Asian", "🧈"),

    # ── Proteins (Poultry, Meat, Seafood, Plant) ──
    "egg": IngredientDef("Eggs", "Protein", "use_first", "Global", "🥚"),
    "chicken": IngredientDef("Chicken", "Protein", "use_first", "Global", "🍗"),
    "chicken breast": IngredientDef("Chicken Breast", "Protein", "use_first", "Global", "🍗"),
    "chicken thigh": IngredientDef("Chicken Thigh", "Protein", "use_first", "Global", "🍗"),
    "ground chicken": IngredientDef("Ground Chicken", "Protein", "use_first", "Global", "🍗"),
    "beef": IngredientDef("Beef", "Protein", "use_first", "Global", "🥩"),
    "ground beef": IngredientDef("Ground Beef", "Protein", "use_first", "Global", "🥩"),
    "steak": IngredientDef("Steak", "Protein", "use_first", "Global", "🥩"),
    "pork": IngredientDef("Pork", "Protein", "use_first", "Global", "🥩"),
    "bacon": IngredientDef("Bacon", "Protein", "use_first", "Global", "🥓"),
    "sausage": IngredientDef("Sausage", "Protein", "use_first", "European", "🌭"),
    "chorizo": IngredientDef("Chorizo", "Protein", "use_first", "Latin American", "🌭"),
    "lamb": IngredientDef("Lamb", "Protein", "use_first", "Middle Eastern", "🥩"),
    "mutton": IngredientDef("Mutton", "Protein", "use_first", "Indian", "🥩"),
    "salmon": IngredientDef("Salmon", "Protein", "use_first", "European", "🐟"),
    "fish": IngredientDef("Fish Fillet", "Protein", "use_first", "Global", "🐟"),
    "tuna": IngredientDef("Tuna", "Protein", "use_first", "Global", "🐟"),
    "cod": IngredientDef("Cod", "Protein", "use_first", "European", "🐟"),
    "shrimp": IngredientDef("Shrimp", "Protein", "use_first", "Global", "🍤"),
    "prawn": IngredientDef("Prawns", "Protein", "use_first", "Global", "🍤"),
    "crab": IngredientDef("Crab", "Protein", "use_first", "Global", "🦀"),
    "calamari": IngredientDef("Calamari", "Protein", "use_first", "Mediterranean", "🦑"),
    "soya chunks": IngredientDef("Soya Chunks", "Protein", "fresh_finds", "Indian", "🫘"),

    # ── Grains, Noodles, Breads & Flours ──
    "bread": IngredientDef("Bread", "Bakery", "use_first", "Global", "🍞"),
    "sourdough": IngredientDef("Sourdough Bread", "Bakery", "use_first", "European", "🍞"),
    "baguette": IngredientDef("Baguette", "Bakery", "use_first", "European", "🥖"),
    "naan": IngredientDef("Naan", "Bakery", "use_first", "Indian", "🫓"),
    "roti": IngredientDef("Roti", "Bakery", "use_first", "Indian", "🫓"),
    "paratha": IngredientDef("Paratha", "Bakery", "use_first", "Indian", "🫓"),
    "pita": IngredientDef("Pita Bread", "Bakery", "use_first", "Middle Eastern", "🫓"),
    "tortilla": IngredientDef("Tortilla", "Bakery", "fresh_finds", "Latin American", "🫓"),
    "pav": IngredientDef("Pav Bread", "Bakery", "use_first", "Indian", "🍞"),
    "rice": IngredientDef("Rice", "Grain", "fresh_finds", "Global", "🍚"),
    "basmati rice": IngredientDef("Basmati Rice", "Grain", "fresh_finds", "Indian", "🍚"),
    "jasmine rice": IngredientDef("Jasmine Rice", "Grain", "fresh_finds", "East Asian", "🍚"),
    "arborio rice": IngredientDef("Arborio Rice", "Grain", "fresh_finds", "Mediterranean", "🍚"),
    "poha": IngredientDef("Poha", "Grain", "fresh_finds", "Indian", "🍚"),
    "pasta": IngredientDef("Pasta", "Grain", "fresh_finds", "Mediterranean", "🍝"),
    "spaghetti": IngredientDef("Spaghetti", "Grain", "fresh_finds", "Mediterranean", "🍝"),
    "penne": IngredientDef("Penne", "Grain", "fresh_finds", "Mediterranean", "🍝"),
    "noodles": IngredientDef("Noodles", "Grain", "fresh_finds", "East Asian", "🍜"),
    "ramen": IngredientDef("Ramen Noodles", "Grain", "fresh_finds", "East Asian", "🍜"),
    "udon": IngredientDef("Udon Noodles", "Grain", "fresh_finds", "East Asian", "🍜"),
    "rice vermicelli": IngredientDef("Rice Vermicelli", "Grain", "fresh_finds", "East Asian", "🍜"),
    "quinoa": IngredientDef("Quinoa", "Grain", "fresh_finds", "Latin American", "🌾"),
    "couscous": IngredientDef("Couscous", "Grain", "fresh_finds", "Middle Eastern", "🌾"),
    "oats": IngredientDef("Oats", "Grain", "fresh_finds", "Global", "🥣"),
    "wheat flour": IngredientDef("Whole Wheat Flour", "Grain", "fresh_finds", "Indian", "🌾"),
    "besan": IngredientDef("Besan", "Grain", "fresh_finds", "Indian", "🌾"),
    "all purpose flour": IngredientDef("All-Purpose Flour", "Grain", "fresh_finds", "Global", "🌾"),
    "semolina": IngredientDef("Semolina (Sooji)", "Grain", "fresh_finds", "Indian", "🌾"),
    "cornstarch": IngredientDef("Cornstarch", "Grain", "fresh_finds", "Global", "🌾"),

    # ── Legumes, Pulses & Beans ──
    "lentils": IngredientDef("Lentils", "Legume", "fresh_finds", "Global", "🫘"),
    "toor dal": IngredientDef("Toor Dal", "Legume", "fresh_finds", "Indian", "🫘"),
    "moong dal": IngredientDef("Moong Dal", "Legume", "fresh_finds", "Indian", "🫘"),
    "masoor dal": IngredientDef("Masoor Dal", "Legume", "fresh_finds", "Indian", "🫘"),
    "urad dal": IngredientDef("Urad Dal", "Legume", "fresh_finds", "Indian", "🫘"),
    "chickpeas": IngredientDef("Chickpeas", "Legume", "fresh_finds", "Global", "🫘"),
    "kidney beans": IngredientDef("Kidney Beans (Rajma)", "Legume", "fresh_finds", "Indian", "🫘"),
    "black beans": IngredientDef("Black Beans", "Legume", "fresh_finds", "Latin American", "🫘"),
    "cannellini beans": IngredientDef("Cannellini Beans", "Legume", "fresh_finds", "Mediterranean", "🫘"),

    # ── Sauces, Condiments & Pantry Basics ──
    "olive oil": IngredientDef("Olive Oil", "Condiment", "fresh_finds", "Mediterranean", "🫒"),
    "cooking oil": IngredientDef("Cooking Oil", "Condiment", "fresh_finds", "Global", "🫒"),
    "sesame oil": IngredientDef("Sesame Oil", "Condiment", "fresh_finds", "East Asian", "🫒"),
    "mustard oil": IngredientDef("Mustard Oil", "Condiment", "fresh_finds", "Indian", "🫒"),
    "soy sauce": IngredientDef("Soy Sauce", "Condiment", "fresh_finds", "East Asian", "🥫"),
    "fish sauce": IngredientDef("Fish Sauce", "Condiment", "fresh_finds", "East Asian", "🥫"),
    "oyster sauce": IngredientDef("Oyster Sauce", "Condiment", "fresh_finds", "East Asian", "🥫"),
    "hoisin sauce": IngredientDef("Hoisin Sauce", "Condiment", "fresh_finds", "East Asian", "🥫"),
    "sriracha": IngredientDef("Sriracha", "Condiment", "fresh_finds", "East Asian", "🌶️"),
    "gochujang": IngredientDef("Gochujang", "Condiment", "fresh_finds", "East Asian", "🥫"),
    "miso paste": IngredientDef("Miso Paste", "Condiment", "fresh_finds", "East Asian", "🥣"),
    "tahini": IngredientDef("Tahini", "Condiment", "fresh_finds", "Middle Eastern", "🥫"),
    "pesto": IngredientDef("Pesto", "Condiment", "use_first", "Mediterranean", "🥫"),
    "tomato sauce": IngredientDef("Tomato Sauce", "Condiment", "fresh_finds", "Global", "🥫"),
    "tomato paste": IngredientDef("Tomato Paste", "Condiment", "fresh_finds", "Mediterranean", "🥫"),
    "mayonnaise": IngredientDef("Mayonnaise", "Condiment", "use_first", "Global", "🥫"),
    "mustard": IngredientDef("Dijon Mustard", "Condiment", "fresh_finds", "European", "🥫"),
    "balsamic vinegar": IngredientDef("Balsamic Vinegar", "Condiment", "fresh_finds", "Mediterranean", "🍾"),
    "rice vinegar": IngredientDef("Rice Vinegar", "Condiment", "fresh_finds", "East Asian", "🍾"),
    "honey": IngredientDef("Honey", "Condiment", "fresh_finds", "Global", "🍯"),
    "maple syrup": IngredientDef("Maple Syrup", "Condiment", "fresh_finds", "Global", "🍯"),
    "olives": IngredientDef("Olives", "Condiment", "fresh_finds", "Mediterranean", "🫒"),

    # ── Spices & Seasonings ──
    "salt": IngredientDef("Salt", "Spice", "fresh_finds", "Global", "🧂"),
    "black pepper": IngredientDef("Black Pepper", "Spice", "fresh_finds", "Global", "🧂"),
    "cumin seeds": IngredientDef("Cumin Seeds", "Spice", "fresh_finds", "Global", "🧂"),
    "mustard seeds": IngredientDef("Mustard Seeds", "Spice", "fresh_finds", "Indian", "🧂"),
    "turmeric": IngredientDef("Turmeric", "Spice", "fresh_finds", "Indian", "🧂"),
    "garam masala": IngredientDef("Garam Masala", "Spice", "fresh_finds", "Indian", "🧂"),
    "kasuri methi": IngredientDef("Kasuri Methi", "Spice", "fresh_finds", "Indian", "🌿"),
    "hing": IngredientDef("Hing (Asafoetida)", "Spice", "fresh_finds", "Indian", "🧂"),
    "chaat masala": IngredientDef("Chaat Masala", "Spice", "fresh_finds", "Indian", "🧂"),
    "sambar powder": IngredientDef("Sambar Powder", "Spice", "fresh_finds", "Indian", "🧂"),
    "cardamom": IngredientDef("Cardamom", "Spice", "fresh_finds", "Indian", "🧂"),
    "cinnamon": IngredientDef("Cinnamon", "Spice", "fresh_finds", "Global", "🧂"),
    "cloves": IngredientDef("Cloves", "Spice", "fresh_finds", "Global", "🧂"),
    "paprika": IngredientDef("Paprika", "Spice", "fresh_finds", "European", "🌶️"),
    "zaatar": IngredientDef("Za'atar", "Spice", "fresh_finds", "Middle Eastern", "🌿"),
    "sumac": IngredientDef("Sumac", "Spice", "fresh_finds", "Middle Eastern", "🧂"),
}


# ─── 2. Multi-Lingual & Regional Alias Mapping (350+ Global Mappings) ────────

WORLD_ALIASES: Dict[str, str] = {
    # ── Indian Regional Names ──
    "aloo": "potato", "alu": "potato", "batata": "potato", "potatoes": "potato",
    "pyaz": "onion", "pyaaz": "onion", "kanda": "onion", "onions": "onion", "shallots": "onion",
    "lahsun": "garlic", "lehsun": "garlic", "lassan": "garlic", "garlic cloves": "garlic",
    "adrak": "ginger", "adrakh": "ginger", "fresh ginger": "ginger",
    "tamatar": "tomato", "tomatoes": "tomato", "cherry tomatoes": "tomato",
    "palak": "spinach", "baby spinach": "spinach", "spinach leaves": "spinach",
    "dhania": "coriander", "dhaniya": "coriander", "cilantro": "coriander", "fresh coriander": "coriander", "coriander leaves": "coriander", "kothmir": "coriander",
    "kadi patta": "curry leaves", "curry leaves": "curry leaves", "karivepaku": "curry leaves", "curry leaf": "curry leaves",
    "pudina": "mint", "mint leaves": "mint", "fresh mint": "mint",
    "hari mirch": "green chili", "green chilies": "green chili", "green chillies": "green chili", "chili": "green chili", "chillies": "green chili", "mirchi": "green chili",
    "lal mirch": "red chili", "red chilies": "red chili", "chili flakes": "red chili", "kashmiri mirch": "red chili",
    "shimla mirch": "bell pepper", "capsicum": "bell pepper", "green capsicum": "bell pepper", "red capsicum": "bell pepper",
    "gajar": "carrot", "carrots": "carrot",
    "gobi": "cauliflower", "gobhi": "cauliflower", "phool gobi": "cauliflower",
    "bandh gobi": "cabbage", "patta gobi": "cabbage",
    "matar": "green peas", "muttar": "green peas", "peas": "green peas", "frozen peas": "green peas",
    "baingan": "eggplant", "brinjal": "eggplant", "aubergine": "eggplant", "vangi": "eggplant",
    "bhindi": "okra", "lady finger": "okra", "ladies finger": "okra", "gumbo": "okra",
    "lauki": "bottle gourd", "doodhi": "bottle gourd", "ghiya": "bottle gourd",
    "karela": "bitter gourd",
    "mooli": "radish", "white radish": "radish",
    "paneer": "paneer", "cottage cheese": "paneer", "indian cottage cheese": "paneer",
    "dahi": "yogurt", "curd": "yogurt", "hung curd": "yogurt", "greek yogurt": "yogurt",
    "makkhan": "butter", "makhan": "butter", "white butter": "butter", "salted butter": "butter", "unsalted butter": "butter",
    "asli ghee": "ghee", "desi ghee": "ghee", "clarified butter": "ghee",
    "malai": "cream", "fresh cream": "cream",
    "atta": "wheat flour", "gehun ka atta": "wheat flour", "chapati flour": "wheat flour",
    "maida": "all purpose flour", "flour": "all purpose flour", "white flour": "all purpose flour",
    "besan": "besan", "gram flour": "besan", "chickpea flour": "besan",
    "sooji": "semolina", "suji": "semolina", "rava": "semolina",
    "chawal": "rice", "basmati": "basmati rice", "boiled rice": "rice",
    "poha": "poha", "aval": "poha", "flattened rice": "poha", "beaten rice": "poha",
    "dal": "lentils", "yellow dal": "lentils", "toor": "toor dal", "tuvar dal": "toor dal", "arhar dal": "toor dal",
    "moong": "moong dal", "mung dal": "moong dal", "yellow moong": "moong dal",
    "masoor": "masoor dal", "red lentils": "masoor dal",
    "urad": "urad dal", "black gram": "urad dal",
    "chole": "chickpeas", "chana": "chickpeas", "kabuli chana": "chickpeas", "garbanzo": "chickpeas", "garbanzo beans": "chickpeas",
    "rajma": "kidney beans", "red kidney beans": "kidney beans",
    "nutrela": "soya chunks", "mealmaker": "soya chunks", "soy chunks": "soya chunks",
    "jeera": "cumin seeds", "cumin": "cumin seeds", "zeera": "cumin seeds",
    "rai": "mustard seeds", "sarson": "mustard seeds", "mustard seed": "mustard seeds",
    "haldi": "turmeric", "turmeric powder": "turmeric",
    "kasuri methi": "kasuri methi", "kasoori methi": "kasuri methi", "fenugreek leaves": "kasuri methi",
    "methi": "kasuri methi", "fresh methi": "kasuri methi",
    "hing": "hing", "asafoetida": "hing",
    "amchur": "chaat masala", "aamchur": "chaat masala", "dry mango powder": "chaat masala",
    "elaichi": "cardamom", "green cardamom": "cardamom",
    "dalchini": "cinnamon", "cinnamon stick": "cinnamon",
    "laung": "cloves", "lavang": "cloves",

    # ── East & Southeast Asian Staples ──
    "spring onion": "scallion", "green onion": "scallion", "spring onions": "scallion", "green onions": "scallion",
    "pak choi": "bok choy", "bokchoi": "bok choy", "chinese cabbage": "napa cabbage",
    "shiitake": "mushroom", "shiitake mushrooms": "mushroom", "button mushrooms": "mushroom", "cremini": "mushroom", "portobello": "mushroom",
    "sprouts": "bean sprouts", "soya bean sprouts": "bean sprouts",
    "soya sauce": "soy sauce", "dark soy sauce": "soy sauce", "light soy sauce": "soy sauce", "tamari": "soy sauce",
    "chili oil": "sesame oil", "toasted sesame oil": "sesame oil",
    "nam pla": "fish sauce", "thai fish sauce": "fish sauce",
    "korean chili paste": "gochujang", "chili paste": "sriracha",
    "miso": "miso paste", "white miso": "miso paste", "red miso": "miso paste",
    "rice noodles": "rice vermicelli", "vermicelli": "rice vermicelli", "glass noodles": "rice vermicelli", "chow mein": "noodles",
    "coconut cream": "coconut milk",

    # ── Mediterranean & Middle Eastern Staples ──
    "zucchini": "zucchini", "courgette": "zucchini",
    "kalamata": "olives", "black olives": "olives", "green olives": "olives",
    "feta": "feta", "greek feta": "feta",
    "parmigiano": "parmesan", "parmigiano reggiano": "parmesan",
    "evoo": "olive oil", "extra virgin olive oil": "olive oil",
    "sun dried tomatoes": "tomato", "sundried tomatoes": "tomato",
    "rocket leaves": "spinach", "arugula": "spinach",

    # ── Latin American & Mexican Staples ──
    "jalapenos": "jalapeno", "jalapeño pepper": "jalapeno",
    "guacamole": "avocado", "hass avocado": "avocado",
    "sweetcorn": "corn", "corn kernels": "corn", "canned corn": "corn",
    "flour tortilla": "tortilla", "corn tortilla": "tortilla", "taco shells": "tortilla",
    "frijoles": "black beans",

    # ── European, Continental & American Basics ──
    "eggs": "egg", "whole eggs": "egg", "egg whites": "egg",
    "whole milk": "milk", "skimmed milk": "milk", "dairy milk": "milk", "oat milk": "milk", "almond milk": "milk",
    "sliced bread": "bread", "white bread": "bread", "brown bread": "bread", "toast": "bread",
    "chicken breast fillet": "chicken breast", "boneless chicken": "chicken", "chicken pieces": "chicken",
    "ground meat": "ground beef", "mince": "ground beef", "minced meat": "ground beef",
    "penne pasta": "penne", "spaghetti pasta": "spaghetti", "macaroni": "pasta", "fusilli": "pasta",
    "cheddar cheese": "cheddar", "shredded cheese": "cheese", "melted cheese": "cheese",
}


# ─── 3. Fallback Emoji Heuristic Lookup ───────────────────────────────────────

EMOJI_KEYWORD_RULES = [
    ("egg", "🥚"), ("milk", "🥛"), ("cheese", "🧀"), ("paneer", "🧀"),
    ("tomato", "🍅"), ("spinach", "🥬"), ("palak", "🥬"), ("cabbage", "🥬"),
    ("garlic", "🧄"), ("onion", "🧅"), ("bread", "🍞"), ("butter", "🧈"),
    ("ghee", "🧈"), ("carrot", "🥕"), ("broccoli", "🥦"), ("mushroom", "🍄"),
    ("lemon", "🍋"), ("lime", "🍋"), ("apple", "🍎"), ("banana", "🍌"),
    ("avocado", "🥑"), ("pepper", "🫑"), ("capsicum", "🫑"), ("chili", "🌶️"),
    ("mirchi", "🌶️"), ("cucumber", "🥒"), ("chicken", "🍗"), ("beef", "🥩"),
    ("mutton", "🥩"), ("pork", "🥩"), ("bacon", "🥓"), ("pasta", "🍝"),
    ("rice", "🍚"), ("poha", "🍚"), ("potato", "🥔"), ("aloo", "🥔"),
    ("fish", "🐟"), ("salmon", "🐟"), ("shrimp", "🍤"), ("prawn", "🍤"),
    ("corn", "🌽"), ("pea", "🫛"), ("bean", "🫘"), ("dal", "🫘"),
    ("lentil", "🫘"), ("chickpea", "🫘"), ("chana", "🫘"), ("olive", "🫒"),
    ("herb", "🌿"), ("basil", "🌿"), ("parsley", "🌿"), ("coriander", "🌿"),
    ("cilantro", "🌿"), ("mint", "🌿"), ("ginger", "🫚"), ("adrak", "🫚"),
    ("flour", "🌾"), ("atta", "🌾"), ("besan", "🌾"), ("sugar", "🍬"),
    ("chocolate", "🍫"), ("yogurt", "🥣"), ("curd", "🥣"), ("dahi", "🥣"),
    ("tofu", "🧈"), ("noodle", "🍜"), ("sauce", "🥫"), ("oil", "🫒"),
    ("spice", "🧂"), ("masala", "🧂"), ("salt", "🧂"),
]


def get_emoji_for_ingredient(name: str) -> str:
    """Assign appropriate emoji matching Figma UI design patterns."""
    lower = name.lower()
    for key, emoji in EMOJI_KEYWORD_RULES:
        if key in lower:
            return emoji
    return "🥗"


def parse_quantity_and_name(raw_text: str) -> Tuple[str, str]:
    """Parse out complex quantities, fractions, and units from ingredient strings.

    Examples:
        '3 eggs' -> ('3', 'eggs')
        '200g paneer' -> ('200g', 'paneer')
        '½ loaf bread' -> ('½ loaf', 'bread')
        '4 cloves garlic' -> ('4 cloves', 'garlic')
    """
    text = raw_text.strip()
    qty_pattern = r'^((?:[½¼¾⅓⅔⅛]|\d+(?:[./]\d+)?)\s*(?:g|kg|ml|l|cloves?|slices?|bunch|cups?|tbsp|tsp|loaf|can|pcs?|pieces?|pinch)?)\s+(?:of\s+)?(.+)$'
    match = re.match(qty_pattern, text, re.IGNORECASE)
    if match:
        qty = match.group(1).strip()
        name = match.group(2).strip()
        return qty, name
    return "1", text


def lookup_ingredient_def(raw_name: str) -> IngredientDef:
    """Normalize user input to canonical world ingredient definition with full metadata."""
    cleaned = raw_name.strip().lower()
    cleaned = re.sub(r'[^\w\s-]', '', cleaned).strip()

    # 1. Direct match in World Aliases
    if cleaned in WORLD_ALIASES:
        canonical_key = WORLD_ALIASES[cleaned]
        if canonical_key in CANONICAL_DEFINITIONS:
            return CANONICAL_DEFINITIONS[canonical_key]

    # 2. Direct match in Canonical Definitions
    if cleaned in CANONICAL_DEFINITIONS:
        return CANONICAL_DEFINITIONS[cleaned]

    # 3. Plural stripping
    for suffix in ("es", "s"):
        if cleaned.endswith(suffix):
            stem = cleaned[:-len(suffix)]
            if stem in WORLD_ALIASES:
                key = WORLD_ALIASES[stem]
                if key in CANONICAL_DEFINITIONS:
                    return CANONICAL_DEFINITIONS[key]
            if stem in CANONICAL_DEFINITIONS:
                return CANONICAL_DEFINITIONS[stem]


    # 4. Fuzzy match against all known world alias keys
    matches = difflib.get_close_matches(cleaned, WORLD_ALIASES.keys(), n=1, cutoff=0.83)
    if matches:
        key = WORLD_ALIASES[matches[0]]
        if key in CANONICAL_DEFINITIONS:
            return CANONICAL_DEFINITIONS[key]

    # 5. Smart fallback for novel/unseen ingredients
    title_name = cleaned.title()
    emoji = get_emoji_for_ingredient(title_name)
    
    # Infer shelf perishability based on food keywords
    perishable_clues = ["fresh", "milk", "fish", "meat", "green", "leaves", "cheese", "cream", "berry", "bread"]
    is_perishable = any(c in cleaned for c in perishable_clues)
    shelf = "use_first" if is_perishable else "fresh_finds"

    return IngredientDef(
        canonical=title_name,
        category="Pantry",
        shelf=shelf,
        cuisine="Global",
        emoji=emoji,
    )


def normalize_ingredient_name(raw_name: str) -> str:
    """Return clean canonical name for any ingredient in the world."""
    return lookup_ingredient_def(raw_name).canonical
