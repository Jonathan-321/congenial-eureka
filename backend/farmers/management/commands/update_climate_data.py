# backend/farmers/management/commands/update_climate_data.py
import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from backend.farmers.models import Farmer
from backend.loans.climate_services import ClimateDataService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates climate data (NDVI and rainfall anomaly) for farmers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--farmer_id', 
            type=int,
            help='ID of a specific farmer to update'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if data is recent'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed progress information'
        )

    async def handle_async(self, *args, **options):
        farmer_id = options.get('farmer_id')
        force_update = options.get('force', False)
        verbose = options.get('verbose', False)
        
        if verbose:
            self.stdout.write(self.style.HTTP_INFO(
                f"Starting climate data update{'for all farmers' if not farmer_id else f' for farmer {farmer_id}'}"
                f"{' (forced)' if force_update else ''}"
            ))
        
        # Check if specific farmer exists
        if farmer_id:
            try:
                farmer = await self.get_farmer(farmer_id)
                if not farmer:
                    raise CommandError(f"Farmer with ID {farmer_id} does not exist")
                
                if not farmer.has_geo_coordinates:
                    self.stdout.write(self.style.WARNING(
                        f"Farmer {farmer_id} does not have coordinates. "
                        "Update coordinates before updating climate data."
                    ))
                    return
            except Exception as e:
                raise CommandError(f"Error checking farmer: {str(e)}")
        
        # Initialize the service
        climate_service = ClimateDataService()
        
        try:
            # Call the service to update farmer data
            result = await climate_service.update_farmer_climate_data(
                farmer_id=farmer_id,
                force=force_update
            )
            
            # Show results
            if result['success']:
                if result['updated_count'] > 0:
                    self.stdout.write(self.style.SUCCESS(
                        f"Successfully updated climate data for {result['updated_count']} farmers "
                        f"({result['error_count']} errors out of {result['total_farmers']} total)"
                    ))
                else:
                    if farmer_id:
                        self.stdout.write(self.style.WARNING(
                            f"No update needed for farmer {farmer_id}. "
                            "Use --force to update regardless of last update time."
                        ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            "No farmers needed updating. "
                            "Use --force to update regardless of last update time."
                        ))
            else:
                self.stdout.write(self.style.ERROR(
                    f"Failed to update climate data. "
                    f"{result['updated_count']} updated, {result['error_count']} errors."
                ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error updating climate data: {str(e)}"))
            raise CommandError(str(e))

    async def get_farmer(self, farmer_id):
        """Get a farmer by ID asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: Farmer.objects.filter(id=farmer_id).first()
        )

    def handle(self, *args, **options):
        """Entry point for the command"""
        asyncio.run(self.handle_async(*args, **options)) 