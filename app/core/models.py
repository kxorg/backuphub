import uuid
from django.db import models

class TargetSystem(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    system_type = models.CharField(max_length=50, verbose_name='Тип')
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='API-ключ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        db_table = 'target_system'

    def __str__(self):
        return self.name


class Host(models.Model):
    hostname = models.CharField(max_length=255, verbose_name='Имя хоста')
    ip_address = models.GenericIPAddressField(verbose_name='IP-адрес')
    target_system = models.ForeignKey(
        TargetSystem, 
        on_delete=models.CASCADE, 
        related_name='hosts',
        verbose_name='Наблюдаемая система'
    )

    class Meta:
        db_table = 'host'

    def __str__(self):
        return f"{self.hostname} ({self.ip_address})"


class Backup(models.Model):
    STATUS_CHOICES = [
        ('success', 'Успешно'),
        ('error', 'Ошибка'),
        ('in_progress', 'В процессе'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID операции')
    host = models.ForeignKey(Host, on_delete=models.SET_NULL, null=True, blank=True, related_name='backups', verbose_name='Сервер')
    target_system = models.ForeignKey(TargetSystem, on_delete=models.CASCADE, related_name='backups', verbose_name='Система')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='Статус')
    start_time = models.DateTimeField(verbose_name='Время начала')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='Время завершения')
    backup_size = models.BigIntegerField(null=True, blank=True, verbose_name='Размер (байты)')
    storage = models.CharField(max_length=255, null=True, blank=True, verbose_name='Используемое хранилище')
    
    meta_data = models.JSONField(default=dict, blank=True, verbose_name='Технические данные')
    error_message = models.TextField(null=True, blank=True, verbose_name='Сообщение об ошибке')

    class Meta:
        db_table = 'backup'

    @property
    def duration(self):
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None