"""Django admin registration for finance records."""

from django.contrib import admin

from apps.finance.models import Installment, Invoice, Payment, Refund, Scholarship

admin.site.register(Invoice)
admin.site.register(Payment)
admin.site.register(Installment)
admin.site.register(Scholarship)
admin.site.register(Refund)
