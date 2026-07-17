from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.db.models import Q

from .models import BackupOperation

class BackupOperationListView(LoginRequiredMixin, ListView):
    """GET /backup-operations/"""
    model = BackupOperation
    template_name = 'backup_operations/backupoperation_list.html'
    context_object_name = 'operations'
    paginate_by = 50

    def get_queryset(self):
        queryset = BackupOperation.objects.select_related(
            'backup_configuration_version',
            'backup_configuration_version__backup_configuration',
            'backup_configuration_version__backup_configuration__target_system_version',
            'backup_configuration_version__backup_configuration__target_system_version__target_system',
            'backup_configuration_version__backup_tool'
        ).order_by('-started_at')

        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(hostname__icontains=search_query) |
                Q(external_job_id__icontains=search_query) |
                Q(storage_path__icontains=search_query)
            )

        status = self.request.GET.get('status', '').strip()
        if status:
            queryset = queryset.filter(status=status)

        hostname = self.request.GET.get('hostname', '').strip()
        if hostname:
            queryset = queryset.filter(hostname__icontains=hostname)

        config_id = self.request.GET.get('configuration', '').strip()
        if config_id and config_id.isdigit():
            queryset = queryset.filter(
                backup_configuration_version__backup_configuration_id=int(config_id)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['hostname_filter'] = self.request.GET.get('hostname', '')
        context['configuration_filter'] = self.request.GET.get('configuration', '')
        context['status_choices'] = BackupOperation.STATUS_CHOICES
        return context


class BackupOperationDetailView(LoginRequiredMixin, DetailView):
    """GET /backup-operations/<pk>/"""
    model = BackupOperation
    template_name = 'backup_operations/backupoperation_detail.html'
    context_object_name = 'operation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['duration_seconds'] = self.object.duration_seconds
        context['size_human'] = self.object.size_human
        return context


