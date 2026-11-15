"""Finance API.

Finance managers record payments, plans, scholarships, and refund requests.
Center managers can read the same center and are the only role that can
approve a refund. Students see their own invoices. Other centers are excluded
by the queryset before the object lookup.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.choices import Role
from apps.common.exceptions import BusinessRuleError
from apps.enrollments.models import Enrollment
from apps.finance.models import Installment, Invoice, Payment, Refund, Scholarship
from apps.finance.serializers import (
    ApplyScholarshipSerializer,
    InstallmentPlanSerializer,
    InstallmentSerializer,
    InvoiceSerializer,
    PaymentSerializer,
    PaymentWriteSerializer,
    RefundReviewSerializer,
    RefundSerializer,
    RefundWriteSerializer,
    ScholarshipSerializer,
    ScholarshipWriteSerializer,
)
from apps.finance.services import (
    apply_scholarship,
    build_snapshot,
    create_installment_plan,
    create_scholarship,
    record_payment,
    refresh_overdue_installments,
    request_refund,
    review_refund,
)


def _scope(user, queryset, center_field='center_id', student_field='student_id'):
    if user.role == Role.SUPER_ADMIN:
        return queryset
    if user.role == Role.STUDENT:
        return queryset.filter(**{student_field: user.id})
    if user.role in (Role.FINANCE_MANAGER, Role.CENTER_MANAGER) and user.center_id:
        return queryset.filter(**{center_field: user.center_id})
    return queryset.none()


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    search_fields = ('invoice_number', 'student__first_name', 'student__last_name', 'enrollment__course__name')
    ordering_fields = ('created_at', 'net_amount', 'status')
    filterset_fields = ('status', 'center', 'student')

    def get_queryset(self):
        queryset = Invoice.objects.select_related(
            'student', 'student__profile', 'enrollment', 'enrollment__course', 'enrollment__scholarship_grant__scholarship'
        ).prefetch_related('installments', 'payments')
        return _scope(self.request.user, queryset)


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    http_method_names = ['get', 'post', 'head', 'options']
    search_fields = ('reference', 'student__first_name', 'student__last_name', 'invoice__invoice_number')
    ordering_fields = ('paid_at', 'amount')
    filterset_fields = ('method', 'center', 'invoice', 'student')

    def get_queryset(self):
        return _scope(self.request.user, Payment.objects.select_related('student', 'invoice').order_by('-paid_at'))

    def create(self, request, *args, **kwargs):
        serializer = PaymentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        invoice = Invoice.objects.filter(pk=data['invoice']).first()
        if invoice is None:
            raise BusinessRuleError('Invoice was not found.')
        payment = record_payment(
            invoice=invoice,
            amount=data['amount'],
            method=data['method'],
            actor=request.user,
            reference=data.get('reference', ''),
            paid_at=data.get('paid_at'),
            request=request,
            idempotency_key=data.get('idempotency_key', ''),
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def receipt(self, request, pk=None):
        payment = self.get_object()
        return Response({
            'receipt_number': payment.receipt_number,
            'amount': payment.amount,
            'method': payment.method,
            'reference': payment.reference,
            'paid_at': payment.paid_at,
            'invoice_number': payment.invoice.invoice_number,
            'student': payment.student.full_name,
            'center': payment.center.code,
            'statement': 'This receipt records money received by the center. It is not a bank transfer.',
        })


class InstallmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InstallmentSerializer
    filterset_fields = ('status', 'invoice')
    ordering_fields = ('due_date', 'number')

    def get_queryset(self):
        user = self.request.user
        refresh_overdue_installments(None if user.role == Role.SUPER_ADMIN else user.center_id)
        queryset = Installment.objects.select_related('invoice')
        return _scope(user, queryset, center_field='invoice__center_id', student_field='invoice__student_id')

    @action(detail=False, methods=['post'], url_path='plan')
    def plan(self, request):
        serializer = InstallmentPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = Invoice.objects.filter(pk=serializer.validated_data['invoice']).first()
        if invoice is None:
            raise BusinessRuleError('Invoice was not found.')
        items = []
        for raw in serializer.validated_data['installments']:
            if 'due_date' not in raw:
                raise BusinessRuleError('Each installment needs a due date.')
            from datetime import date
            due = raw['due_date']
            if isinstance(due, str):
                due = date.fromisoformat(due)
            amount = raw.get('amount')
            items.append({'due_date': due, 'amount': amount})
        created = create_installment_plan(
            invoice=invoice,
            installments=items,
            actor=request.user,
            request=request,
            replace=serializer.validated_data.get('replace', False),
        )
        return Response(InstallmentSerializer(created, many=True).data, status=status.HTTP_201_CREATED)


class ScholarshipViewSet(viewsets.ModelViewSet):
    serializer_class = ScholarshipSerializer
    http_method_names = ['get', 'post', 'head', 'options']
    search_fields = ('name',)
    filterset_fields = ('center', 'scholarship_type', 'is_active')

    def get_queryset(self):
        # Grants are center definitions, so students see scholarships applied to them
        # through invoices. The catalog itself is for finance and the manager.
        user = self.request.user
        queryset = Scholarship.objects.all()
        if user.role == Role.SUPER_ADMIN:
            return queryset
        if user.role in (Role.FINANCE_MANAGER, Role.CENTER_MANAGER) and user.center_id:
            return queryset.filter(center_id=user.center_id)
        if user.role == Role.STUDENT:
            return queryset.filter(grants__student=user).distinct()
        return queryset.none()

    def create(self, request, *args, **kwargs):
        serializer = ScholarshipWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scholarship = create_scholarship(serializer.validated_data, request.user, request)
        return Response(ScholarshipSerializer(scholarship).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def apply(self, request):
        serializer = ApplyScholarshipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scholarship = Scholarship.objects.filter(pk=serializer.validated_data['scholarship']).first()
        enrollment = Enrollment.objects.filter(pk=serializer.validated_data['enrollment']).select_related('course', 'center', 'student').first()
        if scholarship is None or enrollment is None:
            raise BusinessRuleError('Scholarship or enrollment was not found.')
        invoice = apply_scholarship(scholarship=scholarship, enrollment=enrollment, actor=request.user, request=request)
        return Response(InvoiceSerializer(Invoice.objects.get(pk=invoice.pk)).data)


class RefundViewSet(viewsets.ModelViewSet):
    serializer_class = RefundSerializer
    http_method_names = ['get', 'post', 'head', 'options']
    search_fields = ('student__first_name', 'student__last_name', 'invoice__invoice_number', 'reason')
    filterset_fields = ('status', 'center', 'student', 'invoice')

    def get_queryset(self):
        queryset = Refund.objects.select_related('student', 'student__profile', 'invoice', 'center')
        return _scope(self.request.user, queryset)

    def create(self, request, *args, **kwargs):
        serializer = RefundWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = Invoice.objects.filter(pk=serializer.validated_data['invoice']).first()
        if invoice is None:
            raise BusinessRuleError('Invoice was not found.')
        refund = request_refund(
            invoice=invoice,
            amount=serializer.validated_data['amount'],
            reason=serializer.validated_data['reason'],
            actor=request.user,
            request=request,
        )
        return Response(RefundSerializer(refund).data, status=status.HTTP_201_CREATED)

    def _review(self, request, pk, approve):
        serializer = RefundReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refund = review_refund(
            refund=self.get_object(),
            actor=request.user,
            approve=approve,
            note=serializer.validated_data.get('decision_note', ''),
            request=request,
        )
        return Response(RefundSerializer(refund).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._review(request, pk, True)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._review(request, pk, False)


class FinanceSummaryView(APIView):
    """Live finance figures. Official reports are a separate frozen snapshot."""

    def get(self, request):
        user = request.user
        if user.role not in (Role.SUPER_ADMIN, Role.CENTER_MANAGER, Role.FINANCE_MANAGER):
            raise PermissionDenied('You cannot view financial summaries.')
        from apps.centers.models import Center
        from datetime import date
        center_id = request.query_params.get('center')
        if user.role == Role.SUPER_ADMIN:
            center = Center.objects.filter(pk=center_id, is_deleted=False).first() if center_id else None
            if center is None:
                raise BusinessRuleError('Choose a center.')
        else:
            center = user.center
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        start = date.fromisoformat(start) if start else None
        end = date.fromisoformat(end) if end else None
        return Response(build_snapshot(center, start, end))
