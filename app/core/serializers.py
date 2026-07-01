from rest_framework import serializers
from .models import TargetSystem, Host, Backup


# ============================================
# Сериализаторы для CRUD (для команды)
# ============================================

class TargetSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetSystem
        fields = ['id', 'name', 'system_type', 'created_at']


class HostSerializer(serializers.ModelSerializer):
    system_name = serializers.CharField(source='target_system.name', read_only=True)

    class Meta:
        model = Host
        fields = ['id', 'hostname', 'ip_address', 'target_system', 'system_name', 'created_at']


class BackupJobSerializer(serializers.ModelSerializer):
    hostname = serializers.CharField(source='host.hostname', read_only=True)
    system_name = serializers.CharField(source='host.target_system.name', read_only=True)

    class Meta:
        model = Backup
        fields = [
            'id', 'host', 'hostname', 'system_name', 
            'started_at', 'finished_at', 'type', 'status', 'meta_data'
        ]
        read_only_fields = ['id', 'started_at']


# ============================================
# Сериализаторы для специфичных эндпоинтов API
# ============================================

class BackupCreateSerializer(serializers.Serializer):
    """Валидация данных для создания записи о бэкапе."""
    host_id = serializers.UUIDField(help_text="ID хоста, на котором запускается бэкап")
    type = serializers.CharField(max_length=50, default='full', required=False)

    def validate_host_id(self, value):
        if not Host.objects.filter(id=value).exists():
            raise serializers.ValidationError("Хост с указанным ID не найден в базе данных.")
        return value


class BackupUpdateSerializer(serializers.Serializer):
    """Валидация данных для обновления записи о бэкапе."""
    status = serializers.ChoiceField(
        choices=['running', 'success', 'failed', 'warning'],
        required=False
    )
    meta_data = serializers.JSONField(required=False, help_text="Технические данные в формате JSON")