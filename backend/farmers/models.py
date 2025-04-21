from django.db import models
from django.conf import settings

class Farmer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='farmer_profile')
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    location = models.CharField(max_length=255)
    # Coordinates for satellite and weather data
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    farm_size = models.DecimalField(max_digits=10, decimal_places=2)
    # Climate data
    ndvi_value = models.FloatField(null=True, blank=True, help_text="Latest Normalized Difference Vegetation Index")
    rainfall_anomaly_mm = models.FloatField(null=True, blank=True, help_text="Rainfall deviation from historical average (mm)")
    last_climate_update = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
        
    @property
    def has_geo_coordinates(self):
        """Check if farmer has valid coordinates for satellite processing"""
        return self.latitude is not None and self.longitude is not None

class ClimateHistory(models.Model):
    """
    Model to store historical climate data for farmers
    Used to track climate changes over time and provide trend analysis
    """
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='climate_history')
    date = models.DateField()
    ndvi_value = models.FloatField(null=True, blank=True, help_text="NDVI value for this date")
    rainfall_anomaly_mm = models.FloatField(null=True, blank=True, help_text="Rainfall anomaly in mm for this date")
    notes = models.TextField(blank=True, null=True, help_text="Optional notes about special weather events")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['farmer', 'date']
        verbose_name_plural = "Climate histories"
        
    def __str__(self):
        return f"{self.farmer.name} - {self.date}"