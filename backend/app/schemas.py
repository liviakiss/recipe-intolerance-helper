from pydantic import BaseModel
from datetime import datetime

class IngredientTagOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class DietPresetOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class RecipeCheckRequest(BaseModel):
    raw_text: str
    active_tag_ids: list[int]

class IngredientCheckResult(BaseModel):
    quantity: float | None
    unit: str | None
    name: str
    status: str
    matched_tags: list[str]

class SubstituteOut(BaseModel):
    name: str
    note: str | None


class IngredientCheckResult(BaseModel):
    quantity: float | None
    unit: str | None
    name: str
    status: str
    matched_tags: list[str]
    substitute: SubstituteOut | None = None

class UserCreate(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class RestrictionsUpdate(BaseModel):
    tag_ids: list[int]


class RestrictionsOut(BaseModel):
    tag_ids: list[int]


class RecipeCreateRequest(BaseModel):
    title: str | None = None
    raw_text: str


class RecipeSaveResult(BaseModel):
    recipe_id: int
    results: list[IngredientCheckResult]

class RecipeListItem(BaseModel):
    id: int
    title: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class RecipeResultOut(BaseModel):
    ingredient_name: str
    flagged_tag_name: str
    substitute_name: str | None
    substitute_note: str | None


class RecipeDetailOut(BaseModel):
    id: int
    title: str | None
    raw_text: str
    created_at: datetime
    results: list[RecipeResultOut]