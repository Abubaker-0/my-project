"""Login, refresh, logout, and password recovery.

Login accepts a username or an email. Logout blacklists the refresh token.
Password reset stores only a hash. The raw token is returned solely when
DEBUG is on, so a local demo can finish the flow without an email server.
"""

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.models import User
from apps.accounts.serializers import (
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserSerializer,
)
from apps.accounts.services import change_password, refresh_expired_contracts, request_password_reset, reset_password
from apps.common.exceptions import BusinessRuleError


class LoginThrottle(AnonRateThrottle):
    """Slow down repeated login attempts from the same address."""

    scope = 'login'


class LoginSerializer(TokenObtainPairSerializer):
    """Issue a JWT and the signed-in profile. Email is accepted as the login."""

    def validate(self, attrs):
        login = attrs.get(self.username_field, '')
        if login and '@' in str(login):
            found = User.objects.filter(email__iexact=login).only('username').first()
            if found:
                attrs[self.username_field] = found.get_username()
        data = super().validate(attrs)
        refresh_expired_contracts(self.user)
        data['user'] = UserSerializer(self.user, context=self.context).data
        return data


class LoginView(TokenObtainPairView):
    """Exchange a username or email and password for an access and refresh token."""

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]


class RefreshView(TokenRefreshView):
    """Rotate a refresh token. The previous refresh token is blacklisted."""

    permission_classes = [AllowAny]


class LogoutView(APIView):
    """Blacklist the presented refresh token."""

    def post(self, request):
        raw = request.data.get('refresh')
        if not raw:
            raise BusinessRuleError('Refresh token is required.')
        try:
            token = RefreshToken(raw)
            token.blacklist()
        except TokenError as exc:
            raise BusinessRuleError('Refresh token is invalid.') from exc
        return Response({'detail': 'Logged out.'})


class MeView(APIView):
    """Return the signed-in user. The client calls this when the app loads."""

    def get(self, request):
        refresh_expired_contracts(request.user)
        return Response(UserSerializer(request.user, context={'request': request}).data)


class ChangePasswordView(APIView):
    """Replace the signed-in user's password."""

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        change_password(request.user, serializer.validated_data['old_password'], serializer.validated_data['new_password'])
        return Response({'detail': 'Password updated.'})


class ForgotPasswordView(APIView):
    """Start a password reset. The response does not reveal whether the account exists."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = request_password_reset(serializer.validated_data['login'].strip())
        payload = {'detail': 'If the account exists, a reset token was issued.'}
        if settings.DEBUG and token:
            payload['debug_token'] = token
        return Response(payload)


class ResetPasswordView(APIView):
    """Set a new password with a reset token."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_password(serializer.validated_data['token'], serializer.validated_data['new_password'])
        return Response({'detail': 'Password updated. You can sign in now.'})
