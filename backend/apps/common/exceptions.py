"""API errors and the JSON envelope used by every endpoint.

Successful bodies are wrapped by the renderer. This handler only normalizes
exceptions that DRF does not already convert, such as Django validation errors
raised from services.
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

logger = logging.getLogger('business')


class BusinessRuleError(APIException):
    """The request is well formed but breaks a tuition-center rule."""

    status_code = 400
    default_detail = 'The request breaks a business rule.'
    default_code = 'business_rule'


class ConflictError(APIException):
    """The request clashes with existing enrollments, contracts, or schedules."""

    status_code = 409
    default_detail = 'The request conflicts with the current records.'
    default_code = 'conflict'


def api_exception_handler(exc, context):
    """Convert Django validation errors into the standard API error shape."""

    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, 'message_dict'):
            detail = exc.message_dict
        else:
            detail = exc.messages
        exc = BusinessRuleError(detail=detail)
    response = exception_handler(exc, context)
    if response is None:
        logger.exception('Unhandled API error', exc_info=exc)
    return response
