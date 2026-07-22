from django.db.models import Q
from systems.models import TargetSystem, TargetSystemVersion
from configurations.models import BackupConfiguration, BackupConfigurationVersion
from operations.models import BackupOperation
from dictionaries.models import SystemType, Environment, BackupTool, InformationSystem


class GlobalSearchService:
    """Global search service across all models"""
    
    @staticmethod
    def search(query, page=1, page_size=25):
        """
        Searches across all models and returns unified results.
        
        Args:
            query: search query
            page: page number
            page_size: number of results per page
            
        Returns:
            dict with fields: count, next, results
        """
        if not query or len(query.strip()) < 2:
            return {
                'count': 0,
                'next': False,
                'results': []
            }
        
        all_results = []
        
        # 1. Target Systems
        all_results.extend(GlobalSearchService._search_target_systems(query))
        
        # 2. Backup Configurations
        all_results.extend(GlobalSearchService._search_backup_configurations(query))
        
        # 3. Backup Operations
        all_results.extend(GlobalSearchService._search_backup_operations(query))
        
        # 4. System Types
        all_results.extend(GlobalSearchService._search_system_types(query))
        
        # 5. Environments
        all_results.extend(GlobalSearchService._search_environments(query))
        
        # 6. Backup Tools
        all_results.extend(GlobalSearchService._search_backup_tools(query))
        
        # 7. Information Systems
        all_results.extend(GlobalSearchService._search_information_systems(query))
        
        # Sort by relevance (simple: exact matches first)
        all_results.sort(key=lambda x: GlobalSearchService._relevance_score(x, query), reverse=True)
        
        # Pagination
        total_count = len(all_results)
        start = (page - 1) * page_size
        end = start + page_size
        page_results = all_results[start:end]
        
        return {
            'count': total_count,
            'next': end < total_count,
            'results': page_results
        }
    
    @staticmethod
    def _search_target_systems(query):
        """Search by TargetSystem"""
        results = []
        systems = TargetSystem.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(api_key__icontains=query)
        ).select_related('system_type', 'environment')[:100]
        
        for system in systems:
            results.append({
                'type': 'target_system',
                'id': system.id,
                'title': system.name,
                'subtitle': f"{system.system_type.name} • {system.environment.name if system.environment else '—'}",
                'url': f"/target-systems/{system.id}/",
                'icon': 'bi-server',
                'color': 'primary'
            })
        
        return results
    
    @staticmethod
    def _search_backup_configurations(query):
        """Search by BackupConfiguration"""
        results = []
        configs = BackupConfiguration.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).select_related(
            'target_system_version__target_system',
            'target_system_version__target_system__system_type'
        )[:100]
        
        for config in configs:
            ts = config.target_system_version.target_system
            results.append({
                'type': 'backup_configuration',
                'id': config.id,
                'title': config.name,
                'subtitle': f"{ts.name} ({ts.system_type.name})",
                'url': f"/backup-configuration/{config.id}/",
                'icon': 'bi-gear',
                'color': 'success'
            })
        
        return results
    
    @staticmethod
    def _search_backup_operations(query):
        """Search by BackupOperation"""
        results = []
        operations = BackupOperation.objects.filter(
            Q(hostname__icontains=query) |
            Q(external_job_id__icontains=query) |
            Q(storage_path__icontains=query)
        ).select_related(
            'backup_configuration_version__backup_configuration',
            'backup_configuration_version__backup_configuration__target_system_version__target_system'
        )[:100]
        
        for op in operations:
            status_badge = {
                'success': 'Success',
                'error': 'Error',
                'in_progress': 'In Progress',
                'warning': 'Warning',
                'cancelled': 'Cancelled'
            }.get(op.status, op.status)
            
            results.append({
                'type': 'backup_operation',
                'id': op.id,
                'title': op.hostname,
                'subtitle': f"#{op.id} • {status_badge}",
                'url': f"/backup-operations/{op.id}/",
                'icon': 'bi-clock-history',
                'color': 'dark'
            })
        
        return results
    
    @staticmethod
    def _search_system_types(query):
        """Search by SystemType"""
        results = []
        types = SystemType.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )[:50]
        
        for st in types:
            results.append({
                'type': 'system_type',
                'id': st.id,
                'title': st.name,
                'subtitle': 'System Type',
                'url': f"/dictionaries/system-types/{st.id}/edit/",
                'icon': 'bi-diagram-3',
                'color': 'secondary'
            })
        
        return results
    
    @staticmethod
    def _search_environments(query):
        """Search by Environment"""
        results = []
        envs = Environment.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )[:50]
        
        for env in envs:
            results.append({
                'type': 'environment',
                'id': env.id,
                'title': env.name,
                'subtitle': 'Environment',
                'url': f"/dictionaries/environments/{env.id}/edit/",
                'icon': 'bi-cloud',
                'color': 'info'
            })
        
        return results
    
    @staticmethod
    def _search_backup_tools(query):
        """Search in BackupTool"""
        results = []
        tools = BackupTool.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )[:50]
        
        for tool in tools:
            results.append({
                'type': 'backup_tool',
                'id': tool.id,
                'title': tool.name,
                'subtitle': 'Backup Tool',
                'url': f"/dictionaries/backup-tools/{tool.id}/edit/",
                'icon': 'bi-tools',
                'color': 'warning'
            })
        
        return results
    
    @staticmethod
    def _search_information_systems(query):
        """Search InformationSystem"""
        results = []
        info_systems = InformationSystem.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )[:50]
        
        for info_sys in info_systems:
            results.append({
                'type': 'information_system',
                'id': info_sys.id,
                'title': info_sys.name,
                'subtitle': 'Information System',
                'url': f"/dictionaries/information-systems/{info_sys.id}/edit/",
                'icon': 'bi-hdd-network',
                'color': 'purple'
            })
        
        return results
    
    @staticmethod
    def _relevance_score(result, query):
        """Calculates the relevance of the result (the higher, the better)"""
        score = 0
        query_lower = query.lower()
        
        # Protection against None values ​​in the title and subtitle fields
        title_str = str(result.get('title') or '').lower()
        subtitle_str = str(result.get('subtitle') or '').lower()
        
        if title_str == query_lower:
            score += 100
        
        elif title_str.startswith(query_lower):
            score += 50
        
        elif query_lower in title_str:
            score += 25
        
        if query_lower in subtitle_str:
            score += 10
        
        return score
