from django.test import TestCase
from django.contrib.auth import get_user_model

from core import models

def sample_user(email="test@mail.com", password="12345"):
    return get_user_model().objects.create_user(email, password)


class ModelTests(TestCase):
    
    def test_create_user_with_email_successful(self):
        email = "test@anything.com"
        password = 'password12345'
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )
        
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
        
    def test_new_user_email_normalized(self):
        email = "test@ANYTHING.com"
        password = 'password12345'
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )
        
        self.assertEqual(user.email, email.lower())
        
    def test_new_user_invalid_email(self):
        with self.assertRaises(ValueError):
            password = 'password12345'
            get_user_model().objects.create_user(
                email=None,
                password=password
            )
            
    def test_create_new_superuser(self):
        email = "test@anything.com"
        password = 'password12345'
        user = get_user_model().objects.create_superuser(
            email=email,
            password=password
        )
        
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_tag_str(self):
        tag = models.Tag.objects.create(
            name='Vegan',
            user=sample_user()
        )
        self.assertEqual(str(tag), tag.name)