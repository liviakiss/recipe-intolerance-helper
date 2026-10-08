"""Tests for the name normalizer, the longest-match rule and free-from qualifiers.

These are pure functions, so no database is involved and the tests run instantly.
"""
import pytest

from app.normalize import (
    normalize_ingredient_name,
    longest_match,
    qualifier_exclusions,
)


# ---------- normalize_ingredient_name ----------

@pytest.mark.parametrize("raw, expected", [
    ("Free-range Eggs", "free range egg"),
    ("  Olive   Oil  ", "olive oil"),
    ("Parmesan, grated", "parmesan grated"),     # punctuation is dropped, words are kept
    ("Za'atar", "zaatar"),
])
def test_basic_cleanup(raw, expected):
    assert normalize_ingredient_name(raw) == expected


@pytest.mark.parametrize("plural, singular", [
    ("eggs", "egg"),
    ("berries", "berry"),
    ("tomatoes", "tomato"),
    ("potatoes", "potato"),
    ("peaches", "peach"),
    ("radishes", "radish"),
    ("boxes", "box"),
    ("glasses", "glass"),
    ("leaves", "leaf"),
    ("chillies", "chilli"),
    ("brioches", "brioche"),
])
def test_plurals_become_singular(plural, singular):
    assert normalize_ingredient_name(plural) == singular


def test_double_s_words_are_left_alone():
    assert normalize_ingredient_name("watercress") == "watercress"
    assert normalize_ingredient_name("lemongrass") == "lemongrass"


def test_short_words_are_left_alone():
    assert normalize_ingredient_name("ham") == "ham"


def test_plural_in_the_middle_of_a_phrase_is_singularized_too():
    # Regression: only the last word used to be handled, so "bay leaves" became
    # "bay leave" and never matched the dictionary entry "bay leaf".
    assert normalize_ingredient_name("bay leaves") == "bay leaf"
    assert normalize_ingredient_name("Brussels sprouts") == "brussel sprout"
    assert normalize_ingredient_name("leaves and thyme") == "leaf and thyme"


def test_accents_are_removed():
    assert normalize_ingredient_name("Crème fraîche") == "creme fraiche"
    assert normalize_ingredient_name("jalapeños") == "jalapeno"


@pytest.mark.parametrize("name", ["bay leaves", "Free-range Eggs", "chillies", "crème fraîche", "peaches"])
def test_normalizing_twice_changes_nothing(name):
    once = normalize_ingredient_name(name)
    assert normalize_ingredient_name(once) == once


# ---------- longest_match ----------

def test_longest_match_wins():
    names = ["butter", "peanut butter"]
    assert longest_match("2 tbsp peanut butter", names) == "peanut butter"


def test_a_shorter_name_still_matches_when_the_longer_one_is_absent():
    assert longest_match("unsalted butter", ["butter", "peanut butter"]) == "butter"


def test_matches_whole_words_only():
    # "egg" must not match inside "eggplant".
    assert longest_match("eggplant", ["egg"]) is None
    assert longest_match("butternut squash", ["butter"]) is None


def test_no_match_returns_none():
    assert longest_match("dragon scales", ["egg", "flour"]) is None


def test_equal_length_matches_are_broken_deterministically():
    # "rice" and "wine" are both four letters and both appear in "rice wine".
    # The answer must not depend on the order the database happened to return.
    forward = longest_match("rice wine", ["rice", "wine"])
    backward = longest_match("rice wine", ["wine", "rice"])
    assert forward == backward == "wine"


def test_special_characters_in_names_are_not_treated_as_regex():
    assert longest_match("a+b mix", ["a+b"]) == "a+b"


# ---------- qualifier_exclusions ----------

def test_gluten_free_cancels_gluten_only():
    assert qualifier_exclusions("gluten free pasta") == {"gluten"}


def test_dairy_free_cancels_dairy_and_lactose():
    assert qualifier_exclusions("dairy free cheddar") == {"dairy", "lactose"}


def test_lactose_free_does_not_cancel_dairy():
    # Lactose-free milk is still milk: fine for lactose intolerance, not for a dairy allergy.
    assert qualifier_exclusions("lactose free milk") == {"lactose"}


def test_vegan_cancels_every_animal_tag():
    cancelled = qualifier_exclusions("vegan mayo")
    assert {"meat", "fish", "shellfish", "dairy", "lactose", "egg", "honey"} <= cancelled
    assert "gluten" not in cancelled


def test_hyphenated_input_works_once_normalized():
    normalized = normalize_ingredient_name("Plant-Based Mince")
    assert "meat" in qualifier_exclusions(normalized)


def test_plain_text_cancels_nothing():
    assert qualifier_exclusions("plain pasta") == set()
    assert qualifier_exclusions("free range egg") == set()
