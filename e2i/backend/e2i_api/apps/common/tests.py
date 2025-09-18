# e2i_api/apps/common/tests.py

import json
import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import UserSession

User = get_user_model()


class AuthTestCase(TestCase):
    """Base test case with authentication utilities."""
    
    def setUp(self):
        """Set up test users and authentication."""
        self.client = Client()
        
        # Create test users
        self.admin_user = User.objects.create_user(
            username='test_admin',
            email='admin@test.com',
            password='admin123',
            role='admin'
        )
        self.admin_user.generate_api_key()
        
        self.regular_user = User.objects.create_user(
            username='test_user',
            email='user@test.com',
            password='user123',
            role='user'
        )
        self.regular_user.generate_api_key()
        
        # Create inactive user for testing
        self.inactive_user = User.objects.create_user(
            username='inactive_user',
            email='inactive@test.com',
            password='inactive123',
            role='user',
            is_active=False
        )

    def authenticate_as_admin(self):
        """Authenticate client as admin using API key."""
        return {'X-API-Key': self.admin_user.api_key}

    def authenticate_as_user(self):
        """Authenticate client as regular user using API key."""
        return {'X-API-Key': self.regular_user.api_key}

    def authenticate_with_session(self, user):
        """Authenticate using session token."""
        session = UserSession.objects.create(
            user=user,
            session_token='test_session_token_' + str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(days=7)
        )
        return {'X-Session-Token': session.session_token}

    def get_json_response(self, response):
        """Helper to parse JSON response."""
        return json.loads(response.content.decode('utf-8'))


class UserModelTests(AuthTestCase):
    """Test the custom User model."""
    
    def test_user_creation(self):
        """Test creating users with different roles."""
        # Test admin user
        self.assertTrue(self.admin_user.is_admin())
        self.assertFalse(self.admin_user.is_regular_user())
        
        # Test regular user
        self.assertFalse(self.regular_user.is_admin())
        self.assertTrue(self.regular_user.is_regular_user())

    def test_api_key_generation(self):
        """Test API key generation."""
        user = User.objects.create_user(
            username='test_api_user',
            password='test123'
        )
        
        # Should not have API key initially
        self.assertIsNone(user.api_key)
        
        # Generate API key
        api_key = user.generate_api_key()
        
        # Should have 64-character hex string
        self.assertEqual(len(api_key), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in api_key))
        
        # Should be saved to user
        user.refresh_from_db()
        self.assertEqual(user.api_key, api_key)

    def test_user_string_representation(self):
        """Test user string representation."""
        expected = f"{self.admin_user.username} ({self.admin_user.role})"
        self.assertEqual(str(self.admin_user), expected)


