"""
Celery tasks for handling farmer climate data updates
"""

import asyncio
import logging
from celery import shared_task
from .models import Farmer
from backend.loans.climate_services import ClimateDataService

logger = logging.getLogger(__name__)

@shared_task(name="farmers.update_farmer_climate_data")
def update_farmer_climate_data(farmer_id=None, force=False):
    """
    Celery task to update climate data for a farmer or all farmers
    
    Args:
        farmer_id: Optional ID of a specific farmer to update
        force: If True, update even if data is recent
    
    Returns:
        Dict with results of the update operation
    """
    logger.info(f"Starting climate data update task for farmer_id={farmer_id}, force={force}")
    
    async def run_update():
        service = ClimateDataService()
        return await service.update_farmer_climate_data(farmer_id=farmer_id, force=force)
    
    try:
        # Run the async update operation
        result = asyncio.run(run_update())
        
        logger.info(
            f"Completed climate data update: "
            f"{result['updated_count']} updated, {result['error_count']} errors"
        )
        return result
    except Exception as e:
        logger.error(f"Error in climate data update task: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "updated_count": 0
        }

@shared_task(name="farmers.update_all_farmer_climate_data")
def update_all_farmer_climate_data():
    """
    Celery task to update climate data for all farmers
    Schedules updates for farmers in batches to avoid overloading the system
    
    Returns:
        Dict with summary of the batched operations
    """
    logger.info("Starting scheduled climate data update for all farmers")
    
    # Get all farmers with coordinates
    farmers_with_coords = Farmer.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    total_farmers = farmers_with_coords.count()
    
    if total_farmers == 0:
        logger.warning("No farmers with coordinates found for climate data update")
        return {
            "success": True,
            "updated_count": 0,
            "total_farmers": 0,
            "error_count": 0
        }
    
    # Create individual tasks for each farmer (could be optimized with chunks/batches)
    for farmer in farmers_with_coords:
        update_farmer_climate_data.delay(farmer_id=farmer.id)
    
    logger.info(f"Scheduled climate data updates for {total_farmers} farmers")
    
    return {
        "success": True,
        "scheduled_count": total_farmers
    } 