import tempfile
import os
from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPES_URL = reverse('recipe:recipe-list')


def image_upload_url(recipe_id):
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_sample_tag(user, name='Test tag'):
    return Tag.objects.create(user=user, name=name)


def create_sample_ingredient(user, name='Ingredient for test'):
    return Ingredient.objects.create(user=user, name=name)


def create_sample_recipe(user, **params):
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': 5.00
    }
    defaults.update(**params)
    return Recipe.objects.create(user=user, **defaults)
    

class PublicRecipeApiTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        
    def test_login_required(self):
        res = self.client.get(RECIPES_URL)
        
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        
        
class PrivateRecipeApiTests(TestCase):
    
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@mail.com",
            password="12345"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        
    def test_retrieve_recipes(self):
        create_sample_recipe(self.user)
        create_sample_recipe(self.user)
        
        res = self.client.get(RECIPES_URL)
        
        recipes = Recipe.objects.all().order_by("-id")
        serializer = RecipeSerializer(recipes, many=True)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        
    def test_recipes_limited_to_user(self):
        user2 = get_user_model().objects.create_user(
            email="testuser2@mail.com",
            password="12345"
        )
        recipe = create_sample_recipe(self.user)
        create_sample_recipe(user2)
        
        res = self.client.get(RECIPES_URL)
        
        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)
        
    def test_view_recipe_detail(self):
        recipe = create_sample_recipe(user=self.user)
        recipe.tags.add(create_sample_tag(user=self.user))
        recipe.ingredients.add(create_sample_ingredient(user=self.user))
        
        url = detail_url(recipe.id)
        res = self.client.get(url)
        
        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)
        
    def test_create_basic_recipe(self):
        payload = {
            'title': 'Chocolate cheesecake',
            'time_minutes': 30,
            'price': 15.00
        }
        res = self.client.post(RECIPES_URL, payload)
        
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))
            
    def test_create_recipe_with_tags(self):
        tag1 = create_sample_tag(user=self.user, name='Vegan')
        tag2 = create_sample_tag(user=self.user, name='Dessert')
        
        payload = {
            'title': 'Avocado cheesecake',
            'tags': [tag1.id, tag2.id],
            'time_minutes': 60,
            'price': 25.00
        }
        res = self.client.post(RECIPES_URL, payload)
        
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)
        
    def test_create_recipe_with_ingredients(self):
        ingredient1 = create_sample_ingredient(user=self.user, name='Prawns')
        ingredient2 = create_sample_ingredient(user=self.user, name='Ginger')
        
        payload = {
            'title': 'Avocado cheesecake',
            'ingredients': [ingredient1.id, ingredient2.id],
            'time_minutes': 20,
            'price': 15.00
        }
        res = self.client.post(RECIPES_URL, payload)
        
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)
        
    def test_parcial_update_recipe(self):
        recipe = create_sample_recipe(user=self.user)
        recipe.tags.add(create_sample_tag(user=self.user))
        new_tag = create_sample_tag(user=self.user, name="New tag")
        
        payload = {
            'title': 'New recipe title',
            'tags': [new_tag.id]
        }
        
        url = detail_url(recipe.id)
        self.client.patch(url, payload)
        
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)
        
    def test_full_update_recipe(self):
        recipe = create_sample_recipe(user=self.user)
        recipe.tags.add(create_sample_tag(user=self.user)) 
        
        payload = {
            'title': 'New recipe title for new test',
            'time_minutes': 45,
            'price': 7.00
        }
        
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.time_minutes, payload['time_minutes'])
        self.assertEqual(recipe.price, payload['price'])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 0)
        
        
class RecipeImageUploadTests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@mail.com",
            password="12345"
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_sample_recipe(user=self.user)
        
    def tearDown(self):
        self.recipe.image.delete()
        
    def test_upload_image_to_recipe(self):
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as ntf:
            img = Image.new('RGB', (10, 10))
            img.save(ntf, format='JPEG')
            ntf.seek(0)
            res = self.client.post(url, {'image': ntf}, format='multipart')
            
        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))
        
    def test_upload_image_bad_request(self):
        url = image_upload_url(self.recipe.id)
        res = self.client.post(url, {'image': 'notimage'}, format='multipart')
        
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_filter_recipes_by_tag(self):
        recipe1 = create_sample_recipe(self.user, title='Thai vegetable curry')
        recipe2 = create_sample_recipe(self.user, title='Aubergine with tahini')
        tag1 = create_sample_tag(user=self.user, name='Vegan')
        tag2 = create_sample_tag(user=self.user, name='Vegetarian')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)
        recipe3 = create_sample_recipe(self.user, title='Fish and chips')
        
        res = self.client.get(
            RECIPES_URL, 
            {'tags': f'{tag1.id},{tag2.id}'}
        )
        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)
        
    def test_filter_recipes_by_ingredients(self):
        recipe1 = create_sample_recipe(self.user, title='Posh beans on toast')
        recipe2 = create_sample_recipe(self.user, title='Chicken cacciatore')
        ingredient1 = create_sample_ingredient(user=self.user, name='Feta cheese')
        ingredient2 = create_sample_ingredient(user=self.user, name='Chicken')
        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)
        recipe3 = create_sample_recipe(self.user, title='Steak and mushrooms')
        
        res = self.client.get(
            RECIPES_URL, 
            {'ingredients': f'{ingredient1.id},{ingredient2.id}'}
        )
        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)