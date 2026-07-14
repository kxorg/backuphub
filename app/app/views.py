from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from systems.models import TargetSystem
from operations.models import BackupOperation
from django.shortcuts import render


@login_required
def index(request):
    """GET / - Dashboard / Home page"""
    now = timezone.now()
    last_24h = now - timedelta(hours=24)

    total_systems = TargetSystem.objects.filter(is_active=True).count()
    new_systems = TargetSystem.objects.filter(created_at__gte=last_24h).count()
    total_backups = BackupOperation.objects.count()
    total_hosts = BackupOperation.objects.values('hostname').distinct().count()

    ops_24h = BackupOperation.objects.filter(started_at__gte=last_24h)
    success_24h = ops_24h.filter(status='success').count()
    in_progress_24h = ops_24h.filter(status='in_progress').count()
    error_24h = ops_24h.filter(status='error').count()

    recent_backups = BackupOperation.objects.select_related(
        'backup_configuration_version__backup_configuration__target_system_version__target_system'
    ).order_by('-started_at')[:10]

    from django.db.models import OuterRef
    
    systems = TargetSystem.objects.filter(is_active=True).select_related('system_type', 'environment')
    
    last_ops = BackupOperation.objects.filter(
        backup_configuration_version__backup_configuration__target_system_version__target_system=OuterRef('pk')
    ).order_by('-started_at')
    
    systems_data = []
    for sys in systems:
        last_op = last_ops.filter(
            backup_configuration_version__backup_configuration__target_system_version__target_system=sys
        ).first()
        
        systems_data.append({
            'system': sys,
            'last_backup': last_op,
            'status_label': 'Активна' if sys.is_active else 'Неактивна',
            'ops_count': BackupOperation.objects.filter(
                backup_configuration_version__backup_configuration__target_system_version__target_system=sys
            ).count()
        })

    context = {
        'total_systems': total_systems,
        'new_systems': new_systems,
        'total_backups': total_backups,
        'total_hosts': total_hosts,
        'success_24h': success_24h,
        'in_progress_24h': in_progress_24h,
        'error_24h': error_24h,
        'recent_backups': recent_backups,
        'systems_data': systems_data,
    }
    return render(request, 'index.html', context)
