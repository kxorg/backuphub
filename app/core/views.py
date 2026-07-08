from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Count, Q

from .models import (
    SystemType,
    Environment,
    BackupTool,
    TargetSystem,
    TargetSystemVersion,
    BackupConfiguration,
    BackupConfigurationVersion,
    BackupOperation,
)
from .serializers import (
    SystemTypeSerializer,
    EnvironmentSerializer,
    BackupToolSerializer,
    TargetSystemSerializer,
    TargetSystemCreateSerializer,
    TargetSystemVersionSerializer,
    BackupConfigurationSerializer,
    BackupConfigurationCreateSerializer,
    BackupConfigurationVersionSerializer,
    BackupOperationSerializer,
    BackupOperationCreateSerializer,
    BackupOperationUpdateSerializer,
)


# ==========================================
# WEB VIEWS
# ==========================================

@login_required
def index(request):
    """Dashboard with KPIs and recent operations."""
    from datetime import timedelta
    
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    
    # === KPI: general counters ===
    total_systems = TargetSystem.objects.filter(is_active=True).count()
    total_operations = BackupOperation.objects.count()
    total_configurations = BackupConfiguration.objects.filter(is_active=True).count()
    new_systems = TargetSystem.objects.filter(created_at__gte=last_7d).count()
    
    # === KPI: operation status for the last 24 hours ===
    operations_24h = BackupOperation.objects.filter(started_at__gte=last_24h)
    success_24h = operations_24h.filter(status='success').count()
    error_24h = operations_24h.filter(status='error').count()
    in_progress_24h = operations_24h.filter(status='in_progress').count()
    
    # === Last 5 backup operations ===
    recent_operations = BackupOperation.objects.select_related(
        'backup_configuration_version__backup_configuration__target_system_version__target_system',
        'backup_configuration_version__backup_tool'
    ).order_by('-started_at')[:5]
    
    # === Active systems with last operation status ===
    systems = TargetSystem.objects.select_related(
        'system_type', 'environment'
    ).filter(is_active=True).all()
    
    systems_data = []
    for system in systems:
        # Get last operation for this system
        last_operation = BackupOperation.objects.filter(
            backup_configuration_version__backup_configuration__target_system_version__target_system=system
        ).select_related(
            'backup_configuration_version__backup_configuration',
            'backup_configuration_version__backup_tool'
        ).order_by('-started_at').first()
        
        if last_operation is None:
            system_status = 'no_data'
            system_status_label = 'no_data'
            system_status_class = 'secondary'
        elif last_operation.status == 'error':
            system_status = 'error'
            system_status_label = 'error'
            system_status_class = 'danger'
        elif last_operation.status == 'in_progress':
            system_status = 'in_progress'
            system_status_label = 'in_progress'
            system_status_class = 'warning'
        elif last_operation.started_at < last_24h:
            system_status = 'warning'
            system_status_label = 'warning'
            system_status_class = 'warning'
        else:
            system_status = 'active'
            system_status_label = 'success'
            system_status_class = 'success'
        
        systems_data.append({
            'system': system,
            'last_operation': last_operation,
            'status': system_status,
            'status_label': system_status_label,
            'status_class': system_status_class,
        })
    
    context = {
        # KPI
        'total_systems': total_systems,
        'total_operations': total_operations,
        'total_configurations': total_configurations,
        'new_systems': new_systems,
        # Operation status for the last 24 hours
        'success_24h': success_24h,
        'error_24h': error_24h,
        'in_progress_24h': in_progress_24h,
        # Data for tables
        'recent_operations': recent_operations,
        'systems_data': systems_data,
    }
    return render(request, "index.html", context)


@login_required
def api(request):
    return render(request, "api.html")


# --- Backup Operations ---
@login_required
def operations_list(request):
    """List all backup operations."""
    operations_list = BackupOperation.objects.select_related(
        'backup_configuration_version__backup_configuration__target_system_version__target_system',
        'backup_configuration_version__backup_tool'
    ).order_by('-started_at')
    
    paginator = Paginator(operations_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "backup_operation/list.html", {"page_obj": page_obj})


@login_required
def operation_detail(request, pk):
    """Backup operation details."""
    operation = get_object_or_404(
        BackupOperation.objects.select_related(
            'backup_configuration_version__backup_configuration__target_system_version__target_system',
            'backup_configuration_version__backup_tool'
        ),
        id=pk
    )
    return render(request, "backup_operation/detail.html", {"operation": operation})


