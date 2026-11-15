"""Permission inspection, restrictions, and in-app notifications."""

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.centers.models import Center
from apps.common.choices import Role
from apps.common.exceptions import BusinessRuleError
from apps.common.models import Notification, PermissionOverride
from apps.common.notifications import mark_read
from apps.common.permissions_catalog import CATALOG, explain_permissions, set_permission_override


class PermissionCatalogView(APIView):
    def get(self, request):
        if request.user.role not in (Role.SUPER_ADMIN, Role.CENTER_MANAGER):
            raise PermissionDenied('You cannot read the permission catalog.')
        return Response([
            {
                'code': spec.code,
                'roles': sorted(spec.ceiling),
                'protected': spec.protected,
                'description': spec.description,
            }
            for spec in CATALOG.values()
        ])


class EffectivePermissionView(APIView):
    def get(self, request):
        center = request.user.center
        center_id = request.query_params.get('center')
        if center_id and request.user.role == Role.SUPER_ADMIN:
            center = Center.objects.filter(pk=center_id).first()
        return Response({
            'role': request.user.role,
            'center': getattr(center, 'id', None),
            'permissions': explain_permissions(request.user, center),
        })


class PermissionOverrideView(APIView):
    def get(self, request):
        if request.user.role == Role.SUPER_ADMIN:
            rows = PermissionOverride.objects.all()
        elif request.user.role == Role.CENTER_MANAGER:
            rows = PermissionOverride.objects.filter(center_id=request.user.center_id)
        else:
            raise PermissionDenied('You cannot read permission restrictions.')
        return Response([
            {'id': row.id, 'role': row.role, 'code': row.code, 'center': row.center_id, 'allowed': row.allowed}
            for row in rows
        ])

    def post(self, request):
        center = None
        if request.data.get('center'):
            center = Center.objects.filter(pk=request.data['center']).first()
            if center is None:
                raise BusinessRuleError('Center was not found.')
        state = set_permission_override(
            actor=request.user,
            role=request.data.get('role'),
            code=request.data.get('code'),
            allowed=bool(request.data.get('allowed', False)),
            center=center,
            request=request,
        )
        return Response({'state': state})


class NotificationListView(APIView):
    def get(self, request):
        rows = Notification.objects.filter(recipient=request.user)[:30]
        return Response([
            {
                'id': row.id,
                'kind': row.kind,
                'title': row.title,
                'body': row.body,
                'read': row.read_at is not None,
                'created_at': row.created_at,
            }
            for row in rows
        ])


class NotificationReadView(APIView):
    def post(self, request, notification_id):
        row = Notification.objects.filter(pk=notification_id, recipient=request.user).first()
        if row is None:
            raise BusinessRuleError('Notification was not found.')
        mark_read(row, request.user)
        return Response({'id': row.id, 'read': True})


class NotificationReadAllView(APIView):
    def post(self, request):
        Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=timezone.now())
        return Response({'read': True})
