from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.core.paginator import Paginator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import TargetSystem, Host, Backup
from .serializers import BackupSerializer, BackupCreateSerializer, BackupUpdateSerializer


# WEB VIEWS 

def index(request):
    return render(request, "index.html")

def api(request):
    return render(request, "api.html")


# (Backups) 
def backups_list(request):
    backup_list = Backup.objects.select_related('host', 'target_system').order_by('-start_time')
    
    # Pagination: 10 backups per page
    paginator = Paginator(backup_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "backup/list.html", {"page_obj": page_obj})


def backup_detail(request, pk):
    backup = get_object_or_404(Backup.objects.select_related('host', 'target_system'), id=pk)
    return render(request, "backup/detail.html", {"backup": backup})


# (TargetSystem CRUD) 
def system_settings(request):
    # Displaying a list of systems with pagination (5 per page)
    systems_list = TargetSystem.objects.all().order_by('-created_at')
    paginator = Paginator(systems_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "target_system/list.html", {"page_obj": page_obj})


def system_create(request):
    if request.method == "POST":
        name = request.POST.get('name')
        system_type = request.POST.get('system_type')
        TargetSystem.objects.create(name=name, system_type=system_type)
        return redirect('target_system_list')  # Изменено
    return render(request, "target_system/form.html")


def system_edit(request, pk):
    system = get_object_or_404(TargetSystem, id=pk)
    if request.method == "POST":
        system.name = request.POST.get('name')
        system.system_type = request.POST.get('system_type')
        system.save()
        return redirect('target_system_list')  # Изменено
    return render(request, "target_system/form.html", {"system": system})


def system_delete(request, pk):
    system = get_object_or_404(TargetSystem, id=pk)
    if request.method == "POST":
        system.delete()
        return redirect('target_system_list')  # Изменено
    return render(request, "target_system/confirm_delete.html", {"system": system})


# (Host CRUD) 
def servers(request):
    hosts_list = Host.objects.select_related('target_system').all().order_by('hostname')
    paginator = Paginator(hosts_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "host/list.html", {"page_obj": page_obj})


def host_create(request):
    systems = TargetSystem.objects.all()
    if request.method == "POST":
        hostname = request.POST.get('hostname')
        ip_address = request.POST.get('ip_address')
        system_id = request.POST.get('target_system')
        target_system = get_object_or_404(TargetSystem, id=system_id)
        Host.objects.create(hostname=hostname, ip_address=ip_address, target_system=target_system)
        return redirect('host_list')  # Изменено
    return render(request, "host/form.html", {"systems": systems})


def host_edit(request, pk):
    host = get_object_or_404(Host, id=pk)
    systems = TargetSystem.objects.all()
    if request.method == "POST":
        host.hostname = request.POST.get('hostname')
        host.ip_address = request.POST.get('ip_address')
        system_id = request.POST.get('target_system')
        host.target_system = get_object_or_404(TargetSystem, id=system_id)
        host.save()
        return redirect('host_list')  # Изменено
    return render(request, "host/form.html", {"host": host, "systems": systems})


def host_delete(request, pk):
    host = get_object_or_404(Host, id=pk)
    if request.method == "POST":
        host.delete()
        return redirect('host_list')  # Изменено
    return render(request, "host/confirm_delete.html", {"host": host})


# API VIEWS (только Backups)


class BackupViewSet(
    ListModelMixin,
    CreateModelMixin,
    RetrieveModelMixin,
    GenericViewSet
):
    """
    Backup API operations.
    """
    queryset = Backup.objects.select_related('host', 'target_system').all()
    serializer_class = BackupSerializer

    @swagger_auto_schema(
        operation_summary='List all backups',
        operation_description='Returns a list of all backup operations',
        tags=['Backups'],
        responses={
            200: openapi.Response('List of backups', BackupSerializer(many=True)),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Retrieve backup details',
        operation_description='Returns details of a specific backup operation',
        tags=['Backups'],
        responses={
            200: openapi.Response('Backup details', BackupSerializer),
            404: 'Backup not found',
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['api_key', 'hostname'],
            properties={
                'api_key': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='uuid',
                    description='API key of the target system'
                ),
                'hostname': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Hostname of the server'
                ),
                'storage': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Path to the backup storage'
                ),
            }
        ),
        responses={
            201: openapi.Response('Backup created', BackupSerializer),
            400: 'Validation error',
            404: 'Target system or host not found',
        },
        operation_summary='Create backup record',
        operation_description=(
            'Creates a new backup record with status in_progress. '
            'Uses api_key and hostname for identification. '
            'If host does not exist, it will be created automatically.'
        ),
        tags=['Backups'],
    )
    def create(self, request, *args, **kwargs):
        serializer = BackupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

<<<<<<< HEAD
        api_key = serializer.validated_data['api_key']
        hostname = serializer.validated_data['hostname']
=======
        host = Host.objects.get(id=serializer.validated_data['host_id'])
        
        # If target_system is not specified, we take it from the host
        target_system = serializer.validated_data.get('target_system_id')
        if target_system:
            target_system = TargetSystem.objects.get(id=target_system)
        else:
            target_system = host.target_system
>>>>>>> DEV

        # Находим систему по API-ключу
        try:
            target_system = TargetSystem.objects.get(api_key=api_key)
        except TargetSystem.DoesNotExist:
            return Response(
                {'error': f'Target system with api_key {api_key} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Находим или создаём хост
        host, created = Host.objects.get_or_create(
            hostname=hostname,
            target_system=target_system,
            defaults={'ip_address': '127.0.0.1'}  # Валидный IP по умолчанию
        )

        # Создаём бэкап
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
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['in_progress', 'success', 'error'],
                    description='Backup execution status'
                ),
                'backup_size': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Backup size in bytes'
                ),
                'storage': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Path to the backup file'
                ),
                'meta_data': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description='Technical data in JSON format'
                ),
                'error_message': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Error message (if status is error)'
                ),
            }
        ),
        responses={
            200: openapi.Response('Backup updated', BackupSerializer),
            404: 'Backup not found',
        },
        operation_summary='Update backup status',
        operation_description=(
            'Updates backup status and metadata after completion. '
            'end_time is set automatically when status is success or error.'
        ),
        tags=['Backups'],
    )
    def partial_update(self, request, *args, **kwargs):
        backup = self.get_object()

        serializer = BackupUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Updating the transferred fields
        for attr, value in serializer.validated_data.items():
            if value is not None:  # Update only if the field is passed
                setattr(backup, attr, value)

<<<<<<< HEAD
        # Автоматически устанавливаем end_time
=======
        # If the status has changed to final and the completion time is not set
>>>>>>> DEV
        if backup.status in ['success', 'error'] and not backup.end_time:
            backup.end_time = timezone.now()

        backup.save()

        response_serializer = BackupSerializer(backup)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