# --- TargetSystem CRUD ---
@login_required
def system_settings(request):
    """List all target systems."""
    systems_list = TargetSystem.objects.select_related(
        'system_type', 'environment'
    ).all().order_by('-created_at')
    
    paginator = Paginator(systems_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "target_system/list.html", {"page_obj": page_obj})


@login_required
def system_detail(request, pk):
    """Target system details with versions and operations."""
    system = get_object_or_404(
        TargetSystem.objects.select_related('system_type', 'environment'),
        id=pk
    )
    
    # Get system versions
    versions = TargetSystemVersion.objects.filter(
        target_system=system
    ).order_by('-version_number')
    
    # Get configurations for this system
    configurations = BackupConfiguration.objects.filter(
        target_system_version__target_system=system
    ).select_related('target_system_version').all()
    
    # Get recent operations
    recent_operations = BackupOperation.objects.filter(
        backup_configuration_version__backup_configuration__target_system_version__target_system=system
    ).select_related(
        'backup_configuration_version__backup_configuration',
        'backup_configuration_version__backup_tool'
    ).order_by('-started_at')[:10]
    
    return render(request, "target_system/detail.html", {
        "system": system,
        "versions": versions,
        "configurations": configurations,
        "recent_operations": recent_operations,
    })


@login_required
def system_create(request):
    """Create new target system."""
    if request.method == "POST":
        name = request.POST.get('name')
        system_type_id = request.POST.get('system_type')
        environment_id = request.POST.get('environment')
        description = request.POST.get('description', '')
        owner = request.POST.get('owner', '')
        administrator = request.POST.get('administrator', '')
        
        system_type = get_object_or_404(SystemType, id=system_type_id)
        environment = get_object_or_404(Environment, id=environment_id)
        
        system = TargetSystem.objects.create(
            name=name,
            system_type=system_type,
            environment=environment,
            description=description,
            owner=owner,
            administrator=administrator,
            created_by=request.user.username
        )
        
        # Create first version
        TargetSystemVersion.objects.create(
            target_system=system,
            version_number=1,
            owner=owner,
            administrator=administrator,
            is_current=True,
            valid_from=timezone.now(),
            created_by=request.user.username
        )
        
        return render(request, "target_system/create_result.html", {
            "system": system,
            "api_key": system.api_key
        })
    
    system_types = SystemType.objects.all()
    environments = Environment.objects.all()
    
    return render(request, "target_system/form.html", {
        "system_types": system_types,
        "environments": environments,
    })


@login_required
def system_edit(request, pk):
    """Edit target system."""
    system = get_object_or_404(TargetSystem, id=pk)
    
    if request.method == "POST":
        system.name = request.POST.get('name')
        system.description = request.POST.get('description', '')
        system.owner = request.POST.get('owner', '')
        system.administrator = request.POST.get('administrator', '')
        system.is_active = request.POST.get('is_active') == 'on'
        system.updated_by = request.user.username
        
        # Check if owner or administrator changed
        current_version = system.current_version
        owner_changed = system.owner != current_version.owner if current_version else True
        admin_changed = system.administrator != current_version.administrator if current_version else True
        
        if owner_changed or admin_changed:
            # Close current version
            if current_version:
                current_version.valid_to = timezone.now()
                current_version.is_current = False
                current_version.save()
            
            # Create new version
            new_version_number = (current_version.version_number + 1) if current_version else 1
            TargetSystemVersion.objects.create(
                target_system=system,
                version_number=new_version_number,
                owner=system.owner,
                administrator=system.administrator,
                is_current=True,
                valid_from=timezone.now(),
                created_by=request.user.username
            )
        
        system.save()
        return redirect('target_system_detail', pk=system.id)
    
    system_types = SystemType.objects.all()
    environments = Environment.objects.all()
    
    return render(request, "target_system/form.html", {
        "system": system,
        "system_types": system_types,
        "environments": environments,
    })


@login_required
def system_delete(request, pk):
    """Delete target system."""
    system = get_object_or_404(TargetSystem, id=pk)
    
    if request.method == "POST":
        system.delete()
        return redirect('target_system_list')
    
    return render(request, "target_system/confirm_delete.html", {"system": system})


# --- Backup Configuration CRUD ---
@login_required
def configuration_list(request):
    """List all backup configurations."""
    configurations_list = BackupConfiguration.objects.select_related(
        'target_system_version__target_system'
    ).all().order_by('-created_at')
    
    paginator = Paginator(configurations_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "backup_configuration/list.html", {"page_obj": page_obj})


