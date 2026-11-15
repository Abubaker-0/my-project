"""Page-number pagination shared by every list endpoint."""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Ten rows by default, with `page` and `page_size` query parameters."""

    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
