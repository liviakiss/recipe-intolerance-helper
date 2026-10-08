"""Tests for `python seed.py`, run against a throwaway database.

These use the real dictionary from seed_data.py, so they also prove the whole
pipeline works with the data the app actually ships with.
"""
import pytest

import seed
from app import models
from app.ingredient_matching import classify_ingredient, check_recipe
from seed_data import TAGS, DIET_PRESETS, INGREDIENTS, INGREDIENT_SUBSTITUTES


@pytest.fixture()
def seeded(db):
    seed.seed(db)
    return db


def tag_id(db, name):
    return db.query(models.IngredientTag).filter(models.IngredientTag.name == name).one().id


def row_counts(db):
    return {
        table.__tablename__: db.query(table).count()
        for table in (
            models.IngredientTag, models.DietPreset, models.DietPresetTagMap,
            models.Ingredient, models.IngredientTagMap,
            models.Substitute, models.IngredientSubstituteMap,
        )
    }


# ---------- what seeding creates ----------

def test_seed_loads_everything_in_the_data_file(seeded):
    counts = row_counts(seeded)

    assert counts["ingredient_tags"] == len(TAGS)
    assert counts["diet_presets"] == len(DIET_PRESETS)
    assert counts["diet_preset_tag_map"] == sum(len(tags) for tags in DIET_PRESETS.values())
    assert counts["ingredients"] == len(INGREDIENTS)
    assert counts["ingredient_tag_map"] == sum(len(tags) for tags in INGREDIENTS.values())
    assert counts["ingredient_substitute_map"] == sum(len(INGREDIENTS[name]) for name in INGREDIENT_SUBSTITUTES)


def test_presets_end_up_linked_to_the_right_tags(seeded):
    for preset_name, expected in DIET_PRESETS.items():
        preset = seeded.query(models.DietPreset).filter(models.DietPreset.name == preset_name).one()
        linked = {
            seeded.get(models.IngredientTag, link.tag_id).name
            for link in seeded.query(models.DietPresetTagMap).filter(models.DietPresetTagMap.preset_id == preset.id)
        }
        assert linked == set(expected), preset_name


# ---------- running it again ----------

def test_seeding_twice_changes_nothing(db):
    seed.seed(db)
    after_first = row_counts(db)

    added_second_time = seed.seed(db)

    assert row_counts(db) == after_first
    assert added_second_time == {"tags": 0, "presets": 0, "ingredients": 0, "substitutes": 0}


def test_a_changed_substitute_replaces_the_old_link(seeded):
    # Simulate a database seeded by an older version, where custard's egg
    # substitute was something else.
    custard = seeded.query(models.Ingredient).filter(models.Ingredient.name == "custard").one()
    egg = tag_id(seeded, "egg")
    legacy = models.Substitute(name="legacy custard", note="old suggestion")
    seeded.add(legacy)
    seeded.flush()
    link = seeded.query(models.IngredientSubstituteMap).filter(
        models.IngredientSubstituteMap.ingredient_id == custard.id,
        models.IngredientSubstituteMap.tag_id == egg,
    ).one()
    link.substitute_id = legacy.id
    seeded.commit()

    seed.seed(seeded)

    links = seeded.query(models.IngredientSubstituteMap).filter(
        models.IngredientSubstituteMap.ingredient_id == custard.id,
        models.IngredientSubstituteMap.tag_id == egg,
    ).all()
    assert len(links) == 1
    assert seeded.get(models.Substitute, links[0].substitute_id).name == INGREDIENT_SUBSTITUTES["custard"][0]


# ---------- the shipped dictionary, through the real matcher ----------

def test_every_ingredient_with_a_substitute_returns_it_when_flagged(seeded):
    """For each ingredient + restriction that has a swap, the app must show that swap."""
    for ingredient_name, (expected_substitute, _note) in INGREDIENT_SUBSTITUTES.items():
        for tag_name in INGREDIENTS[ingredient_name]:
            result = classify_ingredient(
                seeded,
                {"quantity": None, "unit": None, "name": ingredient_name},
                [tag_id(seeded, tag_name)],
            )
            assert result["status"] == "flagged", (ingredient_name, tag_name)
            assert result["substitute"]["name"] == expected_substitute, (ingredient_name, tag_name)


def test_a_realistic_recipe_with_the_real_dictionary(seeded):
    recipe = (
        "2 eggs\n"
        "200 g plain flour\n"
        "100 g butter\n"
        "1 tsp cream of tartar\n"
        "2 bay leaves\n"
        "1 cup dairy-free milk\n"
        "1 jar mystery relish"
    )

    results = check_recipe(seeded, recipe, [tag_id(seeded, "gluten"), tag_id(seeded, "dairy")])

    assert [r["status"] for r in results] == [
        "safe",          # eggs: egg isn't one of the active restrictions
        "flagged",       # flour: gluten
        "flagged",       # butter: dairy
        "safe",          # cream of tartar is not cream
        "safe",          # "bay leaves" finds "bay leaf"
        "safe",          # dairy-free milk
        "unrecognized",  # not in the dictionary: never reported as safe
    ]


def test_shrimp_is_flagged_for_the_vegan_and_vegetarian_presets(seeded):
    for preset_name in ("vegan", "vegetarian"):
        preset = seeded.query(models.DietPreset).filter(models.DietPreset.name == preset_name).one()
        preset_tag_ids = [
            link.tag_id
            for link in seeded.query(models.DietPresetTagMap).filter(models.DietPresetTagMap.preset_id == preset.id)
        ]

        result = check_recipe(seeded, "200 g shrimp", preset_tag_ids)[0]

        assert result["status"] == "flagged", preset_name
