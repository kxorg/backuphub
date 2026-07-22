from rest_framework import viewsets, status, mixins
from rest_framework.response import Response

from operations.models import BackupOperation
from api.authentication import ApiKeyAuthentication
from api.permissions import HasValidApiKey, IsOwnerSystem
from api.pagination import StandardPagination
from api.throttling import ApiKeyRateThrottle
from api.v1.backup_operations.serializers import (
    BackupOperationCreateSerializer,
    BackupOperationUpdateSerializer,
    BackupOperationReadSerializer,
)
from drf_spectacular.utils import extend_schema # Убедись, что это импортировано
from api.v1.backup_operations.filters import BackupOperationFilter
from api.v1.backup_operations.schemas import (
    backup_operation_create_schema,
    backup_operation_update_schema,
    backup_operation_list_schema,
)

class BackupOperationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    REST API for backup operations.

    Endpoints:
      POST   /api/v1/backup-operations/        — create operation
      GET    /api/v1/backup-operations/        — list operations
      GET    /api/v1/backup-operations/{id}/   — retrieve operation
      PATCH  /api/v1/backup-operations/{id}/   — update status
    """
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [HasValidApiKey, IsOwnerSystem]
    pagination_class = StandardPagination
    throttle_classes = [ApiKeyRateThrottle]
    filterset_class = BackupOperationFilter

    def get_queryset(self):
        qs = (
            BackupOperation.objects
            .select_related(
                'backup_configuration_version__backup_configuration__target_system_version__target_system',
                'backup_configuration_version__backup_tool',
            )
            .order_by('-started_at')
        )
        if getattr(self.request, 'auth', None):
            qs = qs.filter(
                backup_configuration_version__backup_configuration__target_system_version__target_system=self.request.auth
            )
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return BackupOperationCreateSerializer
        if self.action in ('partial_update', 'update'):
            return BackupOperationUpdateSerializer
        return BackupOperationReadSerializer

    # ---------- CREATE ----------
    @backup_operation_create_schema
    def create(self, request, *args, **kwargs):
        """
        Creates a new backup operation.
        Verifies that the API key's target system matches the configuration's target system.
        Returns the full created object (not just the id) for consistency.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_system = request.auth
        config = serializer.validated_data['backup_configuration_id']
        config_system = config.target_system_version.target_system

        if target_system.pk != config_system.pk:
            return Response(
                {
                    'error': {
                        'code': 'forbidden',
                        'message': 'API key does not match the configuration\'s target system.',
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        operation = serializer.save()

        # Return full object for consistency with other endpoints
        read_serializer = BackupOperationReadSerializer(operation)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    # ---------- PARTIAL UPDATE ----------
    @backup_operation_update_schema
    def partial_update(self, request, *args, **kwargs):
        """
        Updates operation status and result metadata.
        IsOwnerSystem checks ownership automatically via get_object().
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()

        read_serializer = BackupOperationReadSerializer(updated)
        return Response(read_serializer.data, status=status.HTTP_200_OK)

    # ---------- LIST ----------
    @backup_operation_list_schema
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # ---------- RETRIEVE ----------
    @extend_schema(tags=['Backup Operations API'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)