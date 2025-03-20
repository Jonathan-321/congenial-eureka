from rest_framework import serializers
from .models import Farmer

class FarmerSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField(source='user.id')
    
    class Meta:
        model = Farmer
        fields = ['id', 'user_id', 'name', 'phone_number', 'location', 'farm_size', 'created_at']
        read_only_fields = ['created_at', 'user_id']

    def validate_phone_number(self, value):
        if not value.startswith('+250'):
            raise serializers.ValidationError("Phone number must start with +250")
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class SimpleFarmerSerializer(serializers.ModelSerializer):
    """A simplified serializer for Farmer model with fewer fields"""
    class Meta:
        model = Farmer
        fields = ['id', 'name', 'location', 'phone_number']