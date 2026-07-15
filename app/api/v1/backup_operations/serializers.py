from django.utils import timezone
from rest_framework import serializers

from configurations.models import BackupConfiguration
from operations.models import BackupOperation
from api.utils.status_mapping import (
    API_TO_DB_STATUS,
    DB_TO_API_STATUS,
    API_STATUS_CHOICES,
)


class BackupOperationCreateSerializer(serializers.Serializer):
    """
    POST /api/v1/backup-operations/
    Required: backup_configuration_id.
    Optional: hostname, ip_address.
    """
    backup_configuration_id = serializers.IntegerField(
        help_text='ID of the active backup configuration',
    )
    hostname = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default='',
        help_text='Hostname of the backup server',
    )
    ip_address = serializers.IPAddressField(
        required=False,
        allow_null=True,
        help_text='IP address of the backup server',
    )

    def validate_backup_configuration_id(self, value):
        """Ensures the configuration exists, is active, and has a current version."""
        try:
            config = BackupConfiguration.objects.get(id=value, is_active=True)
        except BackupConfiguration.DoesNotExist:
            raise serializers.ValidationError(
                'Active backup configuration with this ID does not exist.'
            )

        if not config.versions.filter(is_current=True).exists():
            raise serializers.ValidationError(
                f"Configuration '{config.name}' has no current version."
            )

        return config

    def create(self, validated_data):
        """Creates the operation bound to the current version of the configuration."""
        config = validated_data['backup_configuration_id']
        current_version = config.versions.filter(is_current=True).first()

        return BackupOperation.objects.create(
            backup_configuration_version=current_version,
            hostname=validated_data.get('hostname', ''),
            ip_address=validated_data.get('ip_address'),
            status='in_progress',
        )


class BackupOperationUpdateSerializer(serializers.Serializer):
    """
    PATCH /api/v1/backup-operations/{id}/
    Updates status and result metadata. finished_at is set automatically
    when status transitions to SUCCESS/FAILED.
    """
    status = serializers.ChoiceField(
        choices=API_STATUS_CHOICES,
        help_text='New status: running, success, failed',
    )
    size_bytes = serializers.IntegerField(
        required=False,
        min_value=0,
        help_text='Backup size in bytes',
    )
    storage_type = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text='Storage type (s3, local, nfs, ...)',
    )
    storage_path = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text='Path to backup file',
    )
    metadata = serializers.JSONField(
        required=False,
        help_text='Arbitrary metadata (JSON)',
    )
    error_message = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Required when status=FAILED',
    )
    def to_internal_value(self, data):
        """Приводит статус к нижнему регистру ДО валидации ChoiceField."""
        if 'status' in data and isinstance(data['status'], str):
            data = data.copy()  
            data['status'] = data['status'].lower()
        return super().to_internal_value(data)
    
    def validate(self, attrs):
        instance = self.instance
        if instance is None:
            return attrs

        # Block modifications of already completed operations
        if instance.status in ('success', 'error'):
            raise serializers.ValidationError(
                'Cannot modify a completed operation.'
            )

        # FAILED requires an error message
        new_status = attrs.get('status')
        if new_status == 'FAILED' and not attrs.get('error_message'):
            raise serializers.ValidationError({
                'error_message': 'This field is required when status is FAILED.',
            })

        return attrs

    def update(self, instance, validated_data):
        """Applies the update. Sets finished_at on terminal status transitions."""
        if 'status' in validated_data:
            instance.status = API_TO_DB_STATUS[validated_data['status']]

        for field in ('size_bytes', 'storage_type', 'storage_path',
                      'metadata', 'error_message'):
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        # Auto-set finished_at on terminal states
        if instance.status in ('success', 'error') and not instance.finished_at:
            instance.finished_at = timezone.now()

        instance.save()
        return instance


class BackupOperationReadSerializer(serializers.ModelSerializer):
    """
    GET /api/v1/backup-operations/ and /{id}/
    Returns the full operation object with API-level status.
    """
    backup_configuration_id = serializers.IntegerField(
        source='backup_configuration_version.backup_configuration.id',
        read_only=True,
    )
    backup_configuration_version_id = serializers.IntegerField(
        source='backup_configuration_version.id',
        read_only=True,
    )
    target_system_id = serializers.IntegerField(
        source='backup_configuration_version.backup_configuration.target_system_version.target_system.id',
        read_only=True,
    )

    class Meta:
        model = BackupOperation
        fields = [
            'id',
            'backup_configuration_id',
            'backup_configuration_version_id',
            'target_system_id',
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
        """Maps DB status back to API status (e.g. 'success' -> 'SUCCESS')."""
        data = super().to_representation(instance)
        data['status'] = DB_TO_API_STATUS.get(instance.status, instance.status)
        return data