class AuthenticationTests(AuthTestCase):
    """Test authentication endpoints."""
    
    def test_login_success(self):
        """Test successful login."""
        response = self.client.post('/auth/login', {
            'username': 'test_admin',
            'password': 'admin123'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = self.get_json_response(response)
        
        self.assertTrue(data['success'])
        self.assertIn('session_token', data)
        self.assertIn('api_key', data)
        self.assertEqual(data['user']['username'], 'test_admin')
        self.assertEqual(data['user']['role'], 'admin')

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = self.client.post('/auth/login', {
            'username': 'test_admin',
            'password': 'wrong_password'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
        data = self.get_json_response(response)
        self.assertEqual(data['code'], 'INVALID_CREDENTIALS')

    def test_login_inactive_user(self):
        """Test login with inactive user."""
        response = self.client.post('/auth/login', {
            'username': 'inactive_user',
            'password': 'inactive123'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 401)

    def test_api_key_authentication(self):
        """Test API key authentication."""
        headers = self.authenticate_as_admin()
        
        response = self.client.get('/auth/profile', **headers)
        self.assertEqual(response.status_code, 200)
        
        data = self.get_json_response(response)
        self.assertEqual(data['user']['username'], 'test_admin')

    def test_session_token_authentication(self):
        """Test session token authentication."""
        headers = self.authenticate_with_session(self.admin_user)
        
        response = self.client.get('/auth/profile', **headers)
        self.assertEqual(response.status_code, 200)
        
        data = self.get_json_response(response)
        self.assertEqual(data['user']['username'], 'test_admin')

    def test_generate_api_key(self):
        """Test API key generation endpoint."""
        headers = self.authenticate_as_admin()
        
        response = self.client.post('/auth/generate-api-key', **headers)
        self.assertEqual(response.status_code, 200)
        
        data = self.get_json_response(response)
        self.assertTrue(data['success'])
        self.assertIn('api_key', data)
        
        # Verify the API key was updated
        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.api_key, data['api_key'])

    def test_logout(self):
        """Test logout endpoint."""
        headers = self.authenticate_with_session(self.admin_user)
        
        response = self.client.post('/auth/logout', **headers)
        self.assertEqual(response.status_code, 200)
        
        # Session should be deactivated
        session_token = headers['X-Session-Token']
        session = UserSession.objects.get(session_token=session_token)
        self.assertFalse(session.is_active)


class AuthorizationTests(AuthTestCase):
    """Test role-based authorization."""
    
    def test_admin_required_endpoint(self):
        """Test endpoint that requires admin role."""
        # Admin should have access
        headers = self.authenticate_as_admin()
        response = self.client.get('/templates/', **headers)
        self.assertEqual(response.status_code, 200)
        
        # Regular user should have access (templates list is user_access_required)
        headers = self.authenticate_as_user()
        response = self.client.get('/templates/', **headers)
        self.assertEqual(response.status_code, 200)
        
        # Unauthenticated should be denied
        response = self.client.get('/templates/')
        self.assertEqual(response.status_code, 401)

    def test_user_access_required(self):
        """Test endpoint accessible to both admin and user."""
        # Both admin and user should have access
        for headers in [self.authenticate_as_admin(), self.authenticate_as_user()]:
            response = self.client.get('/auth/profile', **headers)
            self.assertEqual(response.status_code, 200)

    def test_invalid_api_key(self):
        """Test with invalid API key."""
        response = self.client.get('/auth/profile', **{'X-API-Key': 'invalid_key'})
        self.assertEqual(response.status_code, 401)

    def test_expired_session(self):
        """Test with expired session token."""
        # Create expired session
        session = UserSession.objects.create(
            user=self.admin_user,
            session_token='expired_token',
            expires_at=timezone.now() - timedelta(days=1)
        )
        
        response = self.client.get('/auth/profile', **{'X-Session-Token': session.session_token})
        self.assertEqual(response.status_code, 401)
        
        # Session should be deactivated
        session.refresh_from_db()
        self.assertFalse(session.is_active)


class UserSessionTests(AuthTestCase):
    """Test UserSession model and functionality."""
    
    def test_session_creation(self):
        """Test creating a user session."""
        session = UserSession.objects.create(
            user=self.admin_user,
            session_token='test_token',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        self.assertTrue(session.is_active)
        self.assertFalse(session.is_expired())

    def test_session_expiry(self):
        """Test session expiry detection."""
        session = UserSession.objects.create(
            user=self.admin_user,
            session_token='expired_token',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        self.assertTrue(session.is_expired())

    def test_session_refresh(self):
        """Test session refresh functionality."""
        session = UserSession.objects.create(
            user=self.admin_user,
            session_token='refresh_token',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        old_expires = session.expires_at
        old_accessed = session.last_accessed
        
        # Wait a moment to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        session.refresh()
        
        self.assertGreater(session.expires_at, old_expires)
        self.assertGreater(session.last_accessed, old_accessed)


class APITestMixin:
    """Mixin providing utilities for API testing."""
    
    def assert_requires_auth(self, url, method='GET', data=None):
        """Assert that an endpoint requires authentication."""
        if method == 'GET':
            response = self.client.get(url)
        elif method == 'POST':
            response = self.client.post(url, data or {}, content_type='application/json')
        elif method == 'PUT':
            response = self.client.put(url, data or {}, content_type='application/json')
        elif method == 'DELETE':
            response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 401)
        data = self.get_json_response(response)
        self.assertEqual(data['code'], 'AUTHENTICATION_REQUIRED')

    def assert_requires_admin(self, url, method='GET', data=None):
        """Assert that an endpoint requires admin role."""
        headers = self.authenticate_as_user()
        
        if method == 'GET':
            response = self.client.get(url, **headers)
        elif method == 'POST':
            response = self.client.post(url, data or {}, content_type='application/json', **headers)
        elif method == 'PUT':
            response = self.client.put(url, data or {}, content_type='application/json', **headers)
        elif method == 'DELETE':
            response = self.client.delete(url, **headers)
        
        self.assertEqual(response.status_code, 403)
        data = self.get_json_response(response)
        self.assertEqual(data['code'], 'ADMIN_REQUIRED')

    def assert_json_response(self, response, expected_status=200):
        """Assert response is JSON and has expected status."""
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(response['Content-Type'], 'application/json')
        return self.get_json_response(response)


# Test configuration for pytest
class TestSettings:
    """Test-specific Django settings."""
    
    @staticmethod
    def get_test_settings():
        """Return settings overrides for testing."""
        return {
            'DATABASES': {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            'CACHES': {
                'default': {
                    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                }
            },
            'PASSWORD_HASHERS': [
                'django.contrib.auth.hashers.MD5PasswordHasher',  # Fast for testing
            ],
            'EMAIL_BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
            'CELERY_TASK_ALWAYS_EAGER': True,
        }


# Test factory utilities
class UserFactory:
    """Factory for creating test users."""
    
    @staticmethod
    def create_admin(username='admin', email='admin@test.com', password='admin123'):
        """Create an admin user for testing."""
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='admin'
        )
        user.generate_api_key()
        return user

    @staticmethod
    def create_user(username='user', email='user@test.com', password='user123'):
        """Create a regular user for testing."""
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='user'
        )
        user.generate_api_key()
        return user

    @staticmethod
    def create_session(user, expires_in_days=7):
        """Create a session for the user."""
        return UserSession.objects.create(
            user=user,
            session_token=f'test_session_{uuid.uuid4()}',
            expires_at=timezone.now() + timedelta(days=expires_in_days)
        )


# Example integration test
class IntegrationTests(AuthTestCase, APITestMixin):
    """Integration tests for the complete authentication workflow."""
    
    def test_complete_auth_workflow(self):
        """Test the complete authentication workflow."""
        
        # 1. Login to get session token
        response = self.client.post('/auth/login', {
            'username': 'test_admin',
            'password': 'admin123'
        }, content_type='application/json')
        
        data = self.assert_json_response(response)
        session_token = data['session_token']
        api_key = data['api_key']
        
        # 2. Use session token to access protected endpoint
        response = self.client.get('/auth/profile', **{'X-Session-Token': session_token})
        profile_data = self.assert_json_response(response)
        self.assertEqual(profile_data['user']['username'], 'test_admin')
        
        # 3. Generate new API key
        response = self.client.post('/auth/generate-api-key', **{'X-Session-Token': session_token})
        new_key_data = self.assert_json_response(response)
        new_api_key = new_key_data['api_key']
        self.assertNotEqual(api_key, new_api_key)
        
        # 4. Use new API key
        response = self.client.get('/auth/profile', **{'X-API-Key': new_api_key})
        self.assert_json_response(response)
        
        # 5. Logout
        response = self.client.post('/auth/logout', **{'X-Session-Token': session_token})
        self.assert_json_response(response)
        
        # 6. Session token should no longer work
        response = self.client.get('/auth/profile', **{'X-Session-Token': session_token})
        self.assertEqual(response.status_code, 401)
        
        # 7. But API key should still work
        response = self.client.get('/auth/profile', **{'X-API-Key': new_api_key})
        self.assert_json_response(response)