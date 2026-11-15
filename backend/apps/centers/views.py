"""Center API. Day-to-day records are reached from here but not created by super admin."""

import mimetypes

from django.db.models import Prefetch
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Contract
from apps.accounts.models import User
from apps.centers.models import Center, CenterSettings, GlobalSettings
from apps.centers.serializers import (
    AssignManagerSerializer,
    CenterSerializer,
    CenterSettingsSerializer,
    CenterUpdateSerializer,
    CenterWriteSerializer,
    GlobalSettingsSerializer,
)
from apps.centers.services import (
    archive_center,
    assign_manager,
    center_statistics,
    create_center,
    set_center_active,
    set_center_logo,
    update_center,
    update_center_settings,
    update_global_settings,
    visible_centers,
)
from apps.common.access import assert_same_center
from apps.common.choices import ContractStatus, Role


def _with_manager(queryset):
    return queryset.prefetch_related(
        Prefetch(
            'contracts',
            queryset=Contract.objects.filter(status=ContractStatus.ACTIVE, active_manager_lock__isnull=False).select_related('user', 'user__profile'),
            to_attr='_prefetched_manager',
        )
    )


class CenterViewSet(viewsets.ModelViewSet):
    """Centers the caller is allowed to see. Writes are split by role."""

    serializer_class = CenterSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    search_fields = ('name', 'code', 'city')
    ordering_fields = ('name', 'code', 'created_at')
    filterset_fields = ('is_active', 'city')

    def get_queryset(self):
        return _with_manager(visible_centers(self.request.user).select_related('settings'))

    def create(self, request, *args, **kwargs):
        serializer = CenterWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        center = create_center(serializer.validated_data, request.user, request)
        center = self.get_queryset().get(pk=center.pk)
        return Response(CenterSerializer(center, context={'request': request}).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        serializer = CenterUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        center = update_center(self.get_object(), serializer.validated_data, request.user, request)
        center = self.get_queryset().get(pk=center.pk)
        return Response(CenterSerializer(center, context={'request': request}).data)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        center = set_center_active(self.get_object(), True, request.user, request)
        return Response(CenterSerializer(self.get_queryset().get(pk=center.pk), context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        center = set_center_active(self.get_object(), False, request.user, request)
        return Response(CenterSerializer(self.get_queryset().get(pk=center.pk), context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        archive_center(self.get_object(), request.user, request)
        return Response({'detail': 'Center archived.'})

    @action(detail=True, methods=['post'], url_path='assign-manager')
    def assign_manager_action(self, request, pk=None):
        serializer = AssignManagerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        manager = User.objects.filter(pk=serializer.validated_data['manager_id']).first()
        if manager is None:
            raise NotFound('Manager was not found.')
        assign_manager(
            center=self.get_object(),
            manager=manager,
            contract_data=serializer.validated_data['contract'],
            actor=request.user,
            replace=serializer.validated_data['replace'],
            request=request,
        )
        return Response(CenterSerializer(self.get_queryset().get(pk=pk), context={'request': request}).data)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        center = self.get_object()
        if request.user.role not in (Role.SUPER_ADMIN, Role.CENTER_MANAGER, Role.FINANCE_MANAGER):
            raise PermissionDenied('You cannot view center statistics.')
        return Response(center_statistics(center))

    @action(detail=True, methods=['get', 'patch'], url_path='settings')
    def center_settings(self, request, pk=None):
        center = self.get_object()
        if request.user.role not in (Role.SUPER_ADMIN, Role.CENTER_MANAGER, Role.FINANCE_MANAGER):
            raise PermissionDenied('You cannot view center settings.')
        settings_obj = center.settings
        if request.method == 'GET':
            return Response(CenterSettingsSerializer(settings_obj).data)
        serializer = CenterSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_center_settings(settings_obj, serializer.validated_data, request.user, request)
        return Response(CenterSettingsSerializer(updated).data)

    @action(detail=True, methods=['get', 'post'], url_path='logo')
    def logo(self, request, pk=None):
        """Download or replace the center logo. The file is not on a public media URL."""

        center = self.get_object()
        if request.method == 'GET':
            if not center.logo:
                raise NotFound('This center has no logo.')
            content_type = mimetypes.guess_type(center.logo.name)[0] or 'image/jpeg'
            return FileResponse(center.logo.open('rb'), content_type=content_type)
        upload = request.FILES.get('logo')
        if upload is None:
            raise NotFound('Choose a logo to upload.')
        set_center_logo(center, upload, request.user, request)
        return Response(CenterSerializer(self.get_queryset().get(pk=pk), context={'request': request}).data)


class GlobalSettingsView(APIView):
    """The single organization settings row."""

    def get(self, request):
        if request.user.role != Role.SUPER_ADMIN:
            raise PermissionDenied('Only the super admin can read global settings.')
        return Response(GlobalSettingsSerializer(GlobalSettings.load()).data)

    def patch(self, request):
        serializer = GlobalSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_global_settings(serializer.validated_data, request.user)
        return Response(GlobalSettingsSerializer(updated).data)
