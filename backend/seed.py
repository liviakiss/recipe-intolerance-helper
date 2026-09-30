from app.database import SessionLocal
from app import models
from app.models import IngredientTag, DietPreset, DietPresetTagMap, Ingredient, IngredientTagMap, Substitute, IngredientSubstituteMap
from app.ingredient_matching import normalize_ingredient_name

TAGS = [
    "gluten", "dairy", "lactose", "egg", "honey", "meat",
    "fish", "shellfish", "tree_nuts", "peanuts", "soy",
    "sesame", "mustard", "sulphites",
]

db = SessionLocal()

for tag_name in TAGS:
    exists = db.query(IngredientTag).filter(IngredientTag.name == tag_name).first()
    if not exists:
        tag = IngredientTag(name=tag_name)
        db.add(tag)

db.commit()

print(f"Seeded {len(TAGS)} ingredient tags.")

#-----------------------------------------------------------------------------------

vegan = db.query(DietPreset).filter(DietPreset.name == "vegan").first()
if not vegan:
    vegan = DietPreset(name="vegan")
    db.add(vegan)
    db.commit()
vegetarian = db.query(DietPreset).filter(DietPreset.name == "vegetarian").first()
if not vegetarian:
    vegetarian = DietPreset(name="vegetarian")
    db.add(vegetarian)
    db.commit()
gluten_free = db.query(DietPreset).filter(DietPreset.name == "gluten_free").first()
if not gluten_free:
    gluten_free = DietPreset(name="gluten_free")
    db.add(gluten_free)
    db.commit()
lactose_free = db.query(DietPreset).filter(DietPreset.name == "lactose_free").first()
if not lactose_free:
    lactose_free = DietPreset(name="lactose_free")
    db.add(lactose_free)
    db.commit()

#-------------------------------------------------------------------------------------------------

def link_preset_to_tag(preset, tag_name):
    tag = db.query(models.IngredientTag).filter(models.IngredientTag.name == tag_name).first()

    existing = db.query(models.DietPresetTagMap).filter(
        models.DietPresetTagMap.preset_id == preset.id,
        models.DietPresetTagMap.tag_id == tag.id
    ).first()

    if not existing:
        mapping = models.DietPresetTagMap(preset_id=preset.id, tag_id=tag.id)
        db.add(mapping)
        db.commit()
        print(f"Linked preset '{preset.name}' to tag '{tag.name}'")


link_preset_to_tag(vegan, "meat")
link_preset_to_tag(vegan, "fish")
link_preset_to_tag(vegan, "dairy")
link_preset_to_tag(vegan, "egg")
link_preset_to_tag(vegan, "honey")

link_preset_to_tag(vegetarian, "meat")
link_preset_to_tag(vegetarian, "fish")

link_preset_to_tag(gluten_free, "gluten")

link_preset_to_tag(lactose_free, "lactose")

#---------------

