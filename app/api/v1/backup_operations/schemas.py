"""
OpenAPI schema extensions for drf-spectacular.
Kept separate from views to avoid cluttering the viewset.
"""
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample


backup_operation_create_schema = extend_schema(
    tags=['Backup Operations API'],
    summary='Create a backup operation',
    description=(
        'Registers the start of a backup operation. '
        'Automatically binds to the current version of the configuration. '
        'The API key must belong to the target system of the configuration.'
    ),
    responses={
        201: OpenApiResponse(description='Operation created'),
        400: OpenApiResponse(description='Validation error'),
        401: OpenApiResponse(description='Missing or invalid API key'),
        403: OpenApiResponse(description='API key does not match the configuration\'s target system'),
    },
    examples=[
        OpenApiExample(
            'Create operation',
            value={
                'backup_configuration_id': 1,
                'hostname': 'backup-server-01',
                'ip_address': '10.10.10.15',
            },
            request_only=True,
        ),
        OpenApiExample(
            'Created response',
            value={
                'id': 42,
                'backup_configuration_id': 1,
                'backup_configuration_version_id': 3,
                'target_system_id': 7,
                'hostname': 'backup-server-01',
                'ip_address': '10.10.10.15',
                'status': 'RUNNING',
                'started_at': '2026-07-14T10:00:00Z',
                'finished_at': None,
                'size_bytes': None,
                'storage_type': None,
                'storage_path': None,
                'metadata': None,
                'error_message': None,
            },
            response_only=True,
        ),
    ],
)


backup_operation_update_schema = extend_schema(
    tags=['Backup Operations API'],
    summary='Update operation status',
    description=(
        'Updates the operation status (RUNNING -> SUCCESS/FAILED). '
        'finished_at is set automatically on SUCCESS/FAILED. '
        'Re-completing an already finished operation is forbidden (400).'
    ),
    responses={
        200: OpenApiResponse(description='Operation updated'),
        400: OpenApiResponse(description='Operation already completed or invalid data'),
        401: OpenApiResponse(description='Invalid API key'),
        403: OpenApiResponse(description='API key does not match the operation\'s target system'),
        404: OpenApiResponse(description='Operation not found'),
    },
    examples=[
        OpenApiExample(
            'Complete with success',
            value={
                'status': 'SUCCESS',
                'size_bytes': 5368709120,
                'storage_type': 's3',
                'storage_path': 's3://backup/prod/backup.sql.gz',
            },
            request_only=True,
        ),
        OpenApiExample(
            'Complete with failure',
            value={
                'status': 'FAILED',
                'error_message': 'Connection timeout to S3',
            },
            request_only=True,
        ),
    ],
)


backup_operation_list_schema = extend_schema(
    tags=['Backup Operations API'],
    summary='List operations',
    description='Returns a paginated list of operations with optional filters.',
    parameters=[
        OpenApiParameter(
            name='status',
            type=str,
            location=OpenApiParameter.QUERY,
            description='API status: RUNNING, SUCCESS, FAILED',
        ),
        OpenApiParameter(
            name='hostname',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Hostname (case-insensitive contains)',
        ),
        OpenApiParameter(
            name='backup_configuration_id',
            type=int,
            location=OpenApiParameter.QUERY,
            description='Filter by configuration ID',
        ),
        OpenApiParameter(
            name='started_after',
            type=str,
            location=OpenApiParameter.QUERY,
            description='ISO 8601 datetime',
        ),
        OpenApiParameter(
            name='started_before',
            type=str,
            location=OpenApiParameter.QUERY,
            description='ISO 8601 datetime',
        ),
        OpenApiParameter(
            name='page',
            type=int,
            location=OpenApiParameter.QUERY,
            description='Page number',
        ),
        OpenApiParameter(
            name='page_size',
            type=int,
            location=OpenApiParameter.QUERY,
            description='Items per page (max 500)',
        ),
    ],
)