"""Django admin registration for reports."""

from django.contrib import admin

from apps.common.models import AuditLog
from apps.reports.models import FinancialReport

admin.site.register(FinancialReport)
admin.site.register(AuditLog)
