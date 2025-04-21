from rest_framework import serializers
from .models import Farmer, ClimateHistory

class FarmerSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField(source='user.id')
    
    class Meta:
        model = Farmer
        fields = ['id', 'user_id', 'name', 'phone_number', 'location', 'farm_size', 'created_at', 'updated_at']
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

class ClimateDataSerializer(serializers.ModelSerializer):
    """Serializer for farmer climate data"""
    risk_level = serializers.SerializerMethodField()
    location_name = serializers.CharField(source='location')
    
    class Meta:
        model = Farmer
        fields = [
            'id', 'name', 'location_name', 'latitude', 'longitude', 
            'ndvi_value', 'rainfall_anomaly_mm', 'last_climate_update',
            'risk_level'
        ]
    
    def get_risk_level(self, obj):
        """
        Calculate a climate risk level based on NDVI and rainfall anomaly
        Returns: 'LOW', 'MEDIUM', or 'HIGH'
        """
        # Default to medium if no data
        if obj.ndvi_value is None or obj.rainfall_anomaly_mm is None:
            return 'UNKNOWN'
            
        # NDVI risk (lower values = higher risk)
        ndvi_risk = 0
        if obj.ndvi_value < 0.1:
            ndvi_risk = 3  # High risk
        elif obj.ndvi_value < 0.3:
            ndvi_risk = 2  # Medium risk
        else:
            ndvi_risk = 1  # Low risk
            
        # Rainfall anomaly risk (extreme values = higher risk)
        rainfall_risk = 0
        if abs(obj.rainfall_anomaly_mm) > 30:
            rainfall_risk = 3  # High risk
        elif abs(obj.rainfall_anomaly_mm) > 15:
            rainfall_risk = 2  # Medium risk
        else:
            rainfall_risk = 1  # Low risk
            
        # Combine risks
        total_risk = ndvi_risk + rainfall_risk
        
        if total_risk >= 5:
            return 'HIGH'
        elif total_risk >= 3:
            return 'MEDIUM'
        else:
            return 'LOW'

class ClimateHistorySerializer(serializers.ModelSerializer):
    """Serializer for farmer climate history records"""
    date = serializers.DateField(format="%Y-%m-%d")
    
    class Meta:
        model = ClimateHistory
        fields = ['id', 'date', 'ndvi_value', 'rainfall_anomaly_mm', 'notes']