# Note: an empty tag list means "safe by default" — most ordinary produce
# and pantry staples don't conflict with any of the MVP's restriction tags,
# and need a row here so the matcher recognizes them at all instead of
# falling back to "unrecognized". find_ingredient does whole-word substring
# matching (see ingredient_matching.py), so a specific variant only needs
# its own entry when it doesn't literally contain a broader word already
# here — "chicken breast" is caught by "chicken", but "spaghetti" needs its
# own line since it doesn't contain "pasta".
INGREDIENTS = {
    # grains / gluten
    "flour": ["gluten"],
    "wheat flour": ["gluten"],
    "plain flour": ["gluten"],
    "self raising flour": ["gluten"],
    "bread": ["gluten"],
    "breadcrumbs": ["gluten"],
    "panko": ["gluten"],
    "pasta": ["gluten"],
    "spaghetti": ["gluten"],
    "penne": ["gluten"],
    "macaroni": ["gluten"],
    "fusilli": ["gluten"],
    "linguine": ["gluten"],
    "tagliatelle": ["gluten"],
    "lasagne": ["gluten"],
    "lasagna": ["gluten"],
    "noodles": ["gluten"],
    "egg noodles": ["gluten", "egg"],
    "couscous": ["gluten"],
    "bulgur": ["gluten"],
    "semolina": ["gluten"],
    "barley": ["gluten"],
    "rye": ["gluten"],
    "pastry": ["gluten"],
    "puff pastry": ["gluten"],
    "pie crust": ["gluten"],
    "tortilla": ["gluten"],
    "pita": ["gluten"],
    "bun": ["gluten"],
    "baguette": ["gluten"],
    "cracker": ["gluten"],
    "soy sauce": ["soy", "gluten"],
    "worcestershire sauce": ["fish"],
    "rice": [],
    "brown rice": [],
    "rice noodles": [],
    "quinoa": [],
    "oats": [],
    "polenta": [],
    "cornstarch": [],
    "corn": [],
    "cornmeal": [],

    # eggs
    "egg": ["egg"],
    "quail egg": ["egg"],
    "mayonnaise": ["egg"],
    "meringue": ["egg"],

    # dairy
    "butter": ["dairy", "lactose"],
    "milk": ["dairy", "lactose"],
    "buttermilk": ["dairy", "lactose"],
    "cheese": ["dairy", "lactose"],
    "cheddar": ["dairy", "lactose"],
    "mozzarella": ["dairy", "lactose"],
    "parmesan": ["dairy", "lactose"],
    "pecorino": ["dairy", "lactose"],
    "feta": ["dairy", "lactose"],
    "ricotta": ["dairy", "lactose"],
    "mascarpone": ["dairy", "lactose"],
    "brie": ["dairy", "lactose"],
    "gouda": ["dairy", "lactose"],
    "halloumi": ["dairy", "lactose"],
    "cream": ["dairy", "lactose"],
    "cream cheese": ["dairy", "lactose"],
    "heavy cream": ["dairy", "lactose"],
    "whipping cream": ["dairy", "lactose"],
    "sour cream": ["dairy", "lactose"],
    "yogurt": ["dairy", "lactose"],
    "yoghurt": ["dairy", "lactose"],
    "condensed milk": ["dairy", "lactose"],
    "evaporated milk": ["dairy", "lactose"],
    "milk chocolate": ["dairy", "lactose"],
    "custard": ["dairy", "lactose", "egg"],
    "ice cream": ["dairy", "lactose"],

    # sweeteners
    "honey": ["honey"],
    "sugar": [],
    "brown sugar": [],
    "icing sugar": [],
    "powdered sugar": [],
    "maple syrup": [],
    "vanilla extract": [],
    "vanilla": [],

    # meat / cured meat
    "chicken": ["meat"],
    "beef": ["meat"],
    "ground beef": ["meat"],
    "mince": ["meat"],
    "pork": ["meat"],
    "bacon": ["meat"],
    "pancetta": ["meat"],
    "prosciutto": ["meat"],
    "guanciale": ["meat"],
    "chorizo": ["meat"],
    "sausage": ["meat"],
    "salami": ["meat"],
    "ham": ["meat"],
    "turkey": ["meat"],
    "duck": ["meat"],
    "lamb": ["meat"],
    "veal": ["meat"],
    "venison": ["meat"],
    "chicken stock": ["meat"],
    "beef stock": ["meat"],
    "chicken broth": ["meat"],
    "beef broth": ["meat"],
    "gelatin": ["meat"],

    # fish / shellfish
    "salmon": ["fish"],
    "tuna": ["fish"],
    "cod": ["fish"],
    "haddock": ["fish"],
    "halibut": ["fish"],
    "mackerel": ["fish"],
    "sardine": ["fish"],
    "trout": ["fish"],
    "anchovy": ["fish"],
    "sea bass": ["fish"],
    "fish sauce": ["fish"],
    "fish stock": ["fish"],
    "shrimp": ["shellfish"],
    "prawn": ["shellfish"],
    "crab": ["shellfish"],
    "lobster": ["shellfish"],
    "mussels": ["shellfish"],
    "clams": ["shellfish"],
    "oyster": ["shellfish"],
    "scallop": ["shellfish"],
    "squid": ["shellfish"],
    "calamari": ["shellfish"],

    # nuts & seeds
    "almond": ["tree_nuts"],
    "walnut": ["tree_nuts"],
    "cashew": ["tree_nuts"],
    "hazelnut": ["tree_nuts"],
    "pistachio": ["tree_nuts"],
    "pecan": ["tree_nuts"],
    "macadamia": ["tree_nuts"],
    "brazil nut": ["tree_nuts"],
    "pine nut": ["tree_nuts"],
    "peanut": ["peanuts"],
    "peanut butter": ["peanuts"],
    "sesame oil": ["sesame"],
    "sesame seeds": ["sesame"],
    "tahini": ["sesame"],

    # soy / legumes
    "tofu": ["soy"],
    "soy milk": ["soy"],
    "tempeh": ["soy"],
    "edamame": ["soy"],
    "miso": ["soy"],
    "chickpeas": [],
    "lentils": [],
    "black beans": [],
    "kidney beans": [],
    "cannellini beans": [],
    "split peas": [],

    # condiments / pantry
    "mustard": ["mustard"],
    "vinegar": [],
    "balsamic vinegar": [],
    "red wine vinegar": [],
    "apple cider vinegar": [],
    "rice vinegar": [],
    "olive oil": [],
    "vegetable oil": [],
    "sunflower oil": [],
    "canola oil": [],
    "coconut oil": [],
    "coconut milk": [],
    "coconut cream": [],
    "wine": ["sulphites"],
    "white wine": ["sulphites"],
    "red wine": ["sulphites"],
    "dried apricot": ["sulphites"],
    "raisins": ["sulphites"],
    "ketchup": [],
    "tomato sauce": [],
    "tomato paste": [],
    "passata": [],
    "stock": [],
    "vegetable stock": [],
    "vegetable broth": [],
    "water": [],

    # produce & other staples (safe by default)
    "garlic": [],
    "onion": [],
    "spring onion": [],
    "shallot": [],
    "leek": [],
    "tomato": [],
    "potato": [],
    "sweet potato": [],
    "carrot": [],
    "celery": [],
    "bell pepper": [],
    "chili pepper": [],
    "chilli": [],
    "spinach": [],
    "kale": [],
    "lettuce": [],
    "cabbage": [],
    "cucumber": [],
    "zucchini": [],
    "courgette": [],
    "broccoli": [],
    "cauliflower": [],
    "mushroom": [],
    "eggplant": [],
    "aubergine": [],
    "avocado": [],
    "peas": [],
    "green beans": [],
    "sweetcorn": [],
    "apple": [],
    "banana": [],
    "lemon": [],
    "lime": [],
    "orange": [],
    "mango": [],
    "pineapple": [],
    "ginger": [],
    "salt": [],
    "black pepper": [],
    "paprika": [],
    "cumin": [],
    "coriander": [],
    "cilantro": [],
    "oregano": [],
    "basil": [],
    "thyme": [],
    "rosemary": [],
    "parsley": [],
    "mint": [],
    "dill": [],
    "chives": [],
    "bay leaf": [],
    "cinnamon": [],
    "nutmeg": [],
    "turmeric": [],
    "curry powder": [],
    "chili flakes": [],
    "cayenne": [],
    "cocoa powder": [],
    "dark chocolate": [],
    "baking powder": [],
    "baking soda": [],
    "yeast": [],
}


