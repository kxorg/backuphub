from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.decorators import api_view

from systems.models import TargetSystem
from operations.models import BackupOperation
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

@extend_schema(
    tags=['Dashboard'],
    summary='Refresh Dashboard Data',
    description=(
        'Returns aggregated statistics for the last 24 hours and the 10 most recent backup operations. '
        'Designed for live UI updates via AJAX (fetch). Requires session authentication.'
    ),
    responses={
        200: OpenApiResponse(
            description='Dashboard statistics and recent operations',
            examples=[
                OpenApiExample(
                    'Dashboard Response',
                    value={
                        'total_systems': 5,
                        'new_systems': 1,
                        'total_backups': 150,
                        'total_hosts': 12,
                        'success_24h': 45,
                        'in_progress_24h': 2,
                        'error_24h': 1,
                        'recent_operations': [
                            {
                                'id': 42,
                                'system_name': 'PG Main DB',
                                'hostname': 'backup-server-01',
                                'status': 'success',
                                'started_at': '14.07.2026 10:00',
                                'size_human': '1.5 GB',
                                'detail_url': '/backup-operations/42/'
                            }
                        ]
                    }
                )
            ]
        ),
        401: OpenApiResponse(description='Unauthorized (Login required)'),
    },
    deprecated=False,
)
@api_view(['GET'])
@login_required
def api_ui_refresh_dashboard(request):
    """
    Internal JSON endpoint for live dashboard refresh.
    Not part of the external API — requires session auth.
    """
    now = timezone.now()
    last_24h = now - timedelta(hours=24)

    data = {
        'total_systems': TargetSystem.objects.filter(is_active=True).count(),
        'new_systems': TargetSystem.objects.filter(created_at__gte=last_24h).count(),
        'total_backups': BackupOperation.objects.count(),
        'total_hosts': BackupOperation.objects.values('hostname').distinct().count(),
        'success_24h': BackupOperation.objects.filter(
            started_at__gte=last_24h, status='success'
        ).count(),
        'in_progress_24h': BackupOperation.objects.filter(
            started_at__gte=last_24h, status='in_progress'
        ).count(),
        'error_24h': BackupOperation.objects.filter(
            started_at__gte=last_24h, status='error'
        ).count(),
    }

    recent_backups = (
        BackupOperation.objects
        .select_related(
            'backup_configuration_version__backup_configuration__target_system_version__target_system'
        )
        .order_by('-started_at')[:10]
    )

    ops_data = []
    for op in recent_backups:
        sys_name = (
            op.backup_configuration_version
            .backup_configuration
            .target_system_version
            .target_system.name
        )
        ops_data.append({
            'id': op.id,
            'system_name': sys_name,
            'hostname': op.hostname,
            'status': op.status,
            'started_at': op.started_at.strftime('%d.%m.%Y %H:%M') if op.started_at else '-',
            'duration_seconds': op.duration_seconds,
            'size_human': op.size_human or '-',
            'detail_url': f'/backup-operations/{op.id}/',
        })

    data['recent_operations'] = ops_data
    return JsonResponse(data)