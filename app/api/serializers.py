from rest_framework import serializers
from django.utils import timezone
from core.models import (
    TargetSystem,
    TargetSystemVersion,
    BackupConfiguration,
    BackupConfigurationVersion,
    BackupOperation,
)

# ==========================================
# STATUS MAPPING
# ==========================================
API_TO_DB_STATUS = {
    'RUNNING': 'in_progress',
    'SUCCESS': 'success',
    'FAILED': 'error',
}
DB_TO_API_STATUS = {v: k for k, v in API_TO_DB_STATUS.items()}


# ==========================================
# CREATE SERIALIZER
# ==========================================
class BackupOperationCreateSerializer(serializers.Serializer):
    """
    POST /api/backup-operations/
    Обязательное: backup_configuration_id.
    Опциональные: hostname, ip_address.
    """
    backup_configuration_id = serializers.IntegerField(
        help_text='ID of the backup configuration (required)'
    )
    hostname = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text='Hostname of the server'
    )
    ip_address = serializers.IPAddressField(
        required=False,
        allow_null=True,
        help_text='IP address'
    )

    def validate_backup_configuration_id(self, value):
        """Проверяет существование активной конфигурации."""
        try:
            config = BackupConfiguration.objects.get(id=value, is_active=True)
        except BackupConfiguration.DoesNotExist:
            raise serializers.ValidationError('Active backup configuration not found.')
        return config

    def create(self, validated_data):
        """Создаёт операцию, привязывая к ТЕКУЩЕЙ версии конфигурации."""
        config = validated_data['backup_configuration_id']
        
        # Бэкенд сам ищет актуальную версию
        current_version = config.versions.filter(is_current=True).first()
        if not current_version:
            raise serializers.ValidationError(
                f"Configuration '{config.name}' has no current version."
            )
        
        return BackupOperation.objects.create(
            backup_configuration_version=current_version,
            hostname=validated_data.get('hostname', ''),
            ip_address=validated_data.get('ip_address'),
            status='in_progress',
            # started_at установится автоматически через auto_now_add
            # external_job_id игнорируется
        )


# ==========================================
# UPDATE SERIALIZER
# ==========================================
class BackupOperationUpdateSerializer(serializers.Serializer):
    """
    PATCH /api/backup-operations/{id}/
    Все поля строго в snake_case. 
    finished_at обрабатывается во view, hostname/ip_address здесь не нужны.
    """
    status = serializers.ChoiceField(
        choices=['RUNNING', 'SUCCESS', 'FAILED'],  
        help_text='Backup execution status'
    )
    size_bytes = serializers.IntegerField(
        required=False, 
        min_value=0, 
        help_text='Backup size in bytes'
    )
    storage_type = serializers.CharField(
        max_length=50, 
        required=False, 
        allow_blank=True, 
        help_text='Storage type'
    )
    storage_path = serializers.CharField(
        max_length=500, 
        required=False, 
        allow_blank=True, 
        help_text='Path to backup file'
    )
    metadata = serializers.JSONField(
        required=False, 
        help_text='Technical data in JSON format'
    )
    error_message = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text='Required only if status=FAILED'
    )

    def validate(self, attrs):
        instance = self.instance
        
        # Запрещаем изменять уже завершённые операции
        if instance.status in ['success', 'error']:
            raise serializers.ValidationError("Cannot modify completed operation.")
        
        # Если статус FAILED, сообщение об ошибке обязательно
        if attrs.get('status') == 'FAILED' and not attrs.get('error_message'):
            raise serializers.ValidationError({
                'error_message': 'This field is required for FAILED status.'
            })
        
        return attrs

    def update(self, instance, validated_data):
        if 'status' in validated_data:
            status_map = {
                'RUNNING': 'in_progress', 
                'SUCCESS': 'success', 
                'FAILED': 'error'
            }
            instance.status = status_map[validated_data['status']]
        
        if 'size_bytes' in validated_data:
            instance.size_bytes = validated_data['size_bytes']
            
        if 'storage_type' in validated_data:
            instance.storage_type = validated_data['storage_type']
            
        if 'storage_path' in validated_data:
            instance.storage_path = validated_data['storage_path']
            
        if 'error_message' in validated_data:
            instance.error_message = validated_data['error_message']
            
        if 'metadata' in validated_data:
            instance.metadata = validated_data['metadata']
        
        instance.save()
        return instance


# ==========================================
# READ SERIALIZER
# ==========================================
class BackupOperationReadSerializer(serializers.ModelSerializer):
    """GET /api/backup-operations/"""
    backup_configuration_id = serializers.IntegerField(
        source='backup_configuration_version.backup_configuration.id',
        read_only=True
    )
    backup_configuration_version_id = serializers.IntegerField(
        source='backup_configuration_version.id',
        read_only=True
    )

    class Meta:
        model = BackupOperation
        fields = [
            'id',
            'backup_configuration_id',
            'backup_configuration_version_id',
            'hostname',
            'ip_address',
            'status',
            'started_at',
            'finished_at',
            'size_bytes',
            'storage_type',
            'storage_path',
            'metadata',
            'error_message',
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['status'] = DB_TO_API_STATUS.get(instance.status, instance.status)
        return data