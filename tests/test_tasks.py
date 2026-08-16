from .conftest import register, login, auth_header


def _create_project(client, headers, name="Task Project"):
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def test_create_task(client, auth_headers):
    project_id = _create_project(client, auth_headers)
    resp = client.post(f"/projects/{project_id}/tasks", json={"title": "Write tests"}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "todo"


def test_viewer_cannot_create_task(client, auth_headers):
    project_id = _create_project(client, auth_headers)
    register(client, email="viewer@example.com")
    client.post(
        f"/projects/{project_id}/members",
        json={"email": "viewer@example.com", "role": "viewer"},
        headers=auth_headers,
    )
    viewer_headers = auth_header(login(client, email="viewer@example.com"))

    resp = client.post(f"/projects/{project_id}/tasks", json={"title": "Nope"}, headers=viewer_headers)
    assert resp.status_code == 403


def test_viewer_can_still_list_tasks(client, auth_headers):
    project_id = _create_project(client, auth_headers)
    client.post(f"/projects/{project_id}/tasks", json={"title": "A"}, headers=auth_headers)
    register(client, email="viewer3@example.com")
    client.post(
        f"/projects/{project_id}/members",
        json={"email": "viewer3@example.com", "role": "viewer"},
        headers=auth_headers,
    )
    viewer_headers = auth_header(login(client, email="viewer3@example.com"))

    resp = client.get(f"/projects/{project_id}/tasks", headers=viewer_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_filter_tasks_by_status(client, auth_headers):
    project_id = _create_project(client, auth_headers)
    client.post(f"/projects/{project_id}/tasks", json={"title": "A", "status": "todo"}, headers=auth_headers)
    client.post(f"/projects/{project_id}/tasks", json={"title": "B", "status": "done"}, headers=auth_headers)

    resp = client.get(f"/projects/{project_id}/tasks?status=done", headers=auth_headers)
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "B"


def test_pagination(client, auth_headers):
    project_id = _create_project(client, auth_headers)
    for i in range(5):
        client.post(f"/projects/{project_id}/tasks", json={"title": f"Task {i}"}, headers=auth_headers)

    resp = client.get(f"/projects/{project_id}/tasks?page=1&page_size=2", headers=auth_headers)
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2


def test_assign_task_to_member(client, auth_headers):
    project_id = _create_project(client, auth_headers)
    reg = register(client, email="assignee@example.com")
    assignee_id = reg.json()["id"]
    client.post(
        f"/projects/{project_id}/members",
        json={"email": "assignee@example.com", "role": "editor"},
        headers=auth_headers,
    )
    task = client.post(f"/projects/{project_id}/tasks", json={"title": "Assign me"}, headers=auth_headers).json()

    resp = client.post(
        f"/projects/{project_id}/tasks/{task['id']}/assign",
        json={"user_id": assignee_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["assignee_id"] == assignee_id


def test_assign_task_to_non_member_rejected(client, auth_headers):
    project_id = _create_project(client, auth_headers)
    task = client.post(f"/projects/{project_id}/tasks", json={"title": "Assign me"}, headers=auth_headers).json()

    resp = client.post(
        f"/projects/{project_id}/tasks/{task['id']}/assign",
        json={"user_id": "00000000-0000-0000-0000-000000000000"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_unassign_task(client, auth_headers):
    project_id = _create_project(client, auth_headers)
    task = client.post(
        f"/projects/{project_id}/tasks", json={"title": "Solo task"}, headers=auth_headers
    ).json()
    client.post(
        f"/projects/{project_id}/tasks/{task['id']}/assign",
        json={"user_id": None},
        headers=auth_headers,
    )
    resp = client.get(f"/projects/{project_id}/tasks/{task['id']}", headers=auth_headers)
    assert resp.json()["assignee_id"] is None


def test_delete_task(client, auth_headers):
    project_id = _create_project(client, auth_headers)
    task = client.post(f"/projects/{project_id}/tasks", json={"title": "Delete me"}, headers=auth_headers).json()

    resp = client.delete(f"/projects/{project_id}/tasks/{task['id']}", headers=auth_headers)
    assert resp.status_code == 204

    resp = client.get(f"/projects/{project_id}/tasks/{task['id']}", headers=auth_headers)
    assert resp.status_code == 404


def test_task_not_found_returns_404(client, auth_headers):
    project_id = _create_project(client, auth_headers)
    resp = client.get(
        f"/projects/{project_id}/tasks/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert resp.status_code == 404
