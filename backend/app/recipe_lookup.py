import requests

MEALDB_SEARCH_URL = "https://www.themealdb.com/api/json/v1/1/search.php"


def _build_raw_text(meal: dict) -> str:
    """TheMealDB stores ingredients and measures as up to 20 numbered,
    parallel fields (strIngredient1/strMeasure1 ... strIngredient20/
    strMeasure20) instead of a list, with unused slots as empty strings.
    This flattens that into the same "quantity unit name" per line format
    our own parser already expects from a pasted recipe.
    """
    lines = []
    for i in range(1, 21):
        ingredient = (meal.get(f"strIngredient{i}") or "").strip()
        measure = (meal.get(f"strMeasure{i}") or "").strip()

        if not ingredient:
            continue

        line = f"{measure} {ingredient}".strip() if measure else ingredient
        lines.append(line)

    return "\n".join(lines)


def fetch_external_recipe(query: str) -> dict | None:
    """Look up a recipe by name via TheMealDB's free public API.

    Returns None both when no recipe matches and when the request itself
    fails (network error, timeout, bad response) — a real distinction we're
    collapsing for now. Worth splitting into two cases later if this needs
    to tell the user "the lookup service is down" vs "we don't know that
    recipe" specifically.
    """
    try:
        response = requests.get(MEALDB_SEARCH_URL, params={"s": query}, timeout=5)
        response.raise_for_status()
    except requests.RequestException:
        return None

    data = response.json()
    meals = data.get("meals")

    if not meals:
        return None

    meal = meals[0]

    return {
        "title": meal.get("strMeal", query),
        "image_url": meal.get("strMealThumb"),
        "source_url": meal.get("strSource") or meal.get("strYoutube"),
        "raw_text": _build_raw_text(meal),
    }
