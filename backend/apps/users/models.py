"""
Custom User model.

Uses Google OAuth as the only authentication mechanism.
No password field — authentication is delegated entirely to Google.
"""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email: str, google_id: str, name: str, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        if not google_id:
            raise ValueError('Google ID is required')
        email = self.normalize_email(email)
        user = self.model(email=email, google_id=google_id, name=name, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, google_id: str, name: str, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.CREATOR)
        return self.create_user(email, google_id, name, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model authenticated via Google OAuth.

    Role is stored explicitly on the user record.
    A user starts as 'user'; a creator is assigned via the admin or seed command.
    Role changes are intentional — not self-service — to prevent privilege escalation.
    """

    class Role(models.TextChoices):
        USER = 'user', 'User'
        CREATOR = 'creator', 'Creator'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Google OAuth identity — unique per Google account
    google_id = models.CharField(max_length=128, unique=True, db_index=True)

    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255)
    bio = models.TextField(blank=True, default='')
    avatar_url = models.URLField(blank=True, default='')

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
        db_index=True,
    )

    # Django admin fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['google_id', 'name']

    class Meta:
        db_table = 'users_user'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.name} <{self.email}> [{self.role}]'

    @property
    def is_creator(self) -> bool:
        return self.role == self.Role.CREATOR

    @property
    def is_regular_user(self) -> bool:
        return self.role == self.Role.USER
