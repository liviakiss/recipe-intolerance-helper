from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.ingredient_matching import check_recipe
from app.schemas import RecipeCheckRequest, IngredientCheckResult

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Recipe Intolerance Helper APIis running"}

@app.get("/ingredient-tags", response_model=list[schemas.IngredientTagOut])
def get_ingredient_tags(db: Session = Depends(get_db)):
    return db.query(models.IngredientTag).all()

@app.get("/diet-presets", response_model=list[schemas.DietPresetOut])
def get_diet_presets(db: Session = Depends(get_db)):
    return db.query(models.DietPreset).all()

@app.post("/check-recipe", response_model=list[IngredientCheckResult])
def check_recipe_endpoint(request: RecipeCheckRequest, db: Session = Depends(get_db)):
    return check_recipe(db, request.raw_text, request.active_tag_ids)