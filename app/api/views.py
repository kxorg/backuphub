from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.models import TargetSystem, BackupOperation
from .authentication import ApiKeyAuthentication
from .serializers import (
    BackupOperationCreateSerializer,
    BackupOperationUpdateSerializer,
    BackupOperationReadSerializer,
)


class HasValidApiKey(BasePermission):
    """Проверяет, что запрос прошёл аутентификацию по API-ключу."""
    
    def has_permission(self, request, view):
        # Для POST нужна аутентификация
        if request.method == 'POST':
            return hasattr(request, 'auth') and request.auth is not None
        # Для GET/PATCH — разрешаем (или добавь свою логику)
        return True


class BackupOperationViewSet(viewsets.GenericViewSet,
                             viewsets.mixins.CreateModelMixin,
                             viewsets.mixins.ListModelMixin,
                             viewsets.mixins.RetrieveModelMixin):
    """REST API для работы с операциями резервного копирования."""
    queryset = BackupOperation.objects.select_related(
        'backup_configuration_version__backup_configuration'
    ).all()
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    
    # 🔐 Кастомная аутентификация
    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [HasValidApiKey]

    def get_serializer_class(self):
        if self.action == 'create':
            return BackupOperationCreateSerializer
        if self.action == 'partial_update':
            return BackupOperationUpdateSerializer
        return BackupOperationReadSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        api_status = self.request.query_params.get('status')
        if api_status:
            status_map = {
                'RUNNING': 'in_progress',
                'SUCCESS': 'success',
                'FAILED': 'error',
            }
            if api_status in status_map:
                qs = qs.filter(status=status_map[api_status])

        config_id = self.request.query_params.get('backupConfigurationId')
        if config_id:
            qs = qs.filter(
                backup_configuration_version__backup_configuration_id=config_id
            )

        return qs.order_by('-started_at')

    # ==================== POST ====================
    @swagger_auto_schema(
        operation_summary='Create backup operation',
        operation_description=(
            'Creates a new backup operation record. '
            'API key must be provided in X-API-Key header. '
            'Automatically finds the current version of the backup configuration.'
        ),
        manual_parameters=[
            openapi.Parameter(
                'X-API-Key',
                openapi.IN_HEADER,
                description='API key of the target system (UUID)',
                type=openapi.TYPE_STRING,
                format='uuid',
                required=True,
            ),
        ],
        request_body=BackupOperationCreateSerializer,
        responses={
            201: openapi.Response(
                'Created',
                examples={'application/json': {'id': 1001}}
            ),
            400: 'Validation error',
            401: 'Invalid or missing API key',
        },
        tags=['Backup Operations'],
    )
    def create(self, request, *args, **kwargs):
        """POST /api/backup-operations/"""
        # 🔑 Получаем систему из request.auth (установлено в ApiKeyAuthentication)
        target_system = request.auth
        
        # Передаём target_system в контекст сериализатора
        serializer = self.get_serializer(
            data=request.data,
            context={'target_system': target_system}
        )
        serializer.is_valid(raise_exception=True)
        operation = serializer.save()
        return Response({'id': operation.id}, status=status.HTTP_201_CREATED)

    # ==================== PATCH ====================
    @swagger_auto_schema(
        operation_summary='Update backup operation',
        operation_description=(
            'Updates status and metadata of a backup operation. '
            'Allowed transitions: RUNNING → SUCCESS, RUNNING → FAILED. '
            'Completed operations cannot be modified.'
        ),
        request_body=BackupOperationUpdateSerializer,
        responses={
            200: BackupOperationReadSerializer,
            400: 'Validation error',
            404: 'Operation not found',
        },
        tags=['Backup Operations'],
    )
    def partial_update(self, request, *args, **kwargs):
        """PATCH /api/backup-operations/{id}/"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        return Response(
            BackupOperationReadSerializer(updated).data,
            status=status.HTTP_200_OK
        )

    # ==================== GET (list) ====================
    @swagger_auto_schema(
        operation_summary='List backup operations',
        operation_description='Returns history of backup operations with optional filters.',
        manual_parameters=[
            openapi.Parameter(
                'status', openapi.IN_QUERY,
                description='Filter by status: RUNNING, SUCCESS, FAILED',
                type=openapi.TYPE_STRING,
                enum=['RUNNING', 'SUCCESS', 'FAILED'],
            ),
            openapi.Parameter(
                'backupConfigurationId', openapi.IN_QUERY,
                description='Filter by backup configuration ID',
                type=openapi.TYPE_INTEGER,
            ),
        ],
        responses={200: BackupOperationReadSerializer(many=True)},
        tags=['Backup Operations'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # ==================== GET (detail) ====================
    @swagger_auto_schema(
        operation_summary='Get backup operation details',
        responses={200: BackupOperationReadSerializer, 404: 'Not found'},
        tags=['Backup Operations'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)