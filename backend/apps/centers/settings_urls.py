"""Routes under /api/settings/."""

from django.urls import path

from apps.centers.views import GlobalSettingsView

urlpatterns = [
    path('global/', GlobalSettingsView.as_view(), name='global-settings'),
]