@login_required
def configuration_detail(request, pk):
    """Backup configuration details with versions."""
    configuration = get_object_or_404(
        BackupConfiguration.objects.select_related(
            'target_system_version__target_system'
        ),
        id=pk
    )
    
    versions = BackupConfigurationVersion.objects.filter(
        backup_configuration=configuration
    ).select_related('backup_tool').order_by('-version_number')
    
    return render(request, "backup_configuration/detail.html", {
        "configuration": configuration,
        "versions": versions,
    })


@login_required
def configuration_create(request):
    """Create new backup configuration."""
    if request.method == "POST":
        name = request.POST.get('name')
        target_system_version_id = request.POST.get('target_system_version')
        description = request.POST.get('description', '')
        
        # Version fields
        backup_tool_id = request.POST.get('backup_tool')
        backup_mode = request.POST.get('backup_mode', 'full')
        schedule_cron = request.POST.get('schedule_cron', '')
        retention_days = int(request.POST.get('retention_days', 30))
        rpo_minutes = int(request.POST.get('rpo_minutes', 1440))
        rto_minutes = int(request.POST.get('rto_minutes', 60))
        storage_type = request.POST.get('storage_type', 'local')
        storage_path = request.POST.get('storage_path', '')
        verify_after_backup = request.POST.get('verify_after_backup') == 'on'
        immutable_storage = request.POST.get('immutable_storage') == 'on'
        
        target_system_version = get_object_or_404(
            TargetSystemVersion.objects.select_related('target_system'),
            id=target_system_version_id
        )
        backup_tool = get_object_or_404(BackupTool, id=backup_tool_id)
        
        # Create configuration
        configuration = BackupConfiguration.objects.create(
            name=name,
            target_system_version=target_system_version,
            description=description,
            is_active=True,
            created_by=request.user.username
        )
        
        # Create first version
        BackupConfigurationVersion.objects.create(
            backup_configuration=configuration,
            backup_tool=backup_tool,
            version_number=1,
            backup_mode=backup_mode,
            schedule_cron=schedule_cron,
            retention_days=retention_days,
            rpo_minutes=rpo_minutes,
            rto_minutes=rto_minutes,
            storage_type=storage_type,
            storage_path=storage_path,
            verify_after_backup=verify_after_backup,
            immutable_storage=immutable_storage,
            is_current=True,
            valid_from=timezone.now(),
            created_by=request.user.username
        )
        
        return redirect('configuration_detail', pk=configuration.id)
    
    # Get all current system versions
    system_versions = TargetSystemVersion.objects.filter(
        is_current=True
    ).select_related('target_system__system_type', 'target_system__environment').all()
    
    backup_tools = BackupTool.objects.filter(is_active=True).all()
    
    return render(request, "backup_configuration/form.html", {
        "system_versions": system_versions,
        "backup_tools": backup_tools,
    })


@login_required
def configuration_edit(request, pk):
    """Edit backup configuration (creates new version)."""
    configuration = get_object_or_404(BackupConfiguration, id=pk)
    
    if request.method == "POST":
        configuration.name = request.POST.get('name')
        configuration.description = request.POST.get('description', '')
        configuration.is_active = request.POST.get('is_active') == 'on'
        configuration.updated_by = request.user.username
        
        # Version fields
        backup_tool_id = request.POST.get('backup_tool')
        backup_mode = request.POST.get('backup_mode', 'full')
        schedule_cron = request.POST.get('schedule_cron', '')
        retention_days = int(request.POST.get('retention_days', 30))
        rpo_minutes = int(request.POST.get('rpo_minutes', 1440))
        rto_minutes = int(request.POST.get('rto_minutes', 60))
        storage_type = request.POST.get('storage_type', 'local')
        storage_path = request.POST.get('storage_path', '')
        verify_after_backup = request.POST.get('verify_after_backup') == 'on'
        immutable_storage = request.POST.get('immutable_storage') == 'on'
        
        backup_tool = get_object_or_404(BackupTool, id=backup_tool_id)
        
        # Get current version
        current_version = configuration.current_version
        
        # Close current version
        if current_version:
            current_version.valid_to = timezone.now()
            current_version.is_current = False
            current_version.save()
        
        # Create new version
        new_version_number = (current_version.version_number + 1) if current_version else 1
        BackupConfigurationVersion.objects.create(
            backup_configuration=configuration,
            backup_tool=backup_tool,
            version_number=new_version_number,
            backup_mode=backup_mode,
            schedule_cron=schedule_cron,
            retention_days=retention_days,
            rpo_minutes=rpo_minutes,
            rto_minutes=rto_minutes,
            storage_type=storage_type,
            storage_path=storage_path,
            verify_after_backup=verify_after_backup,
            immutable_storage=immutable_storage,
            is_current=True,
            valid_from=timezone.now(),
            created_by=request.user.username
        )
        
        configuration.save()
        return redirect('configuration_detail', pk=configuration.id)
    
    current_version = configuration.current_version
    system_versions = TargetSystemVersion.objects.filter(
        is_current=True
    ).select_related('target_system__system_type', 'target_system__environment').all()
    backup_tools = BackupTool.objects.filter(is_active=True).all()
    
    return render(request, "backup_configuration/form.html", {
        "configuration": configuration,
        "current_version": current_version,
        "system_versions": system_versions,
        "backup_tools": backup_tools,
    })


