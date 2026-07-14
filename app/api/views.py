from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timesince import timesince
from rest_framework.decorators import api_view

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
        # Безопасное получение имени системы
        sys_name = 'Unknown'
        try:
            if (op.backup_configuration_version 
                and op.backup_configuration_version.backup_configuration
                and op.backup_configuration_version.backup_configuration.target_system_version
                and op.backup_configuration_version.backup_configuration.target_system_version.target_system):
                sys_name = op.backup_configuration_version.backup_configuration.target_system_version.target_system.name
        except AttributeError:
            sys_name = 'Unknown'
        
        # 🔥 БЕЗОПАСНОЕ формирование относительного времени
        time_display = '—'
        if op.started_at:
            try:
                time_display = f"{timesince(op.started_at, now=now)} ago"
            except (ValueError, TypeError):
                # Если timesince падает, используем запасной вариант
                time_display = op.started_at.strftime('%d.%m.%Y %H:%M')
        
        ops_data.append({
            'id': op.id,
            'system_name': sys_name,
            'hostname': op.hostname or '',
            'status': op.status,
            'started_at': time_display,  # ← Теперь это безопасная строка
            'size_human': op.size_human or '—',
            'detail_url': f"/backup-operations/{op.id}/",
        })
        
    data['recent_operations'] = ops_data
    
    return JsonResponse(data)