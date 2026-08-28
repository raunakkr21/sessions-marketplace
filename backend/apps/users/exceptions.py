"""
Custom exception handler for DRF.

Ensures consistent JSON error responses and prevents stack trace exposure.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Return a consistent JSON error format:
    {
        "error": "Short error code",
        "detail": "Human-readable message"
    }

    Never expose internal exception details or stack traces.
    """
    response = exception_handler(exc, context)

    if response is not None:
        # Normalize the response data into our consistent format
        data = response.data

        if isinstance(data, dict):
            # DRF ValidationErrors come as field-keyed dicts
            detail = data.get('detail', data)
        elif isinstance(data, list):
            detail = data
        else:
            detail = str(data)

        # Map HTTP status to a short error code
        error_codes = {
            400: 'bad_request',
            401: 'unauthorized',
            403: 'forbidden',
            404: 'not_found',
            405: 'method_not_allowed',
            409: 'conflict',
            429: 'rate_limited',
            500: 'server_error',
        }
        error_code = error_codes.get(response.status_code, 'error')

        response.data = {
            'error': error_code,
            'detail': detail,
        }

    return response
