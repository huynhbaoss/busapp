from rest_framework import pagination


class BusesPaginator(pagination.PageNumberPagination):
    page_size = 20
