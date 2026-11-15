"""Print integrity findings without changing data."""

from django.core.management.base import BaseCommand

from apps.reports.services import integrity_report


class Command(BaseCommand):
    help = 'Read-only integrity report. It does not repair or delete rows.'

    def handle(self, *args, **options):
        issues = integrity_report()
        if not issues:
            self.stdout.write(self.style.SUCCESS('No integrity issues found.'))
            return
        for issue in issues:
            self.stdout.write(str(issue))
        self.stdout.write(self.style.WARNING(f'{len(issues)} issue(s). No rows were changed.'))
