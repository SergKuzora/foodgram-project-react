from rest_framework import mixins, permissions, viewsets
from sympy import Li

from api.paginators import LimitPageNumberPagination


class CreateDestroyMixinView(
    mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet,
):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = LimitPageNumberPagination
