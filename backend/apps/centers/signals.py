"""Guarantee that a center always has a settings row."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.centers.models import Center, CenterSettings


@receiver(post_save, sender=Center)
def create_center_settings(sender, instance, created, **kwargs):
    if created:
        CenterSettings.objects.get_or_create(center=instance)
