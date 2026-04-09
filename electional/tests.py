"""
Comprehensive tests for electional astrology: models, forms, views, and API clients.
"""
from datetime import date
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from electional.clients import (
    QueryAPIError,
    QueryRequest,
    QueryTimeoutError,
    get_job_status,
    submit_query,
)
from electional.forms import SavedQueryCreateForm, SavedQueryForm
from electional.models import SavedQuery


User = get_user_model()


# =============================================================================
# MODEL TESTS
# =============================================================================

class SavedQueryModelTest(TestCase):
    """Tests for the SavedQuery model."""

    def setUp(self):
        """Create test users for SavedQuery tests."""
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

    def test_create_saved_query(self):
        """SavedQuery can be created with valid data."""
        query = SavedQuery.objects.create(
            name='Wedding Date Search',
            owner=self.user,
            query_type=SavedQuery.QueryType.WEDDING,
            query_params={
                'description': 'Find an auspicious wedding date',
                'latitude': 40.7128,
                'longitude': -74.0060,
                'location_name': 'New York, NY',
                'start_date': '2024-06-01',
                'end_date': '2024-06-30',
            },
            permission=SavedQuery.Permission.PRIVATE
        )
        self.assertEqual(query.name, 'Wedding Date Search')
        self.assertEqual(query.owner, self.user)
        self.assertEqual(query.query_type, SavedQuery.QueryType.WEDDING)
        self.assertEqual(query.permission, SavedQuery.Permission.PRIVATE)
        self.assertEqual(query.job_status, SavedQuery.JobStatus.PENDING)

    def test_saved_query_str_representation(self):
        """String representation of SavedQuery should include name, type, and owner."""
        query = SavedQuery.objects.create(
            name='Project Launch',
            owner=self.user,
            query_type=SavedQuery.QueryType.PROJECT,
            permission=SavedQuery.Permission.PRIVATE
        )
        self.assertEqual(str(query), f'Project Launch ({SavedQuery.QueryType.PROJECT}) - {self.user}')

    def test_saved_query_query_type_choices(self):
        """SavedQuery should have correct query_type choices."""
        self.assertEqual(SavedQuery.QueryType.WEDDING, 'wedding')
        self.assertEqual(SavedQuery.QueryType.PROJECT, 'project')
        self.assertEqual(SavedQuery.QueryType.TRAVEL, 'travel')
        self.assertEqual(SavedQuery.QueryType.MOVE_IN, 'move_in')
        self.assertEqual(SavedQuery.QueryType.MEDICAL, 'medical')
        self.assertEqual(SavedQuery.QueryType.OTHER, 'other')
        self.assertEqual(len(SavedQuery.QueryType.choices), 6)

    def test_saved_query_permission_choices(self):
        """SavedQuery should have correct permission choices."""
        self.assertEqual(SavedQuery.Permission.PRIVATE, 'private')
        self.assertEqual(SavedQuery.Permission.NAMED_GROUP, 'named_group')
        self.assertEqual(SavedQuery.Permission.PUBLIC, 'public')
        self.assertEqual(len(SavedQuery.Permission.choices), 3)

    def test_saved_query_job_status_choices(self):
        """SavedQuery should have correct job_status choices."""
        self.assertEqual(SavedQuery.JobStatus.PENDING, 'pending')
        self.assertEqual(SavedQuery.JobStatus.PROCESSING, 'processing')
        self.assertEqual(SavedQuery.JobStatus.COMPLETED, 'completed')
        self.assertEqual(SavedQuery.JobStatus.FAILED, 'failed')
        self.assertEqual(len(SavedQuery.JobStatus.choices), 4)

    def test_saved_query_can_view_owner(self):
        """Owner can always view their own saved query."""
        query = SavedQuery.objects.create(
            name='Private Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.OTHER,
            permission=SavedQuery.Permission.PRIVATE
        )
        self.assertTrue(query.can_view(self.user))
        self.assertFalse(query.can_view(self.other_user))

    def test_saved_query_can_view_public(self):
        """Any authenticated user can view public saved queries."""
        query = SavedQuery.objects.create(
            name='Public Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.OTHER,
            permission=SavedQuery.Permission.PUBLIC
        )
        self.assertTrue(query.can_view(self.user))
        self.assertTrue(query.can_view(self.other_user))

    def test_saved_query_can_view_named_group_with_access(self):
        """Users in shared_with can view named_group saved queries."""
        query = SavedQuery.objects.create(
            name='Group Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.OTHER,
            permission=SavedQuery.Permission.NAMED_GROUP
        )
        query.shared_with.add(self.other_user)
        self.assertTrue(query.can_view(self.user))
        self.assertTrue(query.can_view(self.other_user))

    def test_saved_query_can_view_named_group_without_access(self):
        """Users not in shared_with cannot view named_group saved queries."""
        query = SavedQuery.objects.create(
            name='Group Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.OTHER,
            permission=SavedQuery.Permission.NAMED_GROUP
        )
        self.assertTrue(query.can_view(self.user))
        self.assertFalse(query.can_view(self.other_user))

    def test_saved_query_can_edit_owner(self):
        """Only owner can edit their saved query."""
        query = SavedQuery.objects.create(
            name='Private Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.OTHER,
            permission=SavedQuery.Permission.PRIVATE
        )
        self.assertTrue(query.can_edit(self.user))
        self.assertFalse(query.can_edit(self.other_user))

    def test_saved_query_anonymous_cannot_view(self):
        """Anonymous users cannot view any saved queries."""
        query = SavedQuery.objects.create(
            name='Public Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.OTHER,
            permission=SavedQuery.Permission.PUBLIC
        )
        # can_view checks is_authenticated
        self.assertFalse(query.can_view(None))

    def test_saved_query_job_tracking_fields(self):
        """SavedQuery tracks job status correctly."""
        query = SavedQuery.objects.create(
            name='Job Test',
            owner=self.user,
            query_type=SavedQuery.QueryType.WEDDING,
            job_id='job-123',
            job_status=SavedQuery.JobStatus.PROCESSING,
            job_error='',
            result_data=None
        )
        self.assertEqual(query.job_id, 'job-123')
        self.assertEqual(query.job_status, SavedQuery.JobStatus.PROCESSING)
        self.assertEqual(query.job_error, '')
        self.assertIsNone(query.result_data)

    def test_saved_query_result_data_stored(self):
        """SavedQuery stores result data when job completes."""
        query = SavedQuery.objects.create(
            name='Completed Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.PROJECT,
            job_id='job-456',
            job_status=SavedQuery.JobStatus.COMPLETED,
            result_data={
                'elections': [
                    {'date': '2024-06-15', 'score': 0.95, 'reason': 'Venus trine Jupiter'}
                ]
            }
        )
        self.assertEqual(query.result_data['elections'][0]['date'], '2024-06-15')

    def test_saved_query_ordering(self):
        """SavedQuery orders by created_at descending."""
        query1 = SavedQuery.objects.create(
            name='First Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.OTHER
        )
        query2 = SavedQuery.objects.create(
            name='Second Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.OTHER
        )
        queries = list(SavedQuery.objects.all())
        # Most recent first
        self.assertEqual(queries[0], query2)
        self.assertEqual(queries[1], query1)


