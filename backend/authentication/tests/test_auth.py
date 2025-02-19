from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from authentication.models import User

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')  # Will now match URL pattern
        self.login_url = reverse('token_obtain_pair')  # Will now match URL pattern
        self.test_user_data = {
            'username': 'testfarmer',
            'email': 'farmer@test.com',
            'password': 'test123!@#',
            'phone_number': '+250789123456',
            'role': 'FARMER'
        }
        
    def test_user_registration(self):
        """Test user registration endpoint"""
        response = self.client.post(
            self.register_url, 
            self.test_user_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('username', response.data)
        self.assertEqual(response.data['role'], 'FARMER')

    def test_user_login(self):
        """Test user login and token generation"""
        # Create user
        User.objects.create_user(**self.test_user_data)
        
        # Login
        response = self.client.post(
            self.login_url,
            {
                'username': self.test_user_data['username'],
                'password': self.test_user_data['password']
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)