import pytest
from app.parser import (
    split_into_lines,
    strip_prep_note,
    strip_leading_quantity,
    strip_leading_unit,
    parse_ingredient_line,
    parse_recipe,
)


def test_split_into_lines_strips_and_drops_empty():
    raw = "3 eggs\n\n  2 cups flour  \n\n"
    assert split_into_lines(raw) == ["3 eggs", "2 cups flour"]


def test_strip_prep_note_no_comma():
    assert strip_prep_note("3 eggs") == "3 eggs"


def test_strip_prep_note_removes_trailing_note():
    assert strip_prep_note("2 cups flour, sifted") == "2 cups flour"


def test_strip_prep_note_skips_decimal_comma_only():
    assert strip_prep_note("3,4g flour") == "3,4g flour"


def test_strip_prep_note_skips_decimal_comma_then_finds_real_note():
    assert strip_prep_note("3,4g flour, sifted") == "3,4g flour"


def test_strip_prep_note_comma_at_end_of_line():
    assert strip_prep_note("2 eggs,") == "2 eggs"


def test_strip_leading_quantity_plain_number():
    quantity, rest = strip_leading_quantity("3 eggs")
    assert quantity == 3.0
    assert rest == "eggs"


def test_strip_leading_quantity_decimal_comma_fused_with_unit():
    quantity, rest = strip_leading_quantity("3,4g flour")
    assert quantity == 3.4
    assert rest == "g flour"


def test_strip_leading_quantity_decimal_comma_with_space_before_unit():
    quantity, rest = strip_leading_quantity("3,4 g flour")
    assert quantity == 3.4
    assert rest == "g flour"


def test_strip_leading_quantity_simple_fraction():
    quantity, rest = strip_leading_quantity("1/2 cup flour")
    assert quantity == 0.5
    assert rest == "cup flour"


def test_strip_leading_quantity_unicode_fraction():
    quantity, rest = strip_leading_quantity("½ cup milk")
    assert quantity == 0.5
    assert rest == "cup milk"


def test_strip_leading_quantity_mixed_number_ascii_fraction():
    quantity, rest = strip_leading_quantity("1 1/2 cups sugar")
    assert quantity == 1.5
    assert rest == "cups sugar"


def test_strip_leading_quantity_mixed_number_unicode_fraction():
    quantity, rest = strip_leading_quantity("1 ½ cups sugar")
    assert quantity == 1.5
    assert rest == "cups sugar"


def test_strip_leading_quantity_fused_whole_and_unicode_fraction():
    quantity, rest = strip_leading_quantity("2½ cups sugar")
    assert quantity == 2.5
    assert rest == "cups sugar"


def test_strip_leading_quantity_range_is_averaged():
    quantity, rest = strip_leading_quantity("2-3 eggs")
    assert quantity == 2.5
    assert rest == "eggs"


def test_strip_leading_quantity_no_quantity_word():
    quantity, rest = strip_leading_quantity("a pinch of salt")
    assert quantity is None
    assert rest == "pinch of salt"


def test_strip_leading_quantity_no_number_no_marker_word():
    quantity, rest = strip_leading_quantity("salt to taste")
    assert quantity is None
    assert rest == "salt to taste"


def test_strip_leading_unit_known_unit():
    unit, name = strip_leading_unit("g flour")
    assert unit == "g"
    assert name == "flour"


def test_strip_leading_unit_unknown_unit_left_in_name():
    unit, name = strip_leading_unit("eggs")
    assert unit is None
    assert name == "eggs"


def test_strip_leading_unit_strips_of_after_unit():
    unit, name = strip_leading_unit("pinch of salt")
    assert unit == "pinch"
    assert name == "salt"


def test_strip_leading_unit_empty_rest():
    unit, name = strip_leading_unit("")
    assert unit is None
    assert name == ""


def test_parse_ingredient_line_full_example():
    result = parse_ingredient_line("3,4g flour")
    assert result == {"quantity": 3.4, "unit": "g", "name": "flour"}


def test_parse_ingredient_line_no_unit():
    result = parse_ingredient_line("3 eggs")
    assert result == {"quantity": 3.0, "unit": None, "name": "eggs"}


def test_parse_ingredient_line_no_quantity():
    result = parse_ingredient_line("a pinch of salt")
    assert result == {"quantity": None, "unit": "pinch", "name": "salt"}


def test_parse_recipe_end_to_end():
    raw = (
        "3 eggs\n"
        "1 1/2 cups flour, sifted\n"
        "2-3 cloves garlic\n"
        "a pinch of salt\n"
        "½ cup milk"
    )
    result = parse_recipe(raw)
    assert result == [
        {"quantity": 3.0, "unit": None, "name": "eggs"},
        {"quantity": 1.5, "unit": "cups", "name": "flour"},
        {"quantity": 2.5, "unit": "cloves", "name": "garlic"},
        {"quantity": None, "unit": "pinch", "name": "salt"},
        {"quantity": 0.5, "unit": "cup", "name": "milk"},
    ]