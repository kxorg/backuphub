from rest_framework import serializers

from .models import (
    SystemType,
    Environment,
    BackupTool,
    TargetSystem,
    TargetSystemVersion,
    BackupConfiguration,
    BackupConfigurationVersion,
    BackupOperation,
)


class SystemTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemType
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class EnvironmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Environment
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class BackupToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupTool
        fields = ['id', 'name', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class TargetSystemVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetSystemVersion
        fields = [
            'id', 'version_number', 'owner', 'administrator',
            'is_current', 'valid_from', 'valid_to', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TargetSystemSerializer(serializers.ModelSerializer):
    system_type_name = serializers.CharField(source='system_type.name', read_only=True)
    environment_name = serializers.CharField(source='environment.name', read_only=True)
    current_version = TargetSystemVersionSerializer(read_only=True)

    class Meta:
        model = TargetSystem
        fields = [
            'id', 'name', 'system_type', 'system_type_name',
            'environment', 'environment_name', 'description',
            'owner', 'administrator', 'api_key', 'is_active',
            'current_version', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'api_key', 'created_at', 'updated_at']


class TargetSystemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating TargetSystem with automatic version creation."""
    
    class Meta:
        model = TargetSystem
        fields = [
            'id', 'name', 'system_type', 'environment',
            'description', 'owner', 'administrator',
            'api_key', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'api_key', 'created_at']

    def create(self, validated_data):
        """Create system and its first version automatically."""
        from django.utils import timezone
        
        # Create the system (API key generated automatically via model save())
        system = TargetSystem.objects.create(**validated_data)
        
        # Create first version
        TargetSystemVersion.objects.create(
            target_system=system,
            version_number=1,
            owner=validated_data.get('owner', ''),
            administrator=validated_data.get('administrator', ''),
            is_current=True,
            valid_from=timezone.now(),
            created_by=self.context['request'].user.username if self.context.get('request') else 'system'
        )
        
        return system


class BackupConfigurationVersionSerializer(serializers.ModelSerializer):
    backup_tool_name = serializers.CharField(source='backup_tool.name', read_only=True)

    class Meta:
        model = BackupConfigurationVersion
        fields = [
            'id', 'version_number', 'backup_tool', 'backup_tool_name',
            'backup_mode', 'schedule_cron', 'retention_days',
            'rpo_minutes', 'rto_minutes', 'storage_type', 'storage_path',
            'verify_after_backup', 'immutable_storage',
            'is_current', 'valid_from', 'valid_to', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class BackupConfigurationSerializer(serializers.ModelSerializer):
    target_system_name = serializers.CharField(
        source='target_system_version.target_system.name',
        read_only=True
    )
    current_version = BackupConfigurationVersionSerializer(read_only=True)

    class Meta:
        model = BackupConfiguration
        fields = [
            'id', 'name', 'target_system_version', 'target_system_name',
            'description', 'is_active', 'current_version',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BackupConfigurationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating BackupConfiguration with automatic version creation."""
    
    # Fields for version creation
    backup_tool = serializers.IntegerField(write_only=True, required=True)
    backup_mode = serializers.ChoiceField(
        choices=BackupConfigurationVersion.BACKUP_MODE_CHOICES,
        write_only=True,
        required=True
    )
    schedule_cron = serializers.CharField(write_only=True, required=False, allow_blank=True)
    retention_days = serializers.IntegerField(write_only=True, required=False, default=30)
    rpo_minutes = serializers.IntegerField(write_only=True, required=False, default=1440)
    rto_minutes = serializers.IntegerField(write_only=True, required=False, default=60)
    storage_type = serializers.ChoiceField(
        choices=BackupConfigurationVersion.STORAGE_TYPE_CHOICES,
        write_only=True,
        required=False,
        default='local'
    )
    storage_path = serializers.CharField(write_only=True, required=False, allow_blank=True)
    verify_after_backup = serializers.BooleanField(write_only=True, required=False, default=False)
    immutable_storage = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = BackupConfiguration
        fields = [
            'id', 'name', 'target_system_version', 'description', 'is_active',
            'backup_tool', 'backup_mode', 'schedule_cron', 'retention_days',
            'rpo_minutes', 'rto_minutes', 'storage_type', 'storage_path',
            'verify_after_backup', 'immutable_storage', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        """Create configuration and its first version automatically."""
        from django.utils import timezone
        
        # Extract version-specific fields
        version_fields = {
            'backup_tool_id': validated_data.pop('backup_tool'),
            'backup_mode': validated_data.pop('backup_mode'),
            'schedule_cron': validated_data.pop('schedule_cron', ''),
            'retention_days': validated_data.pop('retention_days', 30),
            'rpo_minutes': validated_data.pop('rpo_minutes', 1440),
            'rto_minutes': validated_data.pop('rto_minutes', 60),
            'storage_type': validated_data.pop('storage_type', 'local'),
            'storage_path': validated_data.pop('storage_path', ''),
            'verify_after_backup': validated_data.pop('verify_after_backup', False),
            'immutable_storage': validated_data.pop('immutable_storage', False),
        }
        
        # Create configuration
        config = BackupConfiguration.objects.create(**validated_data)
        
        # Create first version
        BackupConfigurationVersion.objects.create(
            backup_configuration=config,
            version_number=1,
            is_current=True,
            valid_from=timezone.now(),
            created_by=self.context['request'].user.username if self.context.get('request') else 'system',
            **version_fields
        )
        
        return config


class BackupOperationSerializer(serializers.ModelSerializer):
    """Serializer for listing and retrieving backup operations."""
    configuration_name = serializers.CharField(
        source='backup_configuration_version.backup_configuration.name',
        read_only=True
    )
    target_system_name = serializers.CharField(
        source='backup_configuration_version.backup_configuration.target_system_version.target_system.name',
        read_only=True
    )
    backup_tool_name = serializers.CharField(
        source='backup_configuration_version.backup_tool.name',
        read_only=True
    )
    duration_seconds = serializers.IntegerField(read_only=True)
    size_human = serializers.CharField(read_only=True)

    class Meta:
        model = BackupOperation
        fields = [
            'id', 'backup_configuration_version', 'configuration_name',
            'target_system_name', 'backup_tool_name',
            'external_job_id', 'hostname', 'ip_address',
            'status', 'started_at', 'finished_at',
            'duration_seconds', 'size_bytes', 'size_human',
            'storage_type', 'storage_path',
            'metadata', 'error_message',
            'created_at', 'created_by'
        ]
        read_only_fields = ['id', 'created_at']


class BackupOperationCreateSerializer(serializers.Serializer):
    """Serializer for creating backup operations (called by backup scripts)."""
    backup_configuration_version_id = serializers.IntegerField(
        help_text='ID of the backup configuration version'
    )
    external_job_id = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text='External job ID (e.g., Kubernetes CronJob ID)'
    )
    hostname = serializers.CharField(
        max_length=255,
        help_text='Hostname of the server'
    )
    ip_address = serializers.IPAddressField(
        required=False,
        help_text='IP address (auto-detected if not provided)'
    )
    storage_type = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text='Storage type (local, s3, azure, etc.)'
    )
    storage_path = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text='Path to backup file'
    )

    def validate_backup_configuration_version_id(self, value):
        """Check if configuration version exists and is active."""
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
        return value


class BackupOperationUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=BackupOperation.STATUS_CHOICES,
        required=False,
        help_text='Backup execution status'
    )
    finished_at = serializers.DateTimeField(
        required=False,
        help_text='Finish time (auto-set if status is success/error)'
    )
    size_bytes = serializers.BigIntegerField(
        required=False,
        min_value=0,
        help_text='Backup size in bytes'
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
        help_text='Error message (if status is error)'
    )