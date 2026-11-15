"""Dashboards, official reports, and the audit log."""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.centers.models import Center
from apps.common.choices import Role
from apps.common.exceptions import BusinessRuleError
from apps.common.models import AuditLog
from apps.reports.models import FinancialReport
from apps.reports.serializers import FinancialReportSerializer, FinancialReportWriteSerializer
from apps.reports.services import build_dashboard, create_financial_report, send_report, submit_report


class DashboardView(APIView):
    """Role-specific dashboard. The service hides other centers."""

    def get(self, request):
        return Response(build_dashboard(request.user))


class FinancialReportViewSet(viewsets.ModelViewSet):
    serializer_class = FinancialReportSerializer
    http_method_names = ['get', 'post', 'head', 'options']
    filterset_fields = ('status', 'center')
    ordering_fields = ('period_end', 'created_at')

    def get_queryset(self):
        queryset = FinancialReport.objects.select_related('center', 'prepared_by', 'sent_by')
        user = self.request.user
        if user.role == Role.SUPER_ADMIN:
            return queryset
        if user.role in (Role.CENTER_MANAGER, Role.FINANCE_MANAGER) and user.center_id:
            return queryset.filter(center_id=user.center_id)
        return queryset.none()

    def create(self, request, *args, **kwargs):
        serializer = FinancialReportWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if request.user.role == Role.FINANCE_MANAGER:
            center = request.user.center
        else:
            center = Center.objects.filter(pk=data.get('center')).first()
        if center is None:
            raise BusinessRuleError('Choose a center.')
        report = create_financial_report(
            center=center,
            title=data.get('title', ''),
            start=data['period_start'],
            end=data['period_end'],
            actor=request.user,
            request=request,
        )
        return Response(FinancialReportSerializer(report).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        report = submit_report(self.get_object(), request.user, request)
        return Response(FinancialReportSerializer(report).data)

    @action(detail=True, methods=['post'], url_path='send')
    def send(self, request, pk=None):
        report = send_report(self.get_object(), request.user, request)
        return Response(FinancialReportSerializer(report).data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Security and business events. Managers see their center. Super admin sees all."""

    filterset_fields = ('action', 'level', 'center')
    search_fields = ('message', 'action', 'entity')
    ordering_fields = ('created_at',)

    def get_serializer_class(self):
        from rest_framework import serializers

        class AuditSerializer(serializers.ModelSerializer):
            username = serializers.CharField(source='user.username', read_only=True)

            class Meta:
                model = AuditLog
                fields = (
                    'id', 'user', 'username', 'center', 'action', 'entity', 'entity_id',
                    'message', 'level', 'ip_address', 'created_at',
                )

        return AuditSerializer

    def get_queryset(self):
        queryset = AuditLog.objects.select_related('user', 'center')
        user = self.request.user
        if user.role == Role.SUPER_ADMIN:
            return queryset
        if user.role == Role.CENTER_MANAGER and user.center_id:
            return queryset.filter(center_id=user.center_id)
        return queryset.none()
