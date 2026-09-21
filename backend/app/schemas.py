from pydantic import BaseModel

class IngredientTagOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True