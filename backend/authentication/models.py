from django.contrib.auth.models import AbstractUser
from django.db import models
from .choices import USER_ROLES

class User(AbstractUser):
    role = models.CharField(
        max_length=10,
        choices=USER_ROLES,
        default='STAFF'
    )
    phone_number = models.CharField(max_length=15, unique=True)

    class Meta:
        db_table = 'authentication_user'