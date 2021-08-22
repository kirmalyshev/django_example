from rest_framework.pagination import LimitOffsetPagination


class DoctorPagination(LimitOffsetPagination):
    default_limit = 100
