"""Routes under /api/enrollments/."""

from rest_framework.routers import DefaultRouter

from apps.enrollments.views import EnrollmentViewSet

router = DefaultRouter()
router.register('', EnrollmentViewSet, basename='enrollment')

urlpatterns = router.urls
