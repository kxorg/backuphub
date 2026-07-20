from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timesince import timesince
from rest_framework.decorators import api_view
from django.db.models import Q
from django.core.paginator import Paginator

from systems.models import TargetSystem, SystemType, Environment, InformationSystem
from operations.models import BackupOperation
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from configurations.models import BackupConfiguration, BackupTool
from django.core.paginator import Paginator

@extend_schema(
    tags=['UI Live Updates'],
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
    tags=['UI Live Updates'],
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

@extend_schema(
    tags=['UI Live Updates'],
    summary='Refresh Operation Detail',
    description='Returns all operation details for live updates',
)
@api_view(['GET'])
@login_required
def api_ui_refresh_operation_detail(request, pk):
    """API для живого обновления всех полей страницы детали операции"""
    from operations.models import BackupOperation
    from django.shortcuts import get_object_or_404
    
    operation = get_object_or_404(BackupOperation, pk=pk)
    
    # Динамический расчет длительности, если операция еще идет
    duration = operation.duration_seconds
    if not duration and operation.started_at and operation.status == 'in_progress':
        duration = int((timezone.now() - operation.started_at).total_seconds())

    # Данные конфигурации
    config_name = '—'
    config_version = '—'
    config_id = None
    if operation.backup_configuration_version:
        config = operation.backup_configuration_version.backup_configuration
        config_name = config.name
        config_version = operation.backup_configuration_version.version_number
        config_id = config.id

    data = {
        'status': operation.status,
        'status_display': operation.get_status_display(),
        'hostname': operation.hostname or '—',
        'ip_address': operation.ip_address or '—',
        'external_job_id': operation.external_job_id or '—',
        'started_at': operation.started_at.strftime('%d.%m.%Y %H:%M:%S') if operation.started_at else '—',
        'finished_at': operation.finished_at.strftime('%d.%m.%Y %H:%M:%S') if operation.finished_at else '—',
        'duration_seconds': duration,
        'size_human': operation.size_human or '—',
        'storage_type': operation.storage_type or '—',
        'storage_path': operation.storage_path or '—',
        'error_message': operation.error_message,
        'metadata': operation.metadata,
        'config_name': config_name,
        'config_version': config_version,
        'config_id': config_id,
    }
    return JsonResponse(data)

@extend_schema(
    tags=['UI Live Updates'],
    summary='Refresh Target System Details',
    description='Returns target system details and recent operations for live updates',
)
@api_view(['GET'])
@login_required
def api_ui_refresh_target_system(request, pk):
    """API для живого обновления страницы детали целевой системы"""
    from systems.models import TargetSystem
    from django.shortcuts import get_object_or_404
    
    ts = get_object_or_404(TargetSystem, pk=pk)
    
    data = {
        'id': ts.id,
        'name': ts.name,
        'is_active': ts.is_active,
    }
    
    # Последние операции для этой целевой системы
    recent_ops = BackupOperation.objects.filter(
        backup_configuration_version__backup_configuration__target_system_version__target_system=ts
    ).select_related(
        'backup_configuration_version__backup_configuration'
    ).order_by('-started_at')[:10]
    
    operations_data = []
    for op in recent_ops:
        config = op.backup_configuration_version.backup_configuration if op.backup_configuration_version else None
        operations_data.append({
            'id': op.id,
            'started_at': op.started_at.strftime('%d.%m.%Y %H:%M') if op.started_at else '—',
            'configuration_name': config.name if config else '—',
            'configuration_id': config.id if config else None,
            'hostname': op.hostname or '—',
            'status': op.status,
            'status_display': op.get_status_display(),
            'duration_seconds': op.duration_seconds,
            'size_human': op.size_human or '—',
            'detail_url': f'/backup-operations/{op.id}/',
        })
        
    data['recent_operations'] = operations_data
    return JsonResponse(data)

@extend_schema(
    tags=['Backup Operations API'],
    summary='Global Search',
    description='Unified search across all models with pagination',
)
@api_view(['GET'])
# @login_required
def api_global_search(request):
    """
    Универсальный поиск по всем моделям системы.
    Возвращает результаты в едином формате с пагинацией.
    """
    query = request.GET.get('q', '').strip()
    
    try:
        page = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page = 1
        
    try:
        page_size = int(request.GET.get('page_size', 25))
    except (ValueError, TypeError):
        page_size = 25
    
    # Ограничиваем максимальный размер страницы
    page_size = min(page_size, 100)

    all_results = []

    # 1. TargetSystem
    if query:
        systems = TargetSystem.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(system_type__name__icontains=query) |
            Q(environment__name__icontains=query) |
            Q(information_system__name__icontains=query)
        ).select_related(
            'system_type', 'environment', 'information_system'
        )[:200]  # Ограничиваем для производительности
    else:
        systems = TargetSystem.objects.all().order_by('-created_at')[:200]
    
    for sys in systems:
        subtitle_parts = []
        if sys.system_type:
            subtitle_parts.append(sys.system_type.name)
        if sys.environment:
            subtitle_parts.append(sys.environment.name)
        
        all_results.append({
            'type': 'target_system',
            'id': sys.id,
            'title': sys.name,
            'subtitle': ' • '.join(subtitle_parts) if subtitle_parts else 'Система',
            'description': sys.description or None,
            'url': f'/target-systems/{sys.id}/',
        })

    # 2. BackupConfiguration
    if query:
        configs = BackupConfiguration.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(versions__is_current=True, versions__backup_tool__name__icontains=query) |
            Q(target_system_version__target_system__name__icontains=query)
        ).select_related(
            'target_system_version__target_system'
        ).distinct()[:200] 
    else:
        configs = BackupConfiguration.objects.all().order_by('-created_at')[:200]
    
    for config in configs:
        target_system_name = ''
        if config.target_system_version and config.target_system_version.target_system:
            target_system_name = config.target_system_version.target_system.name
        
        all_results.append({
            'type': 'backup_configuration',
            'id': config.id,
            'title': config.name,
            'subtitle': target_system_name or 'Конфигурация',
            'description': config.description or None,
            'url': f'/backup-configuration/{config.id}/',
        })
    
    for config in configs:
        target_system_name = ''
        if config.target_system_version and config.target_system_version.target_system:
            target_system_name = config.target_system_version.target_system.name
        
        all_results.append({
            'type': 'backup_configuration',
            'id': config.id,
            'title': config.name,
            'subtitle': target_system_name or 'Конфигурация',
            'description': config.description or None,
            'url': f'/backup-configuration/{config.id}/',
        })

    # 3. BackupOperation
    if query:
        operations = BackupOperation.objects.filter(
            Q(hostname__icontains=query) | 
            Q(external_job_id__icontains=query) |
            Q(storage_path__icontains=query) |
            Q(status__icontains=query)
        ).select_related(
            'backup_configuration_version__backup_configuration'
        )[:200]
    else:
        operations = BackupOperation.objects.all().order_by('-started_at')[:200]
    
    for op in operations:
        config_name = ''
        if op.backup_configuration_version and op.backup_configuration_version.backup_configuration:
            config_name = op.backup_configuration_version.backup_configuration.name
        
        title = f"Операция #{op.id}"
        if op.hostname:
            title += f" ({op.hostname})"
        
        all_results.append({
            'type': 'backup_operation',
            'id': op.id,
            'title': title,
            'subtitle': f"{config_name} • {op.get_status_display()}" if config_name else op.get_status_display(),
            'description': f"Started: {op.started_at.strftime('%d.%m.%Y %H:%M')}" if op.started_at else None,
            'url': f'/backup-operations/{op.id}/',
        })

    # 4. BackupTool
    from configurations.models import BackupTool
    if query:
        tools = BackupTool.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )[:100]
    else:
        tools = BackupTool.objects.all().order_by('name')[:100]
    
    for tool in tools:
        all_results.append({
            'type': 'backup_tool',
            'id': tool.id,
            'title': tool.name,
            'subtitle': 'Инструмент резервного копирования',
            'description': tool.description or None,
            'url': f'/backup-tools/{tool.id}/',
        })

    # 5. SystemType
    if query:
        system_types = SystemType.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )[:100]
    else:
        system_types = SystemType.objects.all().order_by('name')[:100]
    
    for st in system_types:
        all_results.append({
            'type': 'system_type',
            'id': st.id,
            'title': st.name,
            'subtitle': 'Тип системы',
            'description': st.description or None,
            'url': f'/system-types/{st.id}/',
        })

    # 6. Environment
    from systems.models import Environment
    if query:
        environments = Environment.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )[:100]
    else:
        environments = Environment.objects.all().order_by('name')[:100]
    
    for env in environments:
        all_results.append({
            'type': 'environment',
            'id': env.id,
            'title': env.name,
            'subtitle': 'Окружение',
            'description': env.description or None,
            'url': f'/environments/{env.id}/',
        })

    # 7. InformationSystem
    from systems.models import InformationSystem
    if query:
        info_systems = InformationSystem.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )[:100]
    else:
        info_systems = InformationSystem.objects.all().order_by('name')[:100]
    
    for info_sys in info_systems:
        all_results.append({
            'type': 'information_system',
            'id': info_sys.id,
            'title': info_sys.name,
            'subtitle': 'Информационная система',
            'description': info_sys.description or None,
            'url': f'/information-systems/{info_sys.id}/',
        })

    # Сортируем результаты: сначала по релевантности (если есть query), потом по ID
    # Для простоты сортируем по type и id
    all_results.sort(key=lambda x: (x['type'], x['id']))

    # Пагинация
    paginator = Paginator(all_results, page_size)
    
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
        page = 1

    return JsonResponse({
        'count': paginator.count,
        'page': page,
        'page_size': page_size,
        'has_next': page_obj.has_next(),
        'results': page_obj.object_list,
    })