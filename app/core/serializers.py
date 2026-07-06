from rest_framework import serializers
from .models import TargetSystem, Host, Backup

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
    api_key =  serializers.UUIDField(help_text = 'API key of the tagret system')
    hostname = serializers.CharField(max_length = 255, help_text = 'Hostname of the server')

    def validate_api_key(self, value):
        if not TargetSystem.objects.filter(api_key=value).exists():
            raise serializers.ValidationError("Target system with this API key not found.")
        return value


class BackupUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=['success', 'error', 'in_progress'],
        required=False
    )
    end_time = serializers.DateTimeField(required=False)
    backup_size = serializers.IntegerField(required=False, min_value=0)
    storage = serializers.CharField(max_length=255, allow_blank=True)
    meta_data = serializers.JSONField(required=False, help_text="Technical data in format JSON")
    error_message = serializers.CharField(required=False, allow_blank=True)