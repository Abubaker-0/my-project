"""Routes under /api/classes/."""

from rest_framework.routers import DefaultRouter

from apps.classes.views import ClassViewSet, ClassroomViewSet, ScheduleViewSet

router = DefaultRouter()
router.register('classrooms', ClassroomViewSet, basename='classroom')
router.register('schedules', ScheduleViewSet, basename='schedule')
router.register('', ClassViewSet, basename='class')

urlpatterns = router.urls
