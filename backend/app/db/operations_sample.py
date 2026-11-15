"""Sample timetable, fee plan, invoices, and an accountant.

Runs after the academic sample. Safe to repeat: it stops once Monthly tuition exists.
"""

from __future__ import annotations

import logging
from datetime import date, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.academics import Batch, NumberSequence, Staff
from app.models.branch import Branch
from app.models.enrollment import Enrollment
from app.models.operations import (
    AttendanceMark,
    AttendanceSheet,
    ClassSession,
    FeePlan,
    Invoice,
    InvoiceLine,
    Payment,
)
from app.models.people import Student
from app.models.rbac import Role, UserRole
from app.models.user import User

logger = logging.getLogger(__name__)

ACCOUNTANT_EMAIL = "leila.hassan@tuition.example"
ACCOUNTANT_PASSWORD = "Account@12345"


def seed_operations(session: Session, branch: Branch, admin: User) -> None:
    """Insert the Phase 2 sample when this campus does not have it yet."""
    _ensure_sunday(session, branch, admin)
    existing = session.scalar(
        select(FeePlan).where(
            FeePlan.branch_id == branch.id,
            FeePlan.name == "Monthly tuition",
            FeePlan.deleted_at.is_(None),
        )
    )
    if existing is not None:
        return
    batches = {
        row.name: row
        for row in session.scalars(select(Batch).where(Batch.branch_id == branch.id)).all()
    }
    staff = session.scalar(
        select(Staff)
        .join(User, User.id == Staff.user_id)
        .where(Staff.branch_id == branch.id, User.email == "maya.iqbal@tuition.example")
    )
    math = batches["Math A"]
    english = batches["English A"]
    science = batches["Science A"]
    _session(session, math, staff.id if staff else None, 0, admin.id)
    _session(session, math, staff.id if staff else None, 2, admin.id)
    _session(session, english, None, 1, admin.id)
    _session(session, science, staff.id if staff else None, 3, admin.id)
    plan = FeePlan(
        branch_id=branch.id,
        name="Monthly tuition",
        description="Standard monthly tuition.",
        amount=Decimal("150.00"),
        billing_period="monthly",
        status="active",
        created_by=admin.id,
        updated_by=admin.id,
    )
    session.add(plan)
    session.flush()
    students = {
        row.admission_no: row
        for row in session.scalars(
            select(Student).where(Student.branch_id == branch.id, Student.deleted_at.is_(None))
        ).all()
    }
    today = date.today()
    amina = _invoice(
        session,
        branch,
        students["MAIN-2026-0001"],
        plan,
        "MAIN-INV-0001",
        date(2026, 2, 1),
        date(2026, 3, 1),
        admin.id,
    )
    bilal = _invoice(
        session,
        branch,
        students["MAIN-2026-0002"],
        plan,
        "MAIN-INV-0002",
        today.replace(day=1),
        today,
        admin.id,
    )
    chloe = _invoice(
        session,
        branch,
        students["MAIN-2026-0003"],
        plan,
        "MAIN-INV-0003",
        today.replace(day=1),
        today,
        admin.id,
    )
    _payment(session, bilal, Decimal("60.00"), "MAIN-RCT-0001", "seed-bilal-tuition", admin.id)
    _payment(session, chloe, Decimal("150.00"), "MAIN-RCT-0002", "seed-chloe-tuition", admin.id)
    _apply(amina, today)
    _apply(bilal, today)
    _apply(chloe, today)
    session.add_all(
        [
            NumberSequence(
                branch_id=branch.id,
                doc_type="invoice",
                prefix="MAIN-INV-",
                next_number=4,
                created_by=admin.id,
                updated_by=admin.id,
            ),
            NumberSequence(
                branch_id=branch.id,
                doc_type="receipt",
                prefix="MAIN-RCT-",
                next_number=3,
                created_by=admin.id,
                updated_by=admin.id,
            ),
        ]
    )
    if staff is not None:
        sheet = AttendanceSheet(
            branch_id=branch.id,
            batch_id=math.id,
            attended_on=today,
            created_by=admin.id,
            updated_by=admin.id,
        )
        session.add(sheet)
        session.flush()
        enrolled = session.scalars(
            select(Student)
            .join(Enrollment, Enrollment.student_id == Student.id)
            .where(
                Enrollment.batch_id == math.id,
                Enrollment.status == "active",
                Enrollment.deleted_at.is_(None),
            )
            .order_by(Student.admission_no)
            .limit(3)
        ).all()
        for student in enrolled:
            session.add(
                AttendanceMark(
                    branch_id=branch.id,
                    sheet_id=sheet.id,
                    student_id=student.id,
                    status="present",
                    created_by=admin.id,
                    updated_by=admin.id,
                )
            )
    _accountant(session, branch, admin)
    logger.info("Seeded timetable, invoices, and accountant %s", ACCOUNTANT_EMAIL)


