"""Tests for the photo scanner, using real images and the real Tesseract.

The images are drawn on the fly with Pillow, so nothing needs to be checked
in. If Tesseract isn't installed on the machine running the tests, these are
skipped (not failed). The CI workflow installs it, so they run there.
"""
import io

import pytest
import pytesseract
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

from app import ocr  # importing this also finds Tesseract on a default Windows install


def _tesseract_available() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except pytesseract.TesseractNotFoundError:
        return False


pytestmark = pytest.mark.skipif(not _tesseract_available(), reason="Tesseract is not installed")


def _font(size: int):
    return ImageFont.load_default(size=size)


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def single_column_card() -> bytes:
    lines = ["Ingredients", "2 cups plain flour", "3 large eggs", "1 cup whole milk", "1 tsp salt", "100 g butter"]
    image = Image.new("RGB", (900, 120 + 70 * len(lines)), "white")
    draw = ImageDraw.Draw(image)
    y = 40
    for line in lines:
        draw.text((60, y), line, fill="black", font=_font(40))
        y += 70
    return _png(image)


def two_column_card() -> bytes:
    """Ingredients on the left, numbered steps on the right, a title on top."""
    image = Image.new("RGB", (1800, 700), "white")
    draw = ImageDraw.Draw(image)
    draw.text((80, 30), "Weeknight Tomato Soup", fill="black", font=_font(56))

    left = ["Ingredients", "2 tbsp olive oil", "1 onion, diced", "3 cloves garlic",
            "800 g canned tomatoes", "1 cup vegetable stock", "100 ml cream"]
    right = ["Instructions", "1. Heat the oil in a large pot over", "medium heat and soften the onion.",
             "2. Add the garlic and cook for one", "minute, then stir in the tomatoes.",
             "3. Pour in the stock and simmer for", "twenty minutes, then blend smooth."]
    for column, x in ((left, 80), (right, 1000)):
        y = 130
        for line in column:
            draw.text((x, y), line, fill="black", font=_font(40))
            y += 75
    return _png(image)


def test_single_column_list_is_read_line_by_line():
    lines = [line.lower() for line in ocr.extract_text_from_image(single_column_card()).splitlines()]

    for expected in ("flour", "eggs", "milk", "salt", "butter"):
        assert any(expected in line for line in lines), f"{expected!r} missing from {lines}"
    assert not any("ingredients" in line for line in lines), "the heading should be dropped"


def test_two_column_card_keeps_only_the_ingredients():
    text = ocr.extract_text_from_image(two_column_card()).lower()

    for expected in ("olive oil", "onion", "garlic", "tomatoes", "stock", "cream"):
        assert expected in text, f"{expected!r} missing from {text!r}"

    # None of the right-hand column or the title should leak in.
    for unwanted in ("instructions", "heat", "simmer", "blend", "tomato soup"):
        assert unwanted not in text, f"{unwanted!r} leaked into {text!r}"


def test_two_column_lines_are_not_interleaved():
    # Plain OCR reads straight across, producing lines like
    # "2 tbsp olive oil 1. Heat the oil in a large pot over".
    for line in ocr.extract_text_from_image(two_column_card()).splitlines():
        assert "1." not in line and "2." not in line and "3." not in line


def test_blank_image_gives_empty_text():
    assert ocr.extract_text_from_image(_png(Image.new("RGB", (600, 300), "white"))).strip() == ""


def test_bytes_that_are_not_an_image_raise():
    # The endpoint turns this into a clean 422 instead of a crash.
    with pytest.raises(UnidentifiedImageError):
        ocr.extract_text_from_image(b"this is definitely not a picture")
