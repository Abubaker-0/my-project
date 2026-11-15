"""Django admin registration for enrollments."""

from django.contrib import admin

from apps.enrollments.models import Enrollment

admin.site.register(Enrollment)