# =============================================================================
# FORM TESTS
# =============================================================================

class SavedQueryFormTest(TestCase):
    """Tests for the SavedQueryForm."""

    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_form_valid_data(self):
        """Form is valid with complete required data."""
        form = SavedQueryForm(data={
            'name': 'Test Query',
            'query_type': 'wedding',
            'permission': 'private',
        })
        self.assertTrue(form.is_valid())

    def test_form_missing_name(self):
        """Form is invalid when name is missing."""
        form = SavedQueryForm(data={
            'query_type': 'wedding',
            'permission': 'private',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_form_clears_shared_with_for_private(self):
        """Form clears shared_with when permission is private."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        form = SavedQueryForm(
            data={
                'name': 'Test Query',
                'query_type': 'wedding',
                'permission': 'private',
            },
            initial={'shared_with': [other_user]}
        )
        self.assertTrue(form.is_valid())
        cleaned = form.clean()
        self.assertEqual(list(cleaned.get('shared_with', [])), [])

    def test_form_clears_shared_with_for_public(self):
        """Form clears shared_with when permission is public."""
        other_user = User.objects.create_user(
            username='otheruser2',
            email='other2@example.com',
            password='testpass123'
        )
        form = SavedQueryForm(
            data={
                'name': 'Test Query',
                'query_type': 'wedding',
                'permission': 'public',
            },
            initial={'shared_with': [other_user]}
        )
        self.assertTrue(form.is_valid())
        cleaned = form.clean()
        self.assertEqual(list(cleaned.get('shared_with', [])), [])

    def test_form_invalid_query_type(self):
        """Form is invalid with unknown query type."""
        form = SavedQueryForm(data={
            'name': 'Test Query',
            'query_type': 'invalid_type',
            'permission': 'private',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('query_type', form.errors)

    def test_form_invalid_permission(self):
        """Form is invalid with unknown permission."""
        form = SavedQueryForm(data={
            'name': 'Test Query',
            'query_type': 'wedding',
            'permission': 'invalid_permission',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('permission', form.errors)


class SavedQueryCreateFormTest(TestCase):
    """Tests for the SavedQueryCreateForm."""

    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_form_sets_owner(self):
        """CreateForm assigns user as owner on save."""
        form = SavedQueryCreateForm(
            data={
                'name': 'New Query',
                'query_type': 'project',
                'permission': 'private',
            },
            user=self.user
        )
        self.assertTrue(form.is_valid())
        query = form.save()
        self.assertEqual(query.owner, self.user)

    def test_create_form_default_permission(self):
        """CreateForm defaults to private permission."""
        form = SavedQueryCreateForm(
            data={
                'name': 'New Query',
                'query_type': 'wedding',
            },
            user=self.user
        )
        self.assertTrue(form.is_valid())
        query = form.save()
        self.assertEqual(query.permission, SavedQuery.Permission.PRIVATE)

    def test_create_form_default_query_type(self):
        """CreateForm defaults to OTHER query type."""
        form = SavedQueryCreateForm(
            data={
                'name': 'New Query',
                'permission': 'private',
            },
            user=self.user
        )
        self.assertTrue(form.is_valid())
        query = form.save()
        self.assertEqual(query.query_type, SavedQuery.QueryType.OTHER)


# =============================================================================
# VIEW TESTS - LIST
# =============================================================================

class SavedQueryListViewTest(TestCase):
    """Tests for the SavedQuery list view."""

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
        response = self.client.get(reverse('electional:saved_query_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_list_returns_200_for_authenticated(self):
        """Authenticated users should get 200 with their visible queries."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('electional:saved_query_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_shows_own_private_queries(self):
        """Users should see their own private queries."""
        self.client.login(email='test@example.com', password='testpass123')
        SavedQuery.objects.create(
            name='My Private Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.WEDDING,
            permission=SavedQuery.Permission.PRIVATE
        )
        response = self.client.get(reverse('electional:saved_query_list'))
        self.assertContains(response, 'My Private Query')

    def test_list_hides_other_users_private_queries(self):
        """Users should NOT see other users' private queries."""
        self.client.login(email='other@example.com', password='testpass123')
        SavedQuery.objects.create(
            name='Other User Private',
            owner=self.user,
            query_type=SavedQuery.QueryType.WEDDING,
            permission=SavedQuery.Permission.PRIVATE
        )
        response = self.client.get(reverse('electional:saved_query_list'))
        self.assertNotContains(response, 'Other User Private')

    def test_list_shows_public_queries(self):
        """Users should see public queries from other users."""
        self.client.login(email='other@example.com', password='testpass123')
        SavedQuery.objects.create(
            name='Public Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.WEDDING,
            permission=SavedQuery.Permission.PUBLIC
        )
        response = self.client.get(reverse('electional:saved_query_list'))
        self.assertContains(response, 'Public Query')


# =============================================================================
# VIEW TESTS - CREATE
# =============================================================================

class SavedQueryCreateViewTest(TestCase):
    """Tests for the SavedQuery create view."""

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
        response = self.client.get(reverse('electional:saved_query_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_create_get_returns_form(self):
        """GET request should return the create form."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('electional:saved_query_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id_name')
        self.assertContains(response, 'Create Saved Query')

    def test_create_post_success(self):
        """POST with valid data should create query and redirect."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(reverse('electional:saved_query_create'), {
            'name': 'New Saved Query',
            'query_type': 'wedding',
            'permission': 'private',
        })
        # Should redirect to list on success
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SavedQuery.objects.filter(name='New Saved Query').exists())
        query = SavedQuery.objects.get(name='New Saved Query')
        self.assertEqual(query.owner, self.user)

    def test_create_post_invalid_data(self):
        """POST with invalid data should show form errors."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(reverse('electional:saved_query_create'), {
            'name': '',  # Required field missing
            'query_type': 'wedding',
            'permission': 'private',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SavedQuery.objects.filter(name='New Saved Query').exists())


# =============================================================================
# VIEW TESTS - DETAIL
# =============================================================================

class SavedQueryDetailViewTest(TestCase):
    """Tests for the SavedQuery detail view."""

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
        self.query = SavedQuery.objects.create(
            name='Private Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.WEDDING,
            permission=SavedQuery.Permission.PRIVATE
        )

    def test_detail_requires_login(self):
        """Detail view should redirect anonymous users to login."""
        response = self.client.get(
            reverse('electional:saved_query_detail', kwargs={'pk': self.query.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_detail_success_owner(self):
        """Owner should be able to view their private query."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(
            reverse('electional:saved_query_detail', kwargs={'pk': self.query.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Private Query')

    def test_detail_forbidden_non_owner_private(self):
        """Non-owner should get 404 for private query (filtered from queryset)."""
        self.client.login(email='other@example.com', password='testpass123')
        response = self.client.get(
            reverse('electional:saved_query_detail', kwargs={'pk': self.query.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_detail_public_visible_to_all(self):
        """Public queries should be visible to all authenticated users."""
        public_query = SavedQuery.objects.create(
            name='Public Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.WEDDING,
            permission=SavedQuery.Permission.PUBLIC
        )
        self.client.login(email='other@example.com', password='testpass123')
        response = self.client.get(
            reverse('electional:saved_query_detail', kwargs={'pk': public_query.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Query')


# =============================================================================
# VIEW TESTS - UPDATE
# =============================================================================

class SavedQueryUpdateViewTest(TestCase):
    """Tests for the SavedQuery update view."""

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
        self.query = SavedQuery.objects.create(
            name='My Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.WEDDING,
            permission=SavedQuery.Permission.PRIVATE
        )

    def test_edit_requires_login(self):
        """Edit view should redirect anonymous users to login."""
        response = self.client.get(
            reverse('electional:saved_query_edit', kwargs={'pk': self.query.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_edit_success_owner(self):
        """Owner should be able to edit their query."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(
            reverse('electional:saved_query_edit', kwargs={'pk': self.query.pk}),
            {
                'name': 'Updated Query Name',
                'query_type': 'project',
                'permission': 'private',
            }
        )
        # Should redirect to detail on success
        self.assertEqual(response.status_code, 302)
        self.query.refresh_from_db()
        self.assertEqual(self.query.name, 'Updated Query Name')

    def test_edit_forbidden_non_owner(self):
        """Non-owner should get 404 (not found - queryset filtered)."""
        self.client.login(email='other@example.com', password='testpass123')
        response = self.client.get(
            reverse('electional:saved_query_edit', kwargs={'pk': self.query.pk})
        )
        self.assertEqual(response.status_code, 404)


# =============================================================================
# VIEW TESTS - DELETE
# =============================================================================

class SavedQueryDeleteViewTest(TestCase):
    """Tests for the SavedQuery delete view."""

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
        self.query = SavedQuery.objects.create(
            name='My Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.WEDDING,
            permission=SavedQuery.Permission.PRIVATE
        )

    def test_delete_requires_login(self):
        """Delete view should redirect anonymous users to login."""
        response = self.client.get(
            reverse('electional:saved_query_delete', kwargs={'pk': self.query.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_delete_success_owner(self):
        """Owner should be able to delete their query."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(
            reverse('electional:saved_query_delete', kwargs={'pk': self.query.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SavedQuery.objects.filter(pk=self.query.pk).exists())

    def test_delete_forbidden_non_owner(self):
        """Non-owner should get 404 (not found - queryset filtered)."""
        self.client.login(email='other@example.com', password='testpass123')
        response = self.client.get(
            reverse('electional:saved_query_delete', kwargs={'pk': self.query.pk})
        )
        self.assertEqual(response.status_code, 404)


# =============================================================================
# PERMISSION TESTS
# =============================================================================

class SavedQueryPermissionTest(TestCase):
    """Tests for saved query visibility and access permissions."""

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
        self.private_query = SavedQuery.objects.create(
            name='Private Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.WEDDING,
            permission=SavedQuery.Permission.PRIVATE
        )
        self.public_query = SavedQuery.objects.create(
            name='Public Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.PROJECT,
            permission=SavedQuery.Permission.PUBLIC
        )
        self.named_group_query = SavedQuery.objects.create(
            name='Group Query',
            owner=self.user,
            query_type=SavedQuery.QueryType.TRAVEL,
            permission=SavedQuery.Permission.NAMED_GROUP
        )
        self.named_group_query.shared_with.add(self.user2)

    def test_private_queries_invisible_to_other_users(self):
        """Private queries should NOT appear in other users' list views."""
        self.client.login(email='user2@example.com', password='testpass123')
        response = self.client.get(reverse('electional:saved_query_list'))
        self.assertNotContains(response, 'Private Query')

    def test_public_queries_visible_to_all_authenticated(self):
        """Public queries should appear in all authenticated users' list views."""
        # User 2 sees public query
        self.client.login(email='user2@example.com', password='testpass123')
        response = self.client.get(reverse('electional:saved_query_list'))
        self.assertContains(response, 'Public Query')

        # User 3 also sees public query
        self.client.login(email='user3@example.com', password='testpass123')
        response = self.client.get(reverse('electional:saved_query_list'))
        self.assertContains(response, 'Public Query')

    def test_named_group_queries_visible_to_shared_users(self):
        """Named group queries should appear in shared users' list views."""
        self.client.login(email='user2@example.com', password='testpass123')
        response = self.client.get(reverse('electional:saved_query_list'))
        self.assertContains(response, 'Group Query')

    def test_named_group_queries_invisible_to_non_shared_users(self):
        """Named group queries should NOT appear in non-shared users' list views."""
        self.client.login(email='user3@example.com', password='testpass123')
        response = self.client.get(reverse('electional:saved_query_list'))
        self.assertNotContains(response, 'Group Query')

    def test_owner_sees_all_their_queries(self):
        """Owner should see all their queries regardless of permission."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('electional:saved_query_list'))
        self.assertContains(response, 'Private Query')
        self.assertContains(response, 'Public Query')
        self.assertContains(response, 'Group Query')


# =============================================================================
# HTMX TESTS
# =============================================================================

class SavedQueryHTMXTest(TestCase):
    """Tests for HTMX partial template responses."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_htmx_success(self):
        """HTMX create request should redirect on success."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(
            reverse('electional:saved_query_create'),
            HTTP_HX_REQUEST='true',
            data={
                'name': 'HTMX Create Test',
                'query_type': 'wedding',
                'permission': 'private',
            }
        )
        # HTMX redirects on success
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SavedQuery.objects.filter(name='HTMX Create Test').exists())


# =============================================================================
# API CLIENT TESTS
# =============================================================================

class QueryRequestTests(TestCase):
    """Tests for the QueryRequest dataclass."""

    def test_query_request_basic(self):
        """Test creating a basic QueryRequest."""
        request = QueryRequest(
            query_type="wedding",
            description="Find an auspicious date for our wedding ceremony",
            latitude=40.7128,
            longitude=-74.0060,
            location_name="New York, NY",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
        )
        self.assertEqual(request.query_type, "wedding")
        self.assertEqual(request.latitude, 40.7128)
        self.assertEqual(request.longitude, -74.0060)
        self.assertEqual(request.start_date, date(2024, 6, 1))
        self.assertEqual(request.end_date, date(2024, 6, 30))
        self.assertIsNone(request.preferences)

    def test_query_request_with_preferences(self):
        """Test QueryRequest with user preferences."""
        request = QueryRequest(
            query_type="project",
            description="Start a new software project",
            latitude=51.5074,
            longitude=-0.1278,
            location_name="London, UK",
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 31),
            preferences={"avoid_weekends": True, "time_of_day": "morning"},
        )
        self.assertEqual(request.preferences["avoid_weekends"], True)
        self.assertEqual(request.preferences["time_of_day"], "morning")

    def test_query_request_all_query_types(self):
        """Test QueryRequest with all supported query types."""
        query_types = ["wedding", "project", "travel", "move_in", "medical", "other"]
        for qtype in query_types:
            request = QueryRequest(
                query_type=qtype,
                description=f"Test query for {qtype}",
                latitude=0.0,
                longitude=0.0,
                location_name="Test Location",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )
            self.assertEqual(request.query_type, qtype)


class QueryAPIErrorTests(TestCase):
    """Tests for QueryAPIError and QueryTimeoutError exceptions."""

    def test_query_api_error_str(self):
        """Test QueryAPIError string representation."""
        error = QueryAPIError("Test error", status_code=400)
        self.assertEqual(str(error), "QueryAPIError(400): Test error")
        self.assertEqual(error.status_code, 400)
        self.assertEqual(error.error_message, "Test error")

    def test_query_api_error_no_status_code(self):
        """Test QueryAPIError without status code."""
        error = QueryAPIError("Connection failed")
        self.assertIsNone(error.status_code)
        self.assertEqual(str(error), "QueryAPIError: Connection failed")

    def test_query_api_error_with_response_data(self):
        """Test QueryAPIError with response data."""
        error = QueryAPIError(
            "Bad request",
            status_code=422,
            response_data={"field": "query_type", "error": "invalid value"},
        )
        self.assertEqual(error.response_data["field"], "query_type")

    def test_query_timeout_error(self):
        """Test QueryTimeoutError inherits from QueryAPIError."""
        error = QueryTimeoutError("Request timed out")
        self.assertIsInstance(error, QueryAPIError)
        self.assertIsNone(error.status_code)
        self.assertEqual(error.error_message, "Request timed out")


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class SubmitQueryTests(TestCase):
    """Tests for submit_query function."""

    @patch("electional.clients.requests.post")
    def test_submit_query_success(self, mock_post):
        """Test successful query submission."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"job_id": "job-123", "status": "pending"}
        mock_post.return_value = mock_response

        request = QueryRequest(
            query_type="wedding",
            description="Find an auspicious wedding date",
            latitude=40.7128,
            longitude=-74.0060,
            location_name="New York, NY",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
        )

        result = submit_query(request)

        self.assertEqual(result["job_id"], "job-123")
        self.assertEqual(result["status"], "pending")
        mock_post.assert_called_once()

    @patch("electional.clients.requests.post")
    def test_submit_query_with_preferences(self, mock_post):
        """Test query submission with preferences included in payload."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"job_id": "job-456", "status": "pending"}
        mock_post.return_value = mock_response

        request = QueryRequest(
            query_type="project",
            description="Start a new project",
            latitude=51.5074,
            longitude=-0.1278,
            location_name="London, UK",
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 31),
            preferences={"avoid_friday_13th": True},
        )

        submit_query(request)

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        self.assertEqual(payload["query_type"], "project")
        self.assertEqual(payload["preferences"]["avoid_friday_13th"], True)

    @patch("electional.clients.requests.post")
    def test_submit_query_api_error(self, mock_post):
        """Test query submission returns API error on non-success response."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 422
        mock_response.json.return_value = {"error": "Invalid query type"}
        mock_response.text = '{"error": "Invalid query type"}'
        mock_post.return_value = mock_response

        request = QueryRequest(
            query_type="wedding",
            description="Test",
            latitude=0.0,
            longitude=0.0,
            location_name="Test",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        with self.assertRaises(QueryAPIError) as ctx:
            submit_query(request)

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(ctx.exception.error_message, "Invalid query type")

    @patch("electional.clients.requests.post")
    def test_submit_query_timeout(self, mock_post):
        """Test query submission raises QueryTimeoutError on timeout."""
        import requests

        mock_post.side_effect = requests.Timeout("Connection timed out")

        request = QueryRequest(
            query_type="travel",
            description="Find a good travel date",
            latitude=0.0,
            longitude=0.0,
            location_name="Test",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        with self.assertRaises(QueryTimeoutError):
            submit_query(request)

    @patch("electional.clients.requests.post")
    def test_submit_query_connection_error(self, mock_post):
        """Test query submission raises QueryAPIError on connection failure."""
        import requests

        mock_post.side_effect = requests.ConnectionError("Connection refused")

        request = QueryRequest(
            query_type="other",
            description="Test",
            latitude=0.0,
            longitude=0.0,
            location_name="Test",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        with self.assertRaises(QueryAPIError) as ctx:
            submit_query(request)

        self.assertIsNone(ctx.exception.status_code)
        self.assertIn("Could not connect", ctx.exception.error_message)


@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086", QUERY_API_TIMEOUT=30)
class GetJobStatusTests(TestCase):
    """Tests for get_job_status function."""

    @patch("electional.clients.requests.get")
    def test_get_job_status_pending(self, mock_get):
        """Test checking job status when pending."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "job_id": "job-123",
            "status": "pending",
        }
        mock_get.return_value = mock_response

        result = get_job_status("job-123")

        self.assertEqual(result["status"], "pending")
        mock_get.assert_called_once()

    @patch("electional.clients.requests.get")
    def test_get_job_status_completed(self, mock_get):
        """Test checking job status when completed."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "job_id": "job-123",
            "status": "completed",
            "result": {
                "elections": [
                    {"date": "2024-06-15", "score": 0.95},
                ],
            },
        }
        mock_get.return_value = mock_response

        result = get_job_status("job-123")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(result["result"]["elections"]), 1)

    @patch("electional.clients.requests.get")
    def test_get_job_status_failed(self, mock_get):
        """Test checking job status when failed."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "job_id": "job-123",
            "status": "failed",
            "error": "Insufficient date range",
        }
        mock_get.return_value = mock_response

        result = get_job_status("job-123")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "Insufficient date range")

    @patch("electional.clients.requests.get")
    def test_get_job_status_api_error(self, mock_get):
        """Test job status check raises API error on non-success response."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Job not found"}
        mock_response.text = '{"error": "Job not found"}'
        mock_get.return_value = mock_response

        with self.assertRaises(QueryAPIError) as ctx:
            get_job_status("nonexistent-job")

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.error_message, "Job not found")

    @patch("electional.clients.requests.get")
    def test_get_job_status_timeout(self, mock_get):
        """Test job status check raises QueryTimeoutError on timeout."""
        import requests

        mock_get.side_effect = requests.Timeout("Connection timed out")

        with self.assertRaises(QueryTimeoutError):
            get_job_status("job-123")

    @patch("electional.clients.requests.get")
    def test_get_job_status_connection_error(self, mock_get):
        """Test job status check raises QueryAPIError on connection failure."""
        import requests

        mock_get.side_effect = requests.ConnectionError("Connection refused")

        with self.assertRaises(QueryAPIError) as ctx:
            get_job_status("job-123")

        self.assertIsNone(ctx.exception.status_code)
        self.assertIn("Could not connect", ctx.exception.error_message)


# =============================================================================
# FEATURE FLAG TESTS
# =============================================================================

@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086")
class FeatureFlagTests(TestCase):
    """Tests for ELECTIONAL_ENABLED feature flag and context processor."""

    def test_flag_enabled_by_default(self):
        """ELECTIONAL_ENABLED defaults to True in settings."""
        from django.conf import settings
        self.assertTrue(getattr(settings, 'ELECTIONAL_ENABLED', True))

    @override_settings(ELECTIONAL_ENABLED=False)
    def test_flag_disabled_hides_nav(self):
        """When flag is disabled, electional nav link should not render."""
        from django.test import RequestFactory
        from core.context_processors import feature_flags
        
        factory = RequestFactory()
        request = factory.get('/')
        ctx = feature_flags(request)
        self.assertFalse(ctx['feature_flags']['ELECTIONAL_ENABLED'])

    @override_settings(ELECTIONAL_ENABLED=True)
    def test_flag_enabled_shows_nav(self):
        """When flag is enabled, feature_flags context reflects that."""
        from django.test import RequestFactory
        from core.context_processors import feature_flags
        
        factory = RequestFactory()
        request = factory.get('/')
        ctx = feature_flags(request)
        self.assertTrue(ctx['feature_flags']['ELECTIONAL_ENABLED'])


# =============================================================================
# JOB STATUS VIEW TESTS
# =============================================================================

@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086")
class SavedQueryJobStatusViewTests(TestCase):
    """Tests for the job polling HTMX endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
        )
        self.query = SavedQuery.objects.create(
            name="Test Query",
            owner=self.user,
            query_type="wedding",
            query_params={
                "description": "Test",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "location_name": "New York",
                "start_date": "2024-06-01",
                "end_date": "2024-06-30",
            },
            job_id="job-abc123",
            job_status=SavedQuery.JobStatus.PENDING,
        )

    def test_job_status_poll_returns_html(self):
        """Polling endpoint returns HTML for pending job."""
        self.client.force_login(self.user)
        with patch('electional.views.get_job_status') as mock_status:
            mock_status.return_value = {
                'job_id': 'job-abc123',
                'status': 'processing',
            }
            resp = self.client.get(
                f'/electional/{self.query.pk}/job-status/'
            )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'job-abc123', resp.content)

    @patch('electional.views.get_job_status')
    def test_job_status_poll_completed(self, mock_status):
        """Polling detects completed job and stores results."""
        mock_status.return_value = {
            'job_id': 'job-abc123',
            'status': 'completed',
            'result': {'elections': [{'date': '2024-06-15'}]},
        }
        self.client.force_login(self.user)
        resp = self.client.get(
            f'/electional/{self.query.pk}/job-status/'
        )
        self.assertEqual(resp.status_code, 200)
        self.query.refresh_from_db()
        self.assertEqual(self.query.job_status, SavedQuery.JobStatus.COMPLETED)
        self.assertIn('elections', self.query.result_data)

    @patch('electional.views.get_job_status')
    def test_job_status_poll_failed(self, mock_status):
        """Polling detects failed job and stores error."""
        mock_status.return_value = {
            'job_id': 'job-abc123',
            'status': 'failed',
            'error': 'Internal error',
        }
        self.client.force_login(self.user)
        resp = self.client.get(
            f'/electional/{self.query.pk}/job-status/'
        )
        self.assertEqual(resp.status_code, 200)
        self.query.refresh_from_db()
        self.assertEqual(self.query.job_status, SavedQuery.JobStatus.FAILED)
        self.assertEqual(self.query.job_error, 'Internal error')

    @patch('electional.views.get_job_status')
    def test_job_status_poll_transient_error_keeps_status(self, mock_status):
        """Transient API errors don't change job status."""
        mock_status.side_effect = QueryTimeoutError("timeout")
        self.client.force_login(self.user)
        resp = self.client.get(
            f'/electional/{self.query.pk}/job-status/'
        )
        self.assertEqual(resp.status_code, 200)
        self.query.refresh_from_db()
        # Status should remain PENDING despite transient error
        self.assertEqual(self.query.job_status, SavedQuery.JobStatus.PENDING)

    def test_job_status_requires_login(self):
        """Polling endpoint requires authentication."""
        resp = self.client.get(
            f'/electional/{self.query.pk}/job-status/'
        )
        # Should redirect to login
        self.assertEqual(resp.status_code, 302)

    @patch('electional.views.get_job_status')
    def test_job_status_maps_in_process(self, mock_status):
        """API status 'in_process' maps to PROCESSING."""
        mock_status.return_value = {
            'job_id': 'job-abc123',
            'status': 'in_process',
        }
        self.client.force_login(self.user)
        resp = self.client.get(
            f'/electional/{self.query.pk}/job-status/'
        )
        self.assertEqual(resp.status_code, 200)
        self.query.refresh_from_db()
        self.assertEqual(self.query.job_status, SavedQuery.JobStatus.PROCESSING)

    def test_job_status_no_job_id_returns_empty(self):
        """Polling for a query with no job_id returns empty response."""
        self.query.job_id = ''
        self.query.save()
        self.client.force_login(self.user)
        resp = self.client.get(
            f'/electional/{self.query.pk}/job-status/'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b'')


# =============================================================================
# SUBMIT VIEW TESTS
# =============================================================================

@override_settings(ASTRO_CLOCK_SERVER="http://localhost:8086")
class SavedQuerySubmitViewTests(TestCase):
    """Tests for the query submission HTMX endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="submit@example.com",
            username="submituser",
            password="testpass123",
        )
        self.query = SavedQuery.objects.create(
            name="Submit Test Query",
            owner=self.user,
            query_type="project",
            query_params={
                "description": "Launch a project",
                "latitude": 51.5074,
                "longitude": -0.1278,
                "location_name": "London, UK",
                "start_date": "2024-03-01",
                "end_date": "2024-03-31",
            },
        )

    @patch('electional.views.submit_query')
    def test_submit_creates_job(self, mock_submit):
        """Submitting a query stores job_id and sets status to PENDING."""
        mock_submit.return_value = {'job_id': 'new-job-001', 'status': 'pending'}
        self.client.force_login(self.user)
        resp = self.client.post(
            f'/electional/{self.query.pk}/submit/'
        )
        self.assertEqual(resp.status_code, 200)
        self.query.refresh_from_db()
        self.assertEqual(self.query.job_id, 'new-job-001')
        self.assertEqual(self.query.job_status, SavedQuery.JobStatus.PENDING)

    @patch('electional.views.submit_query')
    def test_submit_api_error_marks_failed(self, mock_submit):
        """API error during submit marks query as FAILED."""
        mock_submit.side_effect = QueryAPIError("Server error", status_code=500)
        self.client.force_login(self.user)
        resp = self.client.post(
            f'/electional/{self.query.pk}/submit/'
        )
        self.assertEqual(resp.status_code, 200)
        self.query.refresh_from_db()
        self.assertEqual(self.query.job_status, SavedQuery.JobStatus.FAILED)
        self.assertIn('Server error', self.query.job_error)

    def test_submit_requires_login(self):
        """Submit endpoint requires authentication."""
        resp = self.client.post(
            f'/electional/{self.query.pk}/submit/'
        )
        self.assertEqual(resp.status_code, 302)

    def test_submit_requires_owner(self):
        """Only the owner can submit a query."""
        other = User.objects.create_user(
            email="other@example.com",
            username="otheruser",
            password="testpass123",
        )
        self.client.force_login(other)
        resp = self.client.post(
            f'/electional/{self.query.pk}/submit/'
        )
        self.assertEqual(resp.status_code, 404)

    @patch('electional.views.submit_query')
    def test_submit_already_processing_returns_status(self, mock_submit):
        """Submitting for a query already processing returns current status without new API call."""
        self.query.job_id = 'existing-job'
        self.query.job_status = SavedQuery.JobStatus.PROCESSING
        self.query.save()
        
        self.client.force_login(self.user)
        resp = self.client.post(
            f'/electional/{self.query.pk}/submit/'
        )
        self.assertEqual(resp.status_code, 200)
        mock_submit.assert_not_called()
