"""Routes under /api/centers/."""

from rest_framework.routers import DefaultRouter

from apps.centers.views import CenterViewSet

router = DefaultRouter()
router.register('', CenterViewSet, basename='center')

urlpatterns = router.urls
