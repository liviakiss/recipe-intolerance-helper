"""Tests for the ingredient matcher: how a line of recipe text becomes flagged / safe / unrecognized.

Each test builds the tiny dictionary it needs in a throwaway database, so the
rule being tested is visible right in the test.
"""
from app import models
from app.ingredient_matching import find_ingredient, classify_ingredient, check_recipe


def line(name, quantity=None, unit=None):
    """A parsed ingredient line, as parse_recipe would produce it."""
    return {"quantity": quantity, "unit": unit, "name": name}


# ---------- the three outcomes ----------

def test_flagged_safe_and_unrecognized_are_three_different_outcomes(db, tag_ids, add_ingredient):
    add_ingredient("flour", ["gluten"])
    add_ingredient("salt", [])
    active = [tag_ids["gluten"]]

    assert classify_ingredient(db, line("flour"), active)["status"] == "flagged"
    assert classify_ingredient(db, line("salt"), active)["status"] == "safe"
    assert classify_ingredient(db, line("dragon scales"), active)["status"] == "unrecognized"


def test_unknown_ingredient_is_never_reported_as_safe(db, tag_ids, add_ingredient):
    # The app must not claim something is fine just because it doesn't know it.
    add_ingredient("flour", ["gluten"])
    result = classify_ingredient(db, line("mystery relish"), [tag_ids["gluten"]])

    assert result["status"] == "unrecognized"
    assert result["matched_tags"] == []
    assert result["ingredient_id"] is None
    assert result["substitute"] is None


def test_a_known_ingredient_is_only_flagged_for_active_restrictions(db, tag_ids, add_ingredient):
    add_ingredient("butter", ["dairy", "lactose"])

    assert classify_ingredient(db, line("butter"), [tag_ids["gluten"]])["status"] == "safe"
    assert classify_ingredient(db, line("butter"), [tag_ids["dairy"]])["status"] == "flagged"
    assert classify_ingredient(db, line("butter"), [])["status"] == "safe"


# ---------- longest match wins ----------

def test_the_longest_matching_name_wins(db, tag_ids, add_ingredient):
    add_ingredient("butter", ["dairy", "lactose"])
    add_ingredient("peanut butter", ["peanuts"])

    result = classify_ingredient(db, line("peanut butter"), [tag_ids["dairy"]])

    # Peanut butter is a peanut product, not a dairy one.
    assert result["status"] == "safe"
    assert result["matched_tags"] == ["peanuts"]
    assert classify_ingredient(db, line("peanut butter"), [tag_ids["peanuts"]])["status"] == "flagged"


def test_the_shorter_name_is_used_when_the_longer_one_is_not_in_the_dictionary(db, tag_ids, add_ingredient):
    add_ingredient("butter", ["dairy", "lactose"])

    result = classify_ingredient(db, line("unsalted butter"), [tag_ids["dairy"]])

    assert result["status"] == "flagged"
    assert find_ingredient(db, "unsalted butter").name == "butter"


def test_extra_descriptive_words_around_the_name_are_fine(db, tag_ids, add_ingredient):
    add_ingredient("egg", ["egg"])
    add_ingredient("chicken", ["meat"])

    assert find_ingredient(db, "Free-range Eggs").name == "egg"
    assert find_ingredient(db, "Boneless Chicken Thighs").name == "chicken"


def test_only_whole_words_match(db, add_ingredient):
    add_ingredient("egg", ["egg"])
    add_ingredient("butter", ["dairy"])

    assert find_ingredient(db, "eggplant") is None
    assert find_ingredient(db, "butternut squash") is None


def test_equal_length_matches_always_resolve_the_same_way(db, tag_ids, add_ingredient):
    # "rice" and "wine" are both four letters and both appear in "rice wine".
    add_ingredient("rice", [])
    add_ingredient("wine", ["sulphites"])

    assert find_ingredient(db, "rice wine").name == "wine"


# ---------- normalization reaches the matcher ----------

def test_plural_recipe_text_finds_the_singular_entry(db, add_ingredient):
    add_ingredient("bay leaf", [])
    add_ingredient("tomato", [])
    add_ingredient("chilli", [])

    assert find_ingredient(db, "bay leaves").name == "bay leaf"
    assert find_ingredient(db, "tomatoes").name == "tomato"
    assert find_ingredient(db, "red chillies").name == "chilli"


def test_accented_recipe_text_finds_the_plain_entry(db, add_ingredient):
    add_ingredient("creme fraiche", ["dairy"])

    assert find_ingredient(db, "Crème fraîche").name == "creme fraiche"


# ---------- free-from qualifiers ----------

