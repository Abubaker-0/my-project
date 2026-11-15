"""Timetable overlap, attendance scope, invoice balance, and idempotent payments."""

from __future__ import annotations

from datetime import date, timedelta


def _auth(client, email, password="Admin@12345"):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _batch_named(client, headers, name):
    response = client.get(
        "/api/v1/batches", headers=headers, params={"page_size": 20, "sort": "name"}
    )
    assert response.status_code == 200, response.text
    return next(item for item in response.json()["items"] if item["name"] == name)


def _math(client, headers):
    summary = _batch_named(client, headers, "Math A")
    detail = client.get(f"/api/v1/batches/{summary['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    return detail.json()


def _student(client, headers, admission):
    response = client.get(
        "/api/v1/students", headers=headers, params={"q": admission, "page_size": 5}
    )
    assert response.status_code == 200, response.text
    return next(item for item in response.json()["items"] if item["admission_no"] == admission)


def test_room_and_teacher_cannot_overlap_and_cancel_frees_them(client, admin_headers):
    math = _math(client, admin_headers)
    room_id = math["room_id"]
    staff_id = math["teachers"][0]["staff_id"]
    first = client.post(
        "/api/v1/timetable/sessions",
        headers=admin_headers,
        json={
            "batch_id": math["id"],
            "room_id": room_id,
            "staff_id": staff_id,
            "weekday": 4,
            "start_time": "09:00:00",
            "end_time": "10:00:00",
        },
    )
    assert first.status_code == 201, first.text
    overlap = client.post(
        "/api/v1/timetable/sessions",
        headers=admin_headers,
        json={
            "batch_id": math["id"],
            "room_id": room_id,
            "staff_id": staff_id,
            "weekday": 4,
            "start_time": "09:30:00",
            "end_time": "10:30:00",
        },
    )
    assert overlap.status_code == 409
    assert overlap.json()["code"] == "ROOM_OVERLAP"
    teacher_clash = client.post(
        "/api/v1/timetable/sessions",
        headers=admin_headers,
        json={
            "batch_id": math["id"],
            "staff_id": staff_id,
            "weekday": 4,
            "start_time": "09:30:00",
            "end_time": "10:30:00",
        },
    )
    assert teacher_clash.status_code == 409
    assert teacher_clash.json()["code"] == "TEACHER_OVERLAP"
    adjacent = client.post(
        "/api/v1/timetable/sessions",
        headers=admin_headers,
        json={
            "batch_id": math["id"],
            "room_id": room_id,
            "staff_id": staff_id,
            "weekday": 4,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
        },
    )
    assert adjacent.status_code == 201, adjacent.text
    cancelled = client.post(
        f"/api/v1/timetable/sessions/{first.json()['id']}/cancel",
        headers=admin_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    freed = client.post(
        "/api/v1/timetable/sessions",
        headers=admin_headers,
        json={
            "batch_id": math["id"],
            "room_id": room_id,
            "staff_id": staff_id,
            "weekday": 4,
            "start_time": "09:00:00",
            "end_time": "10:00:00",
        },
    )
    assert freed.status_code == 201, freed.text


def test_teacher_marks_only_assigned_batches(client, admin_headers):
    teacher = _auth(client, "maya.iqbal@tuition.example", "Teacher@12345")
    math = _batch_named(client, teacher, "Math A")
    roster = client.get(
        "/api/v1/attendance/sheets",
        headers=teacher,
        params={"batch_id": math["id"], "attended_on": "2026-05-04"},
    )
    assert roster.status_code == 200, roster.text
    body = roster.json()
    assert len(body["marks"]) == 12
    saved = client.put(
        "/api/v1/attendance/sheets",
        headers=teacher,
        json={
            "batch_id": math["id"],
            "attended_on": "2026-05-04",
            "marks": [
                {"student_id": body["marks"][0]["student_id"], "status": "present"},
                {"student_id": body["marks"][1]["student_id"], "status": "absent", "note": "Sick"},
            ],
        },
    )
    assert saved.status_code == 200, saved.text
    marked = {item["student_id"]: item for item in saved.json()["marks"]}
    assert marked[body["marks"][0]["student_id"]]["status"] == "present"
    assert marked[body["marks"][1]["student_id"]]["note"] == "Sick"
    english = _batch_named(client, admin_headers, "English A")
    hidden = client.get(
        "/api/v1/attendance/sheets",
        headers=teacher,
        params={"batch_id": english["id"], "attended_on": "2026-05-05"},
    )
    assert hidden.status_code == 404


def test_invoice_balance_overdue_cancel_and_idempotent_payment(client, admin_headers):
    student = _student(client, admin_headers, "MAIN-2026-0016")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    issued = client.post(
        "/api/v1/invoices",
        headers=admin_headers,
        json={
            "student_id": student["id"],
            "issue_date": yesterday,
            "due_date": yesterday,
            "lines": [{"description": "Lab fee", "amount": "80.00"}],
        },
    )
    assert issued.status_code == 201, issued.text
    invoice = issued.json()
    assert invoice["status"] == "overdue"
    assert invoice["balance"] == "80.00"
    assert invoice["invoice_no"].startswith("MAIN-INV-")
    first = client.post(
        "/api/v1/payments",
        headers={**admin_headers, "Idempotency-Key": "lab-fee-key-0001"},
        json={"invoice_id": invoice["id"], "amount": "30.00", "method": "cash"},
    )
    assert first.status_code == 201, first.text
    replay = client.post(
        "/api/v1/payments",
        headers={**admin_headers, "Idempotency-Key": "lab-fee-key-0001"},
        json={"invoice_id": invoice["id"], "amount": "30.00", "method": "cash"},
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == first.json()["id"]
    clash = client.post(
        "/api/v1/payments",
        headers={**admin_headers, "Idempotency-Key": "lab-fee-key-0001"},
        json={"invoice_id": invoice["id"], "amount": "10.00", "method": "card"},
    )
    assert clash.status_code == 409
    assert clash.json()["code"] == "IDEMPOTENCY_CONFLICT"
    current = client.get(f"/api/v1/invoices/{invoice['id']}", headers=admin_headers)
    assert current.json()["status"] == "partial"
    assert current.json()["balance"] == "50.00"
    too_much = client.post(
        "/api/v1/payments",
        headers={**admin_headers, "Idempotency-Key": "lab-fee-key-0002"},
        json={"invoice_id": invoice["id"], "amount": "80.00", "method": "cash"},
    )
    assert too_much.status_code == 422
    assert too_much.json()["code"] == "OVERPAYMENT"
    blocked = client.post(
        f"/api/v1/invoices/{invoice['id']}/cancel",
        headers=admin_headers,
        json={"reason": "Issued in error"},
    )
    assert blocked.status_code == 422
    voided = client.post(
        f"/api/v1/payments/{first.json()['id']}/void",
        headers=admin_headers,
        json={"reason": "Taken on the wrong invoice"},
    )
    assert voided.status_code == 200
    assert voided.json()["status"] == "void"
    after_void = client.get(f"/api/v1/invoices/{invoice['id']}", headers=admin_headers)
    assert after_void.json()["balance"] == "80.00"
    assert after_void.json()["status"] == "overdue"
    cancelled = client.post(
        f"/api/v1/invoices/{invoice['id']}/cancel",
        headers=admin_headers,
        json={"reason": "Issued in error"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    refused = client.post(
        "/api/v1/payments",
        headers={**admin_headers, "Idempotency-Key": "lab-fee-key-0003"},
        json={"invoice_id": invoice["id"], "amount": "80.00", "method": "cash"},
    )
    assert refused.status_code == 422
    assert refused.json()["code"] == "INVOICE_CANCELLED"
    receipt = client.get(f"/api/v1/payments/{first.json()['id']}/receipt", headers=admin_headers)
    assert receipt.status_code == 200
    assert receipt.content.startswith(b"%PDF")
    assert receipt.headers["content-type"] == "application/pdf"


def test_finance_dashboard_includes_the_seeded_overdue_invoice(client, admin_headers):
    response = client.get("/api/v1/dashboard/finance", headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["active_students"] >= 30
    assert Decimal_gt(body["overdue_total"], "0.00")
    statuses = {item["status"] for item in body["invoice_counts"]}
    assert "overdue" in statuses
    assert "paid" in statuses


def Decimal_gt(left: str, right: str) -> bool:
    return float(left) > float(right)
