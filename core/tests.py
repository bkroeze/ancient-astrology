"""
Tests for core app - HTMX integration.
"""
from unittest.mock import patch

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


class ChartOfNowTest(TestCase):
    """Test chart-of-now endpoint and partial template."""

    def setUp(self):
        self.client = Client()

    @patch('core.views.generate_chart')
    def test_chart_of_now_authenticated_with_place(self, mock_generate):
        """Authenticated user with default_place gets chart in context."""
        from users.models import User
        from natal.models import Place
        from decimal import Decimal

        mock_generate.return_value = {'chart': '<svg>test</svg>'}

        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060'),
            timezone='America/New_York',
            created_by=user,
        )
        user.default_place = place
        user.save()

        self.client.login(username='test@example.com', password='testpass123')
        response = self.client.get(reverse('core:chart_of_now'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response['Content-Type'].startswith('text/html'),
            f"Expected text/html, got {response['Content-Type']}"
        )
        self.assertContains(response, '<svg>test</svg>')
        mock_generate.assert_called_once()

    def test_chart_of_now_no_default_place(self):
        """Authenticated user without default_place gets empty response."""
        from users.models import User

        user = User.objects.create_user(
            username='noplace',
            email='noplace@example.com',
            password='testpass123'
        )
        self.client.login(username='noplace@example.com', password='testpass123')
        response = self.client.get(reverse('core:chart_of_now'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response['Content-Type'].startswith('text/html'),
            f"Expected text/html, got {response['Content-Type']}"
        )
        # No chart or error — just the loading/empty state
        self.assertNotContains(response, '<svg>')
        self.assertNotContains(response, 'chart-of-now-error')

    def test_chart_of_now_unauthenticated(self):
        """Anonymous user gets empty response (no chart for anonymous)."""
        response = self.client.get(reverse('core:chart_of_now'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response['Content-Type'].startswith('text/html'),
            f"Expected text/html, got {response['Content-Type']}"
        )
        # Should render the empty/loading state
        self.assertNotContains(response, '<svg>')
        self.assertNotContains(response, 'chart-of-now-error')

    @patch('core.views.generate_chart')
    def test_chart_of_now_api_error_handled(self, mock_generate):
        """API errors are handled gracefully with error in context."""
        from users.models import User
        from natal.models import Place
        from decimal import Decimal
        from natal.clients import ChartAPIError

        mock_generate.side_effect = ChartAPIError(
            message="Chart API is unavailable",
            status_code=503
        )

        user = User.objects.create_user(
            username='erroruser',
            email='error@example.com',
            password='testpass123'
        )
        place = Place.objects.create(
            name='London',
            latitude=Decimal('51.5074'),
            longitude=Decimal('-0.1278'),
            timezone='Europe/London',
            created_by=user,
        )
        user.default_place = place
        user.save()

        self.client.login(username='error@example.com', password='testpass123')
        response = self.client.get(reverse('core:chart_of_now'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response['Content-Type'].startswith('text/html'),
            f"Expected text/html, got {response['Content-Type']}"
        )
        self.assertContains(response, 'chart-of-now-error')
        self.assertContains(response, 'Chart API is unavailable')
        self.assertNotContains(response, '<svg>')


class HomeViewChartOfNowTest(TestCase):
    """Test chart-of-now integration in home view."""

    def setUp(self):
        self.client = Client()

    @patch('core.views.generate_chart')
    def test_home_view_with_chart_for_authenticated_user_with_place(self, mock_generate):
        """Home view includes chart context for authenticated user with default_place."""
        from users.models import User
        from natal.models import Place
        from decimal import Decimal

        mock_generate.return_value = {'chart': '<svg>test</svg>'}

        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060'),
            timezone='America/New_York',
            created_by=user,
        )
        user.default_place = place
        user.save()

        self.client.login(username='test@example.com', password='testpass123')
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        # Chart should be in context and rendered
        self.assertIn('chart', response.context)
        self.assertContains(response, 'Chart of Now')
        self.assertContains(response, 'Refresh Chart')
        mock_generate.assert_called_once()

    def test_home_view_without_chart_for_user_without_place(self):
        """Home view does not include chart for authenticated user without default_place."""
        from users.models import User

        user = User.objects.create_user(
            username='noplace',
            email='noplace@example.com',
            password='testpass123'
        )
        self.client.login(username='noplace@example.com', password='testpass123')
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        # No chart in context
        self.assertNotIn('chart', response.context)
        # Widget section should not appear
        self.assertNotContains(response, 'Chart of Now')
        self.assertNotContains(response, 'Refresh Chart')

    def test_home_view_without_chart_for_unauthenticated_user(self):
        """Home view does not include chart for anonymous users."""
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        # No chart in context
        self.assertNotIn('chart', response.context)
        # Widget section should not appear
        self.assertNotContains(response, 'Chart of Now')
        self.assertNotContains(response, 'Refresh Chart')

    @patch('core.views.generate_chart')
    def test_home_view_chart_error_handled_gracefully(self, mock_generate):
        """Home view handles chart generation errors gracefully."""
        from users.models import User
        from natal.models import Place
        from decimal import Decimal
        from natal.clients import ChartAPIError

        mock_generate.side_effect = ChartAPIError(
            message="Chart API is unavailable",
            status_code=503
        )

        user = User.objects.create_user(
            username='erroruser',
            email='error@example.com',
            password='testpass123'
        )
        place = Place.objects.create(
            name='London',
            latitude=Decimal('51.5074'),
            longitude=Decimal('-0.1278'),
            timezone='Europe/London',
            created_by=user,
        )
        user.default_place = place
        user.save()

        self.client.login(username='error@example.com', password='testpass123')
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        # Error should be in context as chart_error
        # ChartAPIError's __str__ includes status code: "ChartAPIError(503): Chart API is unavailable"
        self.assertIn('chart_error', response.context)
        self.assertIn("Chart API is unavailable", response.context['chart_error'])

    def test_home_view_includes_chart_of_now_js(self):
        """Home page includes the chart-of-now.js script."""
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'chart-of-now.js')

    @patch('core.views.generate_chart')
    def test_home_view_chart_refresh_button_works(self, mock_generate):
        """Home view has working HTMX refresh button for chart."""
        from users.models import User
        from natal.models import Place
        from decimal import Decimal

        mock_generate.return_value = {'chart': '<svg>test</svg>'}

        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060'),
            timezone='America/New_York',
            created_by=user,
        )
        user.default_place = place
        user.save()

        self.client.login(username='test@example.com', password='testpass123')
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        # HTMX attributes should be on the refresh button (Django renders URL tags to actual paths)
        self.assertContains(response, 'hx-get="/chart-of-now/"')
        self.assertContains(response, 'hx-target="#chart-of-now-widget"')
        self.assertContains(response, 'hx-swap="innerHTML"')


# =============================================================================
# ONBOARDING WIZARD TESTS
# =============================================================================

class OnboardingWizardTest(TestCase):
    """Test the onboarding wizard flow."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user_without_place = User.objects.create_user(
            username='noplaceuser',
            email='noplace@example.com',
            password='testpass123'
        )
        from allauth.account.models import EmailAddress
        EmailAddress.objects.create(
            user=self.user_without_place,
            email=self.user_without_place.email,
            verified=True,
            primary=True
        )

    def test_home_shows_wizard_for_user_without_place(self):
        """Home page shows wizard for authenticated user without default_place."""
        self.client.login(email='noplace@example.com', password='testpass123')
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        # Should show wizard
        self.assertContains(response, 'id="onboarding-wizard"')
        self.assertContains(response, 'wizard_step1')
        self.assertIn('show_wizard', response.context)
        self.assertTrue(response.context['show_wizard'])

    def test_home_no_wizard_for_user_with_place(self):
        """Home page shows chart, not wizard, for user with default_place."""
        from natal.models import Place
        from decimal import Decimal

        # Create place and assign to user
        place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060'),
            timezone='America/New_York',
            created_by=self.user_without_place,
        )
        self.user_without_place.default_place = place
        self.user_without_place.save()

        self.client.login(email='noplace@example.com', password='testpass123')
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        # Should NOT show wizard
        self.assertNotContains(response, 'id="onboarding-wizard"')
        # Should show chart section
        self.assertContains(response, 'Chart of Now')

    def test_home_no_wizard_for_dismissed_user(self):
        """Home page shows no wizard for user who dismissed it."""
        from django.utils import timezone

        # Mark wizard as dismissed
        self.user_without_place.onboarding_dismissed_at = timezone.now()
        self.user_without_place.save()

        self.client.login(email='noplace@example.com', password='testpass123')
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        # Should NOT show wizard
        self.assertNotContains(response, 'id="onboarding-wizard"')

    def test_home_no_wizard_for_anonymous_user(self):
        """Home page shows no wizard for anonymous users."""
        response = self.client.get(reverse('core:home'))

        self.assertEqual(response.status_code, 200)
        # Should NOT show wizard
        self.assertNotContains(response, 'id="onboarding-wizard"')

    def test_wizard_skip_sets_dismissed_at(self):
        """Skipping wizard sets onboarding_dismissed_at."""
        from django.utils import timezone

        self.client.login(email='noplace@example.com', password='testpass123')

        # Skip the wizard
        response = self.client.post(reverse('core:wizard_skip'))

        self.assertEqual(response.status_code, 200)
        # Verify user was updated
        self.user_without_place.refresh_from_db()
        self.assertIsNotNone(self.user_without_place.onboarding_dismissed_at)
        self.assertLess(
            (timezone.now() - self.user_without_place.onboarding_dismissed_at).total_seconds(),
            5  # Should be very recent
        )

    def test_wizard_skip_redirects_to_empty_if_no_place(self):
        """Skip without place returns empty chart widget."""
        self.client.login(email='noplace@example.com', password='testpass123')

        response = self.client.post(reverse('core:wizard_skip'))

        self.assertEqual(response.status_code, 200)
        # Should return empty placeholder
        self.assertContains(response, 'chart-placeholder')

    @patch('core.wizard.generate_chart')
    def test_wizard_skip_with_place_returns_chart(self, mock_generate):
        """Skip with place set returns chart-of-now partial."""
        from natal.models import Place
        from decimal import Decimal

        # Create place and assign to user
        place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060'),
            timezone='America/New_York',
            created_by=self.user_without_place,
        )
        self.user_without_place.default_place = place
        self.user_without_place.save()

        mock_generate.return_value = {'chart': '<svg>test</svg>'}

        self.client.login(email='noplace@example.com', password='testpass123')
        response = self.client.post(reverse('core:wizard_skip'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<svg>test</svg>')

    def test_wizard_step1_requires_login(self):
        """Wizard step 1 requires authentication."""
        response = self.client.get(reverse('core:wizard_step1'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_wizard_step2_requires_login(self):
        """Wizard step 2 requires authentication."""
        response = self.client.get(reverse('core:wizard_step2'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_wizard_step1_submit_requires_login(self):
        """Wizard step 1 submit requires authentication."""
        response = self.client.post(reverse('core:wizard_step1_submit'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_wizard_step2_submit_requires_login(self):
        """Wizard step 2 submit requires authentication."""
        response = self.client.post(reverse('core:wizard_step2_submit'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_wizard_step1_submit_with_search_data(self):
        """Step 1 submit with search data creates Place and sets default_place."""
        from natal.models import Place
        from decimal import Decimal

        self.client.login(email='noplace@example.com', password='testpass123')

        response = self.client.post(
            reverse('core:wizard_step1_submit'),
            {
                'location_name': 'London',
                'latitude': '51.5074',
                'longitude': '-0.1278',
                'timezone': 'Europe/London',
            }
        )

        self.assertEqual(response.status_code, 200)

        # Verify Place was created
        self.assertTrue(Place.objects.filter(name='London').exists())
        place = Place.objects.get(name='London')
        self.assertEqual(place.latitude, Decimal('51.5074'))
        self.assertEqual(place.longitude, Decimal('-0.1278'))
        self.assertEqual(place.timezone, 'Europe/London')
        self.assertEqual(place.created_by, self.user_without_place)

        # Verify default_place was set
        self.user_without_place.refresh_from_db()
        self.assertEqual(self.user_without_place.default_place, place)

    def test_wizard_step1_reuses_existing_place(self):
        """Step 1 reuses existing Place with same name."""
        from natal.models import Place
        from decimal import Decimal

        # Create existing place
        existing_place = Place.objects.create(
            name='Paris',
            latitude=Decimal('48.8566'),
            longitude=Decimal('2.3522'),
            timezone='Europe/Paris',
            created_by=self.user_without_place,
        )

        self.client.login(email='noplace@example.com', password='testpass123')

        response = self.client.post(
            reverse('core:wizard_step1_submit'),
            {
                'location_name': 'Paris',
                'latitude': '48.8566',
                'longitude': '2.3522',
                'timezone': 'Europe/Paris',
            }
        )

        self.assertEqual(response.status_code, 200)

        # Should reuse existing place, not create new one
        self.assertEqual(Place.objects.filter(name='Paris', created_by=self.user_without_place).count(), 1)

        # Verify default_place was set
        self.user_without_place.refresh_from_db()
        self.assertEqual(self.user_without_place.default_place, existing_place)

    def test_wizard_step1_error_missing_coordinates(self):
        """Step 1 returns error when coordinates are missing."""
        self.client.login(email='noplace@example.com', password='testpass123')

        response = self.client.post(
            reverse('core:wizard_step1_submit'),
            {
                'location_name': '',
                'latitude': '',
                'longitude': '',
                'timezone': '',
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'select a location')

    def test_wizard_step1_error_missing_timezone(self):
        """Step 1 returns error when timezone is missing."""
        self.client.login(email='noplace@example.com', password='testpass123')

        response = self.client.post(
            reverse('core:wizard_step1_submit'),
            {
                'location_name': 'Test Place',
                'latitude': '40.7128',
                'longitude': '-74.0060',
                'timezone': '',
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'timezone')

    @patch('core.wizard.generate_chart')
    def test_wizard_step2_submit_creates_natal_set(self, mock_generate):
        """Step 2 submit creates NatalSet and returns chart-of-now."""
        from natal.models import Place, NatalSet
        from decimal import Decimal

        # Create place first
        place = Place.objects.create(
            name='San Francisco',
            latitude=Decimal('37.7749'),
            longitude=Decimal('-122.4194'),
            timezone='America/Los_Angeles',
            created_by=self.user_without_place,
        )
        self.user_without_place.default_place = place
        self.user_without_place.save()

        mock_generate.return_value = {'chart': '<svg>test</svg>'}

        self.client.login(email='noplace@example.com', password='testpass123')

        response = self.client.post(
            reverse('core:wizard_step2_submit'),
            {
                'birth_datetime': '1990-06-15T12:00',
                'name': 'My Birth Chart',
            }
        )

        self.assertEqual(response.status_code, 200)

        # Verify NatalSet was created
        self.assertTrue(NatalSet.objects.filter(name='My Birth Chart').exists())
        natal_set = NatalSet.objects.get(name='My Birth Chart')
        self.assertEqual(natal_set.owner, self.user_without_place)
        self.assertEqual(natal_set.location_name, 'San Francisco')
        self.assertEqual(natal_set.latitude, Decimal('37.7749'))
        self.assertEqual(natal_set.longitude, Decimal('-122.4194'))
        self.assertEqual(natal_set.timezone, 'America/Los_Angeles')

    @patch('core.wizard.generate_chart')
    def test_wizard_step2_submit_uses_default_name(self, mock_generate):
        """Step 2 submit uses default name when none provided."""
        from natal.models import Place, NatalSet
        from decimal import Decimal

        place = Place.objects.create(
            name='Boston',
            latitude=Decimal('42.3601'),
            longitude=Decimal('-71.0589'),
            timezone='America/New_York',
            created_by=self.user_without_place,
        )
        self.user_without_place.default_place = place
        self.user_without_place.save()

        mock_generate.return_value = {'chart': '<svg>test</svg>'}

        self.client.login(email='noplace@example.com', password='testpass123')

        response = self.client.post(
            reverse('core:wizard_step2_submit'),
            {
                'birth_datetime': '1990-06-15T12:00',
                'name': '',  # Empty name
            }
        )

        self.assertEqual(response.status_code, 200)

        # Verify NatalSet was created with default name
        self.assertTrue(NatalSet.objects.filter(name='My Birth Chart').exists())

    def test_wizard_step2_error_missing_datetime(self):
        """Step 2 returns error when birth_datetime is missing."""
        from natal.models import Place
        from decimal import Decimal

        place = Place.objects.create(
            name='Chicago',
            latitude=Decimal('41.8781'),
            longitude=Decimal('-87.6298'),
            timezone='America/Chicago',
            created_by=self.user_without_place,
        )
        self.user_without_place.default_place = place
        self.user_without_place.save()

        self.client.login(email='noplace@example.com', password='testpass123')

        response = self.client.post(
            reverse('core:wizard_step2_submit'),
            {
                'birth_datetime': '',
                'name': 'Test Chart',
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'enter your birth date')

    def test_wizard_step2_error_no_default_place(self):
        """Step 2 returns error when no default_place is set."""
        self.client.login(email='noplace@example.com', password='testpass123')

        response = self.client.post(
            reverse('core:wizard_step2_submit'),
            {
                'birth_datetime': '1990-06-15T12:00',
                'name': 'Test Chart',
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'default location')
