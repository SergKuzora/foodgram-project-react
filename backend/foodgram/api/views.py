from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import RecipeFilter, SearchFilter
from food.models import (Favorite, Ingredient, IngredientRecipe, PurchaseList,
                         Recipe, Subscribe, Tag)
from .mixins import CreateDestroyMixinView
from .paginators import PageNumberPaginatorModified
from .permissions import AuthorOrReadOnly
from .serializers import (CreateDeleteSerializer, CreateRecipeSerializer,
                          IngredientSerializer, RecipeListSerializer,
                          SubscribersSerializer, SubscribeSerializer,
                          TagSerializer)

User = get_user_model()


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = CreateRecipeSerializer
    permission_classes = [AuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filter_class = RecipeFilter
    pagination_class = PageNumberPaginatorModified

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return RecipeListSerializer
        return CreateRecipeSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny, ]
    filter_backends = [SearchFilter]
    search_fields = ['name', ]


@api_view(['get'])
@permission_classes([IsAuthenticated])
def show_subscribs(request):
    user_obj = User.objects.filter(following__user=request.user)
    paginator = PageNumberPagination()
    paginator.page_size = 10
    result_page = paginator.paginate_queryset(user_obj, request)
    serializer = SubscribersSerializer(
        result_page,
        many=True,
        context={'current_user': request.user}
    )
    return paginator.get_paginated_response(serializer.data)


class SubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        user = request.user
        data = {
            'user': user.id,
            'author': user_id
        }
        serializer = SubscribeSerializer(
            data=data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status.HTTP_201_CREATED)

    def delete(self, request, user_id):
        user = request.user
        follow = get_object_or_404(
            Subscribe,
            user=user,
            author_id=user_id
        )
        follow.delete()
        return Response('Вы отписались от данного пользователя',
                        status.HTTP_204_NO_CONTENT)


class CreateDeleteView(CreateDestroyMixinView):

    def get_model(self):
        if self.basename == 'favorite':
            return Favorite
        return PurchaseList

    def get_serializer_class(self):
        CreateDeleteSerializer.Meta.model = self.get_model()
        return CreateDeleteSerializer

    def get_object(self):
        user = self.request.user
        recipe = get_object_or_404(Recipe, pk=self.kwargs['recipe_id'])
        obj = get_object_or_404(
            self.get_model(), user=user, recipe=recipe,
        )
        self.check_object_permissions(self.request, obj)
        return obj

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class DownloadPurchaseList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        recipes = request.user.purchases.all().values_list('recipe', flat=True)
        ingredients = IngredientRecipe.objects.filter(
            recipe__in=recipes).all().values_list(
                'ingredient', flat=True).annotate(total_amount=Sum('amount'))
        purchase_list = {}

        for ingredient in ingredients:
            name = ingredient.ingredient.name
            amount = ingredient.total_amount
            unit = ingredient.ingredient.measurement_unit
            purchase_list[name] = {
                'amount': amount,
                'unit': unit
            }
        wishlist = []
        for item in purchase_list:
            wishlist.append(f'{item} ({purchase_list[item]["unit"]}): '
                            f'{purchase_list[item]["amount"]} \n')
            wishlist.append('Хороших покупок!')
        response = HttpResponse(wishlist, 'Content-Type: application/pdf')
        response['Content-Disposition'] = 'attachment; filename="wishlist.pdf"'
        return response
