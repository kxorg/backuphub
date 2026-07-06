from rest_framework import serializers
from .models import TargetSystem, Host, Backup


class TargetSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetSystem
        fields = ['id', 'name', 'system_type', 'api_key', 'created_at']


class HostSerializer(serializers.ModelSerializer):
    system_name = serializers.CharField(source='target_system.name', read_only=True)

    class Meta:
        model = Host
        fields = ['id', 'hostname', 'ip_address', 'target_system', 'system_name']


class BackupSerializer(serializers.ModelSerializer):
    hostname = serializers.CharField(source='host.hostname', read_only=True)
    system_name = serializers.CharField(source='target_system.name', read_only=True)
    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = Backup
        fields = [
            'id', 'host', 'target_system', 'hostname', 'system_name',
            'status', 'start_time', 'end_time', 'duration_seconds',
            'backup_size', 'storage', 'meta_data', 'error_message'
        ]
        read_only_fields = ['id', 'start_time']

    def get_duration_seconds(self, obj):
        if obj.start_time and obj.end_time:
            return int((obj.end_time - obj.start_time).total_seconds())
        return None


class BackupCreateSerializer(serializers.Serializer):
    host_id = serializers.IntegerField(help_text="ID of the host on which the backup is running")
    target_system_id = serializers.IntegerField(help_text="ID system", required=False)
    storage = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_host_id(self, value):
        if not Host.objects.filter(id=value).exists():
            raise serializers.ValidationError("The host with the specified ID was not found in the database.")
        return value

    def validate_target_system_id(self, value):
        if value and not TargetSystem.objects.filter(id=value).exists():
            raise serializers.ValidationError("The system with the specified ID was not found in the database.")
        return value


class BackupUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=['success', 'error', 'in_progress'],
        required=False
    )
    end_time = serializers.DateTimeField(required=False)
    backup_size = serializers.IntegerField(required=False, min_value=0)
    storage = serializers.CharField(max_length=255, required=False, allow_blank=True)
    meta_data = serializers.JSONField(required=False, help_text="Technical data in format JSON")
    error_message = serializers.CharField(required=False, allow_blank=True)