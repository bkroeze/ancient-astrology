from django.test import TestCase
from django.db import IntegrityError
from users.models import User


class UserModelTest(TestCase):
    """Tests for the custom User model."""
    
    def test_create_user_with_email(self):
        """User can be created with email as the unique identifier."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('testpass123'))
    
    def test_email_is_unique(self):
        """Email addresses must be unique."""
        User.objects.create_user(
            username='user1',
            email='test@example.com',
            password='testpass123'
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username='user2',
                email='test@example.com',
                password='testpass123'
            )
    
    def test_email_normalized(self):
        """Email addresses should be normalized (lowercase domain)."""
        user = User.objects.create_user(
            username='testuser',
            email='Test@EXAMPLE.COM',
            password='testpass123'
        )
        self.assertEqual(user.email, 'Test@example.com')
    
    def test_str_representation(self):
        """String representation of user should be email."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(str(user), 'test@example.com')
    
    def test_get_by_email(self):
        """Users can be retrieved by email."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        retrieved = User.objects.get(email='test@example.com')
        self.assertEqual(retrieved.id, user.id)
    
    def test_email_required(self):
        """Email is a required field - empty string should fail validation."""
        from django.core.exceptions import ValidationError
        user = User(username='testuser', email='', password='testpass123')
        with self.assertRaises(ValidationError):
            user.full_clean()