def test_gluten_free_version_is_not_flagged_for_gluten(db, tag_ids, add_ingredient):
    add_ingredient("pasta", ["gluten"], substitute=("gluten-free pasta", "Use rice pasta 1:1."))
    active = [tag_ids["gluten"]]

    plain = classify_ingredient(db, line("pasta"), active)
    gluten_free = classify_ingredient(db, line("gluten-free pasta"), active)

    assert plain["status"] == "flagged"
    assert gluten_free["status"] == "safe"
    assert gluten_free["substitute"] is None


def test_a_qualifier_only_cancels_the_tags_it_covers(db, tag_ids, add_ingredient):
    add_ingredient("soy sauce", ["soy", "gluten"])
    active = [tag_ids["soy"]]

    # "gluten-free soy sauce" is still soy sauce.
    result = classify_ingredient(db, line("gluten-free soy sauce"), active)

    assert result["status"] == "flagged"
    assert result["matched_tags"] == ["soy"]


def test_lactose_free_milk_is_still_dairy(db, tag_ids, add_ingredient):
    add_ingredient("milk", ["dairy", "lactose"])

    lactose = classify_ingredient(db, line("lactose-free milk"), [tag_ids["lactose"]])
    dairy = classify_ingredient(db, line("lactose-free milk"), [tag_ids["dairy"]])

    assert lactose["status"] == "safe"
    assert dairy["status"] == "flagged"


def test_vegan_cancels_animal_tags(db, tag_ids, add_ingredient):
    add_ingredient("mayonnaise", ["egg"])

    result = classify_ingredient(db, line("vegan mayonnaise"), [tag_ids["egg"]])

    assert result["status"] == "safe"


# ---------- substitutes ----------

def test_flagged_ingredient_comes_with_its_substitute(db, tag_ids, add_ingredient):
    add_ingredient("butter", ["dairy", "lactose"], substitute=("vegan margarine", "Use in equal amounts."))

    result = classify_ingredient(db, line("butter"), [tag_ids["dairy"]])

    assert result["substitute"] == {"name": "vegan margarine", "note": "Use in equal amounts."}
    assert result["substitute_id"] is not None
    assert result["flagged_tag_id"] == tag_ids["dairy"]


def test_substitute_depends_on_which_restriction_was_hit(db, tag_ids, add_ingredient):
    soy_sauce = add_ingredient("soy sauce", ["soy", "gluten"])

    # Two different swaps for the same ingredient, one per restriction.
    for tag, sub_name in (("soy", "coconut aminos"), ("gluten", "tamari-style sauce")):
        sub = models.Substitute(name=sub_name, note=None)
        db.add(sub)
        db.flush()
        db.add(models.IngredientSubstituteMap(
            ingredient_id=soy_sauce.id, substitute_id=sub.id, tag_id=tag_ids[tag],
        ))
    db.commit()

    for_soy = classify_ingredient(db, line("soy sauce"), [tag_ids["soy"]])
    for_gluten = classify_ingredient(db, line("soy sauce"), [tag_ids["gluten"]])

    assert for_soy["substitute"]["name"] == "coconut aminos"
    assert for_gluten["substitute"]["name"] == "tamari-style sauce"


def test_flagged_ingredient_without_a_substitute_still_flags(db, tag_ids, add_ingredient):
    add_ingredient("mustard", ["mustard"])

    result = classify_ingredient(db, line("mustard"), [tag_ids["mustard"]])

    assert result["status"] == "flagged"
    assert result["substitute"] is None
    assert result["substitute_id"] is None


def test_when_several_restrictions_conflict_the_lowest_tag_id_is_reported(db, tag_ids, add_ingredient):
    add_ingredient("cheese", ["dairy", "lactose"])
    active = [tag_ids["dairy"], tag_ids["lactose"]]

    result = classify_ingredient(db, line("cheese"), list(reversed(active)))

    assert result["flagged_tag_id"] == min(active)


# ---------- whole recipes ----------

def test_check_recipe_parses_and_classifies_every_line(db, tag_ids, add_ingredient):
    add_ingredient("egg", ["egg"])
    add_ingredient("flour", ["gluten"])

    results = check_recipe(
        db,
        "2 eggs\n1 1/2 cups flour, sifted\n3 unicorn tears",
        [tag_ids["egg"]],
    )

    assert [r["status"] for r in results] == ["flagged", "safe", "unrecognized"]
    assert [r["quantity"] for r in results] == [2.0, 1.5, 3.0]
    assert [r["unit"] for r in results] == [None, "cups", None]
    assert results[1]["name"] == "flour"


def test_empty_text_gives_no_results(db, tag_ids):
    assert check_recipe(db, "", [tag_ids["gluten"]]) == []
    assert check_recipe(db, "\n\n  \n", [tag_ids["gluten"]]) == []


def test_everything_is_unrecognized_with_an_empty_dictionary(db, tag_ids):
    results = check_recipe(db, "2 eggs\n1 cup flour", [tag_ids["egg"]])

    assert [r["status"] for r in results] == ["unrecognized", "unrecognized"]
