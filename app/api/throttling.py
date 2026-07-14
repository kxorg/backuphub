from rest_framework.throttling import SimpleRateThrottle


class ApiKeyRateThrottle(SimpleRateThrottle):
    """
    Rate limit per API key.
    Configured in settings: REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['api_key']
    """
    scope = 'api_key'

    def get_cache_key(self, request, view):
        # request.auth is TargetSystem instance (see ApiKeyAuthentication)
        if request.auth is None:
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': getattr(request.auth, 'pk', 'anon'),
        }