"""Routes under /api/reports/."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.reports.views import (
    AuditLogViewSet,
    DashboardView,
    FinancialReportViewSet,
    IntegrityView,
    InvoiceExportView,
)

router = DefaultRouter()
router.register('financial', FinancialReportViewSet, basename='financial-report')
router.register('audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('integrity/', IntegrityView.as_view(), name='integrity'),
    path('export/invoices/', InvoiceExportView.as_view(), name='invoice-export'),
    *router.urls,
]