def get_or_create_ingredient(name):
    normalized = normalize_ingredient_name(name)

    existing = db.query(Ingredient).filter(Ingredient.normalized_name == normalized).first()
    if existing:
        return existing

    ingredient = Ingredient(name=name, normalized_name=normalized)
    db.add(ingredient)
    db.commit()
    print(f"Seeded ingredient '{name}' (normalized: '{normalized}')")
    return ingredient


def link_ingredient_to_tag(ingredient, tag_name):
    tag = db.query(models.IngredientTag).filter(models.IngredientTag.name == tag_name).first()

    existing = db.query(IngredientTagMap).filter(
        IngredientTagMap.ingredient_id == ingredient.id,
        IngredientTagMap.tag_id == tag.id
    ).first()

    if not existing:
        mapping = IngredientTagMap(ingredient_id=ingredient.id, tag_id=tag.id)
        db.add(mapping)
        db.commit()
        print(f"Linked ingredient '{ingredient.name}' to tag '{tag.name}'")


for ingredient_name, tag_names in INGREDIENTS.items():
    ingredient = get_or_create_ingredient(ingredient_name)
    for tag_name in tag_names:
        link_ingredient_to_tag(ingredient, tag_name)

#-----------------------

# Only ingredients that can actually be flagged need a substitute — mustard
# and the sulphite items are intentionally left without one where there's no
# good general-purpose swap. Where several new entries share the same real
# swap (all the pasta shapes, all the named cheeses, all the cured meats),
# they're pointed at the same Substitute row rather than duplicating it.
INGREDIENT_SUBSTITUTES = {
    "flour": ("gluten-free flour blend", "Use a 1:1 gluten-free blend for most baking recipes."),
    "wheat flour": ("gluten-free flour blend", "Use a 1:1 gluten-free blend for most baking recipes."),
    "plain flour": ("gluten-free flour blend", "Use a 1:1 gluten-free blend for most baking recipes."),
    "self raising flour": ("gluten-free self-raising flour blend", "Use a certified gluten-free self-raising blend 1:1."),
    "bread": ("gluten-free bread", "Use a certified gluten-free loaf or wrap."),
    "breadcrumbs": ("gluten-free breadcrumbs", "Use a certified gluten-free breadcrumb or crushed gluten-free crackers."),
    "panko": ("gluten-free breadcrumbs", "Use a certified gluten-free breadcrumb or crushed gluten-free crackers."),
    "pasta": ("gluten-free pasta", "Use rice, corn, or legume-based pasta 1:1."),
    "spaghetti": ("gluten-free spaghetti", "Use a rice or corn-based gluten-free spaghetti 1:1."),
    "penne": ("gluten-free pasta", "Use rice, corn, or legume-based pasta 1:1."),
    "macaroni": ("gluten-free pasta", "Use rice, corn, or legume-based pasta 1:1."),
    "fusilli": ("gluten-free pasta", "Use rice, corn, or legume-based pasta 1:1."),
    "linguine": ("gluten-free pasta", "Use rice, corn, or legume-based pasta 1:1."),
    "tagliatelle": ("gluten-free pasta", "Use rice, corn, or legume-based pasta 1:1."),
    "lasagne": ("gluten-free lasagne sheets", "Use rice or corn-based gluten-free sheets 1:1."),
    "lasagna": ("gluten-free lasagne sheets", "Use rice or corn-based gluten-free sheets 1:1."),
    "noodles": ("rice noodles", "Substitute 1:1 in most stir-fries and soups."),
    "egg noodles": ("rice noodles", "Substitute 1:1; also removes the egg content."),
    "couscous": ("quinoa", "Use in equal amounts as a gluten-free grain substitute."),
    "bulgur": ("quinoa", "Use in equal amounts as a gluten-free grain substitute."),
    "barley": ("quinoa", "Use in equal amounts as a gluten-free grain substitute."),
    "rye": ("gluten-free flour blend", "Use a 1:1 gluten-free blend for baking."),
    "pastry": ("gluten-free pastry", "Use a certified gluten-free pastry or pie crust."),
    "puff pastry": ("gluten-free puff pastry", "Use a certified gluten-free puff pastry."),
    "pie crust": ("gluten-free pie crust", "Use a certified gluten-free pie crust."),
    "tortilla": ("corn tortilla", "Use a corn tortilla in place of a wheat one."),
    "pita": ("gluten-free flatbread", "Use a certified gluten-free flatbread or wrap."),
    "bun": ("gluten-free bun", "Use a certified gluten-free bun or lettuce wrap."),
    "baguette": ("gluten-free bread", "Use a certified gluten-free loaf."),
    "cracker": ("gluten-free crackers", "Use a certified gluten-free cracker."),
    "soy sauce": ("coconut aminos", "Substitute 1:1; slightly sweeter and lower sodium."),
    "worcestershire sauce": ("vegan worcestershire sauce", "Use a fish-free worcestershire-style sauce 1:1."),
    "egg": ("flax egg", "1 tbsp ground flaxseed + 3 tbsp water, rested 5 minutes, replaces 1 egg."),
    "quail egg": ("flax egg", "1 tbsp ground flaxseed + 3 tbsp water, rested 5 minutes, replaces 1 egg."),
    "mayonnaise": ("egg-free mayonnaise", "Use a store-bought vegan mayonnaise 1:1."),
    "meringue": ("aquafaba meringue", "Whipped chickpea brine (aquafaba) whips up similarly to egg whites."),
    "butter": ("vegan margarine", "Use a plant-based margarine or coconut oil in equal amounts."),
    "milk": ("oat milk", "Substitute 1:1 for dairy milk in most recipes."),
    "buttermilk": ("oat milk + lemon juice", "1 cup oat milk + 1 tbsp lemon juice, rested 5 minutes."),
    "cheese": ("dairy-free cheese", "Use a plant-based cheese alternative; melting behavior may differ."),
    "cheddar": ("dairy-free cheddar", "Use a plant-based cheddar-style alternative."),
    "mozzarella": ("dairy-free mozzarella", "Use a plant-based mozzarella alternative; melting behavior may differ."),
    "parmesan": ("nutritional yeast", "Use to taste for a similar savory, cheesy flavor."),
    "pecorino": ("nutritional yeast", "Use to taste for a similar savory, cheesy flavor."),
    "feta": ("dairy-free feta", "Use a plant-based feta-style alternative, often made from tofu."),
    "ricotta": ("blended firm tofu", "Blended with lemon juice and salt for a similar texture."),
    "mascarpone": ("cashew cream", "Blended soaked cashews for a similar rich texture."),
    "brie": ("dairy-free soft cheese", "Use a plant-based soft cheese alternative."),
    "gouda": ("dairy-free cheese", "Use a plant-based cheese alternative; melting behavior may differ."),
    "halloumi": ("firm tofu", "Sliced and pan-seared for a similar salty, chewy texture."),
    "cream": ("coconut cream", "Substitute 1:1 in most sauces and desserts."),
    "cream cheese": ("dairy-free cream cheese", "Use a plant-based cream cheese alternative 1:1."),
    "heavy cream": ("coconut cream", "Substitute 1:1 in most sauces and desserts."),
    "whipping cream": ("coconut cream", "Chilled and whipped, substitutes 1:1."),
    "sour cream": ("dairy-free sour cream", "Use a plant-based sour cream alternative 1:1."),
    "yogurt": ("coconut yogurt", "Substitute 1:1 in most recipes."),
    "yoghurt": ("coconut yogurt", "Substitute 1:1 in most recipes."),
    "condensed milk": ("dairy-free condensed milk", "Use a coconut-based condensed milk alternative 1:1."),
    "evaporated milk": ("oat milk", "Substitute 1:1; simmer briefly to thicken if needed."),
    "milk chocolate": ("dairy-free dark chocolate", "Use a dairy-free dark chocolate 1:1."),
    "custard": ("dairy-free custard", "Use a coconut or oat milk based custard alternative."),
    "ice cream": ("dairy-free ice cream", "Use a coconut or oat milk based ice cream alternative."),
    "honey": ("maple syrup", "Use in equal amounts; slightly thinner consistency."),
    "chicken": ("seitan", "Sliced or cubed and seasoned similarly, pan-seared or baked."),
    "beef": ("seitan", "Use in equal amounts; adjust cooking time as it needs less."),
    "ground beef": ("plant-based mince", "Use a store-bought plant-based mince 1:1."),
    "mince": ("plant-based mince", "Use a store-bought plant-based mince 1:1."),
    "pork": ("jackfruit", "Shredded and seasoned similarly for a comparable texture."),
    "bacon": ("smoked tempeh", "Sliced thin and pan-fried for a similar smoky, salty bite."),
    "pancetta": ("smoked tempeh", "Sliced thin and pan-fried for a similar smoky, salty bite."),
    "prosciutto": ("smoked tempeh", "Thinly sliced for a similar salty, savory note."),
    "guanciale": ("smoked tempeh", "Sliced thin and pan-fried for a similar smoky, salty bite."),
    "chorizo": ("spiced plant-based sausage", "Use a store-bought spiced plant-based sausage."),
    "sausage": ("plant-based sausage", "Use a store-bought plant-based sausage 1:1."),
    "salami": ("plant-based salami", "Use a store-bought plant-based deli slice."),
    "ham": ("smoked tempeh", "Sliced thin for a similar smoky, savory note."),
    "turkey": ("seitan", "Sliced or cubed and seasoned similarly, pan-seared or baked."),
    "duck": ("seitan", "Seasoned similarly and pan-seared or baked."),
    "lamb": ("jackfruit", "Shredded and seasoned similarly for a comparable texture."),
    "veal": ("seitan", "Sliced or cubed and seasoned similarly, pan-seared or baked."),
    "venison": ("seitan", "Seasoned similarly and pan-seared or baked."),
    "chicken stock": ("vegetable stock", "Substitute 1:1 in soups and sauces."),
    "beef stock": ("vegetable stock", "Substitute 1:1 in soups and sauces."),
    "chicken broth": ("vegetable broth", "Substitute 1:1 in soups and sauces."),
    "beef broth": ("vegetable broth", "Substitute 1:1 in soups and sauces."),
    "gelatin": ("agar agar", "Use about half the amount of agar agar powder as a plant-based setting agent."),
    "salmon": ("marinated tofu", "Firm tofu marinated in similar seasonings, pan-seared or baked."),
    "tuna": ("mashed chickpeas", "Mashed with the same seasonings for a similar texture in salads and sandwiches."),
    "cod": ("marinated tofu", "Firm tofu marinated in similar seasonings, pan-seared or baked."),
    "haddock": ("marinated tofu", "Firm tofu marinated in similar seasonings, pan-seared or baked."),
    "halibut": ("marinated tofu", "Firm tofu marinated in similar seasonings, pan-seared or baked."),
    "mackerel": ("marinated tofu", "Firm tofu marinated in similar seasonings, pan-seared or baked."),
    "sardine": ("marinated tofu", "Firm tofu marinated in similar seasonings, pan-seared or baked."),
    "trout": ("marinated tofu", "Firm tofu marinated in similar seasonings, pan-seared or baked."),
    "anchovy": ("capers", "Use a small amount for a similar salty, briny note."),
    "sea bass": ("marinated tofu", "Firm tofu marinated in similar seasonings, pan-seared or baked."),
    "fish sauce": ("soy sauce", "Use a small amount as a savory, salty substitute; flavor profile differs."),
    "fish stock": ("vegetable stock", "Substitute 1:1 in soups and sauces."),
    "shrimp": ("king oyster mushroom", "Sliced and pan-seared for a similar texture."),
    "prawn": ("king oyster mushroom", "Sliced and pan-seared for a similar texture."),
    "crab": ("hearts of palm", "Shredded for a similar texture in salads and cakes."),
    "lobster": ("king oyster mushroom", "Sliced and pan-seared for a similar texture."),
    "mussels": ("king oyster mushroom", "Sliced and pan-seared for a similar texture."),
    "clams": ("king oyster mushroom", "Sliced and pan-seared for a similar texture."),
    "oyster": ("king oyster mushroom", "Sliced and pan-seared for a similar texture."),
    "scallop": ("king oyster mushroom", "Sliced into rounds and pan-seared for a similar texture."),
    "squid": ("king oyster mushroom", "Sliced into rings and pan-seared for a similar texture."),
    "calamari": ("king oyster mushroom", "Sliced into rings and pan-seared for a similar texture."),
    "almond": ("sunflower seeds", "Use in equal amounts for baking or snacking."),
    "walnut": ("sunflower seeds", "Use in equal amounts for baking or snacking."),
    "cashew": ("sunflower seeds", "Use in equal amounts for baking or sauces."),
    "hazelnut": ("sunflower seeds", "Use in equal amounts for baking or snacking."),
    "pistachio": ("sunflower seeds", "Use in equal amounts for baking or snacking."),
    "pecan": ("sunflower seeds", "Use in equal amounts for baking or snacking."),
    "macadamia": ("sunflower seeds", "Use in equal amounts for baking or snacking."),
    "brazil nut": ("sunflower seeds", "Use in equal amounts for baking or snacking."),
    "pine nut": ("sunflower seeds", "Use in equal amounts in pesto or baking."),
    "peanut": ("sunflower seeds", "Use in equal amounts for snacking or toppings."),
    "peanut butter": ("sunflower seed butter", "Use in equal amounts for spreads and baking."),
    "sesame oil": ("sunflower oil", "Neutral substitute; won't replicate the toasted flavor."),
    "sesame seeds": ("poppy seeds", "Use in equal amounts as a topping."),
    "tahini": ("sunflower seed butter", "Use in equal amounts in dressings and sauces."),
    "tofu": ("chickpeas", "Use cooked chickpeas for a similar protein source in stir-fries and salads."),
    "soy milk": ("oat milk", "Substitute 1:1 for soy milk in most recipes."),
    "tempeh": ("mushroom", "Sliced and pan-seared for a similar texture."),
    "edamame": ("green peas", "Use in equal amounts in salads and stir-fries."),
    "miso": ("chickpea miso", "Use a soy-free chickpea-based miso 1:1."),
    "wine": ("grape juice", "Use in equal amounts; reduce added sugar elsewhere in the recipe."),
    "white wine": ("white grape juice", "Use in equal amounts; reduce added sugar elsewhere in the recipe."),
    "red wine": ("red grape juice", "Use in equal amounts; reduce added sugar elsewhere in the recipe."),
    "dried apricot": ("dried mango", "Use a sulphite-free dried fruit in equal amounts."),
    "raisins": ("fresh grapes", "Use a sulphite-free dried fruit, or fresh grapes, in equal amounts."),
}

