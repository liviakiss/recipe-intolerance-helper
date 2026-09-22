from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

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