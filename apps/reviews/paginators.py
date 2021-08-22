from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination


class ReviewPagination(LimitOffsetPagination):
    default_limit = 100
