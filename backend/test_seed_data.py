"""Tests for the ingredient dictionary itself (seed_data.py).

The dictionary is data, but it is also where most real-world mistakes would
come from: a typo in a tag name, two entries that collapse into one, or a
"safe" substitute that the app would flag itself. These tests catch that
without needing a database.
"""
import pytest

from app.normalize import normalize_ingredient_name, longest_match, qualifier_exclusions
from seed_data import TAGS, DIET_PRESETS, INGREDIENTS, INGREDIENT_SUBSTITUTES

NORMALIZED = {normalize_ingredient_name(name): name for name in INGREDIENTS}


def tags_for(text: str):
    """What the matcher would conclude about a line of recipe text.

    Returns a set of tag names, or None if the text isn't recognized at all.
    Uses the same rules as the real matcher: longest whole-word match, then
    free-from qualifiers like "gluten-free" or "vegan".
    """
    normalized = normalize_ingredient_name(text)
    best = longest_match(normalized, NORMALIZED.keys())
    if best is None:
        return None
    return set(INGREDIENTS[NORMALIZED[best]]) - qualifier_exclusions(normalized)


# ---------- structure ----------

def test_dictionary_is_not_tiny():
    # Guards against an accidental truncation of the data.
    assert len(INGREDIENTS) >= 500


def test_every_tag_used_is_a_real_tag():
    unknown = {(name, tag) for name, tags in INGREDIENTS.items() for tag in tags if tag not in TAGS}
    assert not unknown


def test_no_two_entries_collapse_into_one():
    # Seeding looks entries up by normalized name, so two names that normalize
    # the same would silently merge ("peas" and "pea", say).
    seen = {}
    for name in INGREDIENTS:
        seen.setdefault(normalize_ingredient_name(name), []).append(name)
    collisions = {key: names for key, names in seen.items() if len(names) > 1}
    assert not collisions


def test_names_are_clean_lowercase_text():
    messy = [name for name in INGREDIENTS if name != name.strip().lower() or "  " in name]
    assert not messy


# Words whose plural is not made by adding "s" (or is never used in recipes).
PLURAL_EXEMPT = {"brie", "roe", "creme fraiche", "dulce de leche"}


def test_a_plural_in_a_recipe_still_finds_the_entry():
    """If a recipe says "2 peaches", the entry "peach" must be found.

    Checks that adding an "s" to the last word normalizes back to the same
    thing. Catches entries like "cookie" (whose plural "cookies" would turn
    into "cooky").
    """
    def pluralize(name):
        *front, last = name.split(" ")
        if last.endswith("y") and last[-2] not in "aeiou":
            last = last[:-1] + "ies"
        elif last.endswith(("x", "z", "ch", "sh")):
            last += "es"
        else:
            last += "s"
        return " ".join(front + [last])

    unstable = [
        name for name in INGREDIENTS
        if not name.endswith("s") and name not in PLURAL_EXEMPT
        and normalize_ingredient_name(pluralize(name)) != normalize_ingredient_name(name)
    ]
    assert not unstable


# ---------- presets ----------

def test_presets_only_use_real_tags():
    unknown = {(preset, tag) for preset, tags in DIET_PRESETS.items() for tag in tags if tag not in TAGS}
    assert not unknown


def test_vegan_and_vegetarian_presets_cover_shellfish():
    # Regression: shrimp used to pass both presets.
    assert {"meat", "fish", "shellfish"} <= set(DIET_PRESETS["vegetarian"])
    assert {"meat", "fish", "shellfish", "dairy", "egg", "honey"} <= set(DIET_PRESETS["vegan"])


# ---------- substitutes ----------

def test_substitutes_belong_to_ingredients_that_can_be_flagged():
    for name in INGREDIENT_SUBSTITUTES:
        assert name in INGREDIENTS, f"substitute listed for unknown ingredient {name!r}"
        assert INGREDIENTS[name], f"{name!r} has no tags, so its substitute can never be shown"


def test_every_substitute_has_a_note():
    for name, (substitute, note) in INGREDIENT_SUBSTITUTES.items():
        assert substitute.strip() and note.strip(), name


def test_a_suggested_substitute_never_triggers_the_restriction_it_solves():
    """Paste the app's own suggestion back in: it must not be flagged.

    For every ingredient + tag that has a substitute, run the substitute's
    name through the matcher. If it still carries that tag, the app would be
    recommending something it then warns you about.
    """
    problems = []
    for ingredient, (substitute, _note) in INGREDIENT_SUBSTITUTES.items():
        found = tags_for(substitute)
        if found is None:
            continue  # not in the dictionary, so it can't be flagged either
        for tag in INGREDIENTS[ingredient]:
            if tag in found:
                problems.append((ingredient, tag, substitute))
    assert not problems


# ---------- the traps the dictionary was built to avoid ----------

@pytest.mark.parametrize("text, expected", [
    # A broad word inside a longer name must not drag in the wrong tag.
    ("1 tsp cream of tartar", set()),          # not cream
    ("2 tbsp cocoa butter", set()),            # not butter
    ("1 can butter beans", set()),             # not butter
    ("200 g almond flour", {"tree_nuts"}),     # not gluten
    ("200 g rice flour", set()),               # not gluten
    ("250 g rice pasta", set()),               # not gluten
    ("2 tbsp white wine vinegar", set()),      # not wine
    ("1 cup coconut milk", set()),             # not dairy
    ("2 tbsp sunflower seed butter", set()),   # not butter
    ("2 tbsp peanut butter", {"peanuts"}),     # peanuts only, not dairy
    ("1 eggplant", set()),                     # not egg
    ("2 corn tortillas", set()),               # not gluten
    # Free-from qualifiers.
    ("200 g gluten-free pasta", set()),
    ("100 g dairy-free cheddar", set()),
    ("2 tbsp vegan butter", set()),
    ("1 cup lactose-free milk", {"dairy"}),    # still dairy
    # And the ordinary cases still work.
    ("3 eggs", {"egg"}),
    ("200 g plain flour", {"gluten"}),
    ("100 g butter", {"dairy", "lactose"}),
    ("2 bay leaves", set()),
    ("1 red chilli", set()),
    ("Crème fraîche", {"dairy", "lactose"}),
])
def test_known_tricky_phrases(text, expected):
    assert tags_for(text) == expected


@pytest.mark.parametrize("text", [
    "1 bar of chocolate",
    "2 tbsp hoisin sauce",
    "1 tbsp margarine",
    "1 tbsp tamari",
])
def test_brand_dependent_ingredients_stay_unrecognized(text):
    # Their tags depend on the product, so the app says "unrecognized"
    # instead of guessing "safe".
    assert tags_for(text) is None
