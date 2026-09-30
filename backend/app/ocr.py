import io
from PIL import Image
import pytesseract

# On Windows, if Tesseract isn't on your PATH, uncomment and point this at
# your actual install location (the installer shows it at the end of setup):
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_text_from_image(image_bytes: bytes) -> str:
    """Read a photo of a recipe and return the raw text found in it.

    This is the one swap point for a future "paid" mode: replace the body
    with a call to a vision-capable AI API instead of local OCR, and nothing
    else needs to change — the endpoint calling this only ever depends on
    the signature (image bytes in, text out), not on how the text is found.
    """
    image = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(image)
