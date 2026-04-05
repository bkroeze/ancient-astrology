from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from django.contrib.sites.models import Site
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
        from django.db import IntegrityError
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


class AllauthFlowTest(TestCase):
    """Tests for django-allauth local authentication flow."""
    
    def setUp(self):
        """Set up test client and ensure Site exists."""
        self.client = Client()
        # Ensure Site record exists
        Site.objects.get_or_create(id=1, defaults={
            'domain': 'localhost',
            'name': 'Test Site'
        })
    
    def test_signup_page_loads(self):
        """Signup page renders correctly."""
        response = self.client.get('/accounts/signup/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign Up')
        self.assertContains(response, 'email')
        self.assertContains(response, 'username')
        self.assertContains(response, 'password')
    
    def test_login_page_loads(self):
        """Login page renders correctly."""
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign In')
        self.assertContains(response, 'login')
    
    def test_logout_requires_post(self):
        """Logout page redirects on GET (POST required for logout)."""
        response = self.client.get('/accounts/logout/')
        # With ACCOUNT_LOGOUT_ON_GET = False, GET redirects
        self.assertEqual(response.status_code, 302)
    
    def test_logout_authenticated_user(self):
        """Authenticated user can log out via POST."""
        from allauth.account.models import EmailAddress
        
        # Create and verify user
        user = User.objects.create_user(
            username='testuser',
            email='logout@example.com',
            password='testpass123'
        )
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=True,
            primary=True
        )
        
        # Login first
        self.client.login(email='logout@example.com', password='testpass123')
        
        # Then logout via POST
        response = self.client.post('/accounts/logout/')
        
        # Should redirect after logout
        self.assertEqual(response.status_code, 302)
    
    def test_signup_creates_user_and_sends_verification(self):
        """Signup creates a user and sends email verification."""
        response = self.client.post('/accounts/signup/', {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })
        
        # Should redirect after successful signup
        self.assertEqual(response.status_code, 302)
        
        # User should be created
        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.username, 'newuser')
        
        # Email verification should be sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Confirm Your Email Address', mail.outbox[0].subject)
    
    def test_signup_duplicate_email_fails(self):
        """Signup with existing email should fail."""
        User.objects.create_user(
            username='existinguser',
            email='test@example.com',
            password='testpass123'
        )
        
        response = self.client.post('/accounts/signup/', {
            'email': 'test@example.com',
            'username': 'newuser',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })
        
        # Should redirect back to signup (allauth behavior)
        self.assertEqual(response.status_code, 302)
        # But user count should still be 1 (no new user created)
        self.assertEqual(User.objects.filter(email='test@example.com').count(), 1)
    
    def test_signup_weak_password_fails(self):
        """Signup with weak password should fail validation."""
        response = self.client.post('/accounts/signup/', {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password1': '123',  # Too short
            'password2': '123',
        })
        
        # Should stay on signup page with form errors
        self.assertEqual(response.status_code, 200)
        # User should not be created
        self.assertFalse(User.objects.filter(email='newuser@example.com').exists())
    
    def test_login_with_verified_email_succeeds(self):
        """Login with verified email should succeed."""
        from allauth.account.models import EmailAddress
        
        # Create user
        user = User.objects.create_user(
            username='testuser',
            email='verified@example.com',
            password='testpass123'
        )
        
        # Mark email as verified
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=True,
            primary=True
        )
        
        response = self.client.post('/accounts/login/', {
            'login': 'verified@example.com',
            'password': 'testpass123',
        })
        
        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)
    
    def test_email_verification_flow(self):
        """Test the full email verification flow - signup sends verification email."""
        # Sign up
        response = self.client.post('/accounts/signup/', {
            'email': 'verify@example.com',
            'username': 'verifyuser',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })
        
        # Should redirect after successful signup
        self.assertEqual(response.status_code, 302)
        
        # Get the verification email
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        
        # Extract verification URL
        self.assertIn('/accounts/confirm-email/', email_body)
    
    def test_password_reset_flow(self):
        """Test password reset request sends email."""
        # Create verified user
        user = User.objects.create_user(
            username='testuser',
            email='reset@example.com',
            password='oldpassword123'
        )
        from allauth.account.models import EmailAddress
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=True,
            primary=True
        )
        
        # Request password reset
        response = self.client.post('/accounts/password/reset/', {
            'email': 'reset@example.com',
        })
        
        # Should redirect after successful request (success_url)
        self.assertEqual(response.status_code, 302)
        
        # Email should be sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Password Reset', mail.outbox[0].subject)
    
    def test_authenticated_user_redirect(self):
        """Authenticated users are redirected from login/signup pages."""
        from allauth.account.models import EmailAddress
        
        # Create and verify user
        user = User.objects.create_user(
            username='testuser',
            email='auth@example.com',
            password='testpass123'
        )
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=True,
            primary=True
        )
        
        # Login
        self.client.login(email='auth@example.com', password='testpass123')
        
        # Try to access signup page - should redirect
        response = self.client.get('/accounts/signup/')
        self.assertEqual(response.status_code, 302)
        
        # Try to access login page - should redirect
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 302)
    
    def test_unauthenticated_access_to_pages(self):
        """Unauthenticated users can access login/signup pages."""
        response = self.client.get('/accounts/signup/')
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)
