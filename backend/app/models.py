from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class IngredientTag(Base):
    """The actual restriction unit — gluten, dairy, lactose, meat, etc."""
    __tablename__ = "ingredient_tags"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class DietPreset(Base):
    """UI shortcut buttons — Vegan, Vegetarian, Gluten-free, Lactose-free."""
    __tablename__ = "diet_presets"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class DietPresetTagMap(Base):
    """Which tags each preset bundles together."""
    __tablename__ = "diet_preset_tag_map"

    id = Column(Integer, primary_key=True)
    preset_id = Column(Integer, ForeignKey("diet_presets.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("ingredient_tags.id"), nullable=False)


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    normalized_name = Column(String, unique=True, nullable=False)


class IngredientTagMap(Base):
    """Which tags apply to which ingredients — e.g. butter -> dairy, lactose."""
    __tablename__ = "ingredient_tag_map"

    id = Column(Integer, primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("ingredient_tags.id"), nullable=False)


class Substitute(Base):
    __tablename__ = "substitutes"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    note = Column(String, nullable=True)


class IngredientSubstituteMap(Base):
    """Possible substitutes for an ingredient, specific to which restriction (tag) it solves."""
    __tablename__ = "ingredient_substitute_map"

    id = Column(Integer, primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    substitute_id = Column(Integer, ForeignKey("substitutes.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("ingredient_tags.id"), nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserActiveRestriction(Base):
    """Which tags a specific user currently has active (built from presets + custom picks)."""
    __tablename__ = "user_active_restrictions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("ingredient_tags.id"), nullable=False)


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    raw_text = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RecipeResult(Base):
    """The record of what was flagged AND what substitute was shown/saved, per recipe."""
    __tablename__ = "recipe_results"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    flagged_tag_id = Column(Integer, ForeignKey("ingredient_tags.id"), nullable=False)
    substitute_id = Column(Integer, ForeignKey("substitutes.id"), nullable=True)