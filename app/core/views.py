from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import TargetSystem, Host, Backup, SystemType
from .serializers import BackupSerializer, BackupCreateSerializer, BackupUpdateSerializer


# ==========================================
# WEB VIEWS
# ==========================================

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


# --- TargetSystem CRUD ---
@login_required
def system_settings(request):
    systems_list = TargetSystem.objects.select_related('system_type').all().order_by('-created_at')
    paginator = Paginator(systems_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "target_system/list.html", {"page_obj": page_obj})

@login_required
def system_detail(request, pk):
    """Страница деталей системы с последними бэкапами."""
    system = get_object_or_404(TargetSystem, id=pk)
    recent_backups = system.backups.select_related('host').order_by('-start_time')[:5]
    return render(request, "target_system/detail.html", {
        "system": system,
        "recent_backups": recent_backups
    })

@login_required
def system_create(request):
    """Создание новой системы с возможностью добавления нового типа."""
    if request.method == "POST":
        name = request.POST.get('name')
        system_type_action = request.POST.get('system_type_action')
        
        if system_type_action == 'new':
            new_type_name = request.POST.get('new_system_type')
            if new_type_name:
                system_type, created = SystemType.objects.get_or_create(
                    name=new_type_name.strip(),
                    defaults={'description': f'Тип {new_type_name}'}
                )
            else:
                system_types = SystemType.objects.all()
                return render(request, "target_system/form.html", {
                    "system_types": system_types,
                    "error": "Укажите название нового типа системы"
                })
        else:
            system_type_id = request.POST.get('system_type')
            system_type = get_object_or_404(SystemType, id=system_type_id)
        
        TargetSystem.objects.create(name=name, system_type=system_type)
        return redirect('target_system_list')
    
    system_types = SystemType.objects.all()
    return render(request, "target_system/form.html", {"system_types": system_types})


@login_required
def system_edit(request, pk):
    """Редактирование системы."""
    system = get_object_or_404(TargetSystem, id=pk)
    if request.method == "POST":
        system.name = request.POST.get('name')
        system_type_action = request.POST.get('system_type_action')
        
        if system_type_action == 'new':
            new_type_name = request.POST.get('new_system_type')
            if new_type_name:
                system_type, created = SystemType.objects.get_or_create(
                    name=new_type_name.strip(),
                    defaults={'description': f'Тип {new_type_name}'}
                )
            else:
                system_types = SystemType.objects.all()
                return render(request, "target_system/form.html", {
                    "system": system,
                    "system_types": system_types,
                    "error": "Укажите название нового типа системы"
                })
        else:
            system_type_id = request.POST.get('system_type')
            system_type = get_object_or_404(SystemType, id=system_type_id)
        
        system.system_type = system_type
        system.save()
        return redirect('target_system_list')
    
    system_types = SystemType.objects.all()
    return render(request, "target_system/form.html", {
        "system": system,
        "system_types": system_types
    })


@login_required
def system_delete(request, pk):
    system = get_object_or_404(TargetSystem, id=pk)
    if request.method == "POST":
        system.delete()
        return redirect('target_system_list')
    return render(request, "target_system/confirm_delete.html", {"system": system})


# --- Host CRUD ---
@login_required
def servers(request):
    hosts_list = Host.objects.select_related('target_system').all().order_by('hostname')
    paginator = Paginator(hosts_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "host/list.html", {"page_obj": page_obj})


@login_required
def host_detail(request, pk):
    """Страница деталей хоста с последними бэкапами."""
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
    if request.method == "POST":
        host.hostname = request.POST.get('hostname')
        host.ip_address = request.POST.get('ip_address')
        system_id = request.POST.get('target_system')
        host.target_system = get_object_or_404(TargetSystem, id=system_id)
        host.save()
        return redirect('host_list')
    return render(request, "host/form.html", {"host": host, "systems": systems})


@login_required
def host_delete(request, pk):
    host = get_object_or_404(Host, id=pk)
    if request.method == "POST":
        host.delete()
        return redirect('host_list')
    return render(request, "host/confirm_delete.html", {"host": host})


# ==========================================
# API VIEWS (Only Backups)
# ==========================================

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

    def get_client_ip(self, request):
        """Определяет IP-адрес клиента из HTTP-запроса."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @swagger_auto_schema(
        operation_summary='List all backups',
        operation_description='Returns a list of all backup operations',
        tags=['Backups'],
        responses={200: openapi.Response('List of backups', BackupSerializer(many=True))},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Retrieve backup details',
        operation_description='Returns details of a specific backup operation',
        tags=['Backups'],
        responses={200: openapi.Response('Backup details', BackupSerializer), 404: 'Backup not found'},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['api_key', 'hostname'],
            properties={
                'api_key': openapi.Schema(type=openapi.TYPE_STRING, format='uuid', description='API key of the target system'),
                'hostname': openapi.Schema(type=openapi.TYPE_STRING, description='Hostname of the server'),
                'ip_address': openapi.Schema(type=openapi.TYPE_STRING, format='ipv4', description='IP address (optional, auto-detected if not provided)'),
                'storage': openapi.Schema(type=openapi.TYPE_STRING, description='Path to the backup storage (optional)'),
            }
        ),
        responses={201: openapi.Response('Backup created', BackupSerializer), 400: 'Validation error', 404: 'Target system not found'},
        operation_summary='Create backup record',
        operation_description=(
            'Creates a new backup record with status in_progress. '
            'IP address is auto-detected from request if not provided. '
            'If host exists but IP changed, IP will be updated.'
        ),
        tags=['Backups'],
    )
    def create(self, request, *args, **kwargs):
        serializer = BackupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        api_key = serializer.validated_data['api_key']
        hostname = serializer.validated_data['hostname']
        
        # Комбинированная логика IP: берем из запроса или определяем автоматически
        ip_address = serializer.validated_data.get('ip_address')
        if not ip_address:
            ip_address = self.get_client_ip(request)

        target_system = TargetSystem.objects.get(api_key=api_key)

        host, created = Host.objects.get_or_create(
            hostname=hostname,
            target_system=target_system,
            defaults={'ip_address': ip_address}
        )
        
        # Обновляем IP, если хост уже существует и IP изменился
        if not created and host.ip_address != ip_address:
            host.ip_address = ip_address
            host.save()

        backup = Backup.objects.create(
            host=host,
            target_system=target_system,
            status='in_progress',
            start_time=timezone.now(),
            storage=serializer.validated_data.get('storage', '')
        )

        response_serializer = BackupSerializer(backup)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING, enum=['in_progress', 'success', 'error'], description='Backup execution status'),
                'backup_size': openapi.Schema(type=openapi.TYPE_INTEGER, description='Backup size in bytes'),
                'storage': openapi.Schema(type=openapi.TYPE_STRING, description='Path to the backup file'),
                'meta_data': openapi.Schema(type=openapi.TYPE_OBJECT, description='Technical data in JSON format'),
                'error_message': openapi.Schema(type=openapi.TYPE_STRING, description='Error message (if status is error)'),
            }
        ),
        responses={200: openapi.Response('Backup updated', BackupSerializer), 404: 'Backup not found'},
        operation_summary='Update backup status',
        operation_description='Updates backup status and metadata after completion. end_time is set automatically.',
        tags=['Backups'],
    )
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