def get_or_create_substitute(name, note):
    existing = db.query(Substitute).filter(Substitute.name == name).first()
    if existing:
        return existing

    substitute = Substitute(name=name, note=note)
    db.add(substitute)
    db.commit()
    print(f"Seeded substitute '{name}'")
    return substitute


def link_ingredient_substitute(ingredient, substitute, tag_name):
    tag = db.query(models.IngredientTag).filter(models.IngredientTag.name == tag_name).first()

    existing = db.query(IngredientSubstituteMap).filter(
        IngredientSubstituteMap.ingredient_id == ingredient.id,
        IngredientSubstituteMap.substitute_id == substitute.id,
        IngredientSubstituteMap.tag_id == tag.id
    ).first()

    if not existing:
        mapping = IngredientSubstituteMap(
            ingredient_id=ingredient.id,
            substitute_id=substitute.id,
            tag_id=tag.id,
        )
        db.add(mapping)
        db.commit()
        print(f"Linked substitute '{substitute.name}' to '{ingredient.name}' for tag '{tag.name}'")


for ingredient_name, (substitute_name, note) in INGREDIENT_SUBSTITUTES.items():
    ingredient = db.query(Ingredient).filter(Ingredient.name == ingredient_name).first()
    substitute = get_or_create_substitute(substitute_name, note)
    for tag_name in INGREDIENTS[ingredient_name]:
        link_ingredient_substitute(ingredient, substitute, tag_name)

db.close()
