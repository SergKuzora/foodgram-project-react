from django.contrib.auth import get_user_model
from django.db.models import F
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from food.models import (Favorite, Ingredient, IngredientRecipe, PurchaseList,
                         Recipe, Subscribe, Tag)
from users.serializers import UserSerializer

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class ShowRecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ['id', 'name', 'measurement_unit', 'amount']


class AddIngredientToRecipeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = Ingredient
        fields = ('id', 'amount')


class RecipeListSerializer(serializers.ModelSerializer):
    author = UserSerializer()
    tags = TagSerializer(many=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def get_ingredients(self, obj):
        qs = IngredientRecipe.objects.filter(recipe=obj)
        return ShowRecipeIngredientSerializer(qs, many=True).data

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return PurchaseList.objects.filter(
            user=request.user,
            recipe=obj
        ).exists()


class CreateRecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField(max_length=None, use_url=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    ingredients = AddIngredientToRecipeSerializer(many=True)

    class Meta:
        model = Recipe
        fields = '__all__'
        read_only_fields = ('author',)

    def validate(self, data):
        if len(data['ingredients']) > len(set(data['ingredients'])):
            raise serializers.ValidationError('Ингредиенты не уникальны')
        if len(data['tags']) > len(set(data['tags'])):
            raise serializers.ValidationError('Теги не уникальны')
        for ingredient in data['ingredients']:
            if ingredient['amount'] < 0:
                raise serializers.ValidationError(
                    'Количество ингредиента не может быть '
                    'отрицательным числом.'
                )
        if data['recipe'].cooking_time <= 0:
            raise serializers.ValidationError('Время готовки задано не верно!')
        return data

    def calc_ingredients_amount(self, ingredients, recipe):
        for ingredient in ingredients:
            obj = get_object_or_404(Ingredient, id=ingredient['id'])
            amount = ingredient['amount']
            if IngredientRecipe.objects.filter(
                    recipe=recipe,
                    ingredient=obj
            ).exists():
                amount += F('amount')
            IngredientRecipe.objects.update_or_create(
                recipe=recipe,
                ingredient=obj,
                defaults={'amount': amount}
            )

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.calc_ingredients_amount(ingredients, recipe)

        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' in self.initial_data:
            ingredients = validated_data.pop('ingredients')
            instance.ingredients.clear()
            self.calc_ingredients_amount(ingredients, instance)

        if 'tags' in self.initial_data:
            tags = validated_data.pop('tags')
            instance.tags.set(tags)

        super().update(instance, validated_data)
        return instance

    def to_representation(self, instance):
        return RecipeListSerializer(
            instance,
            context={'request': self.context.get('request')}
        ).data


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']


class CreateDeleteSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    recipe = serializers.SerializerMethodField()

    class Meta:
        model = None
        fields = '__all__'

    def to_representation(self, instance):
        request = self.context.get('request')
        context = {'request': request}
        instance = get_object_or_404(
            Recipe, pk=int(self._context['view'].kwargs['recipe_id'])
        )
        return RecipeSerializer(instance, context=context).data

    def get_user(self, obj):
        return self.context['request'].user

    def get_recipe(self, obj):
        return get_object_or_404(
            Recipe, pk=self._context['view'].kwargs['recipe_id']
        )

    def validate(self, attrs):
        obj = self.Meta.model.objects.filter(
            user=self.context['request'].user,
            recipe=self.context['view'].kwargs['recipe_id']
        ).first()
        if obj is not None:
            raise serializers.ValidationError(
                'Such record is already exists'
            )
        return super().validate(attrs)

    def create(self, validated_data):
        user = self.context['request'].user
        obj = get_object_or_404(
            Recipe, pk=self.context['view'].kwargs['recipe_id'],
        )
        return self.Meta.model.objects.create(user=user, recipe=obj)


class SubscribersSerializer(serializers.ModelSerializer):
    recipes = RecipeShortSerializer(many=True, read_only=True)
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count'
        )

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Subscribe.objects.filter(user=obj, author=request.user).exists()


class SubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscribe
        fields = '__all__'

    def to_representation(self, instance):
        return SubscribersSerializer(
            instance.author,
            context={'request': self.context.get('request')}
        ).data

    def validate(self, attr):
        request = self.context['request']
        if request.method == 'GET':
            if request.user == attr['author']:
                raise serializers.ValidationError(
                    'Невозможно подписаться на себя'
                )
            if Subscribe.objects.filter(
                    user=request.user,
                    author=attr['author']
            ).exists():
                raise serializers.ValidationError('Вы уже подписаны')
        return attr
