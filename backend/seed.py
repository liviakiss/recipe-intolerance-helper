from app.database import SessionLocal
from app.models import IngredientTag

TAGS = [
    "gluten", "dairy", "lactose", "egg", "honey", "meat",
    "fish", "shellfish", "tree_nuts", "peanuts", "soy",
    "sesame", "mustard", "sulphites",
]

db = SessionLocal()

for tag_name in TAGS:
    tag = IngredientTag(name=tag_name)
    db.add(tag)

db.commit()
db.close()

print(f"Seeded {len(TAGS)} ingredient tags.")