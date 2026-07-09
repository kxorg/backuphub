from rest_framework import authentication, exceptions
from core.models import TargetSystem


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication using X-API-Key header.
    """
    
    def authenticate(self, request):
        # Получаем API-ключ из заголовка
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            # Если ключа нет — возвращаем None (DRF попробует другие методы)
            return None
        
        try:
            # Ищем систему по API-ключу
            system = TargetSystem.objects.get(api_key=api_key, is_active=True)
        except TargetSystem.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API key.')
        
        # Возвращаем (user, auth) — но у нас нет пользователя,
        # поэтому возвращаем саму систему как "пользователя"
        return (None, system)