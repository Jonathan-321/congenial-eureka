from django.contrib import admin
from .models import Farmer, ClimateHistory

@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'phone_number', 'farm_size', 'has_climate_data', 'created_at')
    list_filter = ('location', 'created_at')
    search_fields = ('name', 'phone_number', 'location')
    readonly_fields = ('created_at', 'updated_at')
    
    def has_climate_data(self, obj):
        """Check if farmer has climate data"""
        return obj.ndvi_value is not None and obj.rainfall_anomaly_mm is not None
    
    has_climate_data.boolean = True
    has_climate_data.short_description = "Has Climate Data"

@admin.register(ClimateHistory)
class ClimateHistoryAdmin(admin.ModelAdmin):
    list_display = ('farmer', 'date', 'ndvi_value', 'rainfall_anomaly_mm', 'created_at')
    list_filter = ('date', 'farmer__location')
    search_fields = ('farmer__name', 'farmer__location', 'notes')
    date_hierarchy = 'date'
    
    fieldsets = (
        (None, {
            'fields': ('farmer', 'date')
        }),
        ('Climate Data', {
            'fields': ('ndvi_value', 'rainfall_anomaly_mm', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_at',)