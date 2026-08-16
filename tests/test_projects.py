from .conftest import register, login, auth_header


def test_create_project(client, auth_headers):
    resp = client.post("/projects", json={"name": "My Project"}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["name"] == "My Project"


def test_creator_becomes_owner_member(client, auth_headers):
    project_id = client.post("/projects", json={"name": "P"}, headers=auth_headers).json()["id"]
    members = client.get(f"/projects/{project_id}/members", headers=auth_headers).json()
    assert len(members) == 1
    assert members[0]["role"] == "owner"


def test_non_member_cannot_view_project(client, auth_headers):
    project_id = client.post("/projects", json={"name": "Private"}, headers=auth_headers).json()["id"]

    register(client, email="outsider@example.com")
    outsider_headers = auth_header(login(client, email="outsider@example.com"))

    resp = client.get(f"/projects/{project_id}", headers=outsider_headers)
    assert resp.status_code == 403


def test_owner_can_add_member(client, auth_headers):
    project_id = client.post("/projects", json={"name": "Team"}, headers=auth_headers).json()["id"]
    register(client, email="editor@example.com")

    resp = client.post(
        f"/projects/{project_id}/members",
        json={"email": "editor@example.com", "role": "editor"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "editor"


def test_editor_cannot_delete_project_only_owner_can(client, auth_headers):
    project_id = client.post("/projects", json={"name": "ToDelete"}, headers=auth_headers).json()["id"]
    register(client, email="editor2@example.com")
    client.post(
        f"/projects/{project_id}/members",
        json={"email": "editor2@example.com", "role": "editor"},
        headers=auth_headers,
    )
    editor_headers = auth_header(login(client, email="editor2@example.com"))

    resp = client.delete(f"/projects/{project_id}", headers=editor_headers)
    assert resp.status_code == 403

    resp = client.delete(f"/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 204


def test_viewer_cannot_update_project(client, auth_headers):
    project_id = client.post("/projects", json={"name": "Viewme"}, headers=auth_headers).json()["id"]
    register(client, email="viewer2@example.com")
    client.post(
        f"/projects/{project_id}/members",
        json={"email": "viewer2@example.com", "role": "viewer"},
        headers=auth_headers,
    )
    viewer_headers = auth_header(login(client, email="viewer2@example.com"))

    resp = client.patch(f"/projects/{project_id}", json={"name": "Renamed"}, headers=viewer_headers)
    assert resp.status_code == 403


def test_owner_cannot_be_removed_from_membership(client, auth_headers):
    resp = client.post("/projects", json={"name": "Owned"}, headers=auth_headers)
    project_id = resp.json()["id"]
    owner_id = resp.json()["owner_id"]

    resp = client.delete(f"/projects/{project_id}/members/{owner_id}", headers=auth_headers)
    assert resp.status_code == 400
