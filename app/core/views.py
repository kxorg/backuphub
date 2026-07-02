from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from .models import TargetSystem, Host, Backup
from .models import TargetSystem, Host, Backup
from .serializers import (
    TargetSystemSerializer,
    HostSerializer,
    BackupSerializer,
    BackupCreateSerializer,
    BackupUpdateSerializer
)

# (MagazineHub) 
def magazineHub(request):
    backup_list = Backup.objects.select_related('host', 'target_system').order_by('-start_time')
    
    # Пагинация: по 10 бэкапов на страницу
    paginator = Paginator(backup_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "magazineHub.html", {"page_obj": page_obj})

def backup_detail(request, pk):
    backup = get_object_or_404(Backup.objects.select_related('host', 'target_system'), id=pk)
    return render(request, "backup_detail.html", {"backup": backup})


# (System Settings CRUD) 
def settings(request):
    # Вывод списка систем с пагинацией (по 5 на страницу)
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


# (Servers CRUD) 
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


def index(request): return render(request, "index.html")
def api(request): return render(request, "api.html")


class BackupCreateView(APIView):
    """
    POST /api/v1/backups/ - Регистрация начала резервного копирования
    """
    def post(self, request):
        serializer = BackupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        host = Host.objects.get(id=serializer.validated_data['host_id'])
        
        # Если target_system не указан, берем из хоста
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


class BackupUpdateView(APIView):
    """
    PATCH /api/v1/backups/{id}/ - Обновление статуса и метаданных бэкапа
    """
    def patch(self, request, backup_id):
        backup = get_object_or_404(Backup, id=backup_id)

        serializer = BackupUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Обновляем переданные поля
        for attr, value in serializer.validated_data.items():
            if value is not None:  # Обновляем только если поле передано
                setattr(backup, attr, value)

        # Если статус изменился на завершающий и время завершения не стоит
        if backup.status in ['success', 'error'] and not backup.end_time:
            backup.end_time = timezone.now()

        backup.save()

        response_serializer = BackupSerializer(backup)
        return Response(response_serializer.data, status=status.HTTP_200_OK)



class TargetSystemViewSet(ModelViewSet):
    """
    CRUD операции для TargetSystem.
    GET/POST /api/v1/systems/
    GET/PUT/PATCH/DELETE /api/v1/systems/{id}/
    """
    queryset = TargetSystem.objects.all()
    serializer_class = TargetSystemSerializer


class HostViewSet(ModelViewSet):
    """
    CRUD операции для Host.
    GET/POST /api/v1/hosts/
    GET/PUT/PATCH/DELETE /api/v1/hosts/{id}/
    """
    queryset = Host.objects.select_related('target_system').all()
    serializer_class = HostSerializer


class BackupViewSet(ModelViewSet):
    """
    CRUD операции для Backup (только чтение).
    GET /api/v1/backups-list/
    GET /api/v1/backups-list/{id}/
    """
    queryset = Backup.objects.select_related('host', 'target_system').all()
    serializer_class = BackupSerializer
    http_method_names = ['get', 'head', 'options']  # Только чтение

