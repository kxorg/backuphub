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


def magazineHub(request):
    backup_list = Backup.objects.select_related('host', 'target_system').order_by('-start_time')
    paginator = Paginator(backup_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "magazineHub.html", {"page_obj": page_obj})


def backup_detail(request, pk):
    backup = get_object_or_404(Backup.objects.select_related('host', 'target_system'), id=pk)
    return render(request, "backup_detail.html", {"backup": backup})


def settings(request):
    systems_list = TargetSystem.objects.all().order_by('-created_at')
    paginator = Paginator(systems_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "settings.html", {"page_obj": page_obj})


def system_create(request):
    if request.method == "POST":
        name = request.POST.get('name')
        system_type = request.POST.get('system_type')
        TargetSystem.objects.create(name=name, system_type=system_type)
        return redirect('settings')
    return render(request, "system_form.html")


def system_edit(request, pk):
    system = get_object_or_404(TargetSystem, id=pk)
    if request.method == "POST":
        system.name = request.POST.get('name')
        system.system_type = request.POST.get('system_type')
        system.save()
        return redirect('settings')
    return render(request, "system_form.html", {"system": system})


def system_delete(request, pk):
    system = get_object_or_404(TargetSystem, id=pk)
    if request.method == "POST":
        system.delete()
        return redirect('settings')
    return render(request, "system_confirm_delete.html", {"system": system})


def servers(request):
    hosts_list = Host.objects.select_related('target_system').all().order_by('hostname')
    paginator = Paginator(hosts_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "servers.html", {"page_obj": page_obj})


def host_create(request):
    systems = TargetSystem.objects.all()
    if request.method == "POST":
        hostname = request.POST.get('hostname')
        ip_address = request.POST.get('ip_address')
        system_id = request.POST.get('target_system')
        target_system = get_object_or_404(TargetSystem, id=system_id)
        Host.objects.create(hostname=hostname, ip_address=ip_address, target_system=target_system)
        return redirect('servers')
    return render(request, "host_form.html", {"systems": systems})


def host_edit(request, pk):
    host = get_object_or_404(Host, id=pk)
    systems = TargetSystem.objects.all()
    if request.method == "POST":
        host.hostname = request.POST.get('hostname')
        host.ip_address = request.POST.get('ip_address')
        system_id = request.POST.get('target_system')
        host.target_system = get_object_or_404(TargetSystem, id=system_id)
        host.save()
        return redirect('servers')
    return render(request, "host_form.html", {"host": host, "systems": systems})


def host_delete(request, pk):
    host = get_object_or_404(Host, id=pk)
    if request.method == "POST":
        host.delete()
        return redirect('servers')
    return render(request, "host_confirm_delete.html", {"host": host})


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
            required=['host_id'],
            properties={
                'host_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Host ID'),
                'target_system_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Target system ID (optional)'),
                'storage': openapi.Schema(type=openapi.TYPE_STRING, description='Storage path'),
            }
        ),
        responses={
            201: openapi.Response('Backup created', BackupSerializer),
            400: 'Validation error',
        },
        operation_summary='Create backup record',
        operation_description='Creates a new backup record with status in_progress',
        tags=['Backups'],
    )
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

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['in_progress', 'success', 'error']
                ),
                'end_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                'backup_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                'storage': openapi.Schema(type=openapi.TYPE_STRING),
                'meta_data': openapi.Schema(type=openapi.TYPE_OBJECT),
                'error_message': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: openapi.Response('Backup updated', BackupSerializer),
            404: 'Backup not found',
        },
        operation_summary='Update backup status',
        operation_description='Updates backup status and metadata after completion',
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