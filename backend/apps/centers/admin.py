"""Django admin registration for centers."""

from django.contrib import admin

from apps.centers.models import Center, CenterSettings, GlobalSettings

admin.site.register(Center)
admin.site.register(CenterSettings)
admin.site.register(GlobalSettings)
