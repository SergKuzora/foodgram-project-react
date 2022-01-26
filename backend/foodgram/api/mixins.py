from rest_framework import mixins, permissions, viewsets

from api.paginators import PageNumberPaginatorModified


class CreateDestroyMixinView(
    mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet,
):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = PageNumberPaginatorModified
