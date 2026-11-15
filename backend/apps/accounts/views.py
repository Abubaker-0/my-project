"""User management API.

Super admin creates center managers. A center manager creates and maintains
finance managers, teachers, and students in their own center. Querysets are
center-scoped before any lookup, so another center's id returns 404.
"""

from django.db.models import Count, Prefetch, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.models import Contract, User
from apps.accounts.serializers import (
    RoleChangeSerializer,
    UserBriefSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.accounts.services import (
    activate_user,
    change_role,
    create_account,
    deactivate_user,
    refresh_expired_contracts,
    update_account,
)
from apps.centers.services import available_managers
from apps.common.choices import ContractStatus, Role


class UserViewSet(viewsets.ModelViewSet):
    """List, hire, edit, and deactivate people."""

    serializer_class = UserSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    ordering_fields = ('first_name', 'last_name', 'date_joined', 'username')
    filterset_fields = ('role', 'gender', 'is_active', 'center')

    def get_queryset(self):
        refresh_expired_contracts()
        queryset = User.objects.select_related('center', 'profile').prefetch_related(
            Prefetch(
                'contracts',
                queryset=Contract.objects.filter(status=ContractStatus.ACTIVE),
                to_attr='active_contracts',
            )
        ).annotate(
            enrollment_count=Count('enrollments', filter=Q(enrollments__status='active'), distinct=True),
            course_count=Count('courses_teaching', filter=Q(courses_teaching__is_deleted=False), distinct=True),
        )
        user = self.request.user
        if user.role == Role.SUPER_ADMIN:
            return queryset
        if user.role == Role.CENTER_MANAGER:
            return queryset.filter(center_id=user.center_id)
        if user.role == Role.FINANCE_MANAGER:
            return queryset.filter(center_id=user.center_id, role=Role.STUDENT)
        return queryset.none()

    def create(self, request, *args, **kwargs):
        serializer = UserCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = create_account(serializer.validated_data, request.user, request)
        return Response(UserSerializer(user, context={'request': request}).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        target = self.get_object()
        serializer = UserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = update_account(target, serializer.validated_data, request.user, request)
        return Response(UserSerializer(user, context={'request': request}).data)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='available-managers')
    def available_managers_action(self, request):
        """Managers with no active contract. Used by the center assignment form."""

        if request.user.role != Role.SUPER_ADMIN:
            raise PermissionDenied('Only the super admin can view managers available for assignment.')
        return Response(UserBriefSerializer(available_managers(), many=True).data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = deactivate_user(self.get_object(), request.user, request)
        return Response(UserSerializer(user, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = activate_user(self.get_object(), request.user, request)
        return Response(UserSerializer(user, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='role')
    def set_role(self, request, pk=None):
        serializer = RoleChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = change_role(self.get_object(), serializer.validated_data['role'], request.user, request)
        return Response(UserSerializer(user, context={'request': request}).data)
