from fastapi import FastAPI, Depends, HTTPException, Response, UploadFile, File, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.ingredient_matching import check_recipe
from app.recipe_lookup import fetch_external_recipe
from app.ocr import extract_text_from_image
import pytesseract
from app.schemas import RecipeCheckRequest, IngredientCheckResult, UserCreate, UserOut, UserLogin, Token, RestrictionsUpdate, RestrictionsOut, RecipeCreateRequest, RecipeSaveResult, RecipeListItem, RecipeDetailOut, RecipeLookupRequest, RecipeLookupResult
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.models import User, UserActiveRestriction, Recipe, RecipeResult, Ingredient, IngredientTag, Substitute
from fastapi.middleware.cors import CORSMiddleware
from app.ratelimit import RateLimiter, rate_limit
import os

app = FastAPI()

# Which websites may call this API from a browser. Comma-separated, e.g.
# "https://my-app.vercel.app". Defaults to the local dev frontend.
CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

# The login cookie is only marked Secure (HTTPS-only) when this is "true".
# Keep it off for local http://localhost, turn it on when deployed.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

# Limits for the endpoints that cost something or can be abused. The scan
# endpoint is the expensive one (OCR), so it also has a global cap that holds
# no matter how many different visitors there are.
scan_per_visitor = RateLimiter(max_calls=10, window_seconds=3600)
scan_everyone = RateLimiter(max_calls=150, window_seconds=3600)
login_limit = RateLimiter(max_calls=10, window_seconds=60)
register_limit = RateLimiter(max_calls=5, window_seconds=3600)
lookup_limit = RateLimiter(max_calls=30, window_seconds=60)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Recipe Intolerance Helper API is running"}

@app.get("/ingredient-tags", response_model=list[schemas.IngredientTagOut])
def get_ingredient_tags(db: Session = Depends(get_db)):
    return db.query(models.IngredientTag).all()

@app.get("/diet-presets", response_model=list[schemas.DietPresetOut])
def get_diet_presets(db: Session = Depends(get_db)):
    return db.query(models.DietPreset).all()

@app.post("/check-recipe", response_model=list[IngredientCheckResult])
def check_recipe_endpoint(request: RecipeCheckRequest, db: Session = Depends(get_db)):
    return check_recipe(db, request.raw_text, request.active_tag_ids)

@app.post("/lookup-recipe", response_model=RecipeLookupResult, dependencies=[Depends(rate_limit(lookup_limit))])
def lookup_recipe_endpoint(request: RecipeLookupRequest, db: Session = Depends(get_db)):
    meal = fetch_external_recipe(request.query)

    if meal is None:
        raise HTTPException(
            status_code=404,
            detail=f"No recipe found for '{request.query}'",
        )

    results = check_recipe(db, meal["raw_text"], request.active_tag_ids)

    return {
        "title": meal["title"],
        "image_url": meal["image_url"],
        "source_url": meal["source_url"],
        "raw_text": meal["raw_text"],
        "results": results,
    }

MAX_SCAN_IMAGE_BYTES = 8 * 1024 * 1024  # 8MB

@app.post(
    "/scan-recipe",
    response_model=RecipeLookupResult,
    dependencies=[
        Depends(rate_limit(scan_per_visitor, "Too many photo scans from you. Please try again later.")),
        Depends(rate_limit(scan_everyone, "The demo has reached its hourly photo-scan limit. Please try again later.", per_client=False)),
    ],
)
def scan_recipe_endpoint(
    file: UploadFile = File(...),
    active_tag_ids: list[int] = Query(default=[]),
    db: Session = Depends(get_db),
):
    # The client-supplied content_type is just a label the browser sets —
    # it can't be trusted on its own, but it's a cheap first filter that
    # gives a clearer error than letting a non-image reach PIL unfiltered.
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Please upload an image file.")

    image_bytes = file.file.read()

    if len(image_bytes) > MAX_SCAN_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="That image is too large (max 8MB).")

    # The real defense against a lying content_type, or a corrupt/non-image
    # file: let PIL actually try to decode the bytes, and catch it cleanly
    # instead of letting an unhandled exception surface as a raw 500.
    try:
        raw_text = extract_text_from_image(image_bytes)
    except pytesseract.TesseractNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Photo scanning isn't available right now (OCR engine not installed on the server).",
        )
    except Exception:
        raise HTTPException(status_code=422, detail="Couldn't read that file as an image.")

    if not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Couldn't read any text from that photo. Try a clearer, well-lit shot.",
        )

    results = check_recipe(db, raw_text, active_tag_ids)

    return {
        "title": file.filename or "Scanned recipe",
        "image_url": None,
        "source_url": None,
        "raw_text": raw_text,
        "results": results,
    }

@app.post("/register", response_model=UserOut, dependencies=[Depends(rate_limit(register_limit))])
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=user_data.email, hashed_password=hash_password(user_data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/login", dependencies=[Depends(rate_limit(login_limit))])
def login(credentials: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()

    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token({"sub": str(user.id)})

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=60 * 60 * 24,  # 24 hours, matches token expiry
        path="/",
    )

    return {"message": "Logged in successfully"}

@app.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"message": "Logged out successfully"}

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
