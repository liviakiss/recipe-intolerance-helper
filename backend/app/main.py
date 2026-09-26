from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.ingredient_matching import check_recipe
from app.schemas import RecipeCheckRequest, IngredientCheckResult, UserCreate, UserOut, UserLogin, Token, RestrictionsUpdate, RestrictionsOut, RecipeCreateRequest, RecipeSaveResult, RecipeListItem, RecipeDetailOut
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.models import User, UserActiveRestriction, Recipe, RecipeResult, Ingredient, IngredientTag, Substitute

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

@app.put("/me/restrictions", response_model=RestrictionsOut)
def set_active_restrictions(
    data: RestrictionsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(UserActiveRestriction).filter(
        UserActiveRestriction.user_id == current_user.id
    ).delete()

    for tag_id in data.tag_ids:
        db.add(UserActiveRestriction(user_id=current_user.id, tag_id=tag_id))

    db.commit()
    return {"tag_ids": data.tag_ids}


@app.get("/me/restrictions", response_model=RestrictionsOut)
def get_active_restrictions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(UserActiveRestriction).filter(
        UserActiveRestriction.user_id == current_user.id
    ).all()
    return {"tag_ids": [row.tag_id for row in rows]}

@app.post("/recipes", response_model=RecipeSaveResult)
def save_recipe(
    request: RecipeCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    active_rows = db.query(UserActiveRestriction).filter(
        UserActiveRestriction.user_id == current_user.id
    ).all()
    active_tag_ids = [row.tag_id for row in active_rows]

    results = check_recipe(db, request.raw_text, active_tag_ids)

    recipe = Recipe(user_id=current_user.id, title=request.title, raw_text=request.raw_text)
    db.add(recipe)
    db.commit()
    db.refresh(recipe)

    for result in results:
        if result["status"] == "flagged":
            db.add(RecipeResult(
                recipe_id=recipe.id,
                ingredient_id=result["ingredient_id"],
                flagged_tag_id=result["flagged_tag_id"],
                substitute_id=result["substitute_id"],
            ))

    db.commit()

    return {"recipe_id": recipe.id, "results": results}

@app.get("/recipes", response_model=list[RecipeListItem])
def list_recipes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Recipe).filter(Recipe.user_id == current_user.id).all()


@app.get("/recipes/{recipe_id}", response_model=RecipeDetailOut)
def get_recipe(recipe_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recipe = db.query(Recipe).filter(
        Recipe.id == recipe_id,
        Recipe.user_id == current_user.id
    ).first()

    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    result_rows = db.query(RecipeResult).filter(RecipeResult.recipe_id == recipe.id).all()

    results = []
    for row in result_rows:
        ingredient = db.query(Ingredient).filter(Ingredient.id == row.ingredient_id).first()
        tag = db.query(IngredientTag).filter(IngredientTag.id == row.flagged_tag_id).first()
        substitute = db.query(Substitute).filter(Substitute.id == row.substitute_id).first() if row.substitute_id else None

        results.append({
            "ingredient_name": ingredient.name,
            "flagged_tag_name": tag.name,
            "substitute_name": substitute.name if substitute else None,
            "substitute_note": substitute.note if substitute else None,
        })

    return {
        "id": recipe.id,
        "title": recipe.title,
        "raw_text": recipe.raw_text,
        "created_at": recipe.created_at,
        "results": results,
    }