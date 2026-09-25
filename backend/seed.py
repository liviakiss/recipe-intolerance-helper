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


INGREDIENTS = {
    "flour": ["gluten"],
    "egg": ["egg"],
    "butter": ["dairy", "lactose"],
    "milk": ["dairy", "lactose"],
    "honey": ["honey"],
    "soy sauce": ["soy", "gluten"],
    "peanut butter": ["peanuts"],
    "shrimp": ["shellfish"],
    "salmon": ["fish"],
    "almond": ["tree_nuts"],
    "sesame oil": ["sesame"],
    "garlic": [],
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

INGREDIENT_SUBSTITUTES = {
    "flour": ("gluten-free flour blend", "Use a 1:1 gluten-free blend for most baking recipes."),
    "egg": ("flax egg", "1 tbsp ground flaxseed + 3 tbsp water, rested 5 minutes, replaces 1 egg."),
    "butter": ("vegan margarine", "Use a plant-based margarine or coconut oil in equal amounts."),
    "milk": ("oat milk", "Substitute 1:1 for dairy milk in most recipes."),
    "honey": ("maple syrup", "Use in equal amounts; slightly thinner consistency."),
    "soy sauce": ("coconut aminos", "Substitute 1:1; slightly sweeter and lower sodium."),
    "peanut butter": ("sunflower seed butter", "Use in equal amounts for spreads and baking."),
    "shrimp": ("king oyster mushroom", "Sliced and pan-seared for a similar texture."),
    "salmon": ("marinated tofu", "Firm tofu marinated in similar seasonings, pan-seared or baked."),
    "almond": ("sunflower seeds", "Use in equal amounts for baking or snacking."),
    "sesame oil": ("sunflower oil", "Neutral substitute; won't replicate the toasted flavor."),
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