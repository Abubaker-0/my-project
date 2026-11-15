"""Finance serializers. Money is decimal and methods are cash or bank only."""

from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.common.choices import PaymentMethod, ScholarshipType
from apps.finance.models import Installment, Invoice, Payment, Refund, Scholarship, ScholarshipGrant


class InstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Installment
        fields = ('id', 'number', 'due_date', 'amount', 'paid_amount', 'status')


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            'id', 'invoice', 'amount', 'method', 'reference', 'receipt_number',
            'paid_at', 'received_by', 'student',
        )


class ScholarshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scholarship
        fields = ('id', 'center', 'name', 'scholarship_type', 'value', 'description', 'is_active', 'created_at')


class GrantSerializer(serializers.ModelSerializer):
    scholarship_name = serializers.CharField(source='scholarship.name', read_only=True)

    class Meta:
        model = ScholarshipGrant
        fields = ('id', 'scholarship', 'scholarship_name', 'discount_amount', 'student', 'enrollment')


class InvoiceSerializer(serializers.ModelSerializer):
    student = UserBriefSerializer(read_only=True)
    course_name = serializers.CharField(source='enrollment.course.name', read_only=True)
    course_id = serializers.IntegerField(source='enrollment.course_id', read_only=True)
    outstanding = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    refund_state = serializers.CharField(read_only=True)
    installments = InstallmentSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    scholarship = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = (
            'id', 'invoice_number', 'student', 'course_name', 'course_id', 'center',
            'gross_amount', 'scholarship_amount', 'net_amount', 'paid_amount',
            'refunded_amount', 'outstanding', 'status', 'refund_state', 'installments', 'payments',
            'scholarship', 'created_at',
        )

    def get_scholarship(self, obj):
        grant = getattr(obj.enrollment, 'scholarship_grant', None)
        if grant is None:
            try:
                grant = obj.enrollment.scholarship_grant
            except ScholarshipGrant.DoesNotExist:
                return None
        return {'id': grant.scholarship_id, 'name': grant.scholarship.name, 'discount_amount': grant.discount_amount}


class RefundSerializer(serializers.ModelSerializer):
    student = UserBriefSerializer(read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)

    class Meta:
        model = Refund
        fields = (
            'id', 'invoice', 'invoice_number', 'student', 'center', 'amount', 'reason',
            'status', 'requested_by', 'reviewed_by', 'reviewed_at', 'decision_note', 'created_at',
        )


class PaymentWriteSerializer(serializers.Serializer):
    invoice = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    method = serializers.ChoiceField(choices=PaymentMethod.choices)
    reference = serializers.CharField(required=False, allow_blank=True)
    paid_at = serializers.DateTimeField(required=False)
    idempotency_key = serializers.CharField(max_length=80)


class InstallmentPlanSerializer(serializers.Serializer):
    invoice = serializers.IntegerField()
    installments = serializers.ListField(child=serializers.DictField(), min_length=1, max_length=3)
    replace = serializers.BooleanField(required=False, default=False)


class ScholarshipWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    scholarship_type = serializers.ChoiceField(choices=ScholarshipType.choices)
    value = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)


class ApplyScholarshipSerializer(serializers.Serializer):
    scholarship = serializers.IntegerField()
    enrollment = serializers.IntegerField()


class RefundWriteSerializer(serializers.Serializer):
    invoice = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    reason = serializers.CharField()


class RefundReviewSerializer(serializers.Serializer):
    decision_note = serializers.CharField(required=False, allow_blank=True)
