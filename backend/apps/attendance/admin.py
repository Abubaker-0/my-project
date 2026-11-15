"""Django admin registration for attendance."""

from django.contrib import admin

from apps.attendance.models import Attendance, AttendanceRecord

admin.site.register(Attendance)
admin.site.register(AttendanceRecord)
