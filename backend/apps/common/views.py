"""Public health check used by local setup and uptime probes."""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Unauthenticated liveness probe. It does not expose business data."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'status': 'ok', 'service': 'course-tuition-center-mis'})
