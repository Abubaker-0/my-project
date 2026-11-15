"""Contract list, creation, and termination.

Center managers contract teachers and finance managers. The super admin
contracts center managers through the center assignment endpoint, not here.
"""

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Contract, User
from apps.accounts.serializers import ContractInputSerializer, ContractSerializer
from apps.accounts.services import create_contract, refresh_expired_contracts, terminate_contract
from apps.common.choices import Role


class ContractViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Contracts visible to the signed-in role, always limited to their center."""

    serializer_class = ContractSerializer
    search_fields = ('user__first_name', 'user__last_name', 'user__username')
    ordering_fields = ('start_date', 'end_date', 'salary_amount', 'status')
    filterset_fields = ('status', 'contract_type', 'salary_type', 'user', 'center')

    def get_queryset(self):
        refresh_expired_contracts()
        queryset = Contract.objects.select_related('user', 'center')
        user = self.request.user
        if user.role == Role.SUPER_ADMIN:
            return queryset
        if user.role == Role.CENTER_MANAGER:
            return queryset.filter(center_id=user.center_id)
        if user.role in (Role.FINANCE_MANAGER, Role.TEACHER):
            return queryset.filter(user=user)
        return queryset.none()

    def create(self, request, *args, **kwargs):
        if request.user.role != Role.CENTER_MANAGER:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Assign center managers from the center page. This form is for center staff.')
        payload = ContractInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        target = User.objects.filter(pk=request.data.get('user')).first()
        if target is None:
            from apps.common.exceptions import BusinessRuleError
            raise BusinessRuleError('Choose a user for this contract.')
        contract = create_contract(target, request.user.center, payload.validated_data, request.user, request)
        return Response(ContractSerializer(contract).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def terminate(self, request, pk=None):
        contract = terminate_contract(self.get_object(), request.user, request=request)
        return Response(ContractSerializer(contract).data)
