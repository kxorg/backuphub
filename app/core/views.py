from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import TargetSystem, Host, Backup
from .serializers import (
    TargetSystemSerializer,
    HostSerializer,
    BackupSerializer,
    BackupCreateSerializer,
    BackupUpdateSerializer
)

def index(request):
    return render(request, "index.html")

def settings(request):
    return render(request, "settings.html")

def servers(request):
    return render(request, "servers.html")

def magazineHub(request):
    return render(request, "magazineHub.html")

def api(request):
    return render(request, "api.html")



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

