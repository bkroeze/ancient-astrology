"""
Tests for core app - HTMX integration.
"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse


class HtmxIntegrationTest(TestCase):
    """Test HTMX integration and middleware functionality."""

    def setUp(self):
        self.client = Client()

    def test_home_page_loads(self):
        """Home page should load successfully."""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ancient Astrology')

    def test_home_page_contains_htmx_cdn(self):
        """Home page should include HTMX CDN script."""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'htmx.org')
        self.assertContains(response, 'htmx.min.js')

    def test_home_page_contains_csrf_token(self):
        """Home page should have CSRF token for HTMX requests."""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        # Check that CSRF token is present in the response
        self.assertIn('csrf_token', response.context or {})

    def test_htmx_partial_non_htmx_request(self):
        """Non-HTMX request to partial endpoint should return fallback content."""
        response = self.client.get(reverse('core:htmx_partial'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Non-HTMX fallback')

    def test_htmx_partial_with_htmx_header(self):
        """HTMX request to partial endpoint should return partial content."""
        response = self.client.get(
            reverse('core:htmx_partial'),
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'HTMX request detected')
        self.assertContains(response, 'htmx-result')

    def test_htmx_partial_with_target_header(self):
        """HTMX request with HX-Target header should work correctly."""
        response = self.client.get(
            reverse('core:htmx_partial'),
            HTTP_HX_REQUEST='true',
            HTTP_HX_TARGET='test-target'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'HTMX request detected')


class BaseTemplateTest(TestCase):
    """Test base template rendering."""

    def test_base_template_loads(self):
        """Base template should load without errors."""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)

    def test_base_template_has_navigation(self):
        """Base template should have navigation links."""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Home')
        self.assertContains(response, 'Login')

    def test_base_template_includes_static_css(self):
        """Base template should include static CSS file."""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'main.css')

    def test_authenticated_user_sees_logout(self):
        """Authenticated user should see logout option."""
        from users.models import User
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # User model uses email as USERNAME_FIELD
        self.client.login(username='test@example.com', password='testpass123')
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Logout')
        self.assertContains(response, 'test@example.com')


class HtmxMiddlewareTest(TestCase):
    """Test django-htmx middleware configuration."""

    def test_htmx_middleware_detects_htmx_request(self):
        """Middleware should detect HTMX requests via HX-Request header."""
        response = self.client.get(
            reverse('core:htmx_partial'),
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)

    def test_request_htmx_attribute_available(self):
        """Request object should have htmx attribute after middleware processing."""
        response = self.client.get(
            reverse('core:htmx_partial'),
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'HTMX request detected')


class StaticFilesTest(TestCase):
    """Test static files configuration."""

    def test_static_css_accessible(self):
        """Static CSS file should be configured correctly.
        
        Note: In test mode, Django doesn't serve static files the same way.
        This test verifies the path is configured correctly rather than
        actually serving the file.
        """
        from django.conf import settings
        self.assertTrue(hasattr(settings, 'STATIC_URL'))
        self.assertIn('static', settings.STATIC_URL)
        self.assertIn('static', str(settings.STATICFILES_DIRS))
