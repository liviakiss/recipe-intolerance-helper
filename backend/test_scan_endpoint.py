"""Tests for POST /scan-recipe, the photo upload endpoint.

Most of these cover what happens to bad uploads: wrong type, too large, not
actually an image, no OCR engine, nothing readable. The OCR step is replaced
with a stand-in in those tests so they are fast and need no Tesseract. The
last test sends a real picture through the real OCR.
"""
import io

import pytest
import pytesseract
from PIL import Image, ImageDraw, ImageFont

from app.main import MAX_SCAN_IMAGE_BYTES


def upload(client, content=b"x", content_type="image/png", filename="card.png", active_tag_ids=None):
    params = {"active_tag_ids": active_tag_ids} if active_tag_ids else None
    return client.post(
        "/scan-recipe",
        files={"file": (filename, content, content_type)},
        params=params,
    )


def fake_ocr(monkeypatch, text):
    """Make the endpoint's OCR step return fixed text."""
    monkeypatch.setattr("app.main.extract_text_from_image", lambda _image_bytes: text)


# ---------- uploads that must be turned away ----------

def test_a_file_that_is_not_declared_as_an_image_is_rejected(client):
    response = upload(client, b"just some notes", content_type="text/plain", filename="notes.txt")

    assert response.status_code == 415
    assert "image" in response.json()["detail"].lower()


def test_an_image_over_the_size_limit_is_rejected(client):
    response = upload(client, b"0" * (MAX_SCAN_IMAGE_BYTES + 1))

    assert response.status_code == 413
    assert "too large" in response.json()["detail"].lower()


def test_a_file_that_claims_to_be_an_image_but_is_not_is_rejected(client):
    # The declared content type is just a label the browser sets. The real
    # check is whether the bytes decode as a picture.
    response = upload(client, b"this is text, not a picture", content_type="image/png")

    assert response.status_code == 422
    assert "image" in response.json()["detail"].lower()


def test_a_missing_ocr_engine_is_reported_as_unavailable(client, monkeypatch):
    def tesseract_not_installed(_image_bytes):
        raise pytesseract.TesseractNotFoundError()

    monkeypatch.setattr("app.main.extract_text_from_image", tesseract_not_installed)

    response = upload(client)

    assert response.status_code == 503
    assert "isn't available" in response.json()["detail"]


@pytest.mark.parametrize("blank", ["", "   ", "\n \n"])
def test_an_image_with_no_readable_text_is_rejected(client, monkeypatch, blank):
    fake_ocr(monkeypatch, blank)

    response = upload(client)

    assert response.status_code == 422
    assert "any text" in response.json()["detail"].lower()


def test_no_file_at_all_is_rejected(client):
    assert client.post("/scan-recipe").status_code == 422


# ---------- uploads that work ----------

def test_scanned_text_is_checked_against_the_active_restrictions(client, tag_ids, add_ingredient, monkeypatch):
    add_ingredient("egg", ["egg"], substitute=("flax egg", "1 tbsp ground flaxseed + 3 tbsp water."))
    add_ingredient("flour", ["gluten"])
    fake_ocr(monkeypatch, "2 eggs\n1 cup flour")

    response = upload(client, filename="grandmas-cake.png", active_tag_ids=[tag_ids["egg"]])

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "grandmas-cake.png"
    assert body["raw_text"] == "2 eggs\n1 cup flour"
    assert [r["status"] for r in body["results"]] == ["flagged", "safe"]
    assert body["results"][0]["substitute"]["name"] == "flax egg"


def test_with_no_restrictions_selected_nothing_is_flagged(client, add_ingredient, monkeypatch):
    add_ingredient("egg", ["egg"])
    fake_ocr(monkeypatch, "2 eggs")

    response = upload(client)

    assert response.status_code == 200
    assert response.json()["results"][0]["status"] == "safe"


def test_a_real_photo_goes_through_ocr_parser_and_matcher(client, tag_ids, add_ingredient):
    """No stand-ins: draw a recipe card, upload it, read the flags that come back."""
    try:
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError:
        pytest.skip("Tesseract is not installed")

    add_ingredient("flour", ["gluten"])
    add_ingredient("egg", ["egg"])
    add_ingredient("milk", ["dairy", "lactose"])

    lines = ["2 cups plain flour", "3 large eggs", "1 cup whole milk"]
    image = Image.new("RGB", (900, 120 + 70 * len(lines)), "white")
    draw = ImageDraw.Draw(image)
    for index, text in enumerate(lines):
        draw.text((60, 40 + 70 * index), text, fill="black", font=ImageFont.load_default(size=40))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")

    response = upload(client, buffer.getvalue(), active_tag_ids=[tag_ids["gluten"]])

    assert response.status_code == 200
    by_word = {word: r for r in response.json()["results"] for word in ("flour", "egg", "milk") if word in r["name"].lower()}
    assert by_word["flour"]["status"] == "flagged"
    assert by_word["egg"]["status"] == "safe"
    assert by_word["milk"]["status"] == "safe"
