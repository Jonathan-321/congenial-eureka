from django.db import models
from django.conf import settings

class Farmer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='farmer_profile')
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    location = models.CharField(max_length=255)
    farm_size = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name