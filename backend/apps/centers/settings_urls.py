"""Routes under /api/settings/."""

from django.urls import path

from apps.centers.views import EffectivePolicyView, GlobalPolicyHistoryView, GlobalSettingsView

urlpatterns = [
    path('global/', GlobalSettingsView.as_view(), name='global-settings'),
    path('global/history/', GlobalPolicyHistoryView.as_view(), name='global-settings-history'),
    path('effective/', EffectivePolicyView.as_view(), name='effective-policy'),
]
