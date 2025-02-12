from django.contrib import admin
from .models import Farmer

@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'location', 'farm_size', 'created_at')
    search_fields = ('name', 'phone_number')