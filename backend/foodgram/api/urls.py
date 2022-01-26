from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (DownloadPurchaseList, IngredientViewSet,
                    RecipeViewSet, SubscribeView, TagViewSet,
                    show_subscribs, CreateDeleteView)

router = DefaultRouter()

router.register('tags', TagViewSet, basename='tags')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('recipes', RecipeViewSet, basename='recipes')
router.register(
    r'recipes/(?P<recipe_id>\d+)/favorite',
    CreateDeleteView, basename='favorite',
)
router.register(
    r'recipes/(?P<recipe_id>\d+)/shopping_cart',
    CreateDeleteView, basename='shopping_cart',
)
urlpatterns = [
    path('recipes/download_shopping_cart/',
         DownloadPurchaseList.as_view(), name='dowload_shopping_cart'),
    path('users/subscriptions/',
         show_subscribs, name='users_subs'),
    path('users/<int:user_id>/subscribe/',
         SubscribeView.as_view(), name='subscribe'),
    path('', include(router.urls))
]
