from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.ingredient_matching import check_recipe
from app.schemas import RecipeCheckRequest, IngredientCheckResult, UserCreate, UserOut, UserLogin, Token
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.models import User

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

@app.post("/register", response_model=UserOut)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=user_data.email, hashed_password=hash_password(user_data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()

    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user