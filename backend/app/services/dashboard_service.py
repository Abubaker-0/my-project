"""Figures for the admin, accountant, and teacher home screens."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.actor import Actor, BranchScope
from app.models.people import Student
from app.repositories.base import apply_branch_scope
from app.repositories.operations import AttendanceRepository, BillingRepository, TimetableRepository
from app.schemas.operations import FinanceDashboard, StatusTotal, TodayDashboard, TodaySession
from app.services.billing_service import money


class DashboardService:
    """Reads counts. Invoice statuses are refreshed first so overdue is current."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.billing = BillingRepository(session)
        self.timetable = TimetableRepository(session)
        self.attendance = AttendanceRepository(session)

    def finance(self, scope: BranchScope) -> FinanceDashboard:
        from app.services.billing_service import BillingService

        BillingService(self.session).refresh_open(scope)
        invoices = self.billing.invoices_for_summary(scope)
        counts: dict[str, list] = {}
        overdue = Decimal("0.00")
        open_count = 0
        for invoice in invoices:
            bucket = counts.setdefault(invoice.status, [0, Decimal("0.00")])
            bucket[0] += 1
            bucket[1] += invoice.total
            if invoice.status in {"issued", "partial", "overdue"}:
                open_count += 1
                overdue += invoice.balance if invoice.status == "overdue" else Decimal("0.00")
                if invoice.status == "partial" and invoice.due_date < date.today():
                    overdue += invoice.balance
        today = date.today()
        month_start = today.replace(day=1)
        collected = sum(
            (
                payment.amount
                for payment in self.billing.completed_between(scope, month_start, today)
            ),
            Decimal("0.00"),
        )
        students = (
            select(func.count())
            .select_from(Student)
            .where(Student.deleted_at.is_(None), Student.status == "active")
        )
        students = apply_branch_scope(students, Student.branch_id, scope)
        active = int(self.session.scalar(students) or 0)
        return FinanceDashboard(
            active_students=active,
            open_invoices=open_count,
            overdue_total=money(overdue),
            collected_this_month=money(collected),
            invoice_counts=[
                StatusTotal(status=status, count=values[0], total=money(values[1]))
                for status, values in sorted(counts.items())
            ],
        )

    def today(self, actor: Actor, scope: BranchScope) -> TodayDashboard:
        day = date.today()
        sessions = self.timetable.sessions_on(scope, actor, day.weekday(), day)
        items = []
        for row in sessions:
            teacher = None
            if row.staff is not None and row.staff.user is not None:
                teacher = row.staff.user.full_name
            items.append(
                TodaySession(
                    id=row.id,
                    batch_name=row.batch.name,
                    room_name=row.room.name if row.room is not None else None,
                    teacher_name=teacher,
                    start_time=row.start_time,
                    end_time=row.end_time,
                    attendance_marked=self.attendance.sheet_exists(row.batch_id, day),
                )
            )
        return TodayDashboard(attended_on=day, sessions=items)
