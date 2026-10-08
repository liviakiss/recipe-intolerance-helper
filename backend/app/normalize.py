"""Turn an ingredient name into a canonical form for matching.

Both sides of every comparison go through this: the dictionary entries when
they are seeded, and the ingredient text parsed out of a recipe. As long as
both sides are normalized the same way, "Free-range Eggs", "free range egg"
and "eggs" all end up identical.

Kept as its own module (no database or web imports) so it can be tested
quickly and imported from anywhere.
"""
import re
import unicodedata

# Plurals the general rules below would get wrong.
IRREGULAR_PLURALS = {
    "leaves": "leaf",
    "knives": "knife",
    "loaves": "loaf",
    "chillies": "chilli",
    "chilies": "chili",
    "brioches": "brioche",
    "quiches": "quiche",
}


def _strip_accents(text: str) -> str:
    # "crème fraîche" -> "creme fraiche", "jalapeño" -> "jalapeno"
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _singularize_word(word: str) -> str:
    if len(word) <= 3:
        return word
    if word in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[word]
    if word.endswith("ies"):
        return word[:-3] + "y"           # berries -> berry
    if word.endswith(("oes", "ches", "shes", "xes", "sses")):
        return word[:-2]                 # tomatoes -> tomato, peaches -> peach
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]                 # eggs -> egg
    return word


def normalize_ingredient_name(name: str) -> str:
    text = _strip_accents(name.strip().lower())
    text = text.replace("-", " ")
    text = re.sub(r"[.,'’]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Every word is singularized, not just the last one, so a plural in the
    # middle of a phrase ("bay leaves and thyme") still lines up with the
    # singular form stored in the dictionary.
    return " ".join(_singularize_word(word) for word in text.split(" "))


def longest_match(normalized_text: str, candidate_names) -> str | None:
    """Pick which known ingredient a piece of recipe text refers to.

    Each candidate is treated as a whole-word phrase that may appear anywhere
    in the text, and the longest (most specific) one wins, so "peanut butter"
    beats "butter" and "coconut milk" beats "milk". Equal lengths are broken
    by the name itself, so the same input always gives the same answer.
    """
    matches = [
        name for name in candidate_names
        if re.search(rf"\b{re.escape(name)}\b", normalized_text)
    ]
    if not matches:
        return None
    return max(matches, key=lambda name: (len(name), name))


# "gluten-free pasta", "dairy-free cheddar", "vegan butter": a free-from word
# in front of an ingredient cancels the restriction tags it covers. Without
# this, the app would flag its own suggestions the moment someone pasted them
# back into a recipe. Keys are normalized phrases (hyphens already spaces).
_ANIMAL_TAGS = {"meat", "fish", "shellfish", "dairy", "lactose", "egg", "honey"}

FREE_FROM_QUALIFIERS = {
    "gluten free": {"gluten"},
    "dairy free": {"dairy", "lactose"},
    "non dairy": {"dairy", "lactose"},
    "lactose free": {"lactose"},      # lactose-free milk is still dairy
    "egg free": {"egg"},
    "nut free": {"tree_nuts", "peanuts"},
    "peanut free": {"peanuts"},
    "soy free": {"soy"},
    "sesame free": {"sesame"},
    "fish free": {"fish"},
    "shellfish free": {"shellfish"},
    "meat free": {"meat"},
    "mustard free": {"mustard"},
    "sulphite free": {"sulphites"},
    "sulfite free": {"sulphites"},
    "vegan": _ANIMAL_TAGS,
    "plant based": _ANIMAL_TAGS,
    "vegetarian": {"meat", "fish", "shellfish"},
}

_QUALIFIER_PATTERNS = [
    (re.compile(rf"\b{re.escape(phrase)}\b"), tags)
    for phrase, tags in FREE_FROM_QUALIFIERS.items()
]


def qualifier_exclusions(normalized_text: str) -> set[str]:
    """Tag names that a free-from qualifier in this text cancels."""
    removed: set[str] = set()
    for pattern, tags in _QUALIFIER_PATTERNS:
        if pattern.search(normalized_text):
            removed |= tags
    return removed