@login_required
def configuration_delete(request, pk):
    """Delete backup configuration."""
    configuration = get_object_or_404(BackupConfiguration, id=pk)
    
    if request.method == "POST":
        configuration.delete()
        return redirect('configuration_list')
    
    return render(request, "backup_configuration/confirm_delete.html", {"configuration": configuration})


# ==========================================
# API VIEWS
# ==========================================

class SystemTypeViewSet(ModelViewSet):
    """API for SystemType CRUD."""
    queryset = SystemType.objects.all()
    serializer_class = SystemTypeSerializer
    permission_classes = [IsAuthenticated]


class EnvironmentViewSet(ModelViewSet):
    """API for Environment CRUD."""
    queryset = Environment.objects.all()
    serializer_class = EnvironmentSerializer
    permission_classes = [IsAuthenticated]


class BackupToolViewSet(ModelViewSet):
    """API for BackupTool CRUD."""
    queryset = BackupTool.objects.all()
    serializer_class = BackupToolSerializer
    permission_classes = [IsAuthenticated]


class TargetSystemViewSet(ModelViewSet):
    """API for TargetSystem CRUD."""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TargetSystemCreateSerializer
        return TargetSystemSerializer
    
    def get_queryset(self):
        return TargetSystem.objects.select_related(
            'system_type', 'environment'
        ).all()


class BackupConfigurationViewSet(ModelViewSet):
    """API for BackupConfiguration CRUD."""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BackupConfigurationCreateSerializer
        return BackupConfigurationSerializer
    
    def get_queryset(self):
        return BackupConfiguration.objects.select_related(
            'target_system_version__target_system'
        ).all()


