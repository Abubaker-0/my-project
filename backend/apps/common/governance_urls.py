"""Routes for permissions and in-app notifications."""

from django.urls import path

from apps.common.governance_views import (
    EffectivePermissionView,
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
    PermissionCatalogView,
    PermissionHistoryView,
    PermissionMatrixView,
    PermissionOverrideView,
    PermissionPreviewView,
    PermissionRestoreView,
)

urlpatterns = [
    path('permissions/catalog/', PermissionCatalogView.as_view(), name='permission-catalog'),
    path('permissions/effective/', EffectivePermissionView.as_view(), name='permission-effective'),
    path('permissions/overrides/', PermissionOverrideView.as_view(), name='permission-overrides'),
    path('permissions/preview/', PermissionPreviewView.as_view(), name='permission-preview'),
    path('permissions/matrix/', PermissionMatrixView.as_view(), name='permission-matrix'),
    path('permissions/history/', PermissionHistoryView.as_view(), name='permission-history'),
    path('permissions/restore/', PermissionRestoreView.as_view(), name='permission-restore'),
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/read-all/', NotificationReadAllView.as_view(), name='notifications-read-all'),
    path('notifications/<int:notification_id>/read/', NotificationReadView.as_view(), name='notification-read'),
]
