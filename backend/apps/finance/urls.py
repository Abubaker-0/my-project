"""Routes under /api/finance/."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.finance.views import (
    FinanceSummaryView,
    InstallmentViewSet,
    InvoiceViewSet,
    PaymentViewSet,
    RefundViewSet,
    ScholarshipViewSet,
)

router = DefaultRouter()
router.register('invoices', InvoiceViewSet, basename='invoice')
router.register('payments', PaymentViewSet, basename='payment')
router.register('installments', InstallmentViewSet, basename='installment')
router.register('scholarships', ScholarshipViewSet, basename='scholarship')
router.register('refunds', RefundViewSet, basename='refund')

urlpatterns = [
    path('summary/', FinanceSummaryView.as_view(), name='finance-summary'),
    *router.urls,
]