class BackupOperationViewSet(
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    GenericViewSet
):
    """
    Backup Operation API operations.
    Used by backup scripts to register and update operations.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = BackupOperationSerializer
    
    def get_queryset(self):
        return BackupOperation.objects.select_related(
            'backup_configuration_version__backup_configuration__target_system_version__target_system',
            'backup_configuration_version__backup_tool'
        ).all()
    
    def get_client_ip(self, request):
        """Detect client IP from HTTP request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @swagger_auto_schema(
        operation_summary='List all backup operations',
        operation_description='Returns a list of all backup operations',
        tags=['Backup Operations'],
        responses={200: openapi.Response('List of operations', BackupOperationSerializer(many=True))},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_summary='Retrieve operation details',
        operation_description='Returns details of a specific backup operation',
        tags=['Backup Operations'],
        responses={200: openapi.Response('Operation details', BackupOperationSerializer), 404: 'Operation not found'},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['backup_configuration_version_id', 'hostname'],
            properties={
                'backup_configuration_version_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of the backup configuration version'
                ),
                'external_job_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='External job ID (e.g., Kubernetes CronJob ID)'
                ),
                'hostname': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Hostname of the server'
                ),
                'ip_address': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='ipv4',
                    description='IP address (auto-detected if not provided)'
                ),
                'storage_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Storage type (local, s3, azure, etc.)'
                ),
                'storage_path': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Path to backup file'
                ),
            }
        ),
        responses={
            201: openapi.Response('Operation created', BackupOperationSerializer),
            400: 'Validation error',
            404: 'Configuration version not found',
        },
        operation_summary='Create backup operation',
        operation_description=(
            'Creates a new backup operation with status in_progress. '
            'Used by backup scripts to register the start of a backup.'
        ),
        tags=['Backup Operations'],
    )
    def create(self, request, *args, **kwargs):
        """Create a new backup operation."""
        serializer = BackupOperationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        config_version_id = serializer.validated_data['backup_configuration_version_id']
        hostname = serializer.validated_data['hostname']
        external_job_id = serializer.validated_data.get('external_job_id', '')
        storage_type = serializer.validated_data.get('storage_type', '')
        storage_path = serializer.validated_data.get('storage_path', '')
        
        # Auto-detect IP if not provided
        ip_address = serializer.validated_data.get('ip_address')
        if not ip_address:
            ip_address = self.get_client_ip(request)
        
        # Get configuration version
        config_version = BackupConfigurationVersion.objects.get(id=config_version_id)
        
        # Create operation
        operation = BackupOperation.objects.create(
            backup_configuration_version=config_version,
            external_job_id=external_job_id,
            hostname=hostname,
            ip_address=ip_address,
            status='in_progress',
            started_at=timezone.now(),
            storage_type=storage_type,
            storage_path=storage_path,
            created_by='api'
        )
        
        response_serializer = BackupOperationSerializer(operation)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['in_progress', 'success', 'error', 'warning', 'cancelled'],
                    description='Backup execution status'
                ),
                'finished_at': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='date-time',
                    description='Finish time (auto-set if status is success/error)'
                ),
                'size_bytes': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Backup size in bytes'
                ),
                'storage_path': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Path to backup file'
                ),
                'metadata': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description='Technical data in JSON format'
                ),
                'error_message': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Error message (if status is error)'
                ),
            }
        ),
        responses={
            200: openapi.Response('Operation updated', BackupOperationSerializer),
            404: 'Operation not found',
        },
        operation_summary='Update backup operation status',
        operation_description=(
            'Updates backup operation status and metadata after completion. '
            'finished_at is set automatically when status is success or error.'
        ),
        tags=['Backup Operations'],
    )
    def partial_update(self, request, *args, **kwargs):
        """PATCH /backup-operations/{id}/ - Update operation status."""
        operation = self.get_object()
        
        serializer = BackupOperationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        for attr, value in serializer.validated_data.items():
            if value is not None:
                setattr(operation, attr, value)
        
        # Auto-set finished_at if status is success or error
        if operation.status in ['success', 'error'] and not operation.finished_at:
            operation.finished_at = timezone.now()
        
        operation.save()
        
        response_serializer = BackupOperationSerializer(operation)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['patch'], url_path='update_latest')
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['backup_configuration_version_id', 'hostname'],
            properties={
                'backup_configuration_version_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='ID of the backup configuration version'
                ),
                'hostname': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Hostname of the server'
                ),
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['in_progress', 'success', 'error', 'warning', 'cancelled'],
                    description='Backup execution status'
                ),
                'finished_at': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='date-time',
                    description='Finish time'
                ),
                'size_bytes': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Backup size in bytes'
                ),
                'storage_path': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Path to backup file'
                ),
                'metadata': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description='Technical data in JSON format'
                ),
                'error_message': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Error message'
                ),
            }
        ),
        responses={
            200: openapi.Response('Operation updated', BackupOperationSerializer),
            400: 'Validation error',
            404: 'No in-progress operation found',
        },
        operation_summary='Update latest in-progress operation',
        operation_description=(
            'Finds the latest in-progress operation for the specified '
            'configuration version + hostname and updates it. '
            'Useful when the client script does not store the operation ID.'
        ),
        tags=['Backup Operations'],
    )
    def update_latest(self, request, *args, **kwargs):
        """PATCH /backup-operations/update_latest/ - Update latest in-progress operation."""
        config_version_id = request.data.get('backup_configuration_version_id')
        hostname = request.data.get('hostname')
        
        if not config_version_id or not hostname:
            return Response(
                {'error': 'backup_configuration_version_id and hostname are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find latest in-progress operation
        operation = BackupOperation.objects.filter(
            backup_configuration_version_id=config_version_id,
            hostname=hostname,
            status='in_progress'
        ).order_by('-started_at').first()
        
        if not operation:
            return Response(
                {'error': 'No in-progress operation found for this configuration and hostname'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update operation
        serializer = BackupOperationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        for attr, value in serializer.validated_data.items():
            if attr not in ['backup_configuration_version_id', 'hostname'] and value is not None:
                setattr(operation, attr, value)
        
        if operation.status in ['success', 'error'] and not operation.finished_at:
            operation.finished_at = timezone.now()
        
        operation.save()
        
        response_serializer = BackupOperationSerializer(operation)
        return Response(response_serializer.data, status=status.HTTP_200_OK)