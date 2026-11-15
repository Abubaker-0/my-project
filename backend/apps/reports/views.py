"""Dashboards, official reports, and the audit log."""

import csv

from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.centers.models import Center
from apps.common.choices import ReportStatus, Role
from apps.common.exceptions import BusinessRuleError
from apps.common.models import AuditLog
from apps.reports.models import FinancialReport
from apps.reports.serializers import FinancialReportSerializer, FinancialReportWriteSerializer
from apps.common.permissions_catalog import has_permission
from apps.finance.models import Invoice
from apps.reports.services import (
    build_dashboard,
    create_financial_report,
    integrity_report,
    return_report,
    revise_report,
    send_report,
    submit_report,
)


class IntegrityView(APIView):
    """Read-only integrity findings for the super admin."""

    def get(self, request):
        if not has_permission(request.user, 'integrity.read'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only the super admin can read the integrity dashboard.')
        return Response({'issues': integrity_report()})


class InvoiceExportView(APIView):
    """CSV of invoices inside the caller's center. Students are outside the ceiling."""

    def get(self, request):
        center = request.user.center
        if not has_permission(request.user, 'exports.invoices', center):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You cannot export invoices.')
        rows = Invoice.objects.select_related('student', 'center')
        if request.user.role != Role.SUPER_ADMIN:
            rows = rows.filter(center_id=request.user.center_id)
        elif request.query_params.get('center'):
            rows = rows.filter(center_id=request.query_params['center'])
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="invoices.csv"'
        writer = csv.writer(response)
        writer.writerow(['invoice', 'center', 'student', 'net', 'paid', 'refunded', 'outstanding', 'status', 'refund_state'])
        for invoice in rows:
            writer.writerow([
                invoice.invoice_number,
                invoice.center.code,
                invoice.student.username,
                invoice.net_amount,
                invoice.paid_amount,
                invoice.refunded_amount,
                invoice.outstanding,
                invoice.status,
                invoice.refund_state,
            ])
        return response


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
            if 'status' not in self.request.query_params:
                return queryset.filter(status=ReportStatus.SENT_TO_SUPER_ADMIN)
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

    @action(detail=True, methods=['post'], url_path='return')
    def return_to_finance(self, request, pk=None):
        report = return_report(self.get_object(), request.user, request.data.get('note', ''), request)
        return Response(FinancialReportSerializer(report).data)

    @action(detail=True, methods=['post'])
    def revise(self, request, pk=None):
        report = revise_report(self.get_object(), request.user, request)
        return Response(FinancialReportSerializer(report).data, status=status.HTTP_201_CREATED)


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
