"""Validate profile and center images before they are stored."""

from io import BytesIO

from PIL import Image

from apps.common.exceptions import BusinessRuleError

ALLOWED_FORMATS = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}
MAX_BYTES = 2 * 1024 * 1024


def validate_image(upload):
    """Accept only a real JPEG, PNG, or WebP file up to 2 MB.

    The content type header is checked when the client sends one, and Pillow
    must agree. This rejects renamed documents that would break the UI.
    """

    if upload.size > MAX_BYTES:
        raise BusinessRuleError('Image must be 2 MB or smaller.')
    content_type = getattr(upload, 'content_type', '') or ''
    if content_type and content_type not in ALLOWED_FORMATS.values():
        raise BusinessRuleError('Image must be a JPEG, PNG, or WebP file.')
    data = upload.read()
    upload.seek(0)
    try:
        image = Image.open(BytesIO(data))
        image_format = image.format
        image.verify()
    except Exception as exc:
        raise BusinessRuleError('The uploaded file is not a valid image.') from exc
    if image_format not in ALLOWED_FORMATS:
        raise BusinessRuleError('Image must be a JPEG, PNG, or WebP file.')
    upload.seek(0)
