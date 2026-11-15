"""Routes under /api/contracts/."""

from rest_framework.routers import DefaultRouter

from apps.accounts.contract_views import ContractViewSet

router = DefaultRouter()
router.register('', ContractViewSet, basename='contract')

urlpatterns = router.urls
