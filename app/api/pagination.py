from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """
    Default pagination for all API endpoints.
    Client can override page_size via ?page_size=N (max 500).
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500