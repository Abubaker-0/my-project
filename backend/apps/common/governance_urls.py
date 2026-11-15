"""Routes for permissions and in-app notifications."""

from django.urls import path

from apps.common.governance_views import (
    EffectivePermissionView,
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
    PermissionCatalogView,
    PermissionOverrideView,
)

urlpatterns = [
    path('permissions/catalog/', PermissionCatalogView.as_view(), name='permission-catalog'),
    path('permissions/effective/', EffectivePermissionView.as_view(), name='permission-effective'),
    path('permissions/overrides/', PermissionOverrideView.as_view(), name='permission-overrides'),
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/read-all/', NotificationReadAllView.as_view(), name='notifications-read-all'),
    path('notifications/<int:notification_id>/read/', NotificationReadView.as_view(), name='notification-read'),
]
