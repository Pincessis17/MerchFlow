from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.ROLE_OWNER)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_OWNER = "owner"
    ROLE_MANAGER = "manager"
    ROLE_STAFF = "staff"
    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_MANAGER, "Manager"),
        (ROLE_STAFF, "Staff"),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STAFF, db_index=True)
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="users")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["business"]

    objects = UserManager()

    def __str__(self):
        return self.email
