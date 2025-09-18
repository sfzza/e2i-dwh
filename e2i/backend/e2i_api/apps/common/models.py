# e2i_api/apps/common/models.py - Add this to your existing models.py or create a new app

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        
        user = self.model(
            username=username,
            email=self.normalize_email(email) if email else None,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_active', True)
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('user', 'Regular User'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # API Key for header-based authentication
    api_key = models.CharField(max_length=64, unique=True, blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        db_table = 'auth_users'
        indexes = [
            models.Index(fields=['username'], name='idx_users_username'),
            models.Index(fields=['api_key'], name='idx_users_api_key'),
            models.Index(fields=['role'], name='idx_users_role'),
        ]

    def __str__(self):
        return f"{self.username} ({self.role})"

    def is_admin(self):
        return self.role == 'admin'

    def is_regular_user(self):
        return self.role == 'user'

    def generate_api_key(self):
        """Generate a new API key for the user"""
        import secrets
        self.api_key = secrets.token_hex(32)
        self.save(update_fields=['api_key'])
        return self.api_key

    @property
    def is_staff(self):
        return self.role == 'admin'


class UserSession(models.Model):
    """Track user sessions for API access"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    last_accessed = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['session_token'], name='idx_sessions_token'),
            models.Index(fields=['user', 'is_active'], name='idx_sessions_user_active'),
        ]

    def is_expired(self):
        return timezone.now() > self.expires_at

    def refresh(self):
        """Extend session expiry"""
        from datetime import timedelta
        self.expires_at = timezone.now() + timedelta(days=7)
        self.last_accessed = timezone.now()
        self.save(update_fields=['expires_at', 'last_accessed'])