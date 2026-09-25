from pydantic import BaseModel

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