"""Permission checks and branch scoping."""

from __future__ import annotations

from app.db.catalog import ALL_CODES, ROLE_DEFINITIONS
from app.models.branch import Branch


def test_catalog_codes_are_consistent():
    for _name, (_label, _description, codes) in ROLE_DEFINITIONS.items():
        assert codes <= ALL_CODES
    assert ROLE_DEFINITIONS["super_admin"][2] == ALL_CODES
    assert "permissions:assign" not in ROLE_DEFINITIONS["branch_admin"][2]
    assert "payments:create" in ROLE_DEFINITIONS["receptionist"][2]
    assert "results:enter" in ROLE_DEFINITIONS["teacher"][2]


def _role_id(client, headers, name):
    response = client.get("/api/v1/roles?page_size=100", headers=headers)
    assert response.status_code == 200, response.text
    return next(item["id"] for item in response.json()["items"] if item["name"] == name)


def _branch_id(client, headers, code="MAIN"):
    response = client.get("/api/v1/branches?page_size=100", headers=headers)
    assert response.status_code == 200, response.text
    return next(item["id"] for item in response.json()["items"] if item["code"] == code)


def test_branch_admin_cannot_see_another_branch_or_grant_global_access(
    client, admin_headers, db_session
):
    east = Branch(code="EAST", name="East Campus", status="active")
    db_session.add(east)
    db_session.commit()
    main_id = _branch_id(client, admin_headers)
    east_id = east.id
    branch_admin = _role_id(client, admin_headers, "branch_admin")
    receptionist = _role_id(client, admin_headers, "receptionist")

    created = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": "west.admin@tuition.example",
            "full_name": "West Admin",
            "password": "Branch@123",
            "assignments": [{"role_id": branch_admin, "branch_id": main_id}],
        },
    )
    assert created.status_code == 201, created.text
    other = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": "east.desk@tuition.example",
            "full_name": "East Desk",
            "password": "Branch@123",
            "assignments": [{"role_id": receptionist, "branch_id": east_id}],
        },
    )
    assert other.status_code == 201, other.text

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "west.admin@tuition.example", "password": "Branch@123"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    visible = client.get("/api/v1/users?page_size=100", headers=headers)
    emails = {item["email"] for item in visible.json()["items"]}
    assert "east.desk@tuition.example" not in emails
    assert "west.admin@tuition.example" in emails
    assert "admin@tuition.example" not in emails

    forbidden_branch = client.get("/api/v1/users", headers={**headers, "X-Branch-Id": str(east_id)})
    assert forbidden_branch.status_code == 403

    global_grant = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "global@tuition.example",
            "full_name": "Global User",
            "password": "Branch@123",
            "assignments": [{"role_id": receptionist, "branch_id": None}],
        },
    )
    assert global_grant.status_code == 403

    super_grant = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "extra.admin@tuition.example",
            "full_name": "Extra Admin",
            "password": "Branch@123",
            "assignments": [
                {"role_id": _role_id(client, admin_headers, "super_admin"), "branch_id": None}
            ],
        },
    )
    assert super_grant.status_code == 403


def test_teacher_cannot_list_users_and_permission_change_is_audited(client, admin_headers):
    teacher = _role_id(client, admin_headers, "teacher")
    main_id = _branch_id(client, admin_headers)
    created = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": "teacher@tuition.example",
            "full_name": "Taylor Teacher",
            "password": "Teach@1234",
            "assignments": [{"role_id": teacher, "branch_id": main_id}],
        },
    )
    assert created.status_code == 201, created.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher@tuition.example", "password": "Teach@1234"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    denied = client.get("/api/v1/users", headers=headers)
    assert denied.status_code == 403
    assert denied.json()["code"] == "FORBIDDEN"

    roles = client.get("/api/v1/roles?page_size=100", headers=admin_headers).json()["items"]
    teacher_role = next(item for item in roles if item["name"] == "teacher")
    permission_ids = [
        item["id"] for item in teacher_role["permissions"] if item["code"] != "portal:read"
    ]
    updated = client.put(
        f"/api/v1/roles/{teacher_role['id']}/permissions",
        headers=admin_headers,
        json={"permission_ids": permission_ids},
    )
    assert updated.status_code == 200, updated.text
    assert "portal:read" not in {item["code"] for item in updated.json()["permissions"]}
    logs = client.get("/api/v1/audit-logs?action=permission_change", headers=admin_headers)
    assert logs.status_code == 200
    assert logs.json()["total"] >= 1
    assert logs.json()["items"][0]["action"] == "permission_change"

    locked = client.put(
        f"/api/v1/roles/{_role_id(client, admin_headers, 'super_admin')}/permissions",
        headers=admin_headers,
        json={"permission_ids": permission_ids},
    )
    assert locked.status_code == 409


def test_user_search_pagination_and_soft_delete(client, admin_headers):
    role_id = _role_id(client, admin_headers, "student")
    branch_id = _branch_id(client, admin_headers)
    for index in range(3):
        response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "email": f"student{index}@tuition.example",
                "full_name": f"Student {index}",
                "password": "Student@123",
                "assignments": [{"role_id": role_id, "branch_id": branch_id}],
            },
        )
        assert response.status_code == 201, response.text
    page = client.get("/api/v1/users?q=student1&page=1&page_size=1", headers=admin_headers)
    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 1
    assert body["page_size"] == 1
    assert body["items"][0]["email"] == "student1@tuition.example"

    user_id = body["items"][0]["id"]
    removed = client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert removed.status_code == 204
    missing = client.get(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert missing.status_code == 404
    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "student1@tuition.example", "password": "Student@123"},
    )
    assert blocked.status_code == 401
    restored = client.post(f"/api/v1/users/{user_id}/restore", headers=admin_headers)
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"


def test_cannot_remove_the_last_super_admin(client, admin_headers):
    me = client.get("/api/v1/auth/me", headers=admin_headers).json()
    response = client.delete(f"/api/v1/users/{me['id']}", headers=admin_headers)
    assert response.status_code == 409


def test_sort_rejection(client, admin_headers):
    response = client.get("/api/v1/users?sort=password", headers=admin_headers)
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
