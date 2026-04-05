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
        """Create test users and place for NatalSet creation."""
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
        self.place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            created_by=self.user
        )

    def test_create_natal_set(self):
        """NatalSet can be created with valid data."""
        natal_set = NatalSet.objects.create(
            name='My Birth Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            place=self.place,
            permission=NatalSet.Permission.PRIVATE
        )
        self.assertEqual(natal_set.name, 'My Birth Chart')
        self.assertEqual(natal_set.owner, self.user)
        self.assertEqual(natal_set.place, self.place)
        self.assertEqual(natal_set.permission, NatalSet.Permission.PRIVATE)

    def test_natal_set_str_representation(self):
        """String representation of NatalSet should include name and owner."""
        natal_set = NatalSet.objects.create(
            name='Test Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            place=self.place,
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
            place=self.place,
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
            place=self.place,
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
            place=self.place,
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
            place=self.place,
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
            place=self.place,
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
        self.place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            created_by=self.user
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
            place=self.place,
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
            place=self.place,
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
            place=self.place,
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
        self.place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            created_by=self.user
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
            'place': self.place.pk,
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
            'place': self.place.pk,
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
                'place': self.place.pk,
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
        self.place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            created_by=self.user
        )
        self.natal_set = NatalSet.objects.create(
            name='Private Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            place=self.place,
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
            place=self.place,
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
        self.place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            created_by=self.user
        )
        self.natal_set = NatalSet.objects.create(
            name='My Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            place=self.place,
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
                'place': self.place.pk,
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
        self.place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            created_by=self.user
        )
        self.natal_set = NatalSet.objects.create(
            name='My Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            place=self.place,
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
        self.place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            created_by=self.user
        )
        # Create one of each type
        self.private_set = NatalSet.objects.create(
            name='Private Set',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            place=self.place,
            permission=NatalSet.Permission.PRIVATE
        )
        self.public_set = NatalSet.objects.create(
            name='Public Set',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            place=self.place,
            permission=NatalSet.Permission.PUBLIC
        )
        self.named_group_set = NatalSet.objects.create(
            name='Group Set',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            place=self.place,
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
        self.place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            created_by=self.user
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
                'place': self.place.pk,
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
                'place': self.place.pk,
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
        self.place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            created_by=self.user
        )
        self.natal_set = NatalSet.objects.create(
            name='My Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            place=self.place,
            permission=NatalSet.Permission.PRIVATE
        )

    def test_invalid_datetime_format_rejected(self):
        """Invalid datetime format should be rejected."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'Invalid Date Test',
            'birth_datetime': 'not-a-date',
            'place': self.place.pk,
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
            'place': self.place.pk,
            'permission': 'private',
        })
        self.assertEqual(response.status_code, 200)
        
        # Missing birth_datetime
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'Missing Date Test',
            'place': self.place.pk,
            'permission': 'private',
        })
        self.assertEqual(response.status_code, 200)
        
        # Missing place
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'Missing Place Test',
            'birth_datetime': '1990-06-15T12:00',
            'permission': 'private',
        })
        self.assertEqual(response.status_code, 200)

    def test_tampering_other_users_set_returns_404(self):
        """Tampering with other users' set should return 404."""
        # Try to access non-existent set
        self.client.login(email='other@example.com', password='testpass123')
        response = self.client.get(
            reverse('natal:natal_set_detail', kwargs={'pk': 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_place_rejected(self):
        """Non-existent place ID should be rejected."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'Bad Place Test',
            'birth_datetime': '1990-06-15T12:00',
            'place': 99999,  # Non-existent
            'permission': 'private',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(NatalSet.objects.filter(name='Bad Place Test').exists())

    def test_cannot_create_set_with_other_users_place(self):
        """User cannot create natal set with another user's place."""
        other_user_place = Place.objects.create(
            name='Other User Place',
            latitude=Decimal('48.856600'),
            longitude=Decimal('2.352200'),
            timezone='Europe/Paris',
            created_by=self.other_user
        )
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'Unauthorized Place Test',
            'birth_datetime': '1990-06-15T12:00',
            'place': other_user_place.pk,
            'permission': 'private',
        })
        # Form should not be valid since place is filtered to user's places
        self.assertEqual(response.status_code, 200)

    def test_invalid_permission_choice_rejected(self):
        """Invalid permission choice should be rejected."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(reverse('natal:natal_set_create'), {
            'name': 'Bad Permission Test',
            'birth_datetime': '1990-06-15T12:00',
            'place': self.place.pk,
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
        self.place = Place.objects.create(
            name='New York',
            latitude=Decimal('40.712800'),
            longitude=Decimal('-74.006000'),
            timezone='America/New_York',
            created_by=self.user
        )
        self.natal_set = NatalSet.objects.create(
            name='My Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            place=self.place,
            permission=NatalSet.Permission.PRIVATE
        )
        self.public_set = NatalSet.objects.create(
            name='Public Chart',
            owner=self.user,
            birth_datetime=timezone.make_aware(datetime(1990, 6, 15, 12, 0)),
            place=self.place,
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
        self.assertEqual(context['natal_set'].place.name, 'New York')
