import asyncio
import logging
import random
import math
from datetime import timedelta, date
from django.core.management.base import BaseCommand
from django.db import transaction
from farmers.models import Farmer, ClimateHistory

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate sample climate history data for farmers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--farmer_id', 
            type=int,
            help='ID of a specific farmer to generate history for'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days of history to generate (default: 90)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing history before generating new data'
        )

    def handle(self, *args, **options):
        farmer_id = options.get('farmer_id')
        days = options.get('days')
        clear = options.get('clear')
        
        # Get farmers with coordinates
        if farmer_id:
            try:
                farmers = [Farmer.objects.get(id=farmer_id)]
                if not farmers[0].has_geo_coordinates:
                    self.stdout.write(self.style.WARNING(
                        f"Farmer {farmer_id} doesn't have coordinates. "
                        "Results may not be realistic."
                    ))
            except Farmer.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Farmer with ID {farmer_id} not found"))
                return
        else:
            farmers = Farmer.objects.filter(
                latitude__isnull=False,
                longitude__isnull=False
            )
            
            if not farmers.exists():
                self.stdout.write(self.style.WARNING("No farmers with coordinates found"))
                return
        
        self.stdout.write(self.style.HTTP_INFO(
            f"Generating {days} days of climate history for {len(farmers)} farmers"
        ))
        
        total_records = 0
        
        for farmer in farmers:
            # Clear existing history if requested
            if clear:
                deleted, _ = ClimateHistory.objects.filter(farmer=farmer).delete()
                self.stdout.write(
                    f"Cleared {deleted} existing history records for {farmer.name}"
                )
            
            # Generate history
            records = self.generate_history(farmer, days)
            total_records += len(records)
            
            self.stdout.write(
                f"Generated {len(records)} history records for {farmer.name}"
            )
        
        self.stdout.write(self.style.SUCCESS(
            f"Successfully generated {total_records} climate history records"
        ))
    
    def generate_history(self, farmer, days):
        """Generate realistic climate history for a farmer"""
        today = date.today()
        records = []
        
        with transaction.atomic():
            for i in range(days):
                record_date = today - timedelta(days=i)
                
                # Check if record already exists for this date
                if ClimateHistory.objects.filter(farmer=farmer, date=record_date).exists():
                    continue
                
                # Generate NDVI value with seasonal variations
                if farmer.ndvi_value is not None:
                    # Calculate seasonal variation (higher in growing season)
                    month = record_date.month
                    season_factor = 0.1 * math.sin((month - 3) * math.pi / 6)  # Peak in July
                    
                    # Add seasonal variation and small random fluctuation
                    ndvi_base = max(-0.1, min(0.9, farmer.ndvi_value + season_factor))
                    ndvi = max(-0.1, min(0.9, ndvi_base + random.uniform(-0.05, 0.05)))
                else:
                    ndvi = random.uniform(0.2, 0.6)  # Reasonable default range
                    
                # Generate rainfall anomaly with temporal correlation
                if farmer.rainfall_anomaly_mm is not None:
                    # Start with current value and add drift
                    base_anomaly = farmer.rainfall_anomaly_mm
                    
                    # Add time-dependent drift (values further in past will differ more)
                    drift_factor = min(1.0, i / 30) * 30  # Max 30mm drift at 30+ days
                    
                    # Random drift within range
                    drift = random.uniform(-drift_factor, drift_factor)
                    
                    rainfall_anomaly = base_anomaly + drift
                    
                    # Occasionally add weather events
                    if random.random() < 0.05:  # 5% chance
                        rainfall_anomaly += random.choice([-25, -20, 20, 25])
                else:
                    rainfall_anomaly = random.uniform(-30, 30)
                
                # Create record
                history = ClimateHistory.objects.create(
                    farmer=farmer,
                    date=record_date,
                    ndvi_value=round(ndvi, 2),
                    rainfall_anomaly_mm=round(rainfall_anomaly, 1)
                )
                
                records.append(history)
                
        return records 