from rest_framework.decorators import api_view, permission_classes
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# --- Новые импорты для UI Refresh API и Demo страницы ---
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
# --------------------------------------------------------

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

# ==========================================
# UI REFRESH API (Для веб-интерфейса)
# ==========================================

@api_view(['GET'])
# @permission_classes([IsAuthenticated]) # Защищено сессией Django, а не API-ключом
def api_ui_refresh_dashboard(request):
    """API для живого обновления Дашборда"""
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    
    data = {
        'total_systems': TargetSystem.objects.filter(is_active=True).count(),
        'new_systems': TargetSystem.objects.filter(created_at__gte=last_24h).count(),
        'total_backups': BackupOperation.objects.count(),
        'total_hosts': BackupOperation.objects.values('hostname').distinct().count(),
        'success_24h': BackupOperation.objects.filter(started_at__gte=last_24h, status='success').count(),
        'in_progress_24h': BackupOperation.objects.filter(started_at__gte=last_24h, status='in_progress').count(),
        'error_24h': BackupOperation.objects.filter(started_at__gte=last_24h, status='error').count(),
    }
    
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
            'size_human': op.size_human or '-',
        })
        
    data['recent_operations'] = ops_data
    return Response(data)


@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def api_ui_refresh_operations(request):
    """API для живого обновления Списка операций"""
    queryset = BackupOperation.objects.select_related(
        'backup_configuration_version__backup_configuration__target_system_version__target_system',
    ).order_by('-started_at')
    
    # Поддержка фильтров, если они переданы в URL
    search_query = request.GET.get('q', '').strip()
    if search_query:
        queryset = queryset.filter(
            Q(hostname__icontains=search_query) |
            Q(external_job_id__icontains=search_query) |
            Q(storage_path__icontains=search_query)
        )
    
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        queryset = queryset.filter(status=status_filter)
        
    ops_data = []
    for op in queryset[:50]: 
        sys_name = op.backup_configuration_version.backup_configuration.target_system_version.target_system.name
        ops_data.append({
            'id': op.id,
            'system_name': sys_name,
            'hostname': op.hostname,
            'status': op.status,
            'started_at': op.started_at.strftime('%d.%m.%Y %H:%M') if op.started_at else '-',
            'size_human': op.size_human or '-',
        })
        
    return Response({'operations': ops_data})


# ==========================================
# ДЕМО-СТРАНИЦА (Для показа руководителю)
# ==========================================

def demo_dashboard(request):
    """
    Изолированная демо-страница внутри /api/.
    Нужна только для того, чтобы показать руководителю работу AJAX 
    без вмешательства в шаблоны /core/, которые сейчас переделывает фронтендер.
    """
    return render(request, 'demo_dashboard.html')