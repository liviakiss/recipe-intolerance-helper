"""Load restriction tags, diet presets, ingredients and substitutes into the database.

Run it from the backend folder:

    python seed.py

It is safe to run again at any time: it only adds what is missing, and it keeps
the substitute links in line with seed_data.py. The data itself lives in
seed_data.py; this file is only the loading logic.
"""
from app.database import SessionLocal
from app import models
from app.ingredient_matching import normalize_ingredient_name
from seed_data import TAGS, DIET_PRESETS, INGREDIENTS, INGREDIENT_SUBSTITUTES


def _get_tag(db, name):
    return db.query(models.IngredientTag).filter(models.IngredientTag.name == name).first()


def seed_tags(db) -> int:
    created = 0
    for name in TAGS:
        if _get_tag(db, name) is None:
            db.add(models.IngredientTag(name=name))
            created += 1
    db.commit()
    return created


def seed_presets(db) -> int:
    created = 0
    for preset_name, tag_names in DIET_PRESETS.items():
        preset = db.query(models.DietPreset).filter(models.DietPreset.name == preset_name).first()
        if preset is None:
            preset = models.DietPreset(name=preset_name)
            db.add(preset)
            db.flush()  # assigns preset.id without ending the transaction
            created += 1

        for tag_name in tag_names:
            tag = _get_tag(db, tag_name)
            link = db.query(models.DietPresetTagMap).filter(
                models.DietPresetTagMap.preset_id == preset.id,
                models.DietPresetTagMap.tag_id == tag.id,
            ).first()
            if link is None:
                db.add(models.DietPresetTagMap(preset_id=preset.id, tag_id=tag.id))
                created += 1
    db.commit()
    return created


def seed_ingredients(db) -> int:
    created = 0
    for name, tag_names in INGREDIENTS.items():
        normalized = normalize_ingredient_name(name)
        ingredient = db.query(models.Ingredient).filter(
            models.Ingredient.normalized_name == normalized
        ).first()
        if ingredient is None:
            ingredient = models.Ingredient(name=name, normalized_name=normalized)
            db.add(ingredient)
            db.flush()
            created += 1

        for tag_name in tag_names:
            tag = _get_tag(db, tag_name)
            link = db.query(models.IngredientTagMap).filter(
                models.IngredientTagMap.ingredient_id == ingredient.id,
                models.IngredientTagMap.tag_id == tag.id,
            ).first()
            if link is None:
                db.add(models.IngredientTagMap(ingredient_id=ingredient.id, tag_id=tag.id))
    db.commit()
    return created


def seed_substitutes(db) -> int:
    created = 0
    for ingredient_name, (substitute_name, note) in INGREDIENT_SUBSTITUTES.items():
        ingredient = db.query(models.Ingredient).filter(
            models.Ingredient.normalized_name == normalize_ingredient_name(ingredient_name)
        ).first()

        substitute = db.query(models.Substitute).filter(
            models.Substitute.name == substitute_name
        ).first()
        if substitute is None:
            substitute = models.Substitute(name=substitute_name, note=note)
            db.add(substitute)
            db.flush()
            created += 1

        for tag_name in INGREDIENTS[ingredient_name]:
            tag = _get_tag(db, tag_name)

            # seed_data.py is the source of truth: if its substitute for this
            # ingredient + tag changed since the last run, drop the old link so
            # the database doesn't keep two competing suggestions.
            db.query(models.IngredientSubstituteMap).filter(
                models.IngredientSubstituteMap.ingredient_id == ingredient.id,
                models.IngredientSubstituteMap.tag_id == tag.id,
                models.IngredientSubstituteMap.substitute_id != substitute.id,
            ).delete()

            link = db.query(models.IngredientSubstituteMap).filter(
                models.IngredientSubstituteMap.ingredient_id == ingredient.id,
                models.IngredientSubstituteMap.substitute_id == substitute.id,
                models.IngredientSubstituteMap.tag_id == tag.id,
            ).first()
            if link is None:
                db.add(models.IngredientSubstituteMap(
                    ingredient_id=ingredient.id,
                    substitute_id=substitute.id,
                    tag_id=tag.id,
                ))
        db.flush()
    db.commit()
    return created


def seed(db) -> dict:
    """Run every step and return how many new rows each one created."""
    return {
        "tags": seed_tags(db),
        "presets": seed_presets(db),
        "ingredients": seed_ingredients(db),
        "substitutes": seed_substitutes(db),
    }


if __name__ == "__main__":
    session = SessionLocal()
    try:
        added = seed(session)
    finally:
        session.close()

    print("Seed complete. New rows added this run:")
    for kind, count in added.items():
        print(f"  {kind}: {count}")
    print(f"The dictionary now covers {len(INGREDIENTS)} ingredients.")
