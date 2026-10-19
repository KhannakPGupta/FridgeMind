"""Unit tests for the comprehensive 350+ world ingredient normalizer."""

from backend.app.ml.normalizer import (
    normalize_ingredient_name,
    lookup_ingredient_def,
    get_emoji_for_ingredient,
    parse_quantity_and_name,
)


def test_normalize_indian_world_baseline():
    """Verify extensive Indian pantry staples and regional aliases."""
    assert normalize_ingredient_name("aloo") == "Potato"
    assert normalize_ingredient_name("batata") == "Potato"
    assert normalize_ingredient_name("pyaz") == "Onion"
    assert normalize_ingredient_name("kanda") == "Onion"
    assert normalize_ingredient_name("lahsun") == "Garlic"
    assert normalize_ingredient_name("adrak") == "Ginger"
    assert normalize_ingredient_name("palak") == "Spinach"
    assert normalize_ingredient_name("dhania") == "Coriander"
    assert normalize_ingredient_name("kothmir") == "Coriander"
    assert normalize_ingredient_name("kadi patta") == "Curry Leaves"
    assert normalize_ingredient_name("curry leaf") == "Curry Leaves"
    assert normalize_ingredient_name("paneer") == "Paneer"
    assert normalize_ingredient_name("dahi") == "Yogurt"
    assert normalize_ingredient_name("curd") == "Yogurt"
    assert normalize_ingredient_name("besan") == "Besan"
    assert normalize_ingredient_name("atta") == "Whole Wheat Flour"
    assert normalize_ingredient_name("poha") == "Poha"
    assert normalize_ingredient_name("chana") == "Chickpeas"
    assert normalize_ingredient_name("chole") == "Chickpeas"
    assert normalize_ingredient_name("rajma") == "Kidney Beans (Rajma)"
    assert normalize_ingredient_name("kasuri methi") == "Kasuri Methi"
    assert normalize_ingredient_name("hing") == "Hing (Asafoetida)"


def test_normalize_east_and_southeast_asian_baseline():
    """Verify East Asian and Southeast Asian culinary staples."""
    assert normalize_ingredient_name("bok choy") == "Bok Choy"
    assert normalize_ingredient_name("pak choi") == "Bok Choy"
    assert normalize_ingredient_name("spring onions") == "Scallion"
    assert normalize_ingredient_name("scallions") == "Scallion"
    assert normalize_ingredient_name("shiitake mushrooms") == "Mushroom"
    assert normalize_ingredient_name("tofu") == "Tofu"
    assert normalize_ingredient_name("edamame") == "Edamame"
    assert normalize_ingredient_name("miso") == "Miso Paste"
    assert normalize_ingredient_name("lemongrass") == "Lemongrass"
    assert normalize_ingredient_name("galangal") == "Galangal"
    assert normalize_ingredient_name("soya sauce") == "Soy Sauce"
    assert normalize_ingredient_name("korean chili paste") == "Gochujang"


def test_normalize_mediterranean_and_middle_eastern_baseline():
    """Verify Mediterranean and Middle Eastern culinary staples."""
    assert normalize_ingredient_name("aubergine") == "Eggplant"
    assert normalize_ingredient_name("courgette") == "Zucchini"
    assert normalize_ingredient_name("feta") == "Feta Cheese"
    assert normalize_ingredient_name("halloumi") == "Halloumi"
    assert normalize_ingredient_name("tahini") == "Tahini"
    assert normalize_ingredient_name("zaatar") == "Za'atar"
    assert normalize_ingredient_name("sumac") == "Sumac"
    assert normalize_ingredient_name("kalamata") == "Olives"
    assert normalize_ingredient_name("evoo") == "Olive Oil"


def test_normalize_latin_american_baseline():
    """Verify Latin American and Mexican ingredients."""
    assert normalize_ingredient_name("jalapenos") == "Jalapeño"
    assert normalize_ingredient_name("avocado") == "Avocado"
    assert normalize_ingredient_name("guacamole") == "Avocado"
    assert normalize_ingredient_name("sweetcorn") == "Sweet Corn"
    assert normalize_ingredient_name("corn tortilla") == "Tortilla"
    assert normalize_ingredient_name("plantain") == "Plantain"


def test_perishability_shelf_assignment():
    """Verify shelf categorization aligns with use-first (perishable) vs fresh-finds (stable)."""
    # Highly perishable produce and dairy should go to 'use_first'
    milk_def = lookup_ingredient_def("milk")
    assert milk_def.shelf == "use_first"

    spinach_def = lookup_ingredient_def("spinach")
    assert spinach_def.shelf == "use_first"

    paneer_def = lookup_ingredient_def("paneer")
    assert paneer_def.shelf == "use_first"

    bread_def = lookup_ingredient_def("bread")
    assert bread_def.shelf == "use_first"

    # Shelf-stable items should go to 'fresh_finds'
    potato_def = lookup_ingredient_def("potato")
    assert potato_def.shelf == "fresh_finds"

    onion_def = lookup_ingredient_def("onion")
    assert onion_def.shelf == "fresh_finds"

    rice_def = lookup_ingredient_def("rice")
    assert rice_def.shelf == "fresh_finds"

    lentil_def = lookup_ingredient_def("lentils")
    assert lentil_def.shelf == "fresh_finds"


def test_quantity_fraction_parsing():
    """Verify fractional quantities and complex unit extraction."""
    qty, name = parse_quantity_and_name("½ loaf bread")
    assert qty == "½ loaf"
    assert name == "bread"

    qty, name = parse_quantity_and_name("¼ cup olive oil")
    assert qty == "¼ cup"
    assert name == "olive oil"

    qty, name = parse_quantity_and_name("200g paneer")
    assert qty == "200g"
    assert name == "paneer"

    qty, name = parse_quantity_and_name("4 cloves garlic")
    assert qty == "4 cloves"
    assert name == "garlic"
