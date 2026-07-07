from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.core.paginator import Paginator

from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated

from .models import TargetSystem, Host, Backup
from .serializers import BackupSerializer, BackupCreateSerializer, BackupUpdateSerializer


# WEB VIEWS

@login_required
def index(request):
    return render(request, "index.html")

@login_required
def api(request):
    return render(request, "api.html")


# (Backups) 
@login_required
def backups_list(request):
    backup_list = Backup.objects.select_related('host', 'target_system').order_by('-start_time')

    paginator = Paginator(backup_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "backup/list.html", {"page_obj": page_obj})

@login_required
def backup_detail(request, pk):
    backup = get_object_or_404(Backup.objects.select_related('host', 'target_system'), id=pk)
    return render(request, "backup/detail.html", {"backup": backup})


# TargetSystem CRUD
@login_required
def system_settings(request):
    systems_list = TargetSystem.objects.all().order_by('-created_at')
    paginator = Paginator(systems_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "target_system/list.html", {"page_obj": page_obj})


@login_required
def system_detail(request, pk):
    system = get_object_or_404(TargetSystem, id=pk)
    recent_backups = system.backups.select_related('host').order_by('-start_time')[:5]
    return render(request, "target_system/detail.html", {
        "system": system,
        "recent_backups": recent_backups
    })

@login_required
def system_create(request):
    if request.method == "POST":
        name = request.POST.get('name')
        system_type = request.POST.get('system_type')

        if not name:
            return render(request, "target_system/form.html", {
                'error': 'Name is required'
            })

        TargetSystem.objects.create(name=name, system_type=system_type)
        return redirect('target_system_list')
    return render(request, "target_system/form.html")


@login_required
def system_edit(request, pk):
    system = get_object_or_404(TargetSystem, id=pk)
    back_url = request.POST.get('next') or request.GET.get('next')
    if request.method == "POST":
        system.name = request.POST.get('name')
        system.system_type = request.POST.get('system_type')
        system.save()
        if back_url:
            return redirect(back_url)
        return redirect('target_system_list')

    return render(request, "target_system/form.html", {
        "system": system,
        "back_url": back_url
    })


@login_required
def system_delete(request, pk):
    system = get_object_or_404(TargetSystem, id=pk)
    if request.method == "POST":
        system.delete()
        return redirect('target_system_list')
    return render(request, "target_system/confirm_delete.html", {"system": system})




# Host CRUD
@login_required
def servers(request):
    hosts_list = Host.objects.select_related('target_system').all().order_by('hostname')
    paginator = Paginator(hosts_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "host/list.html", {"page_obj": page_obj})


@login_required
def host_detail(request, pk):
    host = get_object_or_404(Host.objects.select_related('target_system'), id=pk)
    recent_backups = host.backups.order_by('-start_time')[:5]
    return render(request, "host/detail.html", {
        "host": host,
        "recent_backups": recent_backups
    })


@login_required
def host_create(request):
    systems = TargetSystem.objects.all()
    if request.method == "POST":
        hostname = request.POST.get('hostname')
        ip_address = request.POST.get('ip_address')
        system_id = request.POST.get('target_system')
        target_system = get_object_or_404(TargetSystem, id=system_id)
        Host.objects.create(hostname=hostname, ip_address=ip_address, target_system=target_system)
        return redirect('host_list')
    return render(request, "host/form.html", {"systems": systems})


@login_required
def host_edit(request, pk):
    host = get_object_or_404(Host, id=pk)
    systems = TargetSystem.objects.all()
    back_url = request.POST.get('next') or request.GET.get('next')
    if request.method == "POST":
        host.hostname = request.POST.get('hostname')
        host.ip_address = request.POST.get('ip_address')
        system_id = request.POST.get('target_system')
        host.target_system = get_object_or_404(TargetSystem, id=system_id)
        host.save()
        if back_url:
            return redirect(back_url)
        return redirect('host_list')

    return render(request, "host/form.html", {
        "host": host,
        "systems": systems,
        "back_url": back_url
    })


@login_required
def host_delete(request, pk):
    host = get_object_or_404(Host, id=pk)
    if request.method == "POST":
        host.delete()
        return redirect('host_list')
    return render(request, "host/confirm_delete.html", {"host": host})


# API VIEWS (Backups only)


class BackupViewSet(
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    GenericViewSet
):
    """
    Backup API operations.
    """
    permission_classes = [IsAuthenticated]

    queryset = Backup.objects.select_related('host', 'target_system').all()
    serializer_class = BackupSerializer

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = BackupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        host = Host.objects.get(id=serializer.validated_data['host_id'])

        target_system = serializer.validated_data.get('target_system_id')
        if target_system:
            target_system = TargetSystem.objects.get(id=target_system)
        else:
            target_system = host.target_system

        backup = Backup.objects.create(
            host=host,
            target_system=target_system,
            status='in_progress',
            start_time=timezone.now(),
            storage=serializer.validated_data.get('storage', '')
        )

        response_serializer = BackupSerializer(backup)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """PATCH /backups/{id}/ - Update backup status"""
        backup = self.get_object()

        serializer = BackupUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for attr, value in serializer.validated_data.items():
            if value is not None:
                setattr(backup, attr, value)

        if backup.status in ['success', 'error'] and not backup.end_time:
            backup.end_time = timezone.now()

        backup.save()

        response_serializer = BackupSerializer(backup)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
