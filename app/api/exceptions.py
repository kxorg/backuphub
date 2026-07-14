import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Unified error response format:
    {
        "error": {
            "code": "validation_error",
            "message": "...",
            "details": {...}
        }
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_payload = {
            'error': {
                'code': _get_error_code(response.status_code),
                'message': _get_error_message(response),
            }
        }

        if isinstance(response.data, dict):
            error_payload['error']['details'] = response.data
        else:
            error_payload['error']['details'] = {'non_field_errors': response.data}

        response.data = error_payload
        return response

    # Unhandled exceptions — log and return 500
    logger.exception('Unhandled exception in API view', exc_info=exc)
    return Response(
        {
            'error': {
                'code': 'internal_error',
                'message': 'An unexpected error occurred.',
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _get_error_code(status_code: int) -> str:
    """Maps HTTP status code to a machine-readable error code."""
    mapping = {
        400: 'validation_error',
        401: 'unauthorized',
        403: 'forbidden',
        404: 'not_found',
        405: 'method_not_allowed',
        409: 'conflict',
        429: 'too_many_requests',
        500: 'internal_error',
    }
    return mapping.get(status_code, 'error')


def _get_error_message(response: Response) -> str:
    """Extracts the most relevant human-readable message from DRF response."""
    data = response.data
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        if 'non_field_errors' in data:
            return str(data['non_field_errors'][0])
        # First field with an error
        for key, value in data.items():
            if isinstance(value, list) and value:
                return f'{key}: {value[0]}'
            if isinstance(value, str):
                return value
    if isinstance(data, list) and data:
        return str(data[0])
    return 'Request failed.'