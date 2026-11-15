"""Routes under /api/courses/."""

from rest_framework.routers import DefaultRouter

from apps.courses.views import CourseViewSet

router = DefaultRouter()
router.register('', CourseViewSet, basename='course')

urlpatterns = router.urls
