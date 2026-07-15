from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.shortcuts import redirect
from django.db.models import Prefetch


from .models import BackupConfiguration, BackupConfigurationVersion
from .forms import BackupConfigurationForm


class BackupConfigurationListView(LoginRequiredMixin, ListView):
    """GET /backup-configuration/"""
    model = BackupConfiguration
    template_name = 'backup_configurations/backupconfiguration_list.html'
    context_object_name = 'backup_configurations'
    paginate_by = 20

    def get_queryset(self):
        return BackupConfiguration.objects.select_related(
            'target_system_version',
            'target_system_version__target_system'
        ).prefetch_related(
            Prefetch(
                'versions',
                queryset=BackupConfigurationVersion.objects.filter(is_current=True),
                to_attr='current_version_list'
            )
        ).filter(is_active=True).order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for config in context['backup_configurations']:
            config.current_version_data = config.current_version_list[0] if config.current_version_list else None
        return context


class BackupConfigurationDetailView(LoginRequiredMixin, DetailView):
    """GET /backup-configuration/<pk>/"""
    model = BackupConfiguration
    template_name = 'backup_configurations/backupconfiguration_detail.html'
    context_object_name = 'backup_configuration'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_version'] = self.object.current_version
        
        # Добавлено для cURL-запросов
        target_system = self.object.target_system_version.target_system
        context['api_key'] = str(target_system.api_key)
        context['config_id'] = self.object.id
        
        return context


class BackupConfigurationCreateView(LoginRequiredMixin, CreateView):
    """GET /backup-configuration/create/"""
    model = BackupConfiguration
    form_class = BackupConfigurationForm
    template_name = 'backup_configurations/backupconfiguration_form.html'
    def get_success_url(self):
        return reverse_lazy('backup_configuration_detail', kwargs={'pk': self.object.pk})

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.created_by = self.request.user.username
        self.object.save()

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
            created_by=self.request.user.username,
        )

        messages.success(self.request, f'Backup Configuration "{self.object.name}" created successfully.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Backup Configuration'
        context['action'] = 'create'
        return context


class BackupConfigurationUpdateView(LoginRequiredMixin, UpdateView):
    """GET /backup-configuration/<pk>/edit/"""
    model = BackupConfiguration
    form_class = BackupConfigurationForm
    template_name = 'backup_configurations/backupconfiguration_form.html'
    success_url = reverse_lazy('backup_configuration_list')

    @transaction.atomic
    def form_valid(self, form):
        current_version = self.object.current_version
        versioned_fields_changed = False

        if current_version:
            versioned_fields = [
                'backup_tool', 'backup_mode', 'schedule_cron',
                'retention_days', 'rpo_minutes', 'rto_minutes',
                'storage_type', 'storage_path',
                'verify_after_backup', 'immutable_storage'
            ]

            versioned_fields_changed = False
            for field in versioned_fields:
                form_value = form.cleaned_data.get(field)
                current_value = getattr(current_version, field)

                if form_value in (None, ''):
                    form_value = None
                if current_value in (None, ''):
                    current_value = None

                if form_value != current_value:
                    versioned_fields_changed = True
                    break

        self.object = form.save(commit=False)
        self.object.updated_by = self.request.user.username
        self.object.save()

        if versioned_fields_changed:
            current_version.is_current = False
            current_version.valid_to = timezone.now()
            current_version.save()

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
                created_by=self.request.user.username,
            )
            messages.success(self.request, f'Updated. New version created.')
        else:
            messages.success(self.request, f'Backup Configuration updated.')

        return redirect(self.get_success_url())


class BackupConfigurationDeleteView(LoginRequiredMixin, DeleteView):
    """POST /backup-configuration/<pk>/delete/"""
    model = BackupConfiguration
    success_url = reverse_lazy('backup_configuration_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.updated_by = request.user.username
        self.object.save()
        messages.success(request, f'Backup Configuration deactivated.')
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        return redirect('backup_configuration_list')


class BackupConfigurationHistoryView(LoginRequiredMixin, DetailView):
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


class BackupConfigurationVersionDetailView(LoginRequiredMixin, DetailView):
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

