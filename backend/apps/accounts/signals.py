"""Keep a profile and a Django auth group aligned with every user save."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.groups import sync_role_group
from apps.accounts.models import Profile, User


@receiver(post_save, sender=User)
def ensure_profile_and_group(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
    sync_role_group(instance)
