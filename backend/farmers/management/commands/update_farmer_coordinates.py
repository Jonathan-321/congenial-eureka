# backend/farmers/management/commands/update_farmer_coordinates.py
import asyncio
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from backend.farmers.models import Farmer
from backend.loans.external.weather_api import WeatherService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update farmer coordinates by geocoding their location names'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Update all farmers, including those with existing coordinates',
        )
        parser.add_argument(
            '--farmer_id',
            type=int,
            help='Update specific farmer by ID',
        )
    
    def handle(self, *args, **options):
        asyncio.run(self._handle_async(*args, **options))
        
    async def _handle_async(self, *args, **options):
        weather_service = WeatherService()
        update_all = options['all']
        farmer_id = options.get('farmer_id')
        
        # Get farmers to update
        if farmer_id:
            farmers = Farmer.objects.filter(id=farmer_id)
            self.stdout.write(f"Updating coordinates for farmer ID {farmer_id}")
        elif update_all:
            farmers = Farmer.objects.all()
            self.stdout.write(f"Updating coordinates for all {farmers.count()} farmers")
        else:
            farmers = Farmer.objects.filter(latitude__isnull=True) | Farmer.objects.filter(longitude__isnull=True)
            self.stdout.write(f"Updating coordinates for {farmers.count()} farmers without coordinates")
            
        if not farmers.exists():
            self.stdout.write(self.style.WARNING("No farmers to update"))
            return
            
        updates = 0
        for farmer in farmers:
            try:
                self.stdout.write(f"Geocoding location '{farmer.location}' for farmer {farmer.id}")
                coords = await weather_service.get_coordinates(farmer.location)
                
                if coords:
                    farmer.latitude = coords['lat']
                    farmer.longitude = coords['lon']
                    farmer.save(update_fields=['latitude', 'longitude', 'updated_at'])
                    updates += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"Updated coordinates for {farmer.name}: ({coords['lat']}, {coords['lon']})"
                    ))
                else:
                    self.stdout.write(self.style.ERROR(f"Could not geocode location '{farmer.location}'"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error updating farmer {farmer.id}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"Updated coordinates for {updates} farmers")) 