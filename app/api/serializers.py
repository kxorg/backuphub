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
    hostname = serializers.CharField(max_length=255,required=False, allow_blank = True)
    ipAddress = serializers.IPAddressField(required=False, allow_null=True)
    backupConfigurationVersionId = serializers.IntegerField() 

    def validate_backupConfigurationVersionId(self, value):
        try:
            config_version = BackupConfigurationVersion.objects.get(
                id=value,
                is_current=True,
                backup_configuration__is_active=True
            )
        except BackupConfigurationVersion.DoesNotExist:
            raise serializers.ValidationError(
                'Active backup configuration version not found.'
            )
        return config_version

    def create(self, validated_data):
        """Создаёт операцию, привязывая к текущей версии конфигурации."""
        config_version = validated_data['backupConfigurationVersionId']
        
        return BackupOperation.objects.create(
            backup_configuration_version=config_version,
            hostname=validated_data.get('hostname', ''),
            ip_address=validated_data.get('ipAddress'),
            status='in_progress',
        )


# ==========================================
# UPDATE SERIALIZER (без изменений)
# ==========================================

class BackupOperationUpdateSerializer(serializers.Serializer):
    """PATCH /api/backup-operations/{id}/"""
    status = serializers.ChoiceField(choices=['SUCCESS', 'FAILED'])
    sizeBytes = serializers.IntegerField(required=False, min_value=0)
    storageType = serializers.CharField(max_length=50, required=False, allow_blank=True)
    storagePath = serializers.CharField(max_length=500, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)
    errorMessage = serializers.CharField(required=False, allow_blank=True)
    hostname = serializers.CharField(max_length =255, required = False, allow_blank = True)
    ipAddress = serializers.IPAddressField(required = False, allow_null = True)

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
        
        instance.hostname = validated_data.get('hostname', instance.hostname)
        instance.ip_address = validated_data.get('ipAddress', instance.ip_address)

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
    ipAddress = serializers.CharField(source='ip_address', read_only=True, allow_null=True)
    startedAt = serializers.DateTimeField(source='started_at', read_only=True)
    finishedAt = serializers.DateTimeField(source='finished_at', read_only=True, allow_null=True)
    sizeBytes = serializers.IntegerField(source='size_bytes', read_only=True, allow_null=True)
    storageType = serializers.CharField(source='storage_type', read_only=True, allow_null=True)
    storagePath = serializers.CharField(source='storage_path', read_only=True, allow_null=True)
    errorMessage = serializers.CharField(source='error_message', read_only=True, allow_null=True)

    class Meta:
        model = BackupOperation
        fields = [
            'id', 'backupConfigurationId',
            'hostname', 'ipAddress', 'status',
            'startedAt', 'finishedAt', 'sizeBytes',
            'storageType', 'storagePath', 'metadata', 'errorMessage',
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['status'] = DB_TO_API_STATUS.get(instance.status, instance.status)
        return data