from app.models import Ingredient, IngredientTagMap, IngredientTag, IngredientSubstituteMap, Substitute
from app.parser import parse_recipe
from app.normalize import normalize_ingredient_name, longest_match, qualifier_exclusions  # normalize_ingredient_name is re-exported: seed.py imports it from here

def find_ingredient(db, name: str):
    normalized = normalize_ingredient_name(name)

    # An exact match covers our own clean test recipes ("egg", "flour"), but
    # real recipe text — hand-typed or from an external source — almost
    # always carries extra descriptive words: "Pecorino Cheese",
    # "Free-range Eggs", "Boneless Chicken Thighs". Requiring the whole
    # string to match exactly meant nearly everything from a real recipe
    # fell through to "unrecognized". Instead, treat each known ingredient
    # name as a whole-word phrase that may appear anywhere inside the
    # parsed name, and prefer the longest (most specific) one that matches,
    # so "olive oil" wins over any shorter coincidental overlap.
    by_name = {
        ingredient.normalized_name: ingredient
        for ingredient in db.query(Ingredient).all()
    }

    best = longest_match(normalized, by_name.keys())
    return by_name[best] if best is not None else None

def get_tags_for_ingredient(db, ingredient):
    tag_maps = db.query(IngredientTagMap).filter(
        IngredientTagMap.ingredient_id == ingredient.id
    ).all()
    tag_ids = [tag_map.tag_id for tag_map in tag_maps]
    return db.query(IngredientTag).filter(IngredientTag.id.in_(tag_ids)).all()


def check_recipe(db, raw_text: str , active_tag_ids: list[int]):
    parsed_ingredients = parse_recipe(raw_text)
    return [
        classify_ingredient(db, ingredient, active_tag_ids)
        for ingredient in parsed_ingredients
    ]

def get_substitute(db, ingredient, tag_id):
    mapping = db.query(IngredientSubstituteMap).filter(
        IngredientSubstituteMap.ingredient_id == ingredient.id,
        IngredientSubstituteMap.tag_id == tag_id
    ).first()

    if mapping is None:
        return None

    return db.query(Substitute).filter(Substitute.id == mapping.substitute_id).first()


def classify_ingredient(db, parsed_ingredient, active_tag_ids):
    ingredient = find_ingredient(db, parsed_ingredient["name"])

    if ingredient is None:
        return {
            **parsed_ingredient,
            "status": "unrecognized",
            "matched_tags": [],
            "substitute": None,
            "ingredient_id": None,
            "flagged_tag_id": None,
            "substitute_id": None,
        }

    # "gluten-free pasta" matches the pasta entry, but the qualifier cancels
    # the gluten tag; see FREE_FROM_QUALIFIERS in app/normalize.py.
    cancelled = qualifier_exclusions(normalize_ingredient_name(parsed_ingredient["name"]))
    tags = [
        tag for tag in get_tags_for_ingredient(db, ingredient)
        if tag.name not in cancelled
    ]
    tag_ids = {tag.id for tag in tags}
    conflicting_tag_ids = tag_ids & set(active_tag_ids)

    if conflicting_tag_ids:
        status = "flagged"
        flagged_tag_id = min(conflicting_tag_ids)  # deterministic when several restrictions conflict
        substitute = get_substitute(db, ingredient, flagged_tag_id)
        substitute_info = {"name": substitute.name, "note": substitute.note} if substitute else None
        substitute_id = substitute.id if substitute else None
    else:
        status = "safe"
        flagged_tag_id = None
        substitute_info = None
        substitute_id = None

    return {
        **parsed_ingredient,
        "status": status,
        "matched_tags": [tag.name for tag in tags],
        "substitute": substitute_info,
        "ingredient_id": ingredient.id,
        "flagged_tag_id": flagged_tag_id,
        "substitute_id": substitute_id,
    }
