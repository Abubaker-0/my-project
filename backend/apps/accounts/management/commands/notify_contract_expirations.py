"""Idempotent contract-expiration notices. Schedule this command daily.

Repeated runs use a dedupe key, so the same window does not create a second notice.
This command does not send email or SMS.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Contract
from apps.common.choices import ContractStatus
from apps.common.notifications import notify


class Command(BaseCommand):
    help = 'Create in-app alerts for contracts that end in 30 days, 7 days, or today.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        created = 0
        for window in (30, 7, 0):
            target = today + timedelta(days=window)
            contracts = Contract.objects.filter(status=ContractStatus.ACTIVE, end_date=target).select_related('user', 'center')
            for contract in contracts:
                key = f'contract-expiry:{contract.id}:{contract.end_date.isoformat()}:{window}'
                label = 'today' if window == 0 else f'in {window} days'
                notice = notify(
                    contract.user,
                    'contract',
                    'Contract ending',
                    f'Your contract at {contract.center.code} ends {label} ({contract.end_date.isoformat()}).',
                    dedupe_key=key,
                )
                if notice and notice.created_at.date() == today:
                    created += 1
                manager = contract.center.get_active_manager()
                if manager and manager.id != contract.user_id:
                    notify(
                        manager,
                        'contract',
                        'Staff contract ending',
                        f'{contract.user.username} at {contract.center.code} ends {label}.',
                        dedupe_key=f'{key}:manager',
                    )
        self.stdout.write(self.style.SUCCESS(f'Contract alerts checked. New notices touched today: {created}.'))
