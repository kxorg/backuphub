from rest_framework.decorators import api_view, permission_classes
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

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
        if request.method in ['POST', 'PATCH']:
            return hasattr(request, 'auth') and request.auth is not None
        return True


class BackupOperationViewSet(viewsets.GenericViewSet,
                             viewsets.mixins.CreateModelMixin,
                             viewsets.mixins.ListModelMixin,
                             viewsets.mixins.RetrieveModelMixin):
    """REST API для работы с операциями резервного копирования."""
    queryset = BackupOperation.objects.select_related(
        'backup_configuration_version__backup_configuration__target_system_version__target_system'
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

    def _get_operation_system(self, operation):
        """Получает TargetSystem из BackupOperation через цепочку связей."""
        return (
            operation.backup_configuration_version
            .backup_configuration
            .target_system_version
            .target_system
        )

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
        # Передаём target_system в контекст сериализатора
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        operation = serializer.save()
        return Response({'id': operation.id}, status=status.HTTP_201_CREATED)

    # ==================== PATCH ====================
    @swagger_auto_schema(
        operation_summary='Update backup operation',
        operation_description=(
            'Updates status and metadata of a backup operation. '
            'Requires X-API-Key header. The API key must belong to the same target system '
            'that the operation is associated with. '
            'Allowed transitions: RUNNING → SUCCESS, RUNNING → FAILED. '
            'Completed operations cannot be modified.'
        ),
        manual_parameters=[
            openapi.Parameter(
                'X-API-Key',
                openapi.IN_HEADER,
                description='API key of the target system (must match the operation\'s system)',
                type=openapi.TYPE_STRING,
                format='uuid',
                required=True,
            ),
        ],
        request_body=BackupOperationUpdateSerializer,
        responses={
            200: BackupOperationReadSerializer,
            400: 'Validation error (invalid transition or completed operation)',
            401: 'Invalid or missing API key',
            403: 'API key does not match the operation\'s target system',
            404: 'Operation not found',
        },
        tags=['Backup Operations'],
    )
    def partial_update(self, request, *args, **kwargs):
        """PATCH /api/backup-operations/{id}/"""
        instance = self.get_object()
        
        # 🔐 Получаем систему из API-ключа (установлено в ApiKeyAuthentication)
        target_system = request.auth
        
        # 🔐 Получаем систему, к которой привязана операция
        operation_system = self._get_operation_system(instance)
        
        # 🔐 Проверяем, что API-ключ соответствует системе операции
        if target_system != operation_system:
            return Response(
                {'error': 'API key does not match the operation\'s target system.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        
        if updated.status in ['success', 'error'] and not updated.finished_at:
            updated.finished_at = timezone.now()
            updated.save()

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

# ==========================================
# UI REFRESH API 
# ==========================================

@login_required
def api_ui_refresh_dashboard(request):
    """API для живого обновления дашборда"""
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    
    # Статистика
    data = {
        'total_systems': TargetSystem.objects.filter(is_active=True).count(),
        'new_systems': TargetSystem.objects.filter(created_at__gte=last_24h).count(),
        'total_backups': BackupOperation.objects.count(),
        'total_hosts': BackupOperation.objects.values('hostname').distinct().count(),
        'success_24h': BackupOperation.objects.filter(started_at__gte=last_24h, status='success').count(),
        'in_progress_24h': BackupOperation.objects.filter(started_at__gte=last_24h, status='in_progress').count(),
        'error_24h': BackupOperation.objects.filter(started_at__gte=last_24h, status='error').count(),
    }
    
    # Последние операции
    recent_backups = BackupOperation.objects.select_related(
        'backup_configuration_version__backup_configuration__target_system_version__target_system'
    ).order_by('-started_at')[:10]
    
    ops_data = []
    for op in recent_backups:
        sys_name = op.backup_configuration_version.backup_configuration.target_system_version.target_system.name
        ops_data.append({
            'id': op.id,
            'system_name': sys_name,
            'hostname': op.hostname,
            'status': op.status,
            'started_at': op.started_at.strftime('%d.%m.%Y %H:%M') if op.started_at else '-',
            'duration_seconds': op.duration_seconds, 
            'size_human': op.size_human or '-',
            'detail_url': f"/backup-operations/{op.id}/"
        })
        
    data['recent_operations'] = ops_data
    
    return JsonResponse(data)