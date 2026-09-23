def split_into_lines(raw_text: str) -> list[str]:
    lines = raw_text.split("\n")
    result = []
    for line in lines:
        cleaned = line.strip()
        if cleaned:
            result.append(cleaned)
    return result

#-----

def strip_prep_note(line: str) -> str:
    search_start = 0
    while True:
        comma_position = line.find(",", search_start)
        if comma_position == -1:
            return line.strip()

        if comma_position + 1 >= len(line):
            return line[:comma_position].strip()

        next_char = line[comma_position + 1]
        if next_char.isdigit():
            search_start = comma_position + 1
            continue

        return line[:comma_position].strip()

#-----

KNOWN_UNITS = {
    "g", "gram", "grams", "kg",
    "ml", "l", "liter", "liters",
    "tsp", "tbsp", "cup", "cups",
    "oz", "lb", "lbs",
    "pinch", "piece", "pieces", "clove", "cloves",
    "dash", "stick", "sticks", "can", "cans",
}

NO_QUANTITY_WORDS = {"a", "an", "some", "few", "handful"}

FRACTION_CHARS = {
    "½": 0.5, "⅓": 1 / 3, "⅔": 2 / 3, "¼": 0.25, "¾": 0.75,
    "⅕": 0.2, "⅖": 0.4, "⅗": 0.6, "⅘": 0.8,
    "⅙": 1 / 6, "⅚": 5 / 6, "⅛": 0.125, "⅜": 0.375, "⅝": 0.625, "⅞": 0.875,
}

#-----

def _split_first_token(s):
    parts = s.split(" ", 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]

#-----

def _try_leading_fraction(s):
    if s and s[0] in FRACTION_CHARS:
        return FRACTION_CHARS[s[0]], s[1:].strip()

    token, remainder = _split_first_token(s)
    if "/" in token:
        numerator_str, _, denominator_str = token.partition("/")
        if numerator_str.isdigit() and denominator_str.isdigit():
            return float(numerator_str) / float(denominator_str), remainder.strip()

    return None, s

#-----

def strip_leading_quantity(element):
    if element and element[0] in FRACTION_CHARS:
        return FRACTION_CHARS[element[0]], element[1:].strip()

    i = 0
    while i < len(element) and (element[i].isdigit() or element[i] in ",."):
        i += 1

    if i == 0:
        first_word, remainder = _split_first_token(element)
        if first_word.lower() in NO_QUANTITY_WORDS:
            return None, remainder.strip()
        return None, element

    if i < len(element) and element[i] == "/":
        j = i + 1
        denom_start = j
        while j < len(element) and element[j].isdigit():
            j += 1
        if j > denom_start:
            numerator = float(element[:i].replace(",", "."))
            denominator = float(element[denom_start:j])
            return numerator / denominator, element[j:].strip()

    quantity_str = element[:i]
    whole_value = float(quantity_str.replace(",", "."))
    rest = element[i:]

    if rest.startswith("-") and len(rest) > 1 and rest[1].isdigit():
        j = 1
        while j < len(rest) and (rest[j].isdigit() or rest[j] in ",."):
            j += 1
        second_value = float(rest[1:j].replace(",", "."))
        return (whole_value + second_value) / 2, rest[j:].strip()

    rest = rest.strip()

    fraction_value, rest_after_fraction = _try_leading_fraction(rest)
    if fraction_value is not None:
        return whole_value + fraction_value, rest_after_fraction

    return whole_value, rest

#-----

def strip_leading_unit(rest):
    if rest == "":
        return None, rest

    parts = rest.split(" ", 1)
    first_word = parts[0].lower()

    if first_word in KNOWN_UNITS:
        remainder = parts[1].strip() if len(parts) > 1 else ""
        if remainder.lower().startswith("of "):
            remainder = remainder[3:].strip()
        return first_word, remainder

    return None, rest

#-----

def parse_ingredient_line(element):
    quantity, rest = strip_leading_quantity(element)
    unit, name = strip_leading_unit(rest)
    return {
        "quantity": quantity,
        "unit": unit,
        "name": name.strip(),
    }

#-----

def parse_recipe(raw_text: str) -> list[dict]:
    lines = split_into_lines(raw_text)
    ingredients = []
    for line in lines:
        cleaned = strip_prep_note(line)
        ingredients.append(parse_ingredient_line(cleaned))
    return ingredients