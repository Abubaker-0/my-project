"""Routes under /api/profile/."""

from django.urls import path

from apps.accounts.profile_views import ProfilePhotoUploadView, ProfilePhotoView, ProfileView

urlpatterns = [
    path('', ProfileView.as_view(), name='profile'),
    path('photo/', ProfilePhotoUploadView.as_view(), name='profile-photo-upload'),
    path('photo/<int:user_id>/', ProfilePhotoView.as_view(), name='profile-photo'),
]
