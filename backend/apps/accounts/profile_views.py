"""The signed-in person's profile and protected profile photos.

Photos are not served from public media URLs. The client downloads them with
the access token, and a user outside the center receives 403.
"""

import mimetypes

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.serializers import ProfileUpdateSerializer, UserSerializer
from apps.accounts.services import set_profile_photo, update_own_profile
from apps.common.choices import Role


class ProfileView(APIView):
    """Read and update the signed-in profile. Role and center cannot be changed here."""

    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        return Response(UserSerializer(request.user, context={'request': request}).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update_own_profile(request.user, serializer.validated_data)
        if request.FILES.get('photo'):
            set_profile_photo(request.user, request.FILES['photo'])
        request.user.refresh_from_db()
        return Response(UserSerializer(request.user, context={'request': request}).data)


class ProfilePhotoUploadView(APIView):
    """Upload a new profile photo without sending the rest of the profile."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get('photo')
        if upload is None:
            raise NotFound('Choose a photo to upload.')
        set_profile_photo(request.user, upload)
        return Response(UserSerializer(request.user, context={'request': request}).data)


class ProfilePhotoView(APIView):
    """Stream a profile photo to a user in the same center, the owner, or super admin."""

    def get(self, request, user_id):
        target = get_object_or_404(User.objects.select_related('profile', 'center'), pk=user_id)
        viewer = request.user
        allowed = viewer.id == target.id or viewer.role == Role.SUPER_ADMIN
        if viewer.role == Role.CENTER_MANAGER and viewer.center_id and viewer.center_id == target.center_id:
            allowed = True
        if not allowed:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You cannot view this photo.')
        from apps.accounts.models import Profile

        try:
            photo = target.profile.photo
        except Profile.DoesNotExist as exc:
            raise NotFound('No profile photo.') from exc
        if not photo:
            raise NotFound('No profile photo.')
        content_type = mimetypes.guess_type(photo.name)[0] or 'image/jpeg'
        response = FileResponse(photo.open('rb'), content_type=content_type)
        response['Cache-Control'] = 'private, max-age=300'
        return response
