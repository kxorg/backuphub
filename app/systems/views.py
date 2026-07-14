from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.shortcuts import redirect
from django.db.models import Prefetch



from .models import TargetSystem, TargetSystemVersion
from .forms import TargetSystemForm

class TargetSystemListView(LoginRequiredMixin, ListView):
    def get_queryset(self):
        return TargetSystem.objects.select_related(
            'system_type', 'environment'
        ).prefetch_related(
            Prefetch(
                'versions',
                queryset=TargetSystemVersion.objects.filter(is_current=True),
                to_attr='current_version_list'
            )
        ).filter(is_active=True).order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for system in context['target_systems']:
            system.current_version_data = system.current_version_list[0] if system.current_version_list else None
        return context


class TargetSystemDetailView(LoginRequiredMixin, DetailView):
    """GET /target-systems/<pk>/"""
    model = TargetSystem
    template_name = 'target_systems/targetsystem_detail.html'
    context_object_name = 'target_system'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_version'] = self.object.current_version
        return context


class TargetSystemCreateView(LoginRequiredMixin, CreateView):
    """GET /target-systems/create/"""
    model = TargetSystem
    form_class = TargetSystemForm
    template_name = 'target_systems/targetsystem_form.html'
    success_url = reverse_lazy('target_system_list')

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.created_by = self.request.user.username
        self.object.save()

        TargetSystemVersion.objects.create(
            target_system=self.object,
            version_number=1,
            owner=form.cleaned_data.get('owner'),
            administrator=form.cleaned_data.get('administrator'),
            is_current=True,
            valid_from=timezone.now(),
            created_by=self.request.user.username,
        )

        messages.success(self.request, f'Target System "{self.object.name}" created successfully.')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Target System'
        context['action'] = 'create'
        return context


class TargetSystemUpdateView(LoginRequiredMixin, UpdateView):
    """GET /target-systems/<pk>/edit/"""
    model = TargetSystem
    form_class = TargetSystemForm
    template_name = 'target_systems/targetsystem_form.html'
    success_url = reverse_lazy('target_system_list')

    @transaction.atomic
    def form_valid(self, form):
        current_version = self.object.current_version
        versioned_fields_changed = False
        
        if current_version:
            if (form.cleaned_data.get('owner') != current_version.owner or
                form.cleaned_data.get('administrator') != current_version.administrator):
                versioned_fields_changed = True

        self.object = form.save(commit=False)
        self.object.updated_by = self.request.user.username
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
                created_by=self.request.user.username,
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


class TargetSystemDeleteView(LoginRequiredMixin, DeleteView):
    """POST /target-systems/<pk>/delete/"""
    model = TargetSystem
    success_url = reverse_lazy('target_system_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.updated_by = request.user.username
        self.object.save()
        messages.success(request, f'Target System deactivated.')
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        return redirect('target_system_list')


class TargetSystemHistoryView(LoginRequiredMixin, DetailView):
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


class TargetSystemVersionDetailView(LoginRequiredMixin, DetailView):
    """GET /target-systems/<pk>/history/<version_pk>/"""
    model = TargetSystemVersion
    template_name = 'target_systems/targetsystem_version_detail.html'
    context_object_name = 'version'
    pk_url_kwarg = 'version_pk'

    def get_queryset(self):
        return TargetSystemVersion.objects.filter(
            target_system_id=self.kwargs['pk']
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target_system'] = self.object.target_system
        context['is_readonly'] = True
        return context
