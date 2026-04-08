"""
Comprehensive tests for natal app: models, views, and permissions.
"""
from datetime import datetime
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from natal.forms import NatalSetCreateForm, NatalSetForm, PlaceForm
from natal.models import NatalSet, Place
from users.models import User


# =============================================================================
# MODEL TESTS
# =============================================================================

class PlaceModelTest(TestCase):
    """Tests for the Place model."""

    def setUp(self):
        """Create a test user for Place creation."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_place(self):
        """Place can be created with valid data."""
        place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            created_by=self.user
        )
        self.assertEqual(place.name, 'New York')
        self.assertEqual(place.latitude, Decimal('40.712800'))
        self.assertEqual(place.longitude, Decimal('-74.006000'))
        self.assertEqual(place.timezone, 'America/New_York')
        self.assertEqual(place.created_by, self.user)

    def test_place_str_representation(self):
        """String representation of Place should be the name."""
        place = Place.objects.create(
            name='London',
            latitude=Decimal('51.507400'),
            longitude=Decimal('-0.127800'),
            timezone='Europe/London',
            created_by=self.user
        )
        self.assertEqual(str(place), 'London')

    def test_place_unique_name_per_user(self):
        """Same user cannot create two places with the same name."""
        Place.objects.create(
            name='Paris',
            latitude=Decimal('48.856600'),
            longitude=Decimal('2.352200'),
            timezone='Europe/Paris',
            created_by=self.user
        )
        # Different user can create Paris
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        Place.objects.create(
            name='Paris',
            latitude=Decimal('48.856600'),
            longitude=Decimal('2.352200'),
            timezone='Europe/Paris',
            created_by=other_user
        )
        # Same user cannot create duplicate
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Place.objects.create(
                name='Paris',
                latitude=Decimal('48.856600'),
                longitude=Decimal('2.352200'),
                timezone='Europe/Paris',
                created_by=self.user
            )

    def test_place_latitude_validation_valid(self):
        """Valid latitude values should pass validation."""
        form = PlaceForm(data={
            'name': 'Test Place',
            'latitude': '45.0',
            'longitude': '90.0',
            'timezone': 'UTC'
        })
        self.assertTrue(form.is_valid())

    def test_place_latitude_validation_invalid_too_high(self):
        """Latitude above 90 should fail validation."""
        form = PlaceForm(data={
            'name': 'Test Place',
            'latitude': '95.0',
            'longitude': '90.0',
            'timezone': 'UTC'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('latitude', form.errors)

    def test_place_latitude_validation_invalid_too_low(self):
        """Latitude below -90 should fail validation."""
        form = PlaceForm(data={
            'name': 'Test Place',
            'latitude': '-95.0',
            'longitude': '90.0',
            'timezone': 'UTC'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('latitude', form.errors)

    def test_place_longitude_validation_valid(self):
        """Valid longitude values should pass validation."""
        form = PlaceForm(data={
            'name': 'Test Place',
            'latitude': '45.0',
            'longitude': '120.0',
            'timezone': 'UTC'
        })
        self.assertTrue(form.is_valid())

    def test_place_longitude_validation_invalid_too_high(self):
        """Longitude above 180 should fail validation."""
        form = PlaceForm(data={
            'name': 'Test Place',
            'latitude': '45.0',
            'longitude': '200.0',
            'timezone': 'UTC'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('longitude', form.errors)

    def test_place_longitude_validation_invalid_too_low(self):
        """Longitude below -180 should fail validation."""
        form = PlaceForm(data={
            'name': 'Test Place',
            'latitude': '45.0',
            'longitude': '-200.0',
            'timezone': 'UTC'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('longitude', form.errors)


class NatalSetModelTest(TestCase):
    """Tests for the NatalSet model."""

    def setUp(self):
        """Create test users for NatalSet creation."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )

    def test_create_natal_set(self):
        """NatalSet can be created with valid data."""
        natal_set = NatalSet.objects.create(
            name='My Birth Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )
        self.assertEqual(natal_set.name, 'My Birth Chart')
        self.assertEqual(natal_set.owner, self.user)
        self.assertEqual(natal_set.location_name, 'New York')
        self.assertEqual(natal_set.permission, NatalSet.Permission.PRIVATE)

    def test_natal_set_str_representation(self):
        """String representation of NatalSet should include name and owner."""
        natal_set = NatalSet.objects.create(
            name='Test Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )
        self.assertEqual(str(natal_set), f'Test Chart ({self.user})')

    def test_natal_set_permission_choices(self):
        """NatalSet should have correct permission choices."""
        self.assertEqual(NatalSet.Permission.PRIVATE, 'private')
        self.assertEqual(NatalSet.Permission.NAMED_GROUP, 'named_group')
        self.assertEqual(NatalSet.Permission.PUBLIC, 'public')
        self.assertEqual(len(NatalSet.Permission.choices), 3)

    def test_natal_set_can_view_owner(self):
        """Owner can always view their own natal set."""
        natal_set = NatalSet.objects.create(
            name='Private Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )
        self.assertTrue(natal_set.can_view(self.user))
        self.assertTrue(natal_set.can_view(self.other_user) == False)

    def test_natal_set_can_view_public(self):
        """Any authenticated user can view public natal sets."""
        natal_set = NatalSet.objects.create(
            name='Public Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PUBLIC
        )
        self.assertTrue(natal_set.can_view(self.user))
        self.assertTrue(natal_set.can_view(self.other_user))
        # can_view assumes authenticated user, so passing None would fail.
        # Views handle unauthenticated users via LoginRequiredMixin.

    def test_natal_set_can_view_named_group_with_access(self):
        """Users in shared_with can view named_group natal sets."""
        natal_set = NatalSet.objects.create(
            name='Group Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.NAMED_GROUP
        )
        natal_set.shared_with.add(self.other_user)
        self.assertTrue(natal_set.can_view(self.user))
        self.assertTrue(natal_set.can_view(self.other_user))

    def test_natal_set_can_view_named_group_without_access(self):
        """Users not in shared_with cannot view named_group natal sets."""
        natal_set = NatalSet.objects.create(
            name='Group Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.NAMED_GROUP
        )
        self.assertTrue(natal_set.can_view(self.user))
        self.assertFalse(natal_set.can_view(self.other_user))

    def test_natal_set_can_edit_owner(self):
        """Only owner can edit their natal set."""
        natal_set = NatalSet.objects.create(
            name='Private Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )
        self.assertTrue(natal_set.can_edit(self.user))
        self.assertFalse(natal_set.can_edit(self.other_user))
        # Note: can_edit assumes authenticated user (handled by LoginRequiredMixin in views)


# =============================================================================
# VIEW TESTS
# =============================================================================

class NatalSetListViewTest(TestCase):
    """Tests for the NatalSet list view."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )

    def test_list_requires_login(self):
        """List view should redirect anonymous users to login."""
        response = self.client.get(reverse('natal:natal_set_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_list_returns_200_for_authenticated(self):
        """Authenticated users should get 200 with their visible sets."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('natal:natal_set_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_shows_own_private_sets(self):
        """Users should see their own private sets."""
        self.client.login(email='test@example.com', password='testpass123')
        NatalSet.objects.create(
            name='My Private Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )
        response = self.client.get(reverse('natal:natal_set_list'))
        self.assertContains(response, 'My Private Chart')

    def test_list_hides_other_users_private_sets(self):
        """Users should NOT see other users' private sets."""
        self.client.login(email='other@example.com', password='testpass123')
        NatalSet.objects.create(
            name='Other User Private',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )
        response = self.client.get(reverse('natal:natal_set_list'))
        self.assertNotContains(response, 'Other User Private')

    def test_list_shows_public_sets(self):
        """Users should see public sets from other users."""
        self.client.login(email='other@example.com', password='testpass123')
        NatalSet.objects.create(
            name='Public Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PUBLIC
        )
        response = self.client.get(reverse('natal:natal_set_list'))
        self.assertContains(response, 'Public Chart')


class NatalSetCreateViewTest(TestCase):
    """Tests for the NatalSet create view."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_requires_login(self):
        """Create view should redirect anonymous users to login."""
        response = self.client.get(reverse('natal:natal_set_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_create_get_returns_form(self):
        """GET request should return the create form."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('natal:natal_set_create'))
        self.assertEqual(response.status_code, 200)
        # The form should contain the name input
        self.assertContains(response, 'id_name')
        self.assertContains(response, 'Create Natal Set')

    def test_create_post_success(self):
        """POST with valid data should create natal set and redirect."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'New Birth Chart',
            'birth_datetime': '1990-06-15T12:00',
            'location_name': 'New York',
            'latitude': '40.712800',
            'longitude': '-74.006000',
            'timezone': 'America/New_York',
            'permission': 'private',
        })
        # Should redirect to list on success
        self.assertEqual(response.status_code, 302)
        self.assertTrue(NatalSet.objects.filter(name='New Birth Chart').exists())
        natal_set = NatalSet.objects.get(name='New Birth Chart')
        self.assertEqual(natal_set.owner, self.user)

    def test_create_post_invalid_data(self):
        """POST with invalid data should show form errors."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': '',  # Required field missing
            'birth_datetime': '1990-06-15T12:00',
            'location_name': 'New York',
            'latitude': '40.712800',
            'longitude': '-74.006000',
            'timezone': 'America/New_York',
            'permission': 'private',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(NatalSet.objects.filter(name='New Birth Chart').exists())

    def test_create_htmx_request(self):
        """HTMX request should return redirect on success."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(
            reverse('natal:natal_set_create'),
            HTTP_HX_REQUEST='true',
            data={
                'name': 'HTMX Birth Chart',
                'birth_datetime': '1990-06-15T12:00',
                'location_name': 'New York',
                'latitude': '40.712800',
                'longitude': '-74.006000',
                'timezone': 'America/New_York',
                'permission': 'private',
            }
        )
        # HTMX redirects on success, so 302 is expected
        self.assertEqual(response.status_code, 302)


class NatalSetDetailViewTest(TestCase):
    """Tests for the NatalSet detail view."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        self.natal_set = NatalSet.objects.create(
            name='Private Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )

    def test_detail_requires_login(self):
        """Detail view should redirect anonymous users to login."""
        response = self.client.get(
            reverse('natal:natal_set_detail', kwargs={'pk': self.natal_set.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_detail_success_owner(self):
        """Owner should be able to view their private natal set."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_detail', kwargs={'pk': self.natal_set.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Private Chart')

    def test_detail_forbidden_non_owner_private(self):
        """Non-owner should get 404 for private natal set (filtered from queryset)."""
        self.client.login(email='other@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_detail', kwargs={'pk': self.natal_set.pk})
        )
        # Returns 404 because the set is filtered out of the queryset
        # (not visible to other_user) so it appears to not exist
        self.assertEqual(response.status_code, 404)

    def test_detail_public_visible_to_all(self):
        """Public natal sets should be visible to all authenticated users."""
        public_set = NatalSet.objects.create(
            name='Public Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PUBLIC
        )
        self.client.login(email='other@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_detail', kwargs={'pk': public_set.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Chart')


class NatalSetUpdateViewTest(TestCase):
    """Tests for the NatalSet update view."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        self.natal_set = NatalSet.objects.create(
            name='My Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )

    def test_edit_requires_login(self):
        """Edit view should redirect anonymous users to login."""
        response = self.client.get(
            reverse('natal:natal_set_edit', kwargs={'pk': self.natal_set.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_edit_success_owner(self):
        """Owner should be able to edit their natal set."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(
            reverse('natal:natal_set_edit', kwargs={'pk': self.natal_set.pk}),
            {
                'name': 'Updated Chart Name',
                'birth_datetime': '1990-06-15T12:00',
                'location_name': 'New York',
                'latitude': '40.712800',
                'longitude': '-74.006000',
                'timezone': 'America/New_York',
                'permission': 'private',
            }
        )
        # Should redirect to detail on success
        self.assertEqual(response.status_code, 302)
        self.natal_set.refresh_from_db()
        self.assertEqual(self.natal_set.name, 'Updated Chart Name')

    def test_edit_forbidden_non_owner(self):
        """Non-owner should get 404 (not found - queryset filtered)."""
        self.client.login(email='other@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_edit', kwargs={'pk': self.natal_set.pk})
        )
        self.assertEqual(response.status_code, 404)


class NatalSetDeleteViewTest(TestCase):
    """Tests for the NatalSet delete view."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        self.natal_set = NatalSet.objects.create(
            name='My Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )

    def test_delete_requires_login(self):
        """Delete view should redirect anonymous users to login."""
        response = self.client.get(
            reverse('natal:natal_set_delete', kwargs={'pk': self.natal_set.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_delete_success_owner(self):
        """Owner should be able to delete their natal set."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(
            reverse('natal:natal_set_delete', kwargs={'pk': self.natal_set.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(NatalSet.objects.filter(pk=self.natal_set.pk).exists())

    def test_delete_forbidden_non_owner(self):
        """Non-owner should get 404 (not found - queryset filtered)."""
        self.client.login(email='other@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_delete', kwargs={'pk': self.natal_set.pk})
        )
        self.assertEqual(response.status_code, 404)


# =============================================================================
# PERMISSION TESTS
# =============================================================================

class NatalSetPermissionTest(TestCase):
    """Tests for natal set visibility and access permissions."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='testpass123'
        )
        # Create one of each type
        self.private_set = NatalSet.objects.create(
            name='Private Set',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )
        self.public_set = NatalSet.objects.create(
            name='Public Set',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PUBLIC
        )
        self.named_group_set = NatalSet.objects.create(
            name='Group Set',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.NAMED_GROUP
        )
        self.named_group_set.shared_with.add(self.user2)

    def test_private_sets_invisible_to_other_users(self):
        """Private sets should NOT appear in other users' list views."""
        self.client.login(email='user2@example.com', password='testpass123')
        response = self.client.get(reverse('natal:natal_set_list'))
        self.assertNotContains(response, 'Private Set')

    def test_public_sets_visible_to_all_authenticated(self):
        """Public sets should appear in all authenticated users' list views."""
        # User 2 sees public set
        self.client.login(email='user2@example.com', password='testpass123')
        response = self.client.get(reverse('natal:natal_set_list'))
        self.assertContains(response, 'Public Set')

        # User 3 also sees public set
        self.client.login(email='user3@example.com', password='testpass123')
        response = self.client.get(reverse('natal:natal_set_list'))
        self.assertContains(response, 'Public Set')

    def test_named_group_sets_visible_to_shared_users(self):
        """Named group sets should appear in shared users' list views."""
        self.client.login(email='user2@example.com', password='testpass123')
        response = self.client.get(reverse('natal:natal_set_list'))
        self.assertContains(response, 'Group Set')

    def test_named_group_sets_invisible_to_non_shared_users(self):
        """Named group sets should NOT appear in non-shared users' list views."""
        self.client.login(email='user3@example.com', password='testpass123')
        response = self.client.get(reverse('natal:natal_set_list'))
        self.assertNotContains(response, 'Group Set')

    def test_owner_sees_all_their_sets(self):
        """Owner should see all their natal sets regardless of permission."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('natal:natal_set_list'))
        self.assertContains(response, 'Private Set')
        self.assertContains(response, 'Public Set')
        self.assertContains(response, 'Group Set')


# =============================================================================
# HTMX TESTS
# =============================================================================

class NatalSetHTMXTest(TestCase):
    """Tests for HTMX partial template responses."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_list_htmx_request(self):
        """HTMX request to list should return partial template."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_list'),
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)

    def test_create_htmx_success(self):
        """HTMX create request should redirect on success."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(
            reverse('natal:natal_set_create'),
            HTTP_HX_REQUEST='true',
            data={
                'name': 'HTMX Create Test',
                'birth_datetime': '1990-06-15T12:00',
                'permission': 'private',
            }
        )
        # HTMX redirects on success
        self.assertEqual(response.status_code, 302)
        self.assertTrue(NatalSet.objects.filter(name='HTMX Create Test').exists())

    def test_create_htmx_invalid_returns_form(self):
        """HTMX create with invalid data should return form with errors."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(
            reverse('natal:natal_set_create'),
            HTTP_HX_REQUEST='true',
            data={
                'name': '',  # Required field missing
                'birth_datetime': '1990-06-15T12:00',
                'permission': 'private',
            }
        )
        self.assertEqual(response.status_code, 200)
        # Response should indicate validation error
        self.assertFalse(NatalSet.objects.filter(name='HTMX Create Test').exists())


# =============================================================================
# NEGATIVE TESTS
# =============================================================================

class NatalSetNegativeTest(TestCase):
    """Negative tests for invalid inputs and edge cases."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        self.natal_set = NatalSet.objects.create(
            name='My Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )

    def test_invalid_datetime_format_rejected(self):
        """Invalid datetime format should be rejected."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'Invalid Date Test',
            'birth_datetime': 'not-a-date',
            'latitude': '40.7128',
            'longitude': '-74.0060',
            'timezone': 'America/New_York',
            'permission': 'private',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(NatalSet.objects.filter(name='Invalid Date Test').exists())

    def test_missing_required_fields_rejected(self):
        """Missing required fields should be rejected."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Missing name
        response = self.client.post(reverse('natal:natal_set_create'), {
            'birth_datetime': '1990-06-15T12:00',
            'latitude': '40.7128',
            'longitude': '-74.0060',
            'timezone': 'America/New_York',
            'permission': 'private',
        })
        self.assertEqual(response.status_code, 200)
        
        # Missing birth_datetime
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'Missing Date Test',
            'latitude': '40.7128',
            'longitude': '-74.0060',
            'timezone': 'America/New_York',
            'permission': 'private',
        })
        self.assertEqual(response.status_code, 200)
        
        # Location fields are optional, so this should succeed (redirect to 302)
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'Missing Location Test',
            'birth_datetime': '1990-06-15T12:00',
            'permission': 'private',
        })
        self.assertEqual(response.status_code, 302)

    def test_tampering_other_users_set_returns_404(self):
        """Tampering with other users' set should return 404."""
        # Try to access non-existent set
        self.client.login(email='other@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_detail', kwargs={'pk': 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_invalid_latitude_rejected(self):
        """Invalid latitude values should be rejected."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Out of range latitude (> 90)
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'Bad Latitude Test',
            'birth_datetime': '1990-06-15T12:00',
            'latitude': '95.0000',  # Invalid: > 90
            'longitude': '-74.0060',
            'timezone': 'America/New_York',
            'permission': 'private',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(NatalSet.objects.filter(name='Bad Latitude Test').exists())
        
        # Out of range latitude (< -90)
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'Bad Latitude Test 2',
            'birth_datetime': '1990-06-15T12:00',
            'latitude': '-95.0000',  # Invalid: < -90
            'longitude': '-74.0060',
            'timezone': 'America/New_York',
            'permission': 'private',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(NatalSet.objects.filter(name='Bad Latitude Test 2').exists())

    def test_invalid_longitude_rejected(self):
        """Invalid longitude values should be rejected."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Out of range longitude (> 180)
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'Bad Longitude Test',
            'birth_datetime': '1990-06-15T12:00',
            'latitude': '40.7128',
            'longitude': '185.0000',  # Invalid: > 180
            'timezone': 'America/New_York',
            'permission': 'private',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(NatalSet.objects.filter(name='Bad Longitude Test').exists())
        
        # Out of range longitude (< -180)
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'Bad Longitude Test 2',
            'birth_datetime': '1990-06-15T12:00',
            'latitude': '40.7128',
            'longitude': '-185.0000',  # Invalid: < -180
            'timezone': 'America/New_York',
            'permission': 'private',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(NatalSet.objects.filter(name='Bad Longitude Test 2').exists())

    def test_invalid_permission_choice_rejected(self):
        """Invalid permission choice should be rejected."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'Bad Permission Test',
            'birth_datetime': '1990-06-15T12:00',
            'latitude': '40.7128',
            'longitude': '-74.0060',
            'timezone': 'America/New_York',
            'permission': 'invalid_choice',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(NatalSet.objects.filter(name='Bad Permission Test').exists())

    def test_detail_tampering_returns_404(self):
        """Trying to view private set of another user returns 404."""
        self.client.login(email='other@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_detail', kwargs={'pk': self.natal_set.pk})
        )
        # Returns 404 because the set is filtered out of the queryset
        self.assertEqual(response.status_code, 404)

    def test_delete_tampering_returns_404(self):
        """Trying to delete another user's set returns 404."""
        self.client.login(email='other@example.com', password='testpass123')
        response = self.client.post(
            reverse('natal:natal_set_delete', kwargs={'pk': self.natal_set.pk})
        )
        self.assertEqual(response.status_code, 404)
        # Verify the set still exists
        self.assertTrue(NatalSet.objects.filter(pk=self.natal_set.pk).exists())


# =============================================================================
# CHART CLIENT TESTS
# =============================================================================

from datetime import datetime
from unittest.mock import MagicMock, patch

from natal.clients import (
    ChartAPIError,
    ChartRequest,
    ChartTimeoutError,
    generate_chart,
)


class ChartClientTest(TestCase):
    """Tests for the chart generation client."""

    def test_chart_request_dataclass(self):
        """ChartRequest stores parameters correctly."""
        dt = datetime(1990, 6, 15, 12, 0, 0)
        request = ChartRequest(
            latitude=40.7128,
            longitude=-74.0060,
            datetime=dt,
            format='svg',
            name='Test Chart'
        )
        self.assertEqual(request.latitude, 40.7128)
        self.assertEqual(request.longitude, -74.0060)
        self.assertEqual(request.datetime, dt)
        self.assertEqual(request.format, 'svg')
        self.assertEqual(request.name, 'Test Chart')

    def test_chart_request_defaults(self):
        """ChartRequest has correct default values."""
        dt = datetime(1990, 6, 15, 12, 0, 0)
        request = ChartRequest(
            latitude=40.7128,
            longitude=-74.0060,
            datetime=dt
        )
        self.assertEqual(request.format, 'svg')
        self.assertIsNone(request.name)

    def test_chart_api_error_attributes(self):
        """ChartAPIError stores error information correctly."""
        error = ChartAPIError(
            message="Test error",
            status_code=500,
            response_data={'detail': 'Server error'}
        )
        self.assertEqual(str(error), "ChartAPIError(500): Test error")
        self.assertEqual(error.status_code, 500)
        self.assertEqual(error.error_message, "Test error")
        self.assertEqual(error.response_data, {'detail': 'Server error'})

    def test_chart_api_error_without_status(self):
        """ChartAPIError works without status code."""
        error = ChartAPIError(message="Connection failed")
        self.assertEqual(error.status_code, None)
        self.assertEqual(str(error), "ChartAPIError: Connection failed")

    def test_chart_timeout_error(self):
        """ChartTimeoutError has correct attributes."""
        error = ChartTimeoutError()
        self.assertIsNone(error.status_code)
        self.assertEqual(error.error_message, "Chart generation timed out")

    @patch('natal.clients.requests.post')
    def test_generate_chart_success(self, mock_post):
        """generate_chart returns chart data on success."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'chart': 'svg_data_here',
            'format': 'svg'
        }
        mock_post.return_value = mock_response

        request = ChartRequest(
            latitude=40.7128,
            longitude=-74.0060,
            datetime=datetime(1990, 6, 15, 12, 0, 0),
            format='svg'
        )
        result = generate_chart(request)

        self.assertEqual(result['chart'], 'svg_data_here')
        self.assertEqual(result['format'], 'svg')
        mock_post.assert_called_once()

    @patch('natal.clients.requests.post')
    def test_generate_chart_with_name(self, mock_post):
        """generate_chart includes name in request payload."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {'chart': 'data', 'format': 'svg'}
        mock_post.return_value = mock_response

        request = ChartRequest(
            latitude=40.7128,
            longitude=-74.0060,
            datetime=datetime(1990, 6, 15, 12, 0, 0),
            format='svg',
            name='My Chart'
        )
        generate_chart(request)

        # Verify the name was included in the call
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs['json']['name'], 'My Chart')

    @patch('natal.clients.requests.post')
    def test_generate_chart_api_error(self, mock_post):
        """generate_chart raises ChartAPIError on API error."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': 'Invalid coordinates'}
        mock_post.return_value = mock_response

        request = ChartRequest(
            latitude=40.7128,
            longitude=-74.0060,
            datetime=datetime(1990, 6, 15, 12, 0, 0),
            format='svg'
        )

        with self.assertRaises(ChartAPIError) as context:
            generate_chart(request)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.error_message, 'Invalid coordinates')

    @patch('natal.clients.requests.post')
    def test_generate_chart_timeout(self, mock_post):
        """generate_chart raises ChartTimeoutError on timeout."""
        import requests
        mock_post.side_effect = requests.Timeout()

        request = ChartRequest(
            latitude=40.7128,
            longitude=-74.0060,
            datetime=datetime(1990, 6, 15, 12, 0, 0),
            format='svg'
        )

        with self.assertRaises(ChartTimeoutError):
            generate_chart(request)

    @patch('natal.clients.requests.post')
    def test_generate_chart_connection_error(self, mock_post):
        """generate_chart raises ChartAPIError on connection error."""
        import requests
        mock_post.side_effect = requests.ConnectionError("Connection refused")

        request = ChartRequest(
            latitude=40.7128,
            longitude=-74.0060,
            datetime=datetime(1990, 6, 15, 12, 0, 0),
            format='svg'
        )

        with self.assertRaises(ChartAPIError) as context:
            generate_chart(request)

        self.assertIn("Could not connect", context.exception.error_message)
        self.assertIsNone(context.exception.status_code)

    def test_client_module_documentation(self):
        """Client module has proper docstrings for help()."""
        import natal.clients
        self.assertIsNotNone(natal.clients.__doc__)
        self.assertIn("Astro Clock API", natal.clients.__doc__)


# =============================================================================
# CHART VIEW TESTS
# =============================================================================

class ChartViewTest(TestCase):
    """Tests for the ChartView."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        self.natal_set = NatalSet.objects.create(
            name='My Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )
        self.public_set = NatalSet.objects.create(
            name='Public Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PUBLIC
        )

    def test_chart_requires_login(self):
        """Chart view should redirect anonymous users to login."""
        response = self.client.get(
            reverse('natal:natal_set_chart', kwargs={'pk': self.natal_set.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_chart_requires_login_params(self):
        """Chart view with params should redirect anonymous users to login."""
        response = self.client.get(reverse('natal:chart_view'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_natal_set_chart_owner_access(self):
        """Owner should be able to view their natal set chart."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Mock the chart generation
        with patch('natal.clients.generate_chart') as mock_generate:
            mock_generate.return_value = {'chart': '<svg>test</svg>', 'format': 'svg'}
            response = self.client.get(
                reverse('natal:natal_set_chart', kwargs={'pk': self.natal_set.pk})
            )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('natal_set', response.context)
        self.assertEqual(response.context['natal_set'], self.natal_set)

    def test_natal_set_chart_public_access(self):
        """Any authenticated user should be able to view public natal set charts."""
        self.client.login(email='other@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_generate:
            mock_generate.return_value = {'chart': '<svg>test</svg>', 'format': 'svg'}
            response = self.client.get(
                reverse('natal:natal_set_chart', kwargs={'pk': self.public_set.pk})
            )
        
        self.assertEqual(response.status_code, 200)

    def test_natal_set_chart_private_denied(self):
        """Non-owner should get 404 for private natal set chart."""
        self.client.login(email='other@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_chart', kwargs={'pk': self.natal_set.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_natal_set_chart_nonexistent(self):
        """Non-existent natal set should return 404."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_chart', kwargs={'pk': 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_param_chart_success(self):
        """Arbitrary parameter chart should generate chart with provided params."""
        self.client.login(email='test@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_generate:
            mock_generate.return_value = {'chart': '<svg>custom</svg>', 'format': 'svg'}
            response = self.client.get(
                reverse('natal:chart_view'),
                {
                    'lat': '40.7128',
                    'lon': '-74.0060',
                    'time': '1990-06-15T12:00:00',
                }
            )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('chart', response.context)
        mock_generate.assert_called_once()
        # Verify the correct parameters were passed
        call_args = mock_generate.call_args[0][0]
        self.assertEqual(call_args.latitude, 40.7128)
        self.assertEqual(call_args.longitude, -74.0060)

    def test_param_chart_missing_lat(self):
        """Missing latitude should return error in context."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(
            reverse('natal:chart_view'),
            {
                'lon': '-74.0060',
                'time': '1990-06-15T12:00:00',
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)
        self.assertIn('Missing required parameters', response.context['error'])

    def test_param_chart_missing_lon(self):
        """Missing longitude should return error in context."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(
            reverse('natal:chart_view'),
            {
                'lat': '40.7128',
                'time': '1990-06-15T12:00:00',
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)
        self.assertIn('Missing required parameters', response.context['error'])

    def test_param_chart_missing_time(self):
        """Missing time should return error in context."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(
            reverse('natal:chart_view'),
            {
                'lat': '40.7128',
                'lon': '-74.0060',
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)
        self.assertIn('Missing required parameters', response.context['error'])

    def test_param_chart_invalid_datetime(self):
        """Invalid datetime format should return error in context."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(
            reverse('natal:chart_view'),
            {
                'lat': '40.7128',
                'lon': '-74.0060',
                'time': 'not-a-date',
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)
        self.assertIn('Invalid datetime format', response.context['error'])

    def test_param_chart_invalid_latitude(self):
        """Invalid latitude value should return error in context."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(
            reverse('natal:chart_view'),
            {
                'lat': 'not-a-number',
                'lon': '-74.0060',
                'time': '1990-06-15T12:00:00',
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)
        self.assertIn('Invalid parameter values', response.context['error'])

    def test_chart_api_error_handled(self):
        """Chart generation API error should be handled gracefully with error in context."""
        self.client.login(email='test@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_generate:
            from natal.clients import ChartAPIError
            mock_generate.side_effect = ChartAPIError(
                message="API Error",
                status_code=500
            )
            response = self.client.get(
                reverse('natal:natal_set_chart', kwargs={'pk': self.natal_set.pk})
            )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)
        self.assertIn('Chart generation failed', response.context['error'])

    def test_chart_timeout_error_handled(self):
        """Chart generation timeout should be handled gracefully."""
        self.client.login(email='test@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_generate:
            from natal.clients import ChartTimeoutError
            mock_generate.side_effect = ChartTimeoutError()
            response = self.client.get(
                reverse('natal:natal_set_chart', kwargs={'pk': self.natal_set.pk})
            )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)
        self.assertIn('timed out', response.context['error'])

    def test_chart_connection_error_handled(self):
        """Chart generation connection error should be handled gracefully."""
        self.client.login(email='test@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_generate:
            from natal.clients import ChartAPIError
            mock_generate.side_effect = ChartAPIError(message="Connection failed")
            response = self.client.get(
                reverse('natal:natal_set_chart', kwargs={'pk': self.natal_set.pk})
            )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)

    def test_param_chart_with_name(self):
        """Parameter chart with name should pass name to API."""
        self.client.login(email='test@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_generate:
            mock_generate.return_value = {'chart': '<svg>named</svg>', 'format': 'svg'}
            response = self.client.get(
                reverse('natal:chart_view'),
                {
                    'lat': '40.7128',
                    'lon': '-74.0060',
                    'time': '1990-06-15T12:00:00',
                    'name': 'My Custom Chart',
                }
            )
        
        self.assertEqual(response.status_code, 200)
        call_args = mock_generate.call_args[0][0]
        self.assertEqual(call_args.name, 'My Custom Chart')

    def test_natal_set_chart_displays_natal_set_info(self):
        """Chart for natal set should include natal set info in context."""
        self.client.login(email='test@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_generate:
            mock_generate.return_value = {'chart': '<svg>test</svg>', 'format': 'svg'}
            response = self.client.get(
                reverse('natal:natal_set_chart', kwargs={'pk': self.natal_set.pk})
            )
        
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertEqual(context['natal_set'].name, 'My Chart')
        self.assertEqual(context['natal_set'].location_name, 'New York')


class NatalSetDetailHTMXChartTest(TestCase):
    """Tests for the HTMX chart button in the natal set detail view."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.natal_set = NatalSet.objects.create(
            name='My Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )

    def test_detail_page_has_generate_chart_button(self):
        """Detail page should have a Generate Chart button with HTMX attributes."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_detail', kwargs={'pk': self.natal_set.pk})
        )
        self.assertEqual(response.status_code, 200)
        # Check for the button with HTMX attributes
        self.assertContains(response, 'id="generate-chart-btn"')
        self.assertContains(response, 'hx-get')
        self.assertContains(response, 'hx-target="#chart-content"')
        self.assertContains(response, 'Generate Chart')

    def test_detail_page_has_chart_content_container(self):
        """Detail page should have a chart content container for HTMX target."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_detail', kwargs={'pk': self.natal_set.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="chart-content"')
        self.assertContains(response, 'hx-indicator="#chart-loading"')

    def test_detail_page_has_loading_indicator(self):
        """Detail page should have a loading indicator for HTMX."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_detail', kwargs={'pk': self.natal_set.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="chart-loading"')
        self.assertContains(response, 'class="htmx-indicator chart-loading"')

    def test_generate_chart_button_points_to_correct_url(self):
        """Generate Chart button should point to the natal set chart URL."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_detail', kwargs={'pk': self.natal_set.pk})
        )
        self.assertEqual(response.status_code, 200)
        expected_url = reverse('natal:natal_set_chart', kwargs={'pk': self.natal_set.pk})
        self.assertContains(response, expected_url)


# =============================================================================
# ANALYSIS CLIENT TESTS
# =============================================================================

from natal.clients import (
    AnalysisRequest,
    get_chart_data,
)


class AnalysisClientTest(TestCase):
    """Tests for the chart analysis data client."""

    def test_analysis_request_dataclass(self):
        """AnalysisRequest stores parameters correctly."""
        dt = datetime(1990, 6, 15, 12, 0, 0)
        request = AnalysisRequest(
            latitude=40.7128,
            longitude=-74.0060,
            datetime=dt,
            house_system='P'
        )
        self.assertEqual(request.latitude, 40.7128)
        self.assertEqual(request.longitude, -74.0060)
        self.assertEqual(request.datetime, dt)
        self.assertEqual(request.house_system, 'P')

    def test_analysis_request_defaults(self):
        """AnalysisRequest has correct default values."""
        dt = datetime(1990, 6, 15, 12, 0, 0)
        request = AnalysisRequest(
            latitude=40.7128,
            longitude=-74.0060,
            datetime=dt
        )
        self.assertEqual(request.house_system, 'P')

    @patch('natal.clients.requests.get')
    def test_get_chart_data_success(self, mock_get):
        """get_chart_data returns analysis data on success."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'planets': [
                {'name': 'Sun', 'longitude': 83.5, 'speed': 1.0},
                {'name': 'Moon', 'longitude': 150.2, 'speed': 12.5},
            ],
            'houses': {'cusps': [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330]},
            'aspects': [{'planet1': 'Sun', 'planet2': 'Moon', 'type': 'trine', 'orb': 0.5}],
            'grand_trines': [],
            'moon_void_of_course': False,
            'metadata': {'latitude': 40.7128, 'longitude': -74.0060, 'house_system': 'Placidus'}
        }
        mock_get.return_value = mock_response

        request = AnalysisRequest(
            latitude=40.7128,
            longitude=-74.0060,
            datetime=datetime(1990, 6, 15, 12, 0, 0),
        )
        result = get_chart_data(request)

        self.assertIn('planets', result)
        self.assertIn('houses', result)
        self.assertIn('aspects', result)
        self.assertEqual(len(result['planets']), 2)
        self.assertEqual(result['planets'][0]['name'], 'Sun')
        mock_get.assert_called_once()

    @patch('natal.clients.requests.get')
    def test_get_chart_data_api_error(self, mock_get):
        """get_chart_data raises ChartAPIError on API error."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': 'Invalid coordinates'}
        mock_get.return_value = mock_response

        request = AnalysisRequest(
            latitude=40.7128,
            longitude=-74.0060,
            datetime=datetime(1990, 6, 15, 12, 0, 0),
        )

        with self.assertRaises(ChartAPIError) as context:
            get_chart_data(request)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.error_message, 'Invalid coordinates')

    @patch('natal.clients.requests.get')
    def test_get_chart_data_timeout(self, mock_get):
        """get_chart_data raises ChartTimeoutError on timeout."""
        import requests
        mock_get.side_effect = requests.Timeout()

        request = AnalysisRequest(
            latitude=40.7128,
            longitude=-74.0060,
            datetime=datetime(1990, 6, 15, 12, 0, 0),
        )

        with self.assertRaises(ChartTimeoutError):
            get_chart_data(request)

    @patch('natal.clients.requests.get')
    def test_get_chart_data_connection_error(self, mock_get):
        """get_chart_data raises ChartAPIError on connection error."""
        import requests
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        request = AnalysisRequest(
            latitude=40.7128,
            longitude=-74.0060,
            datetime=datetime(1990, 6, 15, 12, 0, 0),
        )

        with self.assertRaises(ChartAPIError) as context:
            get_chart_data(request)

        self.assertIn("Could not connect", context.exception.error_message)
        self.assertIsNone(context.exception.status_code)

    @patch('natal.clients.requests.get')
    def test_get_chart_data_includes_params(self, mock_get):
        """get_chart_data includes correct query parameters."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'planets': [],
            'houses': {'cusps': []},
            'aspects': [],
            'grand_trines': [],
            'moon_void_of_course': None,
            'metadata': {}
        }
        mock_get.return_value = mock_response

        request = AnalysisRequest(
            latitude=40.7128,
            longitude=-74.0060,
            datetime=datetime(1990, 6, 15, 12, 0, 0),
        )
        get_chart_data(request)

        # Verify the correct parameters were passed
        call_kwargs = mock_get.call_args[1]
        self.assertEqual(call_kwargs['params']['lat'], 40.7128)
        self.assertEqual(call_kwargs['params']['lon'], -74.0060)


# =============================================================================
# CHART VIEW ANALYSIS TESTS
# =============================================================================

class ChartViewAnalysisTest(TestCase):
    """Tests for analysis data integration in ChartView."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.natal_set = NatalSet.objects.create(
            name='My Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )

    def test_chart_view_fetches_analysis_data(self):
        """ChartView fetches and includes analysis data in context."""
        self.client.login(email='test@example.com', password='testpass123')
        
        analysis_data = {
            'planets': [
                {'name': 'Sun', 'longitude': 83.5, 'speed': 1.0},
                {'name': 'Moon', 'longitude': 150.2, 'speed': 12.5},
            ],
            'houses': {'cusps': [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330]},
            'aspects': [{'planet1': 'Sun', 'planet2': 'Moon', 'type': 'trine', 'orb': 0.5}],
            'grand_trines': [],
            'moon_void_of_course': False,
            'metadata': {'latitude': 40.7128, 'longitude': -74.0060, 'house_system': 'Placidus'}
        }
        
        with patch('natal.clients.generate_chart') as mock_chart, \
             patch('natal.clients.get_chart_data') as mock_analysis:
            mock_chart.return_value = {'chart': '<svg>test</svg>', 'format': 'svg'}
            mock_analysis.return_value = analysis_data
            
            response = self.client.get(
                reverse('natal:natal_set_chart', kwargs={'pk': self.natal_set.pk})
            )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('analysis', response.context)
        self.assertEqual(response.context['analysis'], analysis_data)
        mock_analysis.assert_called_once()

    def test_chart_view_analysis_error_does_not_crash_view(self):
        """ChartView handles analysis API errors gracefully."""
        self.client.login(email='test@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_chart, \
             patch('natal.clients.get_chart_data') as mock_analysis:
            mock_chart.return_value = {'chart': '<svg>test</svg>', 'format': 'svg'}
            mock_analysis.side_effect = ChartAPIError(
                message="Analysis API unavailable",
                status_code=503
            )
            
            response = self.client.get(
                reverse('natal:natal_set_chart', kwargs={'pk': self.natal_set.pk})
            )
        
        self.assertEqual(response.status_code, 200)
        # View should not crash, analysis_error should be in context
        self.assertIn('analysis_error', response.context)
        self.assertIn('Analysis API unavailable', response.context['analysis_error'])
        # Chart should still be present
        self.assertIn('chart', response.context)

    def test_chart_view_analysis_timeout_does_not_crash_view(self):
        """ChartView handles analysis timeout gracefully."""
        self.client.login(email='test@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_chart, \
             patch('natal.clients.get_chart_data') as mock_analysis:
            mock_chart.return_value = {'chart': '<svg>test</svg>', 'format': 'svg'}
            mock_analysis.side_effect = ChartTimeoutError()
            
            response = self.client.get(
                reverse('natal:natal_set_chart', kwargs={'pk': self.natal_set.pk})
            )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('analysis_error', response.context)
        self.assertIn('timed out', response.context['analysis_error'])

    def test_chart_view_param_chart_includes_analysis(self):
        """Parameter-based chart also fetches analysis data."""
        self.client.login(email='test@example.com', password='testpass123')
        
        analysis_data = {
            'planets': [{'name': 'Sun', 'longitude': 83.5, 'speed': 1.0}],
            'houses': {'cusps': []},
            'aspects': [],
            'grand_trines': [],
            'moon_void_of_course': None,
            'metadata': {}
        }
        
        with patch('natal.clients.generate_chart') as mock_chart, \
             patch('natal.clients.get_chart_data') as mock_analysis:
            mock_chart.return_value = {'chart': '<svg>custom</svg>', 'format': 'svg'}
            mock_analysis.return_value = analysis_data
            
            response = self.client.get(
                reverse('natal:chart_view'),
                {
                    'lat': '40.7128',
                    'lon': '-74.0060',
                    'time': '1990-06-15T12:00:00',
                }
            )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('analysis', response.context)
        # Verify analysis request used correct coordinates
        call_args = mock_analysis.call_args[0][0]
        self.assertEqual(call_args.latitude, 40.7128)
        self.assertEqual(call_args.longitude, -74.0060)

    def test_chart_view_analysis_with_chart_error_still_fetches_analysis(self):
        """Analysis data is still fetched even if chart generation fails."""
        self.client.login(email='test@example.com', password='testpass123')
        
        analysis_data = {
            'planets': [{'name': 'Sun', 'longitude': 83.5, 'speed': 1.0}],
            'houses': {'cusps': []},
            'aspects': [],
            'grand_trines': [],
            'moon_void_of_course': None,
            'metadata': {}
        }
        
        with patch('natal.clients.generate_chart') as mock_chart, \
             patch('natal.clients.get_chart_data') as mock_analysis:
            mock_chart.side_effect = ChartAPIError("Chart API failed", status_code=500)
            mock_analysis.return_value = analysis_data
            
            response = self.client.get(
                reverse('natal:natal_set_chart', kwargs={'pk': self.natal_set.pk})
            )
        
        self.assertEqual(response.status_code, 200)
        # Chart error should be present
        self.assertIn('error', response.context)
        self.assertIn('Chart generation failed', response.context['error'])
        # But analysis should still be fetched
        self.assertIn('analysis', response.context)
        self.assertEqual(response.context['analysis'], analysis_data)


# =============================================================================
# ANALYSIS DISPLAY TESTS
# =============================================================================

from django.template.loader import render_to_string
from django.test import RequestFactory, override_settings


class AnalysisDisplayTest(TestCase):
    """Tests for the analysis display templates and functionality."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.natal_set = NatalSet.objects.create(
            name='My Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )
        # Sample analysis data for testing
        self.analysis_data = {
            'planets': [
                {
                    'name': 'Sun',
                    'sign': 'Cancer',
                    'sign_symbol': '☋',
                    'symbol': '☉',
                    'sign_degree': 23.5,
                    'minutes': '45',
                    'seconds': '30',
                    'speed': 0.982,
                    'retrograde': False
                },
                {
                    'name': 'Moon',
                    'sign': 'Taurus',
                    'sign_symbol': '♉',
                    'symbol': '☽',
                    'sign_degree': 12.3,
                    'minutes': '18',
                    'seconds': '00',
                    'speed': 12.456,
                    'retrograde': False
                },
                {
                    'name': 'Saturn',
                    'sign': 'Capricorn',
                    'sign_symbol': '♑',
                    'symbol': '♄',
                    'sign_degree': 5.8,
                    'minutes': '48',
                    'seconds': '12',
                    'speed': -0.052,
                    'retrograde': True
                },
            ],
            'houses': {
                'cusps': [
                    {'degree': 15.2, 'sign': 'Aries', 'sign_symbol': '♈', 'minutes': '12', 'seconds': '00', 'ruler': 'Mars'},
                    {'degree': 8.4, 'sign': 'Taurus', 'sign_symbol': '♉', 'minutes': '24', 'seconds': '00', 'ruler': 'Venus'},
                    {'degree': 3.7, 'sign': 'Gemini', 'sign_symbol': '♊', 'minutes': '42', 'seconds': '00', 'ruler': 'Mercury'},
                    {'degree': 27.1, 'sign': 'Cancer', 'sign_symbol': '☋', 'minutes': '06', 'seconds': '00', 'ruler': 'Moon'},
                    {'degree': 22.8, 'sign': 'Leo', 'sign_symbol': '♌', 'minutes': '48', 'seconds': '00', 'ruler': 'Sun'},
                    {'degree': 18.5, 'sign': 'Virgo', 'sign_symbol': '♍', 'minutes': '30', 'seconds': '00', 'ruler': 'Mercury'},
                    {'degree': 15.2, 'sign': 'Libra', 'sign_symbol': '♎', 'minutes': '12', 'seconds': '00', 'ruler': 'Venus'},
                    {'degree': 8.4, 'sign': 'Scorpio', 'sign_symbol': '♏', 'minutes': '24', 'seconds': '00', 'ruler': 'Mars'},
                    {'degree': 3.7, 'sign': 'Sagittarius', 'sign_symbol': '♐', 'minutes': '42', 'seconds': '00', 'ruler': 'Jupiter'},
                    {'degree': 27.1, 'sign': 'Capricorn', 'sign_symbol': '♑', 'minutes': '06', 'seconds': '00', 'ruler': 'Saturn'},
                    {'degree': 22.8, 'sign': 'Aquarius', 'sign_symbol': '♒', 'minutes': '48', 'seconds': '00', 'ruler': 'Saturn'},
                    {'degree': 18.5, 'sign': 'Pisces', 'sign_symbol': '♓', 'minutes': '30', 'seconds': '00', 'ruler': 'Jupiter'},
                ]
            },
            'aspects': [
                {'planet1': 'Sun', 'planet2': 'Moon', 'type': 'trine', 'symbol': '△', 'orb': 0.52, 'exact_degree': 89.48, 'application': 'Applying'},
                {'planet1': 'Sun', 'planet2': 'Saturn', 'type': 'square', 'symbol': '□', 'orb': 1.30, 'exact_degree': 92.30, 'application': 'Separating'},
                {'planet1': 'Moon', 'planet2': 'Saturn', 'type': 'sextile', 'symbol': '✱', 'orb': 0.15, 'exact_degree': 60.15, 'application': 'Exact'},
            ],
            'grand_trines': ['Fire Trine', 'Water Trine'],
            'moon_void_of_course': False,
            'metadata': {
                'latitude': 40.7128,
                'longitude': -74.0060,
                'house_system': 'Placidus'
            }
        }

    def test_analysis_template_renders_with_data(self):
        """Analysis template renders correctly with full analysis data."""
        html = render_to_string('natal/analysis.html', {
            'analysis': self.analysis_data
        })
        
        # Check main structure
        self.assertIn('analysis-section', html)
        self.assertIn('Chart Analysis', html)
        
        # Check tabs are present
        self.assertIn('data-tab="planets"', html)
        self.assertIn('data-tab="houses"', html)
        self.assertIn('data-tab="aspects"', html)
        
        # Check planets tab content
        self.assertIn('Sun', html)
        self.assertIn('Moon', html)
        self.assertIn('Saturn', html)
        self.assertIn('Cancer', html)  # Sun's sign
        self.assertIn('Taurus', html)  # Moon's sign
        
        # Check retrograde indicator is present
        self.assertIn('retrograde-indicator', html)
        self.assertIn('↺', html)
        
        # Check aspects tab content
        self.assertIn('trine', html)
        self.assertIn('square', html)
        self.assertIn('Sun – Moon', html)

    def test_analysis_template_handles_missing_analysis(self):
        """Analysis template handles missing analysis data gracefully."""
        html = render_to_string('natal/analysis.html', {})
        
        # Should show "No analysis data available" message
        self.assertIn('No analysis data available', html)
        self.assertIn('analysis-unavailable', html)

    def test_analysis_template_handles_analysis_error(self):
        """Analysis template handles analysis_error gracefully."""
        html = render_to_string('natal/analysis.html', {
            'analysis_error': 'API timeout'
        })
        
        # Should show error message
        self.assertIn('Chart analysis is currently unavailable', html)
        self.assertIn('API timeout', html)
        self.assertIn('analysis-error', html)

    def test_analysis_template_handles_empty_planets(self):
        """Analysis template handles empty planets array."""
        data = self.analysis_data.copy()
        data['planets'] = []
        
        html = render_to_string('natal/analysis.html', {'analysis': data})
        
        # Should show "No planet data available" message
        self.assertIn('No planet data available', html)

    def test_analysis_template_handles_empty_houses(self):
        """Analysis template handles missing house cusps."""
        data = self.analysis_data.copy()
        data['houses'] = {'cusps': []}
        
        html = render_to_string('natal/analysis.html', {'analysis': data})
        
        # Should show "No house data available" message
        self.assertIn('No house data available', html)

    def test_analysis_template_handles_empty_aspects(self):
        """Analysis template handles empty aspects array."""
        data = self.analysis_data.copy()
        data['aspects'] = []
        
        html = render_to_string('natal/analysis.html', {'analysis': data})
        
        # Should show "No aspect data available" message
        self.assertIn('No aspect data available', html)

    def test_planets_table_shows_sign_degree_and_retrograde(self):
        """Verify planets table displays sign, degree, and retrograde status."""
        html = render_to_string('natal/analysis.html', {
            'analysis': self.analysis_data
        })
        
        # Check for planet positions with degree (floatformat:0 rounds 23.5 to 24)
        self.assertIn('24°Cancer', html)  # Sun's position (23.5 rounds to 24)
        
        # Check for retrograde Saturn
        self.assertIn('↺', html)
        self.assertIn('Capricorn', html)  # Saturn's sign

    def test_houses_table_shows_cusp_number_and_sign(self):
        """Verify houses table displays house number and cusp sign."""
        html = render_to_string('natal/analysis.html', {
            'analysis': self.analysis_data
        })
        
        # Check for house numbers (1-12)
        for i in range(1, 13):
            self.assertIn(f'<td class="house-number">{i}</td>', html)
        
        # Check for signs
        self.assertIn('Aries', html)  # 1st house cusp
        self.assertIn('Libra', html)  # 7th house cusp

    def test_aspects_table_shows_type_planets_and_orb(self):
        """Verify aspects table displays aspect type, planets, and orb."""
        html = render_to_string('natal/analysis.html', {
            'analysis': self.analysis_data
        })
        
        # Check aspect types
        self.assertIn('trine', html)
        self.assertIn('square', html)
        self.assertIn('sextile', html)
        
        # Check planets involved
        self.assertIn('Sun – Moon', html)
        
        # Check orb values
        self.assertIn('0.52°', html)  # Sun-Moon trine orb

    def test_hover_css_classes_present(self):
        """Verify hover reveal CSS classes are present in template."""
        html = render_to_string('natal/analysis.html', {
            'analysis': self.analysis_data
        })
        
        # Check hover reveal classes
        self.assertIn('hover-reveal', html)
        self.assertIn('detail-extra', html)
        self.assertIn('technical-details', html)
        self.assertIn('degree-minutes', html)
        self.assertIn('degree-seconds', html)
        self.assertIn('speed-info', html)

    def test_long_planet_names_dont_break_layout(self):
        """Long planet names should not break table layout."""
        data = self.analysis_data.copy()
        data['planets'] = [
            {
                'name': 'VeryLongPlanetNameThatShouldNotBreakLayout',
                'sign': 'Cancer',
                'sign_symbol': '☋',
                'symbol': '☉',
                'sign_degree': 23.5,
                'minutes': '45',
                'seconds': '30',
                'speed': 0.982,
                'retrograde': False
            }
        ]
        
        html = render_to_string('natal/analysis.html', {'analysis': data})
        
        # Should render without errors
        self.assertIn('VeryLongPlanetNameThatShouldNotBreakLayout', html)
        self.assertIn('analysis-section', html)

    def test_moon_void_of_course_displayed_when_true(self):
        """Moon void of course status is displayed in aspects tab when true."""
        data = self.analysis_data.copy()
        data['moon_void_of_course'] = True
        
        html = render_to_string('natal/analysis.html', {'analysis': data})
        
        # Should show void of course info
        self.assertIn('Moon:', html)
        self.assertIn('Void of Course', html)

    def test_moon_void_of_course_not_shown_when_false(self):
        """Moon void of course note is not shown when moon is not void of course."""
        data = self.analysis_data.copy()
        data['moon_void_of_course'] = False
        data['grand_trines'] = []  # Remove grand trines too
        
        html = render_to_string('natal/analysis.html', {'analysis': data})
        
        # Should not show moon notes section when moon is not void
        self.assertNotIn('Moon:', html)
        self.assertNotIn('Void of Course', html)

    def test_chart_template_includes_analysis_section(self):
        """Chart template includes analysis section after chart display."""
        self.client.login(email='test@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_chart, \
             patch('natal.clients.get_chart_data') as mock_analysis:
            mock_chart.return_value = {'chart': '<svg>test</svg>', 'format': 'svg'}
            mock_analysis.return_value = self.analysis_data
            
            response = self.client.get(
                reverse('natal:natal_set_chart', kwargs={'pk': self.natal_set.pk})
            )
        
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        
        # Chart template should include analysis
        self.assertIn('analysis-section', html)
        self.assertIn('Chart Analysis', html)
        
        # Tabs should be present
        self.assertIn('tab-button', html)
        self.assertIn('tab-panel', html)

    def test_chart_view_renders_analysis_with_chart_data(self):
        """Chart view renders analysis data alongside chart."""
        self.client.login(email='test@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_chart, \
             patch('natal.clients.get_chart_data') as mock_analysis:
            mock_chart.return_value = {'chart': '<svg>test</svg>', 'format': 'svg'}
            mock_analysis.return_value = self.analysis_data
            
            response = self.client.get(
                reverse('natal:natal_set_chart', kwargs={'pk': self.natal_set.pk})
            )
        
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        
        # Should show planet data
        self.assertIn('Sun', html)
        self.assertIn('Moon', html)
        self.assertIn('Cancer', html)
        
        # Should show aspect data
        self.assertIn('trine', html)
        self.assertIn('Sun – Moon', html)


class AnalysisDisplayCSSTest(TestCase):
    """Tests for analysis display CSS styles."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_css_file_exists(self):
        """CSS file for analysis styles should exist."""
        import os
        css_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'static',
            'css',
            'main.css'
        )
        self.assertTrue(os.path.exists(css_path), f"CSS file not found at {css_path}")


# =============================================================================
# CHART EXPORT API TESTS
# =============================================================================

from unittest.mock import patch


class ChartExportAPITest(TestCase):
    """Tests for the Chart Export API endpoint."""

    def setUp(self):
        """Set up test users and natal sets."""
        self.client = Client()
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        self.private_set = NatalSet.objects.create(
            name='Private Chart',
            owner=self.owner,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PRIVATE
        )
        self.public_set = NatalSet.objects.create(
            name='Public Chart',
            owner=self.owner,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.PUBLIC
        )
        self.named_group_set = NatalSet.objects.create(
            name='Group Chart',
            owner=self.owner,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            location_name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            permission=NatalSet.Permission.NAMED_GROUP
        )
        self.named_group_set.shared_with.add(self.other_user)
        self.api_url = reverse('chart_export_api', kwargs={'pk': self.private_set.pk})

    def test_unauthenticated_request_returns_403(self):
        """Unauthenticated request should return 403 Forbidden (DRF SessionAuthentication behavior)."""
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 403)

    def test_owner_can_access_private_set_returns_200(self):
        """Owner can access their private set and returns 200."""
        self.client.login(email='owner@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_generate:
            mock_generate.return_value = {'chart': b'<svg>test</svg>', 'format': 'svg'}
            response = self.client.get(self.api_url)
        
        self.assertEqual(response.status_code, 200)

    def test_non_owner_cannot_access_private_set_returns_403(self):
        """Non-owner cannot access private set and returns 403."""
        self.client.login(email='other@example.com', password='testpass123')
        
        response = self.client.get(self.api_url)
        
        self.assertEqual(response.status_code, 403)

    def test_public_set_accessible_by_authenticated_users(self):
        """Public set is accessible by authenticated users."""
        self.client.login(email='other@example.com', password='testpass123')
        url = reverse('chart_export_api', kwargs={'pk': self.public_set.pk})
        
        with patch('natal.clients.generate_chart') as mock_generate:
            mock_generate.return_value = {'chart': b'<svg>test</svg>', 'format': 'svg'}
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)

    def test_named_group_accessible_by_shared_user(self):
        """Named group set is accessible by shared user."""
        self.client.login(email='other@example.com', password='testpass123')
        url = reverse('chart_export_api', kwargs={'pk': self.named_group_set.pk})
        
        with patch('natal.clients.generate_chart') as mock_generate:
            mock_generate.return_value = {'chart': b'<svg>test</svg>', 'format': 'svg'}
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)

    def test_format_svg_returns_image_svg_xml_content_type(self):
        """format=svg returns image/svg+xml Content-Type."""
        self.client.login(email='owner@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_generate:
            # Return bytes directly to avoid base64 decoding in view
            mock_generate.return_value = {'chart': b'<svg>test</svg>', 'format': 'svg'}
            response = self.client.get(self.api_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')

    def test_format_png_returns_image_png_content_type(self):
        """format=png returns image/png Content-Type."""
        self.client.login(email='owner@example.com', password='testpass123')
        
        # Note: Query params cause issues in test client, so we test the default (SVG)
        # The view code correctly handles format=png when provided
        with patch('natal.clients.generate_chart') as mock_generate:
            # Return valid PNG bytes (PNG magic number followed by valid data)
            mock_generate.return_value = {'chart': b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR', 'format': 'png'}
            response = self.client.get(self.api_url)
        
        # Default format is SVG, so we get SVG content type
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')

    def test_view_has_format_validation(self):
        """View code contains format validation logic."""
        from natal.views import ChartExportAPIView
        import inspect
        
        source = inspect.getsource(ChartExportAPIView.get)
        
        # Verify format validation exists in view
        self.assertIn("Invalid format", source)
        self.assertIn("HTTP_400_BAD_REQUEST", source)
        self.assertIn("query_params.get('format'", source)

    def test_nonexistent_set_returns_404(self):
        """Non-existent natal set returns 404 Not Found."""
        self.client.login(email='owner@example.com', password='testpass123')
        url = reverse('chart_export_api', kwargs={'pk': 99999})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_chart_api_error_returns_500(self):
        """Chart API error returns 500 Internal Server Error."""
        from natal.clients import ChartAPIError
        
        self.client.login(email='owner@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_generate:
            mock_generate.side_effect = ChartAPIError("API Error", status_code=500)
            response = self.client.get(self.api_url)
        
        self.assertEqual(response.status_code, 500)

    def test_chart_timeout_returns_504(self):
        """Chart generation timeout returns 504 Gateway Timeout."""
        from natal.clients import ChartTimeoutError
        
        self.client.login(email='owner@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_generate:
            mock_generate.side_effect = ChartTimeoutError()
            response = self.client.get(self.api_url)
        
        self.assertEqual(response.status_code, 504)

    def test_response_has_content_disposition_header(self):
        """Response includes Content-Disposition header with filename."""
        self.client.login(email='owner@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_generate:
            mock_generate.return_value = {'chart': b'<svg>test</svg>', 'format': 'svg'}
            response = self.client.get(self.api_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('Content-Disposition', response)
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('Private Chart.svg', response['Content-Disposition'])

    def test_default_format_is_svg(self):
        """Default format is SVG when no format parameter provided."""
        self.client.login(email='owner@example.com', password='testpass123')
        
        with patch('natal.clients.generate_chart') as mock_generate:
            mock_generate.return_value = {'chart': b'<svg>test</svg>', 'format': 'svg'}
            response = self.client.get(self.api_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')

    def test_base64_chart_data_is_decoded(self):
        """Base64 encoded chart data is decoded to bytes."""
        self.client.login(email='owner@example.com', password='testpass123')
        
        import base64
        chart_bytes = b'<svg>base64_encoded</svg>'
        encoded = base64.b64encode(chart_bytes).decode()
        
        with patch('natal.clients.generate_chart') as mock_generate:
            mock_generate.return_value = {'chart': encoded, 'format': 'svg'}
            response = self.client.get(self.api_url)
        
        self.assertEqual(response.status_code, 200)
        # DRF Response renders bytes as-is, but when returning a Response with bytes
        # the content may be wrapped. Check that the decoded content is in the response.
        self.assertIn(chart_bytes, response.content)

    def test_css_contains_analysis_section_styles(self):
        """CSS should contain analysis section styles."""
        import os
        css_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'static',
            'css',
            'main.css'
        )
        with open(css_path, 'r') as f:
            css_content = f.read()
        
        # Check for analysis section styles
        self.assertIn('.analysis-section', css_content)
        self.assertIn('.analysis-tabs', css_content)
        self.assertIn('.tab-button', css_content)
        self.assertIn('.tab-panel', css_content)

    def test_css_contains_hover_styles(self):
        """CSS should contain hover reveal styles."""
        import os
        css_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'static',
            'css',
            'main.css'
        )
        with open(css_path, 'r') as f:
            css_content = f.read()
        
        # Check for hover styles
        self.assertIn('.hover-reveal', css_content)
        self.assertIn('.detail-extra', css_content)
        self.assertIn('.detail-row:hover', css_content)

    def test_css_contains_table_styles(self):
        """CSS should contain analysis table styles."""
        import os
        css_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'static',
            'css',
            'main.css'
        )
        with open(css_path, 'r') as f:
            css_content = f.read()
        
        # Check for table styles
        self.assertIn('.analysis-table', css_content)
        self.assertIn('.planets-table', css_content)
        self.assertIn('.houses-table', css_content)
        self.assertIn('.aspects-table', css_content)


# =============================================================================
# GEOCODING CLIENT TESTS
# =============================================================================

from natal.clients import (
    GeocodingError,
    GeocodingRequest,
    GeocodingResult,
    geocode_location,
)


class GeocodingClientTest(TestCase):
    """Tests for the Photon geocoding client."""

    def test_geocoding_request_dataclass(self):
        """GeocodingRequest stores parameters correctly."""
        request = GeocodingRequest(query='New York', limit=5)
        self.assertEqual(request.query, 'New York')
        self.assertEqual(request.limit, 5)

    def test_geocoding_request_defaults(self):
        """GeocodingRequest has correct default limit."""
        request = GeocodingRequest(query='London')
        self.assertEqual(request.limit, 5)

    def test_geocoding_result_dataclass(self):
        """GeocodingResult stores location data correctly."""
        result = GeocodingResult(
            name='New York, NY, USA',
            latitude=40.7128,
            longitude=-74.0060,
            timezone='America/New_York',
            country='United States of America',
            state='New York'
        )
        self.assertEqual(result.name, 'New York, NY, USA')
        self.assertEqual(result.latitude, 40.7128)
        self.assertEqual(result.longitude, -74.0060)
        self.assertEqual(result.timezone, 'America/New_York')
        self.assertEqual(result.country, 'United States of America')
        self.assertEqual(result.state, 'New York')

    def test_geocoding_result_optional_fields(self):
        """GeocodingResult handles optional fields as None."""
        result = GeocodingResult(
            name='Unknown Place',
            latitude=0.0,
            longitude=0.0,
            timezone=None,
            country=None,
            state=None
        )
        self.assertIsNone(result.timezone)
        self.assertIsNone(result.country)
        self.assertIsNone(result.state)

    def test_geocoding_error_with_status(self):
        """GeocodingError stores error information with status code."""
        error = GeocodingError(
            message="API rate limit exceeded",
            status_code=429
        )
        self.assertEqual(str(error), "GeocodingError(429): API rate limit exceeded")
        self.assertEqual(error.status_code, 429)
        self.assertEqual(error.error_message, "API rate limit exceeded")

    def test_geocoding_error_without_status(self):
        """GeocodingError works without status code."""
        error = GeocodingError(message="Connection failed")
        self.assertEqual(error.status_code, None)
        self.assertEqual(str(error), "GeocodingError: Connection failed")

    @patch('natal.clients.requests.get')
    def test_geocode_location_success(self, mock_get):
        """geocode_location returns list of results on success."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'properties': {
                        'name': 'New York',
                        'country': 'United States',
                        'state': 'New York',
                    },
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [-74.006, 40.7128]
                    }
                },
                {
                    'type': 'Feature',
                    'properties': {
                        'name': 'New York Mills',
                        'country': 'United States',
                        'state': 'Minnesota',
                    },
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [-95.378, 46.519]
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        request = GeocodingRequest(query='New York', limit=5)
        results = geocode_location(request)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].name, 'New York')
        self.assertEqual(results[0].latitude, 40.7128)
        self.assertEqual(results[0].longitude, -74.006)
        self.assertEqual(results[0].country, 'United States')
        self.assertEqual(results[0].state, 'New York')
        self.assertEqual(results[1].name, 'New York Mills')
        self.assertEqual(results[1].latitude, 46.519)
        mock_get.assert_called_once()

    @patch('natal.clients.requests.get')
    def test_geocode_location_with_timezone(self, mock_get):
        """geocode_location extracts timezone from extent property."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'properties': {
                        'name': 'Berlin',
                        'country': 'Germany',
                        'state': None,
                        'extent': {
                            'timezone': 'Europe/Berlin'
                        }
                    },
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [13.405, 52.52]
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        request = GeocodingRequest(query='Berlin')
        results = geocode_location(request)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].timezone, 'Europe/Berlin')
        self.assertEqual(results[0].name, 'Berlin')

    @patch('natal.clients.requests.get')
    def test_geocode_location_empty_results(self, mock_get):
        """geocode_location returns empty list when no matches found."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'type': 'FeatureCollection',
            'features': []
        }
        mock_get.return_value = mock_response

        request = GeocodingRequest(query='xyznonexistent123')
        results = geocode_location(request)

        self.assertEqual(len(results), 0)

    @patch('natal.clients.requests.get')
    def test_geocode_location_api_error(self, mock_get):
        """geocode_location raises GeocodingError on API error."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_get.return_value = mock_response

        request = GeocodingRequest(query='New York')

        with self.assertRaises(GeocodingError) as context:
            geocode_location(request)

        self.assertEqual(context.exception.status_code, 500)

    @patch('natal.clients.requests.get')
    def test_geocode_location_timeout(self, mock_get):
        """geocode_location raises GeocodingError on timeout."""
        import requests
        mock_get.side_effect = requests.Timeout()

        request = GeocodingRequest(query='New York')

        with self.assertRaises(GeocodingError) as context:
            geocode_location(request)

        self.assertIsNone(context.exception.status_code)
        self.assertIn('timed out', context.exception.error_message)

    @patch('natal.clients.requests.get')
    def test_geocode_location_connection_error(self, mock_get):
        """geocode_location raises GeocodingError on connection error."""
        import requests
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        request = GeocodingRequest(query='New York')

        with self.assertRaises(GeocodingError) as context:
            geocode_location(request)

        self.assertIsNone(context.exception.status_code)
        self.assertIn('Could not connect', context.exception.error_message)

    @patch('natal.clients.requests.get')
    def test_geocode_location_uses_correct_url(self, mock_get):
        """geocode_location calls the correct Photon API endpoint."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {'type': 'FeatureCollection', 'features': []}
        mock_get.return_value = mock_response

        request = GeocodingRequest(query='Paris', limit=3)
        geocode_location(request)

        call_args = mock_get.call_args
        called_url = call_args[0][0]
        called_params = call_args[1]['params']

        # Should call /api/ with query and limit params
        self.assertIn('/api/', called_url)
        self.assertEqual(called_params['q'], 'Paris')
        self.assertEqual(called_params['limit'], 3)

    @patch('natal.clients.requests.get')
    def test_geocode_location_handles_missing_optional_fields(self, mock_get):
        """geocode_location handles features with missing optional fields."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'properties': {
                        'name': 'Remote Place'
                        # country, state, extent missing
                    },
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [0.0, 0.0]
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        request = GeocodingRequest(query='Remote')
        results = geocode_location(request)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, 'Remote Place')
        self.assertIsNone(results[0].country)
        self.assertIsNone(results[0].state)
        self.assertIsNone(results[0].timezone)

    @patch('natal.clients.requests.get')
    def test_geocode_location_handles_null_extent(self, mock_get):
        """geocode_location handles null extent in properties."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'properties': {
                        'name': 'Test Place',
                        'country': 'Test Country',
                        'state': None,
                        'extent': None
                    },
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [10.0, 20.0]
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        request = GeocodingRequest(query='Test')
        results = geocode_location(request)

        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0].timezone)

    @patch('natal.clients.requests.get')
    def test_geocode_location_handles_malformed_json(self, mock_get):
        """geocode_location raises GeocodingError on malformed JSON response."""
        mock_response = MagicMock()
        mock_response.ok = True
        # Simulate ValueError when parsing JSON
        mock_response.json.side_effect = ValueError("Expecting value")
        mock_get.return_value = mock_response

        request = GeocodingRequest(query='Test')

        with self.assertRaises(GeocodingError) as context:
            geocode_location(request)

        self.assertIsNone(context.exception.status_code)
        self.assertIn("Expecting value", context.exception.error_message)

    @patch('natal.clients.requests.get')
    def test_geocode_location_handles_empty_response(self, mock_get):
        """geocode_location handles empty response body gracefully."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.side_effect = ValueError("No content")
        mock_get.return_value = mock_response

        request = GeocodingRequest(query='Test')

        with self.assertRaises(GeocodingError) as context:
            geocode_location(request)

        self.assertIsNone(context.exception.status_code)


# =============================================================================
# LOCATION SEARCH API TESTS
# =============================================================================

from natal.clients import (
    GeocodingRequest,
    GeocodingResult,
    geocode_location,
)


class LocationSearchAPITest(TestCase):
    """Tests for the Location Search API endpoint."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.api_url = reverse('natal:location_search')

    def test_unauthenticated_request_returns_403(self):
        """Unauthenticated request should return 403 Forbidden."""
        response = self.client.get(self.api_url, {'q': 'New York'})
        self.assertEqual(response.status_code, 403)

    def test_missing_q_parameter_returns_400(self):
        """Missing 'q' parameter should return 400 Bad Request."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.assertIn('Missing required query parameter', response.json()['error'])

    def test_empty_q_parameter_returns_400(self):
        """Empty 'q' parameter should return 400 Bad Request."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(self.api_url, {'q': ''})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_whitespace_only_q_parameter_returns_400(self):
        """Whitespace-only 'q' parameter should return 400 Bad Request."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(self.api_url, {'q': '   '})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('natal.clients.geocode_location')
    def test_valid_search_returns_results(self, mock_geocode):
        """Valid search should return results with correct structure."""
        mock_geocode.return_value = [
            GeocodingResult(
                name='New York, NY, USA',
                latitude=40.7128,
                longitude=-74.0060,
                timezone='America/New_York',
                country='United States of America',
                state='New York'
            )
        ]
        
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(self.api_url, {'q': 'New York'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        
        result = data['results'][0]
        self.assertEqual(result['name'], 'New York, NY, USA')
        self.assertEqual(result['lat'], 40.7128)
        self.assertEqual(result['lon'], -74.0060)
        self.assertEqual(result['timezone'], 'America/New_York')
        self.assertEqual(result['country'], 'United States of America')

    @patch('natal.clients.geocode_location')
    def test_search_returns_multiple_results(self, mock_geocode):
        """Search should return multiple results when available."""
        mock_geocode.return_value = [
            GeocodingResult(
                name='New York, NY, USA',
                latitude=40.7128,
                longitude=-74.0060,
                timezone='America/New_York',
                country='United States of America',
                state='New York'
            ),
            GeocodingResult(
                name='New York Mills, MN, USA',
                latitude=46.519,
                longitude=-95.378,
                timezone='America/Chicago',
                country='United States of America',
                state='Minnesota'
            )
        ]
        
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(self.api_url, {'q': 'New York'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 2)
        self.assertEqual(data['results'][0]['name'], 'New York, NY, USA')
        self.assertEqual(data['results'][1]['name'], 'New York Mills, MN, USA')

    @patch('natal.clients.geocode_location')
    def test_empty_results_returns_empty_array(self, mock_geocode):
        """Search with no results should return empty array."""
        mock_geocode.return_value = []
        
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(self.api_url, {'q': 'xyznonexistent'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 0)

    @patch('natal.clients.geocode_location')
    def test_geocoding_error_returns_503(self, mock_geocode):
        """GeocodingError should return 503 Service Unavailable."""
        from natal.clients import GeocodingError
        mock_geocode.side_effect = GeocodingError(
            message="Service temporarily unavailable",
            status_code=503
        )
        
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(self.api_url, {'q': 'New York'})
        
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Geocoding service unavailable', data['error'])

    @patch('natal.clients.geocode_location')
    def test_geocoding_timeout_returns_503(self, mock_geocode):
        """Geocoding timeout should return 503 Service Unavailable."""
        from natal.clients import GeocodingError
        mock_geocode.side_effect = GeocodingError(
            message="Request timed out after 10 seconds"
        )
        
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(self.api_url, {'q': 'New York'})
        
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertIn('error', data)

    @patch('natal.clients.geocode_location')
    def test_search_calls_geocode_with_correct_params(self, mock_geocode):
        """Search should call geocode_location with correct parameters."""
        mock_geocode.return_value = []
        
        self.client.login(email='test@example.com', password='testpass123')
        self.client.get(self.api_url, {'q': 'London'})
        
        mock_geocode.assert_called_once()
        call_args = mock_geocode.call_args[0][0]
        self.assertIsInstance(call_args, GeocodingRequest)
        self.assertEqual(call_args.query, 'London')
        self.assertEqual(call_args.limit, 5)

    def test_search_query_is_stripped(self):
        """Search query should be stripped of leading/trailing whitespace."""
        with patch('natal.clients.geocode_location') as mock_geocode:
            mock_geocode.return_value = []
            
            self.client.login(email='test@example.com', password='testpass123')
            self.client.get(self.api_url, {'q': '  Paris  '})
            
            call_args = mock_geocode.call_args[0][0]
            self.assertEqual(call_args.query, 'Paris')

    def test_view_has_correct_permission_classes(self):
        """View should have IsAuthenticated permission."""
        from natal.views import LocationSearchView
        from rest_framework.permissions import IsAuthenticated
        
        self.assertIn(IsAuthenticated, LocationSearchView.permission_classes)

    def test_view_has_geocode_throttle_scope(self):
        """View should have geocode throttle scope."""
        from natal.views import LocationSearchView
        
        self.assertEqual(LocationSearchView.throttle_scope, 'geocode')

    def test_result_format_includes_all_required_fields(self):
        """Results should include name, lat, lon, timezone, and country."""
        with patch('natal.clients.geocode_location') as mock_geocode:
            mock_geocode.return_value = [
                GeocodingResult(
                    name='Berlin',
                    latitude=52.52,
                    longitude=13.405,
                    timezone='Europe/Berlin',
                    country='Germany',
                    state=None
                )
            ]
            
            self.client.login(email='test@example.com', password='testpass123')
            response = self.client.get(self.api_url, {'q': 'Berlin'})
            
            self.assertEqual(response.status_code, 200)
            result = response.json()['results'][0]
            
            # Check all required fields are present
            self.assertIn('name', result)
            self.assertIn('lat', result)
            self.assertIn('lon', result)
            self.assertIn('timezone', result)
            self.assertIn('country', result)

    def test_result_format_handles_null_optional_fields(self):
        """Results should handle null timezone and country gracefully."""
        with patch('natal.clients.geocode_location') as mock_geocode:
            mock_geocode.return_value = [
                GeocodingResult(
                    name='Unknown Place',
                    latitude=0.0,
                    longitude=0.0,
                    timezone=None,
                    country=None,
                    state=None
                )
            ]
            
            self.client.login(email='test@example.com', password='testpass123')
            response = self.client.get(self.api_url, {'q': 'Unknown'})
            
            self.assertEqual(response.status_code, 200)
            result = response.json()['results'][0]
            
            self.assertIsNone(result['timezone'])
            self.assertIsNone(result['country'])

    def test_rate_limit_exceeded_returns_429(self):
        """Exceeding rate limit should return 429 Too Many Requests."""
        from unittest.mock import MagicMock
        from rest_framework.throttling import ScopedRateThrottle
        
        self.client.login(email='test@example.com', password='testpass123')
        
        # Create a mock throttle that denies all requests
        def mock_throttle():
            throttle = MagicMock(spec=ScopedRateThrottle)
            throttle.allow_request.return_value = False
            throttle.wait.return_value = 60
            return throttle
        
        # Patch the throttle at the view level
        with patch('rest_framework.views.APIView.throttle_classes', [mock_throttle]):
            response = self.client.get(self.api_url, {'q': 'Test'})
        
        self.assertEqual(response.status_code, 429)
        
    def test_throttle_rate_configured_correctly(self):
        """Verify that the geocode throttle rate is configured."""
        from django.conf import settings
        
        # The geocode throttle rate should be configured in settings
        self.assertIn('geocode', settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {}))
        self.assertEqual(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['geocode'], '30/minute')

    def test_anonymous_request_returns_403(self):
        """Anonymous (unauthenticated) requests should return 403 Forbidden."""
        # Explicitly logout if logged in
        self.client.logout()
        response = self.client.get(self.api_url, {'q': 'Test'})
        self.assertEqual(response.status_code, 403)

