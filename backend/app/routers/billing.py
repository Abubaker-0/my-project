"""Fee plans, invoices, payments, and PDF receipts."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.core.deps import DbSession, get_branch_scope, require_permission
from app.core.pagination import get_page_params, order_by
from app.domain.actor import Actor, BranchScope
from app.models.operations import FeePlan, Invoice
from app.schemas.common import Page
from app.schemas.operations import (
    FeePlanCreate,
    FeePlanPublic,
    FeePlanUpdate,
    InvoiceCreate,
    InvoiceDetail,
    InvoicePublic,
    PaymentCreate,
    PaymentPublic,
    ReasonBody,
)
from app.services.billing_service import BillingService

plans = APIRouter(prefix="/fee-plans", tags=["fees"])
invoices = APIRouter(prefix="/invoices", tags=["invoices"])
payments = APIRouter(prefix="/payments", tags=["payments"])

_PLAN_SORT = {"name": FeePlan.name, "amount": FeePlan.amount, "created_at": FeePlan.created_at}
_INVOICE_SORT = {
    "invoice_no": Invoice.invoice_no,
    "due_date": Invoice.due_date,
    "status": Invoice.status,
    "created_at": Invoice.created_at,
}


@plans.get("", response_model=Page[FeePlanPublic])
def list_plans(
    db: DbSession,
    actor: Actor = Depends(require_permission("fees:read")),
    scope: BranchScope = Depends(get_branch_scope),
    page=Depends(get_page_params),
) -> Page[FeePlanPublic]:
    """List fee plans."""
    return BillingService(db).list_plans(
        scope,
        q=page.q,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _PLAN_SORT, "name"),
    )


@plans.post("", response_model=FeePlanPublic, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: FeePlanCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("fees:create")),
    scope: BranchScope = Depends(get_branch_scope),
) -> FeePlanPublic:
    """Create a reusable charge."""
    return BillingService(db).create_plan(actor, scope, payload)


@plans.patch("/{plan_id}", response_model=FeePlanPublic)
def update_plan(
    plan_id: int,
    payload: FeePlanUpdate,
    db: DbSession,
    actor: Actor = Depends(require_permission("fees:update")),
    scope: BranchScope = Depends(get_branch_scope),
) -> FeePlanPublic:
    """Update a fee plan. Existing invoices keep the amounts they were issued with."""
    return BillingService(db).update_plan(actor, scope, plan_id, payload)


@plans.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(
    plan_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("fees:delete")),
    scope: BranchScope = Depends(get_branch_scope),
) -> Response:
    """Archive a fee plan that no invoice uses."""
    BillingService(db).delete_plan(actor, scope, plan_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@invoices.get("", response_model=Page[InvoicePublic])
def list_invoices(
    db: DbSession,
    actor: Actor = Depends(require_permission("invoices:read")),
    scope: BranchScope = Depends(get_branch_scope),
    page=Depends(get_page_params),
    student_id: int | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
) -> Page[InvoicePublic]:
    """List invoices. Status is refreshed from the balance before the page is returned."""
    return BillingService(db).list_invoices(
        actor,
        scope,
        q=page.q,
        status=status_filter,
        student_id=student_id,
        page=page.page,
        page_size=page.page_size,
        order=order_by(page.sort, _INVOICE_SORT, "-created_at"),
    )


@invoices.post("", response_model=InvoiceDetail, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("invoices:create")),
    scope: BranchScope = Depends(get_branch_scope),
) -> InvoiceDetail:
    """Issue an invoice from explicit lines or from a fee plan."""
    return BillingService(db).create_invoice(actor, scope, payload)


@invoices.get("/{invoice_id}", response_model=InvoiceDetail)
def get_invoice(
    invoice_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("invoices:read")),
    scope: BranchScope = Depends(get_branch_scope),
) -> InvoiceDetail:
    """Return one invoice with its lines, payments, and current balance."""
    return BillingService(db).get_invoice(actor, scope, invoice_id)


@invoices.post("/{invoice_id}/cancel", response_model=InvoiceDetail)
def cancel_invoice(
    invoice_id: int,
    payload: ReasonBody,
    db: DbSession,
    actor: Actor = Depends(require_permission("invoices:cancel")),
    scope: BranchScope = Depends(get_branch_scope),
) -> InvoiceDetail:
    """Cancel an invoice that has no completed payment. The row is kept."""
    return BillingService(db).cancel_invoice(actor, scope, invoice_id, payload.reason)


@payments.post("", response_model=PaymentPublic, status_code=status.HTTP_201_CREATED)
def record_payment(
    payload: PaymentCreate,
    db: DbSession,
    actor: Actor = Depends(require_permission("payments:create")),
    scope: BranchScope = Depends(get_branch_scope),
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> PaymentPublic:
    """Record a payment. The same idempotency key returns the original receipt."""
    return BillingService(db).record_payment(actor, scope, payload, idempotency_key)


@payments.post("/{payment_id}/void", response_model=PaymentPublic)
def void_payment(
    payment_id: int,
    payload: ReasonBody,
    db: DbSession,
    actor: Actor = Depends(require_permission("payments:void")),
    scope: BranchScope = Depends(get_branch_scope),
) -> PaymentPublic:
    """Void a payment. The invoice balance is recalculated and the row stays."""
    return BillingService(db).void_payment(actor, scope, payment_id, payload.reason)


@payments.get("/{payment_id}/receipt")
def receipt(
    payment_id: int,
    db: DbSession,
    actor: Actor = Depends(require_permission("payments:read")),
    scope: BranchScope = Depends(get_branch_scope),
) -> Response:
    """Download the PDF receipt."""
    number, pdf = BillingService(db).receipt_pdf(actor, scope, payment_id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{number}.pdf"'},
    )
