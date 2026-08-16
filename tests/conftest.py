import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "ttUQonZEpuLqEOdacJlzB0l3tH7wMPgQh1/WFoGMRtk=")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal, get_db


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Fresh schema for every test function, so tests never leak state."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture()
def client():
    return TestClient(app)


def register(client, email="user@example.com", password="password123"):
    return client.post("/auth/register", json={"email": email, "password": password})


def login(client, email="user@example.com", password="password123"):
    resp = client.post("/auth/login", data={"username": email, "password": password})
    return resp.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth_headers(client):
    """A ready-to-use, already-registered user's auth headers."""
    register(client)
    token = login(client)
    return auth_header(token)
