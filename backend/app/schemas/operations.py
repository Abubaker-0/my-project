"""Request and response shapes for the timetable, attendance, and billing."""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, PlainSerializer

from app.schemas.common import APIModel, UtcDateTime

Money = Annotated[
    Decimal,
    PlainSerializer(
        lambda value: f"{Decimal(value).quantize(Decimal('0.01')):.2f}", return_type=str
    ),
]
Weekday = Literal[0, 1, 2, 3, 4, 5, 6]
SessionStatus = Literal["scheduled", "cancelled"]
MarkStatus = Literal["present", "absent", "late", "excused"]
BillingPeriod = Literal["once", "monthly", "term"]
PlanStatus = Literal["active", "inactive"]
InvoiceStatus = Literal["issued", "partial", "paid", "overdue", "cancelled"]
PayMethod = Literal["cash", "card", "bank", "other"]
PayStatus = Literal["completed", "void"]


class SessionCreate(APIModel):
    batch_id: int
    room_id: int | None = None
    staff_id: int | None = None
    weekday: Weekday
    start_time: time
    end_time: time


class SessionUpdate(APIModel):
    room_id: int | None = None
    staff_id: int | None = None
    weekday: Weekday | None = None
    start_time: time | None = None
    end_time: time | None = None


class SessionPublic(APIModel):
    id: int
    branch_id: int
    batch_id: int
    batch_name: str
    course_name: str
    room_id: int | None
    room_name: str | None
    staff_id: int | None
    teacher_name: str | None
    weekday: int
    start_time: time
    end_time: time
    starts_on: date
    ends_on: date
    status: str
    created_at: UtcDateTime


class MarkIn(APIModel):
    student_id: int
    status: MarkStatus
    note: str | None = Field(default=None, max_length=500)


class SheetSave(APIModel):
    batch_id: int
    attended_on: date
    marks: list[MarkIn] = Field(max_length=500)


class MarkPublic(APIModel):
    student_id: int
    student_name: str
    admission_no: str
    status: str | None
    note: str | None


class SheetPublic(APIModel):
    id: int | None
    batch_id: int
    batch_name: str
    attended_on: date
    marks: list[MarkPublic]


class FeePlanCreate(APIModel):
    branch_id: int
    course_id: int | None = None
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    billing_period: BillingPeriod = "monthly"
    status: PlanStatus = "active"


class FeePlanUpdate(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    billing_period: BillingPeriod | None = None
    status: PlanStatus | None = None


class FeePlanPublic(APIModel):
    id: int
    branch_id: int
    course_id: int | None
    name: str
    description: str | None
    amount: Money
    billing_period: str
    status: str
    created_at: UtcDateTime


class InvoiceLineIn(APIModel):
    description: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class InvoiceCreate(APIModel):
    student_id: int
    fee_plan_id: int | None = None
    issue_date: date | None = None
    due_date: date
    lines: list[InvoiceLineIn] = Field(default_factory=list, max_length=20)


class InvoiceLinePublic(APIModel):
    id: int
    description: str
    amount: Money


class PaymentPublic(APIModel):
    id: int
    invoice_id: int
    invoice_no: str
    student_id: int
    student_name: str
    receipt_no: str
    amount: Money
    method: str
    status: str
    paid_on: date
    void_reason: str | None
    created_at: UtcDateTime


class InvoicePublic(APIModel):
    id: int
    branch_id: int
    student_id: int
    student_name: str
    admission_no: str
    invoice_no: str
    issue_date: date
    due_date: date
    total: Money
    amount_paid: Money
    balance: Money
    status: str
    created_at: UtcDateTime


class InvoiceDetail(InvoicePublic):
    fee_plan_id: int | None
    cancel_reason: str | None
    lines: list[InvoiceLinePublic]
    payments: list[PaymentPublic]


class PaymentCreate(APIModel):
    invoice_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: PayMethod
    paid_on: date | None = None


class ReasonBody(APIModel):
    reason: str = Field(min_length=2, max_length=500)


class StatusTotal(APIModel):
    status: str
    count: int
    total: Money


class FinanceDashboard(APIModel):
    active_students: int
    open_invoices: int
    overdue_total: Money
    collected_this_month: Money
    invoice_counts: list[StatusTotal]


class TodaySession(APIModel):
    id: int
    batch_name: str
    room_name: str | None
    teacher_name: str | None
    start_time: time
    end_time: time
    attendance_marked: bool


class TodayDashboard(APIModel):
    attended_on: date
    sessions: list[TodaySession]
