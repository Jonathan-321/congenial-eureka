# backend/farmers/serializers.py

from rest_framework import serializers
from .models import Farmer

class FarmerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farmer
        fields = ['id', 'name', 'phone_number', 'location', 'farm_size', 'created_at']

# Add this class
class SimpleFarmerSerializer(serializers.ModelSerializer):
    """A simplified serializer for Farmer model with fewer fields"""
    class Meta:
        model = Farmer
        fields = ['id', 'name', 'location', 'phone_number']