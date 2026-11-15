"""Accounts app config. Syncs Django groups after migrations."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    label = 'accounts'
    verbose_name = 'Accounts'

    def ready(self):
        from django.db.models.signals import post_migrate

        from . import signals  # noqa: F401
        from .groups import assign_role_permissions

        post_migrate.connect(assign_role_permissions, dispatch_uid='tuition-role-permissions')
