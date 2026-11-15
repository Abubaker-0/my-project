"""Wrap every JSON response in one envelope.

Success: {"success": true, "message": "OK", "data": ...}
Failure: {"success": false, "message": "...", "errors": ...}

The frontend reads `data` and shows `message` in toasts.
"""

from rest_framework.renderers import JSONRenderer


def _message_from_errors(data):
    if isinstance(data, dict):
        detail = data.get('detail')
        if isinstance(detail, list) and detail:
            return str(detail[0])
        if isinstance(detail, str):
            return detail
        for key, value in data.items():
            if isinstance(value, list) and value:
                return f'{key}: {value[0]}'
            if isinstance(value, dict):
                nested = _message_from_errors(value)
                if nested:
                    return f'{key}: {nested}'
            if isinstance(value, str):
                return f'{key}: {value}'
    if isinstance(data, list) and data:
        return str(data[0])
    return 'Request failed.'


class ApiRenderer(JSONRenderer):
    """Renderer that adds the success envelope without double-wrapping it."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, dict) and 'success' in data:
            payload = data
        else:
            response = (renderer_context or {}).get('response')
            status_code = getattr(response, 'status_code', 200)
            if status_code >= 400:
                payload = {
                    'success': False,
                    'message': _message_from_errors(data),
                    'errors': data,
                }
            else:
                payload = {
                    'success': True,
                    'message': 'OK',
                    'data': {} if data is None else data,
                }
        return super().render(payload, accepted_media_type, renderer_context)
