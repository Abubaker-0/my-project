"""Center, settings, and statistics serializers."""

from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.centers.models import Center, CenterSettings, GlobalSettings


class CenterSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CenterSettings
        fields = ('allow_self_enrollment', 'require_enrollment_approval', 'max_installments')


class GlobalSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSettings
        fields = (
            'organization_name', 'support_email', 'support_phone', 'currency_label',
            'default_allow_self_enrollment', 'max_installments',
        )


class CenterSerializer(serializers.ModelSerializer):
    """Center list and detail, including the derived active manager."""

    manager = serializers.SerializerMethodField()
    settings = CenterSettingsSerializer(read_only=True)
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Center
        fields = (
            'id', 'name', 'code', 'address', 'city', 'phone', 'email', 'description',
            'is_active', 'established_on', 'manager', 'settings', 'logo_url', 'created_at',
        )

    def get_manager(self, obj):
        manager = obj.get_active_manager()
        if manager is None:
            return None
        return UserBriefSerializer(manager, context=self.context).data

    def get_logo_url(self, obj):
        if not obj.logo:
            return None
        return f'centers/{obj.id}/logo/'


class CenterWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=180)
    code = serializers.CharField(max_length=20)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    established_on = serializers.DateField(required=False, allow_null=True)


class CenterUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=180, required=False)
    code = serializers.CharField(max_length=20, required=False)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    established_on = serializers.DateField(required=False, allow_null=True)


class AssignManagerSerializer(serializers.Serializer):
    """Existing available manager plus the contract that makes the assignment real."""

    from apps.accounts.serializers import ContractInputSerializer

    manager_id = serializers.IntegerField()
    replace = serializers.BooleanField(required=False, default=False)
    contract = ContractInputSerializer()
