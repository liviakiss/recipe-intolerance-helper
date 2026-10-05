import io
import os
import re
import shutil

from PIL import Image, ImageOps
import pytesseract
from pytesseract import Output

# On Windows the Tesseract installer doesn't add itself to PATH. If it isn't
# found on PATH, fall back to the installer's default location. On other
# systems (Linux/Mac, a deployed server) this does nothing and PATH is used.
_WINDOWS_DEFAULT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if shutil.which("tesseract") is None and os.path.exists(_WINDOWS_DEFAULT):
    pytesseract.pytesseract.tesseract_cmd = _WINDOWS_DEFAULT

TARGET_WIDTH = 1600   # small images are upscaled: OCR is far more accurate on bigger text
MAX_WIDTH = 3000      # huge phone photos are shrunk: no accuracy gain, much slower


def _prepare(image: Image.Image) -> Image.Image:
    # Phone photos store their rotation in EXIF metadata instead of rotating
    # the pixels; without this a portrait photo can reach OCR sideways.
    image = ImageOps.exif_transpose(image)
    image = ImageOps.autocontrast(ImageOps.grayscale(image))
    if image.width < TARGET_WIDTH or image.width > MAX_WIDTH:
        scale = (TARGET_WIDTH if image.width < TARGET_WIDTH else MAX_WIDTH) / image.width
        image = image.resize((int(image.width * scale), int(image.height * scale)), Image.LANCZOS)
    return image


def _read_blocks(image: Image.Image) -> list[list[str]]:
    """OCR the image and return its text as blocks of lines.

    Recipe cards often put ingredients and instructions side by side. Plain
    OCR reads straight across, mixing the two columns line by line. Here we
    look at where the words actually sit, detect a column split, and return
    [header_lines, left_column_lines, right_column_lines] instead. If no
    columns are found, a single block with all lines is returned.
    """
    data = pytesseract.image_to_data(image, config="--psm 4", output_type=Output.DICT)

    rows: dict[tuple, list] = {}
    for i, text in enumerate(data["text"]):
        if not text.strip() or float(data["conf"][i]) < 30:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        left, width = data["left"][i], data["width"][i]
        rows.setdefault(key, []).append((left, left + width, data["top"][i], text))

    lines = sorted(
        (sorted(words) for words in rows.values()),
        key=lambda words: min(w[2] for w in words),
    )

    width = image.width
    gaps = []   # (line index, x-position) of every big gap near the middle of a line
    for index, words in enumerate(lines):
        for a, b in zip(words, words[1:]):
            gap = b[0] - a[1]
            mid = (a[1] + b[0]) / 2
            if gap > 0.04 * width and 0.3 * width < mid < 0.7 * width:
                gaps.append((index, mid))

    # A real column split shows up as many lines with a gap at the same x.
    # Unrelated gaps (e.g. spacing inside a "Serves | Prep time" line) don't line up.
    best = []
    for _, centre in gaps:
        cluster = [g for g in gaps if abs(g[1] - centre) < 0.05 * width]
        if len(cluster) > len(best):
            best = cluster
    if len(best) < 3:
        return [[" ".join(w[3] for w in words) for words in lines]]

    first_split_line = min(g[0] for g in best)

    # Place the split in the middle of the widest empty vertical band below
    # the header. Punctuation-only tokens (the card's "|" divider) are ignored.
    spans = sorted(
        (w[0], w[1])
        for words in lines[first_split_line:]
        for w in words
        if any(c.isalnum() for c in w[3])
    )
    split_x, widest, reach = width / 2, 0.0, spans[0][1]
    for start, end in spans[1:]:
        if start - reach > widest and 0.3 * width < (start + reach) / 2 < 0.7 * width:
            widest, split_x = start - reach, (start + reach) / 2
        reach = max(reach, end)
    header = [" ".join(w[3] for w in words) for words in lines[:first_split_line]]
    left, right = [], []
    for words in lines[first_split_line:]:
        l = [w[3] for w in words if (w[0] + w[1]) / 2 < split_x]
        r = [w[3] for w in words if (w[0] + w[1]) / 2 >= split_x]
        if l:
            left.append(" ".join(l))
        if r:
            right.append(" ".join(r))
    return [header, left, right]


_STEP = re.compile(r"^\W*\d+\s*[.)]\s")                      # "1. Saute garlic..."
_QTY = re.compile(r"^\W*(\d|[½¼¾⅓⅔]|(a|an|one|half)\s)", re.I)  # "2 lbs ...", "a pinch"
_START = re.compile(r"^\W*ingredients?\b", re.I)
_STOP = re.compile(
    r"^\W*(instructions?|directions?|method|steps?|preparation|tips?|notes?|nutrition)\b", re.I
)
_META = re.compile(r"\b(serves|servings|yield|makes|prep time|cook time|total time)\b", re.I)
_LEAD_JUNK = re.compile(r"^[\W_]+")   # bullet glyphs OCR turns into (c), *, ', etc.


def _ingredient_score(lines: list[str]) -> float:
    if not lines:
        return 0.0
    hits = sum(1 for l in lines if _QTY.match(l) and not _STEP.match(l))
    return hits / len(lines)


def _clean(lines: list[str]) -> str:
    # If the text has an "Ingredients" heading, keep only what's under it,
    # up to the next section heading (Instructions, Tips, ...).
    start = next((i for i, l in enumerate(lines) if _START.match(l)), None)
    if start is not None:
        lines = lines[start + 1:]
        stop = next((i for i, l in enumerate(lines) if _STOP.match(l)), None)
        if stop is not None:
            lines = lines[:stop]

    cleaned = []
    for line in lines:
        if _STEP.match(line) or _META.search(line):
            continue
        line = _LEAD_JUNK.sub("", line).strip()
        if sum(c.isalpha() for c in line) < 3:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def extract_text_from_image(image_bytes: bytes) -> str:
    """Read a photo of a recipe and return the ingredient lines found in it.

    This is the one swap point for a future "paid" mode: replace the body
    with a call to a vision-capable AI API instead of local OCR, and nothing
    else needs to change — the endpoint calling this only ever depends on
    the signature (image bytes in, text out), not on how the text is found.
    """
    image = _prepare(Image.open(io.BytesIO(image_bytes)))
    blocks = _read_blocks(image)

    if len(blocks) == 3:
        header, left, right = blocks
        # Two-column card: the ingredients are the column that looks like a
        # list of quantities; the other column (steps, tips) is discarded.
        chosen = left if _ingredient_score(left) >= _ingredient_score(right) else right
        return _clean(chosen)

    return _clean(blocks[0])
