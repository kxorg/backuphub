import django_filters

from operations.models import BackupOperation
from api.utils.status_mapping import API_TO_DB_STATUS


class BackupOperationFilter(django_filters.FilterSet):
    """
    Filters for the backup operations list endpoint.
    Status values are API-level (RUNNING/SUCCESS/FAILED), mapped to DB internally.
    """
    status = django_filters.ChoiceFilter(
        choices=[(s, s) for s in API_TO_DB_STATUS.keys()],
        method='filter_status',
        help_text='API status: RUNNING, SUCCESS, FAILED',
    )
    hostname = django_filters.CharFilter(
        lookup_expr='icontains',
        help_text='Hostname (case-insensitive contains)',
    )
    backup_configuration_id = django_filters.NumberFilter(
        field_name='backup_configuration_version__backup_configuration__id',
        help_text='Filter by backup configuration ID',
    )
    started_after = django_filters.DateTimeFilter(
        field_name='started_at',
        lookup_expr='gte',
        help_text='Started at or after (ISO 8601)',
    )
    started_before = django_filters.DateTimeFilter(
        field_name='started_at',
        lookup_expr='lte',
        help_text='Started at or before (ISO 8601)',
    )

    class Meta:
        model = BackupOperation
        fields = [
            'hostname',
            'backup_configuration_id',
            'started_after',
            'started_before',
        ]

    def filter_status(self, queryset, name, value):
        """Maps API status to DB status and filters the queryset."""
        db_status = API_TO_DB_STATUS.get(value)
        if db_status is None:
            return queryset.none()
        return queryset.filter(status=db_status)