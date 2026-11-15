"""Official financial report serializer. The snapshot is stored as sent."""

from rest_framework import serializers

from apps.reports.models import FinancialReport


class FinancialReportSerializer(serializers.ModelSerializer):
    center_name = serializers.CharField(source='center.name', read_only=True)
    prepared_by_name = serializers.CharField(source='prepared_by.full_name', read_only=True)

    class Meta:
        model = FinancialReport
        fields = (
            'id', 'center', 'center_name', 'title', 'period_start', 'period_end', 'status',
            'prepared_by', 'prepared_by_name', 'submitted_at', 'sent_by', 'sent_at',
            'revision', 'previous', 'return_note', 'returned_at',
            'snapshot', 'created_at',
        )


class FinancialReportWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=180, required=False, allow_blank=True)
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    center = serializers.IntegerField(required=False)