def _ensure_sunday(session: Session, branch: Branch, admin: User) -> None:
    """Keep a Sunday Math slot so the home screen has a class on the sample weekend."""
    math = session.scalar(
        select(Batch).where(
            Batch.branch_id == branch.id, Batch.name == "Math A", Batch.deleted_at.is_(None)
        )
    )
    if math is None:
        return
    found = session.scalar(
        select(ClassSession).where(
            ClassSession.batch_id == math.id,
            ClassSession.weekday == 6,
            ClassSession.deleted_at.is_(None),
        )
    )
    if found is not None:
        if found.ends_on < date(2026, 12, 31):
            found.ends_on = date(2026, 12, 31)
            session.flush()
        return
    staff = session.scalar(
        select(Staff)
        .join(User, User.id == Staff.user_id)
        .where(Staff.branch_id == branch.id, User.email == "maya.iqbal@tuition.example")
    )
    session.add(
        ClassSession(
            branch_id=branch.id,
            batch_id=math.id,
            room_id=math.room_id,
            staff_id=staff.id if staff else None,
            weekday=6,
            start_time=time(10, 0),
            end_time=time(11, 30),
            starts_on=math.start_date,
            ends_on=date(2026, 12, 31),
            status="scheduled",
            created_by=admin.id,
            updated_by=admin.id,
        )
    )
    session.flush()


def _session(
    session: Session, batch: Batch, staff_id: int | None, weekday: int, admin_id: int
) -> None:
    session.add(
        ClassSession(
            branch_id=batch.branch_id,
            batch_id=batch.id,
            room_id=batch.room_id,
            staff_id=staff_id,
            weekday=weekday,
            start_time=time(16, 0),
            end_time=time(17, 30),
            starts_on=batch.start_date,
            ends_on=batch.end_date,
            status="scheduled",
            created_by=admin_id,
            updated_by=admin_id,
        )
    )


def _invoice(session, branch, student, plan, number, issue, due, admin_id) -> Invoice:
    row = Invoice(
        branch_id=branch.id,
        student_id=student.id,
        fee_plan_id=plan.id,
        invoice_no=number,
        issue_date=issue,
        due_date=due,
        total=Decimal("150.00"),
        status="issued",
        created_by=admin_id,
        updated_by=admin_id,
    )
    session.add(row)
    session.flush()
    session.add(
        InvoiceLine(
            branch_id=branch.id,
            invoice_id=row.id,
            description=plan.name,
            amount=Decimal("150.00"),
            created_by=admin_id,
            updated_by=admin_id,
        )
    )
    return row


def _payment(
    session, invoice: Invoice, amount: Decimal, receipt: str, key: str, admin_id: int
) -> None:
    session.add(
        Payment(
            branch_id=invoice.branch_id,
            invoice_id=invoice.id,
            student_id=invoice.student_id,
            receipt_no=receipt,
            amount=amount,
            method="cash",
            status="completed",
            paid_on=invoice.issue_date,
            idempotency_key=key,
            request_fingerprint=f"{invoice.id}|{amount}|cash",
            created_by=admin_id,
            updated_by=admin_id,
        )
    )
    session.flush()


def _apply(invoice: Invoice, today: date) -> None:
    paid = sum(
        (payment.amount for payment in invoice.payments if payment.status == "completed"),
        Decimal("0.00"),
    )
    if paid <= 0 and invoice.due_date < today:
        invoice.status = "overdue"
    elif paid <= 0:
        invoice.status = "issued"
    elif paid < invoice.total:
        invoice.status = "partial"
    else:
        invoice.status = "paid"


def _accountant(session: Session, branch: Branch, admin: User) -> None:
    role = session.scalar(select(Role).where(Role.name == "accountant"))
    user = session.scalar(select(User).where(User.email == ACCOUNTANT_EMAIL))
    if user is None:
        user = User(
            email=ACCOUNTANT_EMAIL,
            full_name="Leila Hassan",
            password_hash=hash_password(ACCOUNTANT_PASSWORD),
            status="active",
            created_by=admin.id,
            updated_by=admin.id,
        )
        session.add(user)
        session.flush()
    link = session.scalar(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
    )
    if link is None:
        session.add(
            UserRole(user_id=user.id, role_id=role.id, branch_id=branch.id, created_by=admin.id)
        )
