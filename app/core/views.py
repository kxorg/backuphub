<<<<<<< HEAD
from django.shortcuts import redirect
from django.urls import reverse_lazy
from datetime import timedelta
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.views.generic import ListView, DetailView
from django.db.models import Q
from .models import TargetSystem, TargetSystemVersion, BackupConfiguration, BackupConfigurationVersion, BackupOperation, SystemType, Environment, BackupTool
from .forms import TargetSystemForm, BackupConfigurationForm, SystemTypeForm, EnvironmentForm, BackupToolForm
from django.shortcuts import render

class TargetSystemListView(ListView):
    """GET /target-systems/"""
    model = TargetSystem
    template_name = 'target_systems/targetsystem_list.html'
    context_object_name = 'target_systems'
    paginate_by = 20

    def get_queryset(self):
        return TargetSystem.objects.select_related(
            'system_type', 'environment'
        ).filter(is_active=True).order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for system in context['target_systems']:
            system.current_version_data = system.current_version
        return context


class TargetSystemDetailView(DetailView):
    """GET /target-systems/<pk>/"""
    model = TargetSystem
    template_name = 'target_systems/targetsystem_detail.html'
    context_object_name = 'target_system'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_version'] = self.object.current_version
        return context


class TargetSystemCreateView(CreateView):
    """
    GET /target-systems/create/
    POST /target-systems/create/
    """
    model = TargetSystem
    form_class = TargetSystemForm
    template_name = 'target_systems/targetsystem_form.html'
    success_url = reverse_lazy('target_systems:target_system_list')

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.created_by = self.request.user.username if self.request.user.is_authenticated else 'System'
        self.object.save()

        # Создаем первую версию
        TargetSystemVersion.objects.create(
            target_system=self.object,
            version_number=1,
            owner=form.cleaned_data.get('owner'),
            administrator=form.cleaned_data.get('administrator'),
            is_current=True,
            valid_from=timezone.now(),
            created_by=self.request.user.username if self.request.user.is_authenticated else 'System',
        )

        messages.success(self.request, f'Target System "{self.object.name}" created successfully.')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Target System'
        context['action'] = 'create'
        return context


class TargetSystemUpdateView(UpdateView):
    """
    GET /target-systems/<pk>/edit/
    POST /target-systems/<pk>/edit/
    """
    model = TargetSystem
    form_class = TargetSystemForm
    template_name = 'target_systems/targetsystem_form.html'
    success_url = reverse_lazy('target_systems:target_system_list')

    @transaction.atomic
    def form_valid(self, form):
        current_version = self.object.current_version
        versioned_fields_changed = False
        
        if current_version:
            if (form.cleaned_data.get('owner') != current_version.owner or
                form.cleaned_data.get('administrator') != current_version.administrator):
                versioned_fields_changed = True

        self.object = form.save(commit=False)
        self.object.updated_by = self.request.user.username if self.request.user.is_authenticated else 'System'
        self.object.save()

        if versioned_fields_changed:
            current_version.is_current = False
            current_version.valid_to = timezone.now()
            current_version.save()

            TargetSystemVersion.objects.create(
                target_system=self.object,
                version_number=current_version.version_number + 1,
                owner=form.cleaned_data.get('owner'),
                administrator=form.cleaned_data.get('administrator'),
                is_current=True,
                valid_from=timezone.now(),
                created_by=self.request.user.username if self.request.user.is_authenticated else 'System',
            )
            messages.success(self.request, f'Updated. New version created.')
        else:
            messages.success(self.request, f'Target System updated.')

        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Target System'
        context['action'] = 'edit'
        context['current_version'] = self.object.current_version
        return context


