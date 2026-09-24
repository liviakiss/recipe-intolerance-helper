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
    