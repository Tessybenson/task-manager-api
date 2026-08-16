from .conftest import register, login, auth_header


def test_register_success(client):
    resp = register(client, email="a@example.com")
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@example.com"
    assert "hashed_password" not in body
    assert "password" not in body


def test_register_duplicate_email_rejected(client):
    register(client, email="dup@example.com")
    resp = register(client, email="dup@example.com")
    assert resp.status_code == 400


def test_register_short_password_rejected(client):
    resp = client.post("/auth/register", json={"email": "short@example.com", "password": "abc"})
    assert resp.status_code == 422


def test_login_success(client):
    register(client, email="b@example.com")
    token = login(client, email="b@example.com")
    assert isinstance(token, str) and len(token) > 0


def test_login_wrong_password_rejected(client):
    register(client, email="c@example.com")
    resp = client.post("/auth/login", data={"username": "c@example.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_unknown_user_rejected(client):
    resp = client.post("/auth/login", data={"username": "ghost@example.com", "password": "password123"})
    assert resp.status_code == 401


def test_protected_route_requires_token(client):
    resp = client.get("/projects")
    assert resp.status_code == 401


def test_protected_route_rejects_garbage_token(client):
    resp = client.get("/projects", headers=auth_header("not-a-real-token"))
    assert resp.status_code == 401
