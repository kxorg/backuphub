from django.db.models import Q
from django.core.paginator import Paginator
from systems.models import TargetSystem, SystemType, Environment, InformationSystem
from configurations.models import BackupConfiguration, BackupTool
from operations.models import BackupOperation


class GlobalSearchService:
    """Global search service across all models"""
    
    @staticmethod
    def search(query: str, page: int = 1, page_size: int = 25) -> dict:
        """
        Searches across all models and returns unified results.
        
        Args:
            query: search query
            page: page number
            page_size: number of results per page
            
        Returns:
            dict with fields: count, page, page_size, has_next, results
        """
        page_size = min(page_size, 100)
        all_results = []
        
        # 1. TargetSystem
        all_results.extend(GlobalSearchService._search_target_systems(query))
        
        # 2. BackupConfiguration
        all_results.extend(GlobalSearchService._search_backup_configurations(query))
        
        # 3. BackupOperation
        all_results.extend(GlobalSearchService._search_backup_operations(query))
        
        # 4. BackupTool
        all_results.extend(GlobalSearchService._search_backup_tools(query))
        
        # 5. SystemType
        all_results.extend(GlobalSearchService._search_system_types(query))
        
        # 6. Environment
        all_results.extend(GlobalSearchService._search_environments(query))
        
        # 7. InformationSystem
        all_results.extend(GlobalSearchService._search_information_systems(query))
        
        # Sort
        all_results.sort(key=lambda x: (x['type'], x['id']))
        
        # Pagination
        paginator = Paginator(all_results, page_size)
        try:
            page_obj = paginator.page(page)
        except:
            page_obj = paginator.page(1)
            page = 1
        
        return {
            'count': paginator.count,
            'page': page,
            'page_size': page_size,
            'has_next': page_obj.has_next(),
            'results': page_obj.object_list,
        }
    
    @staticmethod
    def _search_target_systems(query: str) -> list:
        """Search by TargetSystem"""
        if query:
            systems = TargetSystem.objects.filter(
                Q(name__icontains=query) | 
                Q(description__icontains=query) |
                Q(system_type__name__icontains=query) |
                Q(environment__name__icontains=query) |
                Q(information_system__name__icontains=query)
            ).select_related('system_type', 'environment', 'information_system')[:200]
        else:
            systems = TargetSystem.objects.all().order_by('-created_at')[:200]
        
        results = []
        for sys in systems:
            subtitle_parts = []
            if sys.system_type:
                subtitle_parts.append(sys.system_type.name)
            if sys.environment:
                subtitle_parts.append(sys.environment.name)
            
            results.append({
                'type': 'target_system',
                'id': sys.id,
                'title': sys.name,
                'subtitle': ' • '.join(subtitle_parts) if subtitle_parts else 'System',
                'description': sys.description or None,
                'url': f'/target-systems/{sys.id}/',
            })
        return results
    
    @staticmethod
    def _search_backup_configurations(query: str) -> list:
        """Search by BackupConfiguration"""
        if query:
            configs = BackupConfiguration.objects.filter(
                Q(name__icontains=query) | 
                Q(description__icontains=query) |
                Q(versions__is_current=True, versions__backup_tool__name__icontains=query) |
                Q(target_system_version__target_system__name__icontains=query)
            ).select_related('target_system_version__target_system').distinct()[:200]
        else:
            configs = BackupConfiguration.objects.all().order_by('-created_at')[:200]
        
        results = []
        for config in configs:
            target_system_name = ''
            if config.target_system_version and config.target_system_version.target_system:
                target_system_name = config.target_system_version.target_system.name
            
            results.append({
                'type': 'backup_configuration',
                'id': config.id,
                'title': config.name,
                'subtitle': target_system_name or 'Configuration',
                'description': config.description or None,
                'url': f'/backup-configuration/{config.id}/',
            })
        return results
    
    @staticmethod
    def _search_backup_operations(query: str) -> list:
        """Search by BackupOperation"""
        if query:
            operations = BackupOperation.objects.filter(
                Q(hostname__icontains=query) | 
                Q(external_job_id__icontains=query) |
                Q(storage_path__icontains=query) |
                Q(status__icontains=query)
            ).select_related('backup_configuration_version__backup_configuration')[:200]
        else:
            operations = BackupOperation.objects.all().order_by('-started_at')[:200]
        
        results = []
        for op in operations:
            config_name = ''
            if op.backup_configuration_version and op.backup_configuration_version.backup_configuration:
                config_name = op.backup_configuration_version.backup_configuration.name
            
            title = f"Operation #{op.id}"
            if op.hostname:
                title += f" ({op.hostname})"
            
            results.append({
                'type': 'backup_operation',
                'id': op.id,
                'title': title,
                'subtitle': f"{config_name} • {op.get_status_display()}" if config_name else op.get_status_display(),
                'description': f"Started: {op.started_at.strftime('%d.%m.%Y %H:%M')}" if op.started_at else None,
                'url': f'/backup-operations/{op.id}/',
            })
        return results
    
    @staticmethod
    def _search_backup_tools(query: str) -> list:
        """Search by BackupTool"""
        if query:
            tools = BackupTool.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )[:100]
        else:
            tools = BackupTool.objects.all().order_by('name')[:100]
        
        return [{
            'type': 'backup_tool',
            'id': tool.id,
            'title': tool.name,
            'subtitle': 'Backup tool',
            'description': tool.description or None,
            'url': f'/backup-tools/{tool.id}/edit/',
        } for tool in tools]
    
    @staticmethod
    def _search_system_types(query: str) -> list:
        """Search by SystemType"""
        if query:
            system_types = SystemType.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )[:100]
        else:
            system_types = SystemType.objects.all().order_by('name')[:100]
        
        return [{
            'type': 'system_type',
            'id': st.id,
            'title': st.name,
            'subtitle': 'System type',
            'description': st.description or None,
            'url': f'/system-types/{st.id}/edit/',
        } for st in system_types]
    
    @staticmethod
    def _search_environments(query: str) -> list:
        """Search by Environment"""
        if query:
            environments = Environment.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )[:100]
        else:
            environments = Environment.objects.all().order_by('name')[:100]
        
        return [{
            'type': 'environment',
            'id': env.id,
            'title': env.name,
            'subtitle': 'Environment',
            'description': env.description or None,
            'url': f'/environments/{env.id}/edit/',
        } for env in environments]
    
    @staticmethod
    def _search_information_systems(query: str) -> list:
        """Search by InformationSystem"""
        if query:
            info_systems = InformationSystem.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )[:100]
        else:
            info_systems = InformationSystem.objects.all().order_by('name')[:100]
        
        return [{
            'type': 'information_system',
            'id': info_sys.id,
            'title': info_sys.name,
            'subtitle': 'Information system',
            'description': info_sys.description or None,
            'url': f'/information-systems/{info_sys.id}/edit/',
        } for info_sys in info_systems]