"""Create the first super admin from environment variables.

The command is idempotent. Run it after migrate, then run seed_data for the
demo centers. Passwords come from the environment, never from source code.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.common.choices import Gender, Role


class Command(BaseCommand):
    help = 'Create the initial super admin account if it does not exist.'

    def handle(self, *args, **options):
        username = settings.SUPER_ADMIN_USERNAME
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Super admin "{username}" already exists.'))
            return
        gender = settings.SUPER_ADMIN_GENDER
        if gender not in Gender.values:
            raise SystemExit('SUPER_ADMIN_GENDER must be male or female.')
        User.objects.create_superuser(
            username=username,
            email=settings.SUPER_ADMIN_EMAIL,
            password=settings.SUPER_ADMIN_PASSWORD,
            first_name=settings.SUPER_ADMIN_FIRST_NAME,
            last_name=settings.SUPER_ADMIN_LAST_NAME,
            phone=settings.SUPER_ADMIN_PHONE,
            gender=gender,
            role=Role.SUPER_ADMIN,
        )
        self.stdout.write(self.style.SUCCESS(f'Super admin "{username}" created.'))
