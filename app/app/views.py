from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from systems.models import TargetSystem
from operations.models import BackupOperation
from django.shortcuts import render
from django.db.models import Count, OuterRef, Subquery

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

    
    
    systems = TargetSystem.objects.filter(is_active=True).select_related('system_type', 'environment')
    system_ids = list(systems.values_list('id', flat=True))

    
    ops_counts = BackupOperation.objects.filter(
        backup_configuration_version__backup_configuration__target_system_version__target_system_id__in=system_ids
    ).values(
        'backup_configuration_version__backup_configuration__target_system_version__target_system_id'
    ).annotate(total=Count('id'))
    
    counts_dict = {
        item['backup_configuration_version__backup_configuration__target_system_version__target_system_id']: item['total']
        for item in ops_counts
    }


    last_op_subquery = BackupOperation.objects.filter(
        backup_configuration_version__backup_configuration__target_system_version__target_system_id=OuterRef('backup_configuration_version__backup_configuration__target_system_version__target_system_id')
    ).order_by('-started_at').values('id')[:1]

    
    last_backups_ids = BackupOperation.objects.filter(
        backup_configuration_version__backup_configuration__target_system_version__target_system_id__in=system_ids
    ).annotate(
        latest_id=Subquery(last_op_subquery)
    ).values_list('latest_id', flat=True).distinct()


    recent_ops = BackupOperation.objects.filter(
        id__in=list(filter(None, last_backups_ids))
    ).select_related(
        'backup_configuration_version__backup_configuration__target_system_version'
    )
    

    backups_dict = {}
    for op in recent_ops:
        sys_id = op.backup_configuration_version.backup_configuration.target_system_version.target_system_id
        if sys_id not in backups_dict:
            backups_dict[sys_id] = op

    systems_data = []
    for sys in systems:
        systems_data.append({
            'system': sys,
            'last_backup': backups_dict.get(sys.id),
            'status_label': 'Active' if sys.is_active else 'Inactive',
            'ops_count': counts_dict.get(sys.id, 0)
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
