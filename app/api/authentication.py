from rest_framework import authentication, exceptions

from systems.models import TargetSystem


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication via X-API-Key header.
    Returns (None, TargetSystem) — TargetSystem is used as the "auth" object
    so permissions and throttling can access it via request.auth.
    """
    header = 'HTTP_X_API_KEY'

    def authenticate(self, request):
        api_key = request.META.get(self.header)
        if not api_key:
            return None

        try:
            system = TargetSystem.objects.get(api_key=api_key, is_active=True)
        except TargetSystem.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid or inactive API key.')

        return (None, system)

    def authenticate_header(self, request):
        """
        Returns the challenge string used in WWW-Authenticate header
        on 401 responses. Without this, DRF returns 403 instead of 401.
        """
        return 'X-API-Key'