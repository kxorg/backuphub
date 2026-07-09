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
# CREATE SERIALIZER (без api_key — он в заголовке)
# ==========================================

class BackupOperationCreateSerializer(serializers.Serializer):
    """
    POST /api/backup-operations/
    API-ключ передаётся через заголовок X-API-Key.
    """
    externalJobId = serializers.CharField(max_length=255)
    hostname = serializers.CharField(max_length=255)
    ipAddress = serializers.IPAddressField(required=False, allow_null=True)
    startedAt = serializers.DateTimeField()
    
    # Опциональный ID конфигурации
    configurationId = serializers.IntegerField(
        required=False,
        help_text='Optional. If not provided, uses the first active configuration of the system.'
    )

    def validate(self, attrs):
        """
        Проверяет конфигурацию через target_system из context.
        target_system устанавливается в view из заголовка X-API-Key.
        """
        target_system = self.context.get('target_system')
        
        if not target_system:
            raise serializers.ValidationError(
                "Target system not specified. Check X-API-Key header."
            )
        
        # Находим ТЕКУЩУЮ версию системы
        current_system_version = target_system.versions.filter(
            is_current=True
        ).first()
        
        if not current_system_version:
            raise serializers.ValidationError(
                "Target system has no current version."
            )
        
        self.context['target_system_version'] = current_system_version
        
        # Находим конфигурацию
        config_id = attrs.get('configurationId')
        
        if config_id:
            try:
                config = BackupConfiguration.objects.get(
                    id=config_id,
                    target_system_version=current_system_version,
                    is_active=True
                )
            except BackupConfiguration.DoesNotExist:
                raise serializers.ValidationError({
                    'configurationId': f"Configuration with id={config_id} not found for this system."
                })
        else:
            config = BackupConfiguration.objects.filter(
                target_system_version=current_system_version,
                is_active=True
            ).first()
            
            if not config:
                raise serializers.ValidationError(
                    "No active backup configuration found for this system."
                )
        
        self.context['backup_configuration'] = config
        
        # Находим ТЕКУЩУЮ версию конфигурации
        current_config_version = config.versions.filter(is_current=True).first()
        
        if not current_config_version:
            raise serializers.ValidationError(
                f"Backup configuration '{config.name}' has no current version."
            )
        
        self.context['backup_configuration_version'] = current_config_version
        
        # Проверяем уникальность externalJobId
        external_job_id = attrs.get('externalJobId')
        if BackupOperation.objects.filter(external_job_id=external_job_id).exists():
            raise serializers.ValidationError({
                'externalJobId': f"Operation with externalJobId='{external_job_id}' already exists."
            })
        
        return attrs

    def create(self, validated_data):
        """Создаёт операцию, привязывая к текущей версии конфигурации."""
        config_version = self.context['backup_configuration_version']
        
        return BackupOperation.objects.create(
            backup_configuration_version=config_version,
            external_job_id=validated_data['externalJobId'],
            hostname=validated_data['hostname'],
            ip_address=validated_data.get('ipAddress'),
            status='in_progress',
            started_at=validated_data['startedAt'],
        )


# ==========================================
# UPDATE SERIALIZER (без изменений)
# ==========================================

class BackupOperationUpdateSerializer(serializers.Serializer):
    """PATCH /api/backup-operations/{id}/"""
    status = serializers.ChoiceField(choices=['SUCCESS', 'FAILED'])
    finishedAt = serializers.DateTimeField(required=False)
    sizeBytes = serializers.IntegerField(required=False, min_value=0)
    storageType = serializers.CharField(max_length=50, required=False, allow_blank=True)
    storagePath = serializers.CharField(max_length=500, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)
    errorMessage = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        instance = self.instance

        if instance.status in ['success', 'error']:
            raise serializers.ValidationError(
                "Cannot modify completed operation."
            )

        if attrs.get('status') == 'FAILED' and not attrs.get('errorMessage'):
            raise serializers.ValidationError({
                'errorMessage': 'This field is required for FAILED status.'
            })

        return attrs

    def update(self, instance, validated_data):
        field_mapping = {
            'finishedAt': 'finished_at',
            'sizeBytes': 'size_bytes',
            'storageType': 'storage_type',
            'storagePath': 'storage_path',
            'errorMessage': 'error_message',
        }

        if 'status' in validated_data:
            instance.status = API_TO_DB_STATUS[validated_data['status']]

        for api_field, db_field in field_mapping.items():
            if api_field in validated_data:
                setattr(instance, db_field, validated_data[api_field])

        if 'metadata' in validated_data:
            instance.metadata = validated_data['metadata']

        instance.save()
        return instance


# ==========================================
# READ SERIALIZER (без изменений)
# ==========================================

class BackupOperationReadSerializer(serializers.ModelSerializer):
    """GET /api/backup-operations/"""
    backupConfigurationId = serializers.IntegerField(
        source='backup_configuration_version.backup_configuration.id',
        read_only=True
    )
    externalJobId = serializers.CharField(source='external_job_id', read_only=True)
    ipAddress = serializers.CharField(source='ip_address', read_only=True, allow_null=True)
    startedAt = serializers.DateTimeField(source='started_at', read_only=True)
    finishedAt = serializers.DateTimeField(source='finished_at', read_only=True, allow_null=True)
    sizeBytes = serializers.BigIntegerField(source='size_bytes', read_only=True, allow_null=True)
    storageType = serializers.CharField(source='storage_type', read_only=True, allow_null=True)
    storagePath = serializers.CharField(source='storage_path', read_only=True, allow_null=True)
    errorMessage = serializers.CharField(source='error_message', read_only=True, allow_null=True)

    class Meta:
        model = BackupOperation
        fields = [
            'id', 'backupConfigurationId', 'externalJobId',
            'hostname', 'ipAddress', 'status',
            'startedAt', 'finishedAt', 'sizeBytes',
            'storageType', 'storagePath', 'metadata', 'errorMessage',
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['status'] = DB_TO_API_STATUS.get(instance.status, instance.status)
        return data