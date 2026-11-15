"""Fee plans, invoices, and payments.

An invoice balance is its total minus completed payments. The status follows
that balance. Payments and invoices are voided or cancelled; they are not deleted.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.domain.actor import Actor, BranchScope
from app.models.branch import Branch
from app.models.operations import FeePlan, Invoice, InvoiceLine, Payment
from app.models.people import Student
from app.repositories.operations import BillingRepository, lock_row
from app.schemas.common import Page
from app.schemas.operations import (
    FeePlanCreate,
    FeePlanPublic,
    FeePlanUpdate,
    InvoiceCreate,
    InvoiceDetail,
    InvoiceLinePublic,
    InvoicePublic,
    PaymentCreate,
    PaymentPublic,
)
from app.services.audit_service import AuditService
from app.services.guards import not_found, snapshot, stamp_new, stamp_update
from app.services.numbering import NumberingService
from app.services.transactions import commit_or_conflict

_PLAN_FIELDS = ("name", "amount", "billing_period", "status")
_INVOICE_FIELDS = ("invoice_no", "student_id", "total", "status", "due_date", "cancel_reason")
_PAYMENT_FIELDS = ("receipt_no", "invoice_id", "amount", "method", "status", "void_reason")


def money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def fingerprint(invoice_id: int, amount: Decimal, method: str) -> str:
    return f"{invoice_id}|{money(amount)}|{method}"


class BillingService:
    """Owns the invoice transaction, including the payment that changes it."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = BillingRepository(session)
        self.audit = AuditService(session)
        self.numbers = NumberingService(session)

    def list_plans(self, scope: BranchScope, *, q, page, page_size, order) -> Page[FeePlanPublic]:
        rows, total = self.repo.list_plans(
            scope, q=q, offset=(page - 1) * page_size, limit=page_size, order=order
        )
        return Page(
            items=[FeePlanPublic.model_validate(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_plan(
        self, actor: Actor, scope: BranchScope, payload: FeePlanCreate
    ) -> FeePlanPublic:
        self._branch(scope, payload.branch_id)
        if payload.course_id is not None:
            from app.models.academics import Course

            course = self.session.get(Course, payload.course_id)
            if (
                course is None
                or course.deleted_at is not None
                or course.branch_id != payload.branch_id
            ):
                raise not_found("Course")
        row = FeePlan(
            branch_id=payload.branch_id,
            course_id=payload.course_id,
            name=payload.name.strip(),
            description=payload.description,
            amount=money(payload.amount),
            billing_period=payload.billing_period,
            status=payload.status,
        )
        stamp_new(row, actor.id)
        self.session.add(row)
        self.session.flush()
        self.audit.record(
            action="create",
            entity="fee_plan",
            entity_id=row.id,
            actor_id=actor.id,
            branch_id=row.branch_id,
            new_values=snapshot(row, _PLAN_FIELDS),
        )
        commit_or_conflict(self.session)
        return FeePlanPublic.model_validate(row)

    def update_plan(
        self, actor: Actor, scope: BranchScope, plan_id: int, payload: FeePlanUpdate
    ) -> FeePlanPublic:
        row = self.repo.get_plan(plan_id, scope)
        if row is None:
            raise not_found("Fee plan")
        before = snapshot(row, _PLAN_FIELDS)
        data = payload.model_dump(exclude_unset=True)
        if "amount" in data and data["amount"] is not None:
            data["amount"] = money(data["amount"])
        for key, value in data.items():
            setattr(row, key, value)
        stamp_update(row, actor.id)
        self.audit.record(
            action="update",
            entity="fee_plan",
            entity_id=row.id,
            actor_id=actor.id,
            branch_id=row.branch_id,
            old_values=before,
            new_values=snapshot(row, _PLAN_FIELDS),
        )
        commit_or_conflict(self.session)
        return FeePlanPublic.model_validate(row)

    def delete_plan(self, actor: Actor, scope: BranchScope, plan_id: int) -> None:
        row = self.repo.get_plan(plan_id, scope)
        if row is None:
            raise not_found("Fee plan")
        used = self.session.scalar(
            select(func.count())
            .select_from(Invoice)
            .where(Invoice.fee_plan_id == row.id, Invoice.deleted_at.is_(None))
        )
        if used:
            raise AppException(409, "CONFLICT", "This fee plan is already used by an invoice")
        before = snapshot(row, _PLAN_FIELDS)
        from app.services.guards import soft_delete

        soft_delete(row, actor.id)
        self.audit.record(
            action="delete",
            entity="fee_plan",
            entity_id=row.id,
            actor_id=actor.id,
            branch_id=row.branch_id,
            old_values=before,
        )
        commit_or_conflict(self.session)

    def list_invoices(
        self, actor: Actor, scope: BranchScope, *, q, status, student_id, page, page_size, order
    ) -> Page[InvoicePublic]:
        self.refresh_open(scope)
        rows, total = self.repo.list_invoices(
            scope,
            actor,
            q=q,
            status=status,
            student_id=student_id,
            offset=(page - 1) * page_size,
            limit=page_size,
            order=order,
        )
        return Page(
            items=[to_invoice(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_invoice(self, actor: Actor, scope: BranchScope, invoice_id: int) -> InvoiceDetail:
        row = self.repo.get_invoice(invoice_id, scope, actor)
        if row is None:
            raise not_found("Invoice")
        if self._apply_status(row, date.today()):
            commit_or_conflict(self.session)
            row = self.repo.get_invoice(invoice_id, scope, actor)
        return to_invoice_detail(row)

    def create_invoice(
        self, actor: Actor, scope: BranchScope, payload: InvoiceCreate
    ) -> InvoiceDetail:
        student = self._student(scope, payload.student_id)
        lines = list(payload.lines)
        plan_id = payload.fee_plan_id
        if plan_id is not None:
            plan = self.repo.get_plan(plan_id, scope)
            if plan is None or plan.branch_id != student.branch_id:
                raise not_found("Fee plan")
            if not lines:
                from app.schemas.operations import InvoiceLineIn

                lines = [InvoiceLineIn(description=plan.name, amount=plan.amount)]
        if not lines:
            raise AppException(
                422, "VALIDATION_ERROR", "Add at least one charge, or choose a fee plan"
            )
        issue = payload.issue_date or date.today()
        if payload.due_date < issue:
            raise AppException(
                422, "VALIDATION_ERROR", "The due date must be on or after the issue date"
            )
        total = money(sum((money(line.amount) for line in lines), Decimal("0.00")))
        branch = self.session.get(Branch, student.branch_id)
        number = self.numbers.allocate(
            student.branch_id, "invoice", f"{branch.code}-INV-", actor.id
        )
        invoice = Invoice(
            branch_id=student.branch_id,
            student_id=student.id,
            fee_plan_id=plan_id,
            invoice_no=number,
            issue_date=issue,
            due_date=payload.due_date,
            total=total,
            status="issued",
        )
        stamp_new(invoice, actor.id)
        self.session.add(invoice)
        self.session.flush()
        for line in lines:
            item = InvoiceLine(
                branch_id=student.branch_id,
                invoice_id=invoice.id,
                description=line.description.strip(),
                amount=money(line.amount),
            )
            stamp_new(item, actor.id)
            self.session.add(item)
        self._apply_status(invoice, date.today())
        self.audit.record(
            action="create",
            entity="invoice",
            entity_id=invoice.id,
            actor_id=actor.id,
            branch_id=invoice.branch_id,
            new_values=snapshot(invoice, _INVOICE_FIELDS),
        )
        commit_or_conflict(self.session)
        return to_invoice_detail(self.repo.get_invoice(invoice.id, scope, actor))

    def cancel_invoice(
        self, actor: Actor, scope: BranchScope, invoice_id: int, reason: str
    ) -> InvoiceDetail:
        invoice = self._locked_invoice(scope, actor, invoice_id)
        if invoice.status == "cancelled":
            return to_invoice_detail(invoice)
        if invoice.amount_paid > 0:
            raise AppException(
                422,
                "PAYMENTS_REMAIN",
                "Void the completed payments before cancelling this invoice",
            )
        before = snapshot(invoice, _INVOICE_FIELDS)
        invoice.status = "cancelled"
        invoice.cancel_reason = reason.strip()
        stamp_update(invoice, actor.id)
        self.audit.record(
            action="cancel",
            entity="invoice",
            entity_id=invoice.id,
            actor_id=actor.id,
            branch_id=invoice.branch_id,
            old_values=before,
            new_values=snapshot(invoice, _INVOICE_FIELDS),
        )
        commit_or_conflict(self.session)
        return to_invoice_detail(self.repo.get_invoice(invoice.id, scope, actor))

    def record_payment(
        self, actor: Actor, scope: BranchScope, payload: PaymentCreate, idempotency_key: str
    ) -> PaymentPublic:
        key = idempotency_key.strip()
        if not 8 <= len(key) <= 80:
            raise AppException(
                422, "VALIDATION_ERROR", "The idempotency key must be 8 to 80 characters"
            )
        mark = fingerprint(payload.invoice_id, payload.amount, payload.method)
        existing = self.repo.payment_by_key(key)
        if existing is not None:
            if existing.request_fingerprint != mark:
                raise AppException(
                    409,
                    "IDEMPOTENCY_CONFLICT",
                    "This idempotency key was already used for a different payment",
                )
            return to_payment(existing)
        invoice = self._locked_invoice(scope, actor, payload.invoice_id)
        if invoice.status == "cancelled":
            raise AppException(
                422, "INVOICE_CANCELLED", "A cancelled invoice cannot take a payment"
            )
        amount = money(payload.amount)
        if amount > invoice.balance:
            raise AppException(422, "OVERPAYMENT", "The payment is larger than the invoice balance")
        branch = self.session.get(Branch, invoice.branch_id)
        receipt = self.numbers.allocate(
            invoice.branch_id, "receipt", f"{branch.code}-RCT-", actor.id
        )
        payment = Payment(
            branch_id=invoice.branch_id,
            invoice_id=invoice.id,
            student_id=invoice.student_id,
            receipt_no=receipt,
            amount=amount,
            method=payload.method,
            status="completed",
            paid_on=payload.paid_on or date.today(),
            idempotency_key=key,
            request_fingerprint=mark,
        )
        stamp_new(payment, actor.id)
        self.session.add(payment)
        self.session.flush()
        self.session.expire(invoice, ["payments"])
        before = invoice.status
        self._apply_status(invoice, date.today())
        stamp_update(invoice, actor.id)
        self.audit.record(
            action="payment",
            entity="payment",
            entity_id=payment.id,
            actor_id=actor.id,
            branch_id=payment.branch_id,
            new_values={
                **snapshot(payment, _PAYMENT_FIELDS),
                "invoice_status": invoice.status,
                "previous_status": before,
            },
        )
        commit_or_conflict(self.session)
        return to_payment(self.repo.get_payment(payment.id, scope, actor))

    def void_payment(
        self, actor: Actor, scope: BranchScope, payment_id: int, reason: str
    ) -> PaymentPublic:
        payment = self.repo.get_payment(payment_id, scope, actor)
        if payment is None:
            raise not_found("Payment")
        if payment.status == "void":
            return to_payment(payment)
        invoice = self._locked_invoice(scope, actor, payment.invoice_id)
        before = snapshot(payment, _PAYMENT_FIELDS)
        payment.status = "void"
        payment.void_reason = reason.strip()
        stamp_update(payment, actor.id)
        self.session.flush()
        self.session.expire(invoice, ["payments"])
        self._apply_status(invoice, date.today())
        stamp_update(invoice, actor.id)
        self.audit.record(
            action="void",
            entity="payment",
            entity_id=payment.id,
            actor_id=actor.id,
            branch_id=payment.branch_id,
            old_values=before,
            new_values=snapshot(payment, _PAYMENT_FIELDS),
        )
        commit_or_conflict(self.session)
        return to_payment(self.repo.get_payment(payment.id, scope, actor))

    def receipt_pdf(self, actor: Actor, scope: BranchScope, payment_id: int) -> tuple[str, bytes]:
        payment = self.repo.get_payment(payment_id, scope, actor)
        if payment is None:
            raise not_found("Payment")
        branch = self.session.get(Branch, payment.branch_id)
        from app.services.receipts import build_receipt

        pdf = build_receipt(
            branch_name=branch.name,
            receipt_no=payment.receipt_no,
            student_name=payment.student.full_name,
            admission_no=payment.student.admission_no,
            invoice_no=payment.invoice.invoice_no,
            amount=f"{money(payment.amount):.2f}",
            method=payment.method,
            paid_on=payment.paid_on.isoformat(),
            status=payment.status,
        )
        return payment.receipt_no, pdf

    def refresh_open(self, scope: BranchScope) -> None:
        today = date.today()
        changed = False
        for invoice in self.repo.open_invoices(scope):
            if self._apply_status(invoice, today):
                changed = True
        if changed:
            commit_or_conflict(self.session)

    def _apply_status(self, invoice: Invoice, today: date) -> bool:
        """Set issued, partial, paid, or overdue from the completed payments. Cancelled stays."""
        if invoice.status == "cancelled":
            return False
        paid = invoice.amount_paid
        if paid <= 0 and invoice.due_date < today:
            status = "overdue"
        elif paid <= 0:
            status = "issued"
        elif paid < invoice.total:
            status = "partial"
        else:
            status = "paid"
        if invoice.status == status:
            return False
        invoice.status = status
        return True

    def _locked_invoice(self, scope: BranchScope, actor: Actor, invoice_id: int) -> Invoice:
        invoice = self.repo.get_invoice(invoice_id, scope, actor)
        if invoice is None:
            raise not_found("Invoice")
        locked = lock_row(self.session, Invoice, invoice.id)
        self.session.expire(locked, ["payments", "lines"])
        return locked

    def _student(self, scope: BranchScope, student_id: int) -> Student:
        from app.repositories.base import apply_branch_scope

        stmt = select(Student).where(Student.id == student_id, Student.deleted_at.is_(None))
        stmt = apply_branch_scope(stmt, Student.branch_id, scope)
        student = self.session.scalar(stmt)
        if student is None:
            raise not_found("Student")
        return student

    def _branch(self, scope: BranchScope, branch_id: int) -> None:
        from app.services.guards import ensure_branch

        ensure_branch(scope, branch_id)
        branch = self.session.get(Branch, branch_id)
        if branch is None or branch.deleted_at is not None:
            raise not_found("Branch")


def to_invoice(row: Invoice) -> InvoicePublic:
    return InvoicePublic(
        id=row.id,
        branch_id=row.branch_id,
        student_id=row.student_id,
        student_name=row.student.full_name,
        admission_no=row.student.admission_no,
        invoice_no=row.invoice_no,
        issue_date=row.issue_date,
        due_date=row.due_date,
        total=row.total,
        amount_paid=row.amount_paid,
        balance=row.balance,
        status=row.status,
        created_at=row.created_at,
    )


def to_invoice_detail(row: Invoice) -> InvoiceDetail:
    base = to_invoice(row)
    return InvoiceDetail(
        **base.model_dump(),
        fee_plan_id=row.fee_plan_id,
        cancel_reason=row.cancel_reason,
        lines=[
            InvoiceLinePublic(id=line.id, description=line.description, amount=line.amount)
            for line in row.lines
            if line.deleted_at is None
        ],
        payments=[to_payment(payment) for payment in row.payments if payment.deleted_at is None],
    )


def to_payment(row: Payment) -> PaymentPublic:
    return PaymentPublic(
        id=row.id,
        invoice_id=row.invoice_id,
        invoice_no=row.invoice.invoice_no,
        student_id=row.student_id,
        student_name=row.student.full_name,
        receipt_no=row.receipt_no,
        amount=row.amount,
        method=row.method,
        status=row.status,
        paid_on=row.paid_on,
        void_reason=row.void_reason,
        created_at=row.created_at,
    )
