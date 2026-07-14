from rest_framework.permissions import BasePermission


class HasValidApiKey(BasePermission):
    """
    Ensures the request carries a valid API key.
    Required for all write operations (POST/PATCH/PUT/DELETE).
    Read operations are allowed without a key (can be tightened later).
    """
    write_methods = ('POST', 'PUT', 'PATCH', 'DELETE')

    def has_permission(self, request, view):
        if request.method in self.write_methods:
            return hasattr(request, 'auth') and request.auth is not None
        return True


class IsOwnerSystem(BasePermission):
    """
    Object-level permission: the API key must belong to the target system
    that owns the resource being accessed.
    Works only after HasValidApiKey has passed.
    """
    message = 'API key does not match the target system of this resource.'

    def has_object_permission(self, request, view, obj):
        if request.auth is None:
            return False

        target_system = self._get_target_system(obj)
        if target_system is None:
            return False

        return request.auth.pk == target_system.pk

    @staticmethod
    def _get_target_system(obj):
        """
        Extracts TargetSystem from the object via the relation chain.
        Returns None if the chain is broken (defensive).
        """
        try:
            return (
                obj.backup_configuration_version
                   .backup_configuration
                   .target_system_version
                   .target_system
            )
        except AttributeError:
            return None