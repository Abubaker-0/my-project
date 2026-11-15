"""Serializers for people, profiles, and contracts.

Serializers check the shape of a request. The service layer decides whether
the signed-in role is allowed to perform it.
"""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import Contract, Profile, User
from apps.accounts.services import active_contract_for, creator_error
from apps.common.choices import STAFF_CONTRACT_ROLES, ContractType, Gender, PaymentMethod, Role, SalaryType


def photo_url_for(user):
    """Relative API path the client loads with its access token."""

    try:
        profile = user.profile
    except Profile.DoesNotExist:
        return None
    if not profile.photo:
        return None
    return f'profile/photo/{user.id}/'


class UserBriefSerializer(serializers.ModelSerializer):
    """Compact person used inside courses, rosters, and payments."""

    full_name = serializers.CharField(read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'full_name', 'first_name', 'last_name', 'role', 'gender', 'email', 'phone', 'photo_url')

    def get_photo_url(self, obj):
        return photo_url_for(obj)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        viewer = getattr(request, 'user', None)
        if not viewer or not getattr(viewer, 'is_authenticated', False) or viewer.id == instance.id:
            return data
        # Students and teachers do not receive another student's contact or photo.
        if instance.role == Role.STUDENT and viewer.role in (Role.STUDENT, Role.TEACHER):
            data['email'] = ''
            data['phone'] = ''
            data['photo_url'] = None
        return data


class ContractSerializer(serializers.ModelSerializer):
    """Staff contract as stored. Locks are internal and are not exposed."""

    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Contract
        fields = (
            'id', 'user', 'user_name', 'center', 'contract_type', 'start_date', 'end_date',
            'salary_type', 'salary_amount', 'payment_method', 'status', 'notes',
            'created_at',
        )
        read_only_fields = ('id', 'user', 'center', 'status', 'created_at')


class ContractInputSerializer(serializers.Serializer):
    """Contract fields accepted when hiring staff or assigning a manager."""

    contract_type = serializers.ChoiceField(choices=ContractType.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    salary_type = serializers.ChoiceField(choices=SalaryType.choices)
    salary_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices)
    notes = serializers.CharField(required=False, allow_blank=True)


class UserSerializer(serializers.ModelSerializer):
    """Full account used by the profile page and user tables."""

    full_name = serializers.CharField(read_only=True)
    photo_url = serializers.SerializerMethodField()
    center = serializers.SerializerMethodField()
    contract = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    date_of_birth = serializers.SerializerMethodField()
    enrollment_count = serializers.SerializerMethodField()
    course_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'gender', 'role', 'is_active', 'center', 'photo_url',
            'address', 'bio', 'date_of_birth', 'contract', 'enrollment_count',
            'course_count', 'date_joined',
        )

    def get_photo_url(self, obj):
        return photo_url_for(obj)

    def get_center(self, obj):
        if not obj.center_id:
            return None
        return {'id': obj.center_id, 'name': obj.center.name, 'code': obj.center.code, 'is_active': obj.center.is_active}

    def get_contract(self, obj):
        if obj.role not in STAFF_CONTRACT_ROLES:
            return None
        prefetched = getattr(obj, 'active_contracts', None)
        contract = prefetched[0] if prefetched else None
        if contract is None and prefetched is None:
            contract = active_contract_for(obj)
        if contract is None:
            return None
        return ContractSerializer(contract).data

    def _profile(self, obj):
        try:
            return obj.profile
        except Profile.DoesNotExist:
            return None

    def get_address(self, obj):
        profile = self._profile(obj)
        return profile.address if profile else ''

    def get_bio(self, obj):
        profile = self._profile(obj)
        return profile.bio if profile else ''

    def get_date_of_birth(self, obj):
        profile = self._profile(obj)
        return profile.date_of_birth if profile else None

    def get_enrollment_count(self, obj):
        if hasattr(obj, 'enrollment_count'):
            return obj.enrollment_count
        return obj.enrollments.filter(status='active').count()

    def get_course_count(self, obj):
        if hasattr(obj, 'course_count'):
            return obj.course_count
        return obj.courses_teaching.filter(is_deleted=False).count()


class UserCreateSerializer(serializers.Serializer):
    """Payload for hiring a manager, finance manager, teacher, or student."""

    username = serializers.RegexField(r'^[\w.@+-]+$', max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone = serializers.RegexField(r'^[0-9+\-() ]{7,20}$')
    gender = serializers.ChoiceField(choices=Gender.choices)
    role = serializers.ChoiceField(choices=Role.choices)
    address = serializers.CharField(required=False, allow_blank=True)
    contract = ContractInputSerializer(required=False)

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        actor = self.context['request'].user
        message = creator_error(actor, attrs['role'])
        if message:
            raise serializers.ValidationError({'role': message})
        needs_contract = attrs['role'] in (Role.TEACHER, Role.FINANCE_MANAGER)
        if needs_contract and not attrs.get('contract'):
            raise serializers.ValidationError({'contract': 'A contract is required for this role.'})
        if attrs['role'] == Role.STUDENT and attrs.get('contract'):
            raise serializers.ValidationError({'contract': 'Students do not receive a staff contract.'})
        return attrs


class UserUpdateSerializer(serializers.Serializer):
    """Fields a manager may correct on another person. Role is a separate action."""

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone = serializers.RegexField(r'^[0-9+\-() ]{7,20}$')
    gender = serializers.ChoiceField(choices=Gender.choices)
    email = serializers.EmailField()
    address = serializers.CharField(required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)


class ProfileUpdateSerializer(serializers.Serializer):
    """Fields a person may change on their own profile."""

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone = serializers.RegexField(r'^[0-9+\-() ]{7,20}$')
    gender = serializers.ChoiceField(choices=Gender.choices)
    email = serializers.EmailField()
    address = serializers.CharField(required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(trim_whitespace=False)


class PasswordResetRequestSerializer(serializers.Serializer):
    login = serializers.CharField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(trim_whitespace=False)


class RoleChangeSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[Role.FINANCE_MANAGER, Role.TEACHER, Role.STUDENT])
