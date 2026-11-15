"""Capacity, waitlist, conversion, documents, and row scope."""

from __future__ import annotations

from app.domain.scope import scope_for
from app.models.people import Student
from app.repositories.user_repository import UserRepository
from app.services.presenters import actor_from_user
from app.services.student_service import StudentService
from sqlalchemy import asc


def _auth(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _main(client, headers):
    response = client.get("/api/v1/branches", headers=headers)
    assert response.status_code == 200, response.text
    return next(item for item in response.json()["items"] if item["code"] == "MAIN")


def _year(client, headers):
    response = client.get("/api/v1/academic-years", headers=headers, params={"page_size": 20})
    assert response.status_code == 200, response.text
    year_id = response.json()["items"][0]["id"]
    detail = client.get(f"/api/v1/academic-years/{year_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    return detail.json()


def _course_id(client, headers):
    response = client.get("/api/v1/courses", headers=headers, params={"page_size": 20})
    assert response.status_code == 200, response.text
    return response.json()["items"][0]["id"]


def _lab_batch(client, headers, capacity=1):
    branch = _main(client, headers)
    year = _year(client, headers)
    created = client.post(
        "/api/v1/batches",
        headers=headers,
        json={
            "branch_id": branch["id"],
            "course_id": _course_id(client, headers),
            "term_id": year["terms"][0]["id"],
            "name": f"Capacity {capacity}",
            "start_date": year["terms"][0]["start_date"],
            "end_date": year["terms"][0]["end_date"],
            "capacity": capacity,
            "status": "active",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()


def _new_student(client, headers, first):
    branch = _main(client, headers)
    created = client.post(
        "/api/v1/students",
        headers=headers,
        json={
            "branch_id": branch["id"],
            "first_name": first,
            "last_name": "Lab",
            "grade_level": "Grade 8",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()


def test_full_batch_waitlists_and_withdrawal_promotes(client, admin_headers):
    batch = _lab_batch(client, admin_headers, capacity=1)
    first = _new_student(client, admin_headers, "Ada")
    second = _new_student(client, admin_headers, "Bea")
    seated = client.post(
        "/api/v1/enrollments",
        headers=admin_headers,
        json={"student_id": first["id"], "batch_id": batch["id"]},
    )
    waiting = client.post(
        "/api/v1/enrollments",
        headers=admin_headers,
        json={"student_id": second["id"], "batch_id": batch["id"]},
    )
    assert seated.status_code == 201, seated.text
    assert seated.json()["status"] == "active"
    assert waiting.status_code == 201, waiting.text
    assert waiting.json()["status"] == "waitlisted"
    assert waiting.json()["waitlist_position"] == 1

    again = client.post(
        "/api/v1/enrollments",
        headers=admin_headers,
        json={"student_id": second["id"], "batch_id": batch["id"]},
    )
    assert again.status_code == 409

    withdrawn = client.post(
        f"/api/v1/enrollments/{seated.json()['id']}/withdraw",
        headers=admin_headers,
        json={"reason": "Family moved"},
    )
    assert withdrawn.status_code == 200, withdrawn.text
    promoted = client.get(
        "/api/v1/enrollments",
        headers=admin_headers,
        params={"batch_id": batch["id"], "status": "active"},
    )
    assert promoted.status_code == 200
    assert [row["student_id"] for row in promoted.json()["items"]] == [second["id"]]

    widened = client.patch(
        f"/api/v1/batches/{batch['id']}",
        headers=admin_headers,
        json={"capacity": 2},
    )
    assert widened.status_code == 200, widened.text
    third = _new_student(client, admin_headers, "Cara")
    extra = client.post(
        "/api/v1/enrollments",
        headers=admin_headers,
        json={"student_id": third["id"], "batch_id": batch["id"]},
    )
    assert extra.status_code == 201, extra.text
    assert extra.json()["status"] == "active"
    shrunk = client.patch(
        f"/api/v1/batches/{batch['id']}",
        headers=admin_headers,
        json={"capacity": 1},
    )
    assert shrunk.status_code == 422


def test_teacher_sees_only_assigned_students(client, admin_headers):
    teacher = _auth(client, "maya.iqbal@tuition.example", "Teacher@12345")
    visible = client.get("/api/v1/students", headers=teacher, params={"page_size": 100})
    assert visible.status_code == 200, visible.text
    numbers = {row["admission_no"] for row in visible.json()["items"]}
    assert "MAIN-2026-0001" in numbers
    assert "MAIN-2026-0016" not in numbers
    hidden = next(
        row
        for row in client.get(
            "/api/v1/students",
            headers=admin_headers,
            params={"q": "MAIN-2026-0016", "page_size": 5},
        ).json()["items"]
        if row["admission_no"] == "MAIN-2026-0016"
    )
    denied = client.get(f"/api/v1/students/{hidden['id']}", headers=teacher)
    assert denied.status_code == 404


def test_parent_sees_only_the_linked_child(client, admin_headers, db_session):
    parent_role = next(
        role
        for role in client.get(
            "/api/v1/roles", headers=admin_headers, params={"page_size": 20}
        ).json()["items"]
        if role["name"] == "parent"
    )
    branch = _main(client, admin_headers)
    created = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": "parent.ada@tuition.example",
            "full_name": "Ada Parent",
            "password": "Parent@12345",
            "assignments": [{"role_id": parent_role["id"], "branch_id": branch["id"]}],
        },
    )
    assert created.status_code == 201, created.text
    parent_id = created.json()["id"]
    child = client.get(
        "/api/v1/students", headers=admin_headers, params={"q": "MAIN-2026-0001", "page_size": 5}
    ).json()["items"][0]
    linked = client.post(
        f"/api/v1/students/{child['id']}/guardians",
        headers=admin_headers,
        json={
            "full_name": "Ada Parent",
            "relationship": "Parent",
            "user_id": parent_id,
            "is_primary": False,
        },
    )
    assert linked.status_code == 201, linked.text
    user = UserRepository(db_session).get(parent_id)
    actor = actor_from_user(user)
    page = StudentService(db_session).list_students(
        actor,
        scope_for(actor, None),
        q=None,
        status=None,
        page=1,
        page_size=50,
        order=asc(Student.admission_no),
    )
    assert [item.admission_no for item in page.items] == ["MAIN-2026-0001"]


def test_convert_inquiry_once(client, admin_headers):
    branch = _main(client, admin_headers)
    created = client.post(
        "/api/v1/inquiries",
        headers=admin_headers,
        json={
            "branch_id": branch["id"],
            "name": "Hana Yusuf",
            "phone": "555-300-1001",
            "email": "hana.yusuf@tuition.example",
            "source": "website",
        },
    )
    assert created.status_code == 201, created.text
    inquiry_id = created.json()["id"]
    converted = client.post(
        f"/api/v1/inquiries/{inquiry_id}/convert",
        headers=admin_headers,
        json={"grade_level": "Grade 8"},
    )
    assert converted.status_code == 201, converted.text
    body = converted.json()
    assert body["admission_no"].startswith("MAIN-2026-")
    assert body["first_name"] == "Hana"
    assert body["guardians"][0]["relationship"] == "Contact"
    again = client.post(
        f"/api/v1/inquiries/{inquiry_id}/convert",
        headers=admin_headers,
        json={},
    )
    assert again.status_code == 409
    stored = client.get(f"/api/v1/inquiries/{inquiry_id}", headers=admin_headers)
    assert stored.json()["status"] == "converted"
    assert stored.json()["converted_student_id"] == body["id"]


def test_document_upload_rejects_plain_text_and_accepts_pdf(client, admin_headers):
    student = _new_student(client, admin_headers, "Cara")
    rejected = client.post(
        f"/api/v1/students/{student['id']}/documents",
        headers=admin_headers,
        data={"doc_type": "other"},
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert rejected.status_code == 422
    accepted = client.post(
        f"/api/v1/students/{student['id']}/documents",
        headers=admin_headers,
        data={"doc_type": "report"},
        files={"file": ("card.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF", "application/pdf")},
    )
    assert accepted.status_code == 201, accepted.text
    downloaded = client.get(
        f"/api/v1/students/{student['id']}/documents/{accepted.json()['id']}",
        headers=admin_headers,
    )
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"%PDF")


def test_branch_code_is_unique(client, admin_headers):
    created = client.post(
        "/api/v1/branches",
        headers=admin_headers,
        json={"code": "north", "name": "North Campus"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["code"] == "NORTH"
    duplicate = client.post(
        "/api/v1/branches",
        headers=admin_headers,
        json={"code": "NORTH", "name": "North Again"},
    )
    assert duplicate.status_code == 409
