from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from .models import SystemType, Environment, BackupTool
from .forms import SystemTypeForm, EnvironmentForm, BackupToolForm

# Create your views here.

class SystemTypeListView(LoginRequiredMixin, ListView):
    model = SystemType
    template_name = 'dictionaries/systemtype_list.html'
    context_object_name = 'system_types'
    paginate_by = 50


class SystemTypeCreateView(LoginRequiredMixin, CreateView):
    model = SystemType
    form_class = SystemTypeForm
    template_name = 'dictionaries/systemtype_form.html'
    success_url = reverse_lazy('system_type_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user.username
        messages.success(self.request, 'System Type created successfully.')
        return super().form_valid(form)


class SystemTypeUpdateView(LoginRequiredMixin, UpdateView):
    model = SystemType
    form_class = SystemTypeForm
    template_name = 'dictionaries/systemtype_form.html'
    success_url = reverse_lazy('system_type_list')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user.username
        messages.success(self.request, 'System Type updated successfully.')
        return super().form_valid(form)


class SystemTypeDeleteView(LoginRequiredMixin, DeleteView):
    model = SystemType
    success_url = reverse_lazy('system_type_list')
    template_name = 'dictionaries/systemtype_confirm_delete.html'

    def form_valid(self, form):
        messages.success(self.request, 'System Type deleted successfully.')
        return super().form_valid(form)





class EnvironmentListView(LoginRequiredMixin, ListView):
    model = Environment
    template_name = 'dictionaries/environment_list.html'
    context_object_name = 'environments'
    paginate_by = 50


class EnvironmentCreateView(LoginRequiredMixin, CreateView):
    model = Environment
    form_class = EnvironmentForm
    template_name = 'dictionaries/environment_form.html'
    success_url = reverse_lazy('environment_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user.username
        messages.success(self.request, 'Environment created successfully.')
        return super().form_valid(form)


class EnvironmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Environment
    form_class = EnvironmentForm
    template_name = 'dictionaries/environment_form.html'
    success_url = reverse_lazy('environment_list')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user.username
        messages.success(self.request, 'Environment updated successfully.')
        return super().form_valid(form)


class EnvironmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Environment
    success_url = reverse_lazy('environment_list')
    template_name = 'dictionaries/environment_confirm_delete.html'

    def form_valid(self, form):
        messages.success(self.request, 'Environment deleted successfully.')
        return super().form_valid(form)


class BackupToolListView(LoginRequiredMixin, ListView):
    model = BackupTool
    template_name = 'dictionaries/backuptool_list.html'
    context_object_name = 'backup_tools'
    paginate_by = 50




class BackupToolCreateView(LoginRequiredMixin, CreateView):
    model = BackupTool
    form_class = BackupToolForm
    template_name = 'dictionaries/backuptool_form.html'
    success_url = reverse_lazy('backup_tool_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user.username
        messages.success(self.request, 'Backup Tool created successfully.')
        return super().form_valid(form)


class BackupToolUpdateView(LoginRequiredMixin, UpdateView):
    model = BackupTool
    form_class = BackupToolForm
    template_name = 'dictionaries/backuptool_form.html'
    success_url = reverse_lazy('backup_tool_list')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user.username
        messages.success(self.request, 'Backup Tool updated successfully.')
        return super().form_valid(form)


class BackupToolDeleteView(LoginRequiredMixin, DeleteView):
    model = BackupTool
    success_url = reverse_lazy('backup_tool_list')
    template_name = 'dictionaries/backuptool_confirm_delete.html'

    def form_valid(self, form):
        messages.success(self.request, 'Backup Tool deleted successfully.')
        return super().form_valid(form)

