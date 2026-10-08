"""Shared test setup.

Every test that touches the database gets a brand-new in-memory SQLite
database, so tests never see each other's data and never touch your real
PostgreSQL database.
"""
import os

# app.database reads DATABASE_URL the moment it is imported, so this has to
# happen before anything imports the app. It is assigned, not "set if
# missing", on purpose: even if your shell or .env points at the real
# database, the tests still run against a throwaway one.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest


@pytest.fixture()
def db():
    """A session on an empty in-memory database with all tables created."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app import models  # noqa: F401  (importing registers the tables)
    from app.database import Base

    # StaticPool + check_same_thread=False: the web test client runs requests
    # on another thread, and an in-memory SQLite database must be shared with it.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def tag_ids(db):
    """Creates every restriction tag and returns {tag name: id}."""
    from app import models
    from seed_data import TAGS

    ids = {}
    for name in TAGS:
        tag = models.IngredientTag(name=name)
        db.add(tag)
        db.flush()
        ids[name] = tag.id
    db.commit()
    return ids


@pytest.fixture()
def add_ingredient(db, tag_ids):
    """Returns a function that adds one ingredient to the test database.

        add_ingredient("butter", ["dairy", "lactose"], substitute=("vegan margarine", "1:1"))

    The substitute (if given) is linked to every tag the ingredient carries.
    """
    from app import models
    from app.normalize import normalize_ingredient_name

    def _add(name, tags=(), substitute=None):
        ingredient = models.Ingredient(name=name, normalized_name=normalize_ingredient_name(name))
        db.add(ingredient)
        db.flush()

        for tag in tags:
            db.add(models.IngredientTagMap(ingredient_id=ingredient.id, tag_id=tag_ids[tag]))

        if substitute is not None:
            sub_name, note = substitute
            sub = models.Substitute(name=sub_name, note=note)
            db.add(sub)
            db.flush()
            for tag in tags:
                db.add(models.IngredientSubstituteMap(
                    ingredient_id=ingredient.id, substitute_id=sub.id, tag_id=tag_ids[tag],
                ))

        db.commit()
        return ingredient

    return _add


@pytest.fixture()
def client(db):
    """A test client for the real FastAPI app, wired to the test database."""
    from fastapi.testclient import TestClient

    from app.database import get_db
    from app.main import app
    from app.ratelimit import reset_all

    reset_all()  # every test starts with fresh rate-limit counts

    def use_test_db():
        yield db

    app.dependency_overrides[get_db] = use_test_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