class TargetSystemDeleteView(DeleteView):
    """POST /target-systems/<pk>/delete/"""
    model = TargetSystem
    success_url = reverse_lazy('target_systems:target_system_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.updated_by = request.user.username if request.user.is_authenticated else 'System'
        self.object.save()
        messages.success(request, f'Target System deactivated.')
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        return redirect('target_systems:target_system_list')


class TargetSystemHistoryView(DetailView):
    """GET /target-systems/<pk>/history/"""
    model = TargetSystem
    template_name = 'target_systems/targetsystem_history.html'
    context_object_name = 'target_system'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['versions'] = TargetSystemVersion.objects.filter(
            target_system=self.object
        ).order_by('-version_number')
        return context


class TargetSystemVersionDetailView(DetailView):
    """GET /target-systems/<pk>/history/<version_pk>/"""
    model = TargetSystemVersion
    template_name = 'target_systems/targetsystem_version_detail.html'
    context_object_name = 'version'
    pk_url_kwarg = 'version_pk'  # <-- Указываем, что primary key в URL называется 'version_pk'

    def get_queryset(self):
        # Разрешаем доставать только ту версию, которая принадлежит системе из URL
        return TargetSystemVersion.objects.filter(
            target_system_id=self.kwargs['pk']
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target_system'] = self.object.target_system
        context['is_readonly'] = True
        return context


class BackupConfigurationListView(ListView):
    """GET /backup-configuration/"""
    model = BackupConfiguration
    template_name = 'backup_configurations/backupconfiguration_list.html'
    context_object_name = 'backup_configurations'
    paginate_by = 20

    def get_queryset(self):
        return BackupConfiguration.objects.select_related(
            'target_system_version',
            'target_system_version__target_system'
        ).filter(is_active=True).order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for config in context['backup_configurations']:
            config.current_version_data = config.current_version
        return context


class BackupConfigurationDetailView(DetailView):
    """GET /backup-configuration/<pk>/"""
    model = BackupConfiguration
    template_name = 'backup_configurations/backupconfiguration_detail.html'
    context_object_name = 'backup_configuration'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_version'] = self.object.current_version
        return context


class BackupConfigurationCreateView(CreateView):
    """
    GET /backup-configuration/create/
    POST /backup-configuration/create/
    """
    model = BackupConfiguration
    form_class = BackupConfigurationForm
    template_name = 'backup_configurations/backupconfiguration_form.html'
    success_url = reverse_lazy('backup_configuration_list')

    @transaction.atomic
    def form_valid(self, form):
        # Создаем BackupConfiguration
        self.object = form.save(commit=False)
        self.object.created_by = self.request.user.username if self.request.user.is_authenticated else 'System'
        self.object.save()

        # Создаем первую версию
        BackupConfigurationVersion.objects.create(
            backup_configuration=self.object,
            version_number=1,
            backup_tool=form.cleaned_data.get('backup_tool'),
            backup_mode=form.cleaned_data.get('backup_mode'),
            schedule_cron=form.cleaned_data.get('schedule_cron'),
            retention_days=form.cleaned_data.get('retention_days'),
            rpo_minutes=form.cleaned_data.get('rpo_minutes'),
            rto_minutes=form.cleaned_data.get('rto_minutes'),
            storage_type=form.cleaned_data.get('storage_type'),
            storage_path=form.cleaned_data.get('storage_path'),
            verify_after_backup=form.cleaned_data.get('verify_after_backup'),
            immutable_storage=form.cleaned_data.get('immutable_storage'),
            is_current=True,
            valid_from=timezone.now(),
            created_by=self.request.user.username if self.request.user.is_authenticated else 'System',
        )

        messages.success(self.request, f'Backup Configuration "{self.object.name}" created successfully.')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Backup Configuration'
        context['action'] = 'create'
        return context


class BackupConfigurationUpdateView(UpdateView):
    """
    GET /backup-configuration/<pk>/edit/
    POST /backup-configuration/<pk>/edit/
    """
    model = BackupConfiguration
    form_class = BackupConfigurationForm
    template_name = 'backup_configurations/backupconfiguration_form.html'
    success_url = reverse_lazy('backup_configuration_list')

    @transaction.atomic
    def form_valid(self, form):
        current_version = self.object.current_version
        versioned_fields_changed = False

        if current_version:
            # Проверяем, изменились ли версионируемые поля
            versioned_fields = [
                'backup_tool', 'backup_mode', 'schedule_cron',
                'retention_days', 'rpo_minutes', 'rto_minutes',
                'storage_type', 'storage_path',
                'verify_after_backup', 'immutable_storage'
            ]

            for field in versioned_fields:
                if form.cleaned_data.get(field) != getattr(current_version, field):
                    versioned_fields_changed = True
                    break

        # Обновляем BackupConfiguration
        self.object = form.save(commit=False)
        self.object.updated_by = self.request.user.username if self.request.user.is_authenticated else 'System'
        self.object.save()

        if versioned_fields_changed:
            # Закрываем текущую версию
            current_version.is_current = False
            current_version.valid_to = timezone.now()
            current_version.save()

            # Создаем новую версию
            BackupConfigurationVersion.objects.create(
                backup_configuration=self.object,
                version_number=current_version.version_number + 1,
                backup_tool=form.cleaned_data.get('backup_tool'),
                backup_mode=form.cleaned_data.get('backup_mode'),
                schedule_cron=form.cleaned_data.get('schedule_cron'),
                retention_days=form.cleaned_data.get('retention_days'),
                rpo_minutes=form.cleaned_data.get('rpo_minutes'),
                rto_minutes=form.cleaned_data.get('rto_minutes'),
                storage_type=form.cleaned_data.get('storage_type'),
                storage_path=form.cleaned_data.get('storage_path'),
                verify_after_backup=form.cleaned_data.get('verify_after_backup'),
                immutable_storage=form.cleaned_data.get('immutable_storage'),
                is_current=True,
                valid_from=timezone.now(),
                created_by=self.request.user.username if self.request.user.is_authenticated else 'System',
            )
            messages.success(self.request, f'Updated. New version created.')
        else:
            messages.success(self.request, f'Backup Configuration updated.')

        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Backup Configuration'
        context['action'] = 'edit'
        context['current_version'] = self.object.current_version
        return context


class BackupConfigurationDeleteView(DeleteView):
    """POST /backup-configuration/<pk>/delete/"""
    model = BackupConfiguration
    success_url = reverse_lazy('backup_configuration_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.updated_by = request.user.username if request.user.is_authenticated else 'System'
        self.object.save()
        messages.success(request, f'Backup Configuration deactivated.')
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        return redirect('backup_configuration_list')


class BackupConfigurationHistoryView(DetailView):
    """GET /backup-configuration/<pk>/history/"""
    model = BackupConfiguration
    template_name = 'backup_configurations/backupconfiguration_history.html'
    context_object_name = 'backup_configuration'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['versions'] = BackupConfigurationVersion.objects.filter(
            backup_configuration=self.object
        ).order_by('-version_number')
        return context


class BackupConfigurationVersionDetailView(DetailView):
    """GET /backup-configuration/<pk>/history/<version_pk>/"""
    model = BackupConfigurationVersion
    template_name = 'backup_configurations/backupconfiguration_version_detail.html'
    context_object_name = 'version'
    pk_url_kwarg = 'version_pk'

    def get_queryset(self):
        return BackupConfigurationVersion.objects.filter(
            backup_configuration_id=self.kwargs['pk']
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['backup_configuration'] = self.object.backup_configuration
        context['is_readonly'] = True
        return context
    
class BackupOperationListView(ListView):
    """
    GET /backup-operations/
    Список операций с поиском и фильтрацией
    """
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

        # Поиск по hostname, external_job_id, storage_path
        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(hostname__icontains=search_query) |
                Q(external_job_id__icontains=search_query) |
                Q(storage_path__icontains=search_query)
            )

        # Фильтрация по статусу
        status = self.request.GET.get('status', '').strip()
        if status:
            queryset = queryset.filter(status=status)

        # Фильтрация по hostname
        hostname = self.request.GET.get('hostname', '').strip()
        if hostname:
            queryset = queryset.filter(hostname__icontains=hostname)

        # Фильтрация по конфигурации
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


class BackupOperationDetailView(DetailView):
    """
    GET /backup-operations/<pk>/
    Детальная информация об операции
    """
    model = BackupOperation
    template_name = 'backup_operations/backupoperation_detail.html'
    context_object_name = 'operation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['duration_seconds'] = self.object.duration_seconds
        context['size_human'] = self.object.size_human
        return context
    

class BackupOperationListView(ListView):
    """
    GET /backup-operations/
    Список операций с поиском и фильтрацией
    """
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

        # Поиск по hostname, external_job_id, storage_path
        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(hostname__icontains=search_query) |
                Q(external_job_id__icontains=search_query) |
                Q(storage_path__icontains=search_query)
            )

        # Фильтрация по статусу
        status = self.request.GET.get('status', '').strip()
        if status:
            queryset = queryset.filter(status=status)

        # Фильтрация по hostname
        hostname = self.request.GET.get('hostname', '').strip()
        if hostname:
            queryset = queryset.filter(hostname__icontains=hostname)

        # Фильтрация по конфигурации
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


class BackupOperationDetailView(DetailView):
    """
    GET /backup-operations/<pk>/
    Детальная информация об операции
    """
    model = BackupOperation
    template_name = 'backup_operations/backupoperation_detail.html'
    context_object_name = 'operation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['duration_seconds'] = self.object.duration_seconds
        context['size_human'] = self.object.size_human
        return context
    

class SystemTypeListView(ListView):
    model = SystemType
    template_name = 'dictionaries/systemtype_list.html'
    context_object_name = 'system_types'
    paginate_by = 50


class SystemTypeCreateView(CreateView):
    model = SystemType
    form_class = SystemTypeForm
    template_name = 'dictionaries/systemtype_form.html'
    success_url = reverse_lazy('dictionaries:system_type_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user.username if self.request.user.is_authenticated else 'System'
        messages.success(self.request, 'System Type created successfully.')
        return super().form_valid(form)


class SystemTypeUpdateView(UpdateView):
    model = SystemType
    form_class = SystemTypeForm
    template_name = 'dictionaries/systemtype_form.html'
    success_url = reverse_lazy('dictionaries:system_type_list')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user.username if self.request.user.is_authenticated else 'System'
        messages.success(self.request, 'System Type updated successfully.')
        return super().form_valid(form)


class SystemTypeDeleteView(DeleteView):
    model = SystemType
    success_url = reverse_lazy('dictionaries:system_type_list')
    template_name = 'dictionaries/systemtype_confirm_delete.html'

    def form_valid(self, form):
        messages.success(self.request, 'System Type deleted successfully.')
        return super().form_valid(form)


class EnvironmentListView(ListView):
    model = Environment
    template_name = 'dictionaries/environment_list.html'
    context_object_name = 'environments'
    paginate_by = 50


class EnvironmentCreateView(CreateView):
    model = Environment
    form_class = EnvironmentForm
    template_name = 'dictionaries/environment_form.html'
    success_url = reverse_lazy('dictionaries:environment_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user.username if self.request.user.is_authenticated else 'System'
        messages.success(self.request, 'Environment created successfully.')
        return super().form_valid(form)


class EnvironmentUpdateView(UpdateView):
    model = Environment
    form_class = EnvironmentForm
    template_name = 'dictionaries/environment_form.html'
    success_url = reverse_lazy('dictionaries:environment_list')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user.username if self.request.user.is_authenticated else 'System'
        messages.success(self.request, 'Environment updated successfully.')
        return super().form_valid(form)


class EnvironmentDeleteView(DeleteView):
    model = Environment
    success_url = reverse_lazy('dictionaries:environment_list')
    template_name = 'dictionaries/environment_confirm_delete.html'

    def form_valid(self, form):
        messages.success(self.request, 'Environment deleted successfully.')
        return super().form_valid(form)



class BackupToolListView(ListView):
    model = BackupTool
    template_name = 'dictionaries/backuptool_list.html'
    context_object_name = 'backup_tools'
    paginate_by = 50


class BackupToolCreateView(CreateView):
    model = BackupTool
    form_class = BackupToolForm
    template_name = 'dictionaries/backuptool_form.html'
    success_url = reverse_lazy('dictionaries:backup_tool_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user.username if self.request.user.is_authenticated else 'System'
        messages.success(self.request, 'Backup Tool created successfully.')
        return super().form_valid(form)


class BackupToolUpdateView(UpdateView):
    model = BackupTool
    form_class = BackupToolForm
    template_name = 'dictionaries/backuptool_form.html'
    success_url = reverse_lazy('dictionaries:backup_tool_list')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user.username if self.request.user.is_authenticated else 'System'
        messages.success(self.request, 'Backup Tool updated successfully.')
        return super().form_valid(form)


class BackupToolDeleteView(DeleteView):
    model = BackupTool
    success_url = reverse_lazy('dictionaries:backup_tool_list')
    template_name = 'dictionaries/backuptool_confirm_delete.html'

    def form_valid(self, form):
        messages.success(self.request, 'Backup Tool deleted successfully.')
        return super().form_valid(form)
    
def index(request):
    """GET / - Dashboard / Home page"""
    now = timezone.now()
    last_24h = now - timedelta(hours=24)

    # Статистика
    total_systems = TargetSystem.objects.filter(is_active=True).count()
    new_systems = TargetSystem.objects.filter(created_at__gte=last_24h).count()
    total_backups = BackupOperation.objects.count()
    
    # Уникальные хосты (серверы), с которых делали бэкапы
    total_hosts = BackupOperation.objects.values('hostname').distinct().count()

    # Статус за последние 24 часа
    ops_24h = BackupOperation.objects.filter(started_at__gte=last_24h)
    success_24h = ops_24h.filter(status='success').count()
    in_progress_24h = ops_24h.filter(status='in_progress').count()
    error_24h = ops_24h.filter(status='error').count()

    # Последние операции
    recent_backups = BackupOperation.objects.select_related(
        'backup_configuration_version__backup_configuration__target_system_version__target_system'
    ).order_by('-started_at')[:10]

    # Данные по системам
    systems = TargetSystem.objects.filter(is_active=True).select_related('system_type')
    systems_data = []
    for sys in systems:
        last_op = BackupOperation.objects.filter(
            backup_configuration_version__backup_configuration__target_system_version__target_system=sys
        ).order_by('-started_at').first()
        
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


def operations_list(request):
    """GET /operations/ - List of all backup operations"""
    operations = BackupOperation.objects.select_related(
        'backup_configuration_version__backup_configuration__target_system_version__target_system'
    ).order_by('-started_at')
    return render(request, 'operations/operation_list.html', {'operations': operations})

def operation_detail(request, pk):
    """GET /operations/<pk>/ - Detail of a specific backup operation"""
    operation = get_object_or_404(BackupOperation, pk=pk)
    return render(request, 'operations/operation_detail.html', {'operation': operation})
=======
>>>>>>> a67310cbd931e2983732da421f7c49ad20bc40e0
