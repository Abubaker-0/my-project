"""Routes under /api/attendance/."""

from rest_framework.routers import DefaultRouter

from apps.attendance.views import AttendanceRecordViewSet, AttendanceViewSet

router = DefaultRouter()
router.register('records', AttendanceRecordViewSet, basename='attendance-record')
router.register('', AttendanceViewSet, basename='attendance')

urlpatterns = router.urls
