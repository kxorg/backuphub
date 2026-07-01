from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import TargetSystem, Host, BackupJob
from .serializers import (
    TargetSystemSerializer, 
    HostSerializer, 
    BackupJobSerializer,
    BackupCreateSerializer,
    BackupUpdateSerializer
)


# ============================================
# ЭНДПОИНТ 1: Создание записи о бэкапе
# POST /api/v1/backups/
# ============================================
class BackupCreateView(APIView):
    def post(self, request):
        serializer = BackupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        host = Host.objects.get(id=serializer.validated_data['host_id'])

        backup_job = BackupJob.objects.create(
            host=host,
            type=serializer.validated_data.get('type', 'full'),
            status='running'
        )

        response_serializer = BackupJobSerializer(backup_job)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


# ============================================
# ЭНДПОИНТ 2: Изменение записи о бэкапе
# PATCH /api/v1/backups/{id}/
# ============================================
class BackupUpdateView(APIView):
    def patch(self, request, backup_id):
        backup_job = get_object_or_404(BackupJob, id=backup_id)

        serializer = BackupUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Обновляем переданные поля
        for attr, value in serializer.validated_data.items():
            setattr(backup_job, attr, value)

        # Если статус стал терминальным и время завершения не стоит - ставим его
        if backup_job.status in ['success', 'failed', 'warning'] and not backup_job.finished_at:
            backup_job.finished_at = timezone.now()

        backup_job.save()

        response_serializer = BackupJobSerializer(backup_job)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


# ============================================
# CRUD ViewSets (Готовые вьюхи для команды)
# ============================================

class TargetSystemViewSet(ModelViewSet):
    queryset = TargetSystem.objects.all()
    serializer_class = TargetSystemSerializer

class HostViewSet(ModelViewSet):
    queryset = Host.objects.select_related('target_system').all()
    serializer_class = HostSerializer

class BackupJobViewSet(ModelViewSet):
    queryset = BackupJob.objects.select_related('host', 'host__target_system').all()
    serializer_class = BackupJobSerializer
    # Разрешаем только чтение через этот ViewSet, 
    # так как создание/изменение идет через специальные эндпоинты выше
    http_method_names = ['get', 'head', 'options'] 