import re
from app.models import Ingredient, IngredientTagMap, IngredientTag
from app.parser import parse_recipe

IRREGULAR_PLURALS = {
    "leaves": "leaf",
    "knives": "knife",
    "loaves": "loaf",
}

def normalize_ingredient_name(name: str) -> str:
    word = name.strip().lower()
    word = word.replace("-", " ")
    word = re.sub(r"[.,'’]", "", word)
    word = re.sub(r"\s+", " ", word).strip()

    if word in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[word]
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("oes"):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]

    return word

def find_ingredient(db, name: str):
    normalized = normalize_ingredient_name(name)
    return db.query(Ingredient).filter(Ingredient.normalized_name == normalized).first()

def get_tags_for_ingredient(db, ingredient):
    tag_maps = db.query(IngredientTagMap).filter(
        IngredientTagMap.ingredient_id == ingredient.id
    ).all()
    tag_ids = [tag_map.tag_id for tag_map in tag_maps]
    return db.query(IngredientTag).filter(IngredientTag.id.in_(tag_ids)).all()


def classify_ingredient(db, parsed_ingredient, active_tag_ids):
        ingredient = find_ingredient(db, parsed_ingredient["name"])

        if ingredient is None:
            return {**parsed_ingredient, "status": "unrecognized", "matched_tags": []}

        tags = get_tags_for_ingredient(db, ingredient)
        tag_ids = {tag.id for tag in tags}

        if tag_ids & set(active_tag_ids):
            status = "flagged"
        else:
            status = "safe"

        return {**parsed_ingredient, "status": status, "matched_tags": [tag.name for tag in tags]}

def check_recipe(db, raw_text: str , active_tag_ids: list[int]):
    parsed_ingredients = parse_recipe(raw_text)
    return [
        classify_ingredient(db, ingredient, active_tag_ids)
        for ingredient in parsed_ingredients
    ]

    