from rest_framework import mixins, permissions, viewsets

from backend.foodgram.api.paginators import PageNumberPaginatorModified


class CreateDestroyMixinView(
    mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet,
):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = PageNumberPaginatorModified
