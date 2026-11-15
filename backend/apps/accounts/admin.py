"""Django admin registration for accounts. API rules still apply to the JSON API."""

from django.contrib import admin

from apps.accounts.models import Contract, Profile, User

admin.site.register(User)
admin.site.register(Profile)
admin.site.register(Contract)
