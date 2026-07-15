from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timesince import timesince
from rest_framework.decorators import api_view
from django.db.models import Q
from django.core.paginator import Paginator

from systems.models import TargetSystem
from operations.models import BackupOperation
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

@extend_schema(
    tags=['Dashboard'],
    summary='Refresh Dashboard Data',
    description='Returns aggregated statistics for the last 24 hours and recent backup operations.',
    responses={
        200: OpenApiResponse(description='Dashboard statistics'),
        401: OpenApiResponse(description='Unauthorized'),
    },
)
@api_view(['GET'])
@login_required
def api_ui_refresh_dashboard(request):
    """API для живого обновления дашборда"""
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    
    data = {
        'total_systems': TargetSystem.objects.filter(is_active=True).count(),
        'new_systems': TargetSystem.objects.filter(created_at__gte=last_24h).count(),
        'total_backups': BackupOperation.objects.count(),
        'total_hosts': BackupOperation.objects.exclude(hostname='').values('hostname').distinct().count(),
        'success_24h': BackupOperation.objects.filter(started_at__gte=last_24h, status='success').count(),
        'in_progress_24h': BackupOperation.objects.filter(started_at__gte=last_24h, status='in_progress').count(),
        'error_24h': BackupOperation.objects.filter(started_at__gte=last_24h, status='error').count(),
    }
    
    recent_backups = BackupOperation.objects.select_related(
        'backup_configuration_version__backup_configuration__target_system_version__target_system'
    ).order_by('-started_at')[:10]
    
    ops_data = []
    for op in recent_backups:
        sys_name = 'Unknown'
        try:
            if (op.backup_configuration_version 
                and op.backup_configuration_version.backup_configuration
                and op.backup_configuration_version.backup_configuration.target_system_version
                and op.backup_configuration_version.backup_configuration.target_system_version.target_system):
                sys_name = op.backup_configuration_version.backup_configuration.target_system_version.target_system.name
        except AttributeError:
            sys_name = 'Unknown'
        
        time_display = '—'
        if op.started_at:
            try:
                time_display = f"{timesince(op.started_at, now=now)} ago"
            except (ValueError, TypeError):
                time_display = op.started_at.strftime('%d.%m.%Y %H:%M')
        
        ops_data.append({
            'id': op.id,
            'system_name': sys_name,
            'hostname': op.hostname or '',
            'status': op.status,
            'started_at': time_display,  
            'size_human': op.size_human or '—',
            'detail_url': f"/backup-operations/{op.id}/",
        })
        
    data['recent_operations'] = ops_data
    
    return JsonResponse(data)

@extend_schema(
    tags=['Operations'],
    summary='Refresh Operations List (Live Update)',
    description='Returns a filtered and paginated list of operations for dynamic updates',
)
@api_view(['GET'])
@login_required
def api_ui_refresh_operations(request):
    """API для живого обновления списка Backup Operations"""
    
    queryset = BackupOperation.objects.select_related(
        'backup_configuration_version__backup_configuration',
    ).order_by('-started_at')

    search_query = request.GET.get('q', '').strip()
    if search_query:
        queryset = queryset.filter(
            Q(hostname__icontains=search_query) |
            Q(external_job_id__icontains=search_query) |
            Q(storage_path__icontains=search_query)
        )

    status = request.GET.get('status', '').strip()
    if status:
        queryset = queryset.filter(status=status)

    hostname = request.GET.get('hostname', '').strip()
    if hostname:
        queryset = queryset.filter(hostname__icontains=hostname)

    config_id = request.GET.get('configuration', '').strip()
    if config_id and config_id.isdigit():
        queryset = queryset.filter(
            backup_configuration_version__backup_configuration_id=int(config_id)
        )

    try:
        page_number = int(request.GET.get('page', 1))
    except ValueError:
        page_number = 1

    paginator = Paginator(queryset, 50)

    try:
        page_obj = paginator.page(page_number)
    except:
        page_obj = paginator.page(1)

    operations_data = []
    for op in page_obj:
        config = op.backup_configuration_version.backup_configuration
        operations_data.append({
            'id': op.id,
            'hostname': op.hostname or '',
            'configuration_name': config.name if config else '—',
            'configuration_id': config.id if config else None,
            'version_number': op.backup_configuration_version.version_number,
            'status': op.status,
            'started_at': op.started_at.strftime('%d.%m.%Y %H:%M') if op.started_at else '—',
            'duration_seconds': op.duration_seconds,
            'size_human': getattr(op, 'size_human', None) or '—',
            'detail_url': f"/backup-operations/{op.id}/",
            'config_detail_url': f"/backup-configurations/{config.id}/" if config else '#',
        })

    return JsonResponse({
        'operations': operations_data,
        'page_obj': {
            'number': page_obj.number,
            'num_pages': paginator.num_pages,
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'previous_page_number': page_obj.previous_page_number if page_obj.has_previous() else None,
            'next_page_number': page_obj.next_page_number if page_obj.has_next() else None,
        },
        'total_count': paginator.count,
    })