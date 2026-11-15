"""App config for centers. Creates default settings for every new center."""

from django.apps import AppConfig


class CentersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.centers'
    label = 'centers'
    verbose_name = 'Centers'

    def ready(self):
        from . import signals  # noqa: F401
