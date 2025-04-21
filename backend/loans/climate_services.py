# backend/loans/climate_services.py

from django.utils import timezone
from datetime import timedelta, date
import logging
import asyncio
from functools import wraps
from django.db import transaction
from asgiref.sync import sync_to_async
from .models import Loan, PaymentSchedule
from .external.weather_api import WeatherService
from .external.satellite_api import SatelliteDataService
from .services import SMSService
from farmers.models import Farmer, ClimateHistory

logger = logging.getLogger(__name__)

def retry_async(retries=3, delay=1):
    """Decorator for retrying async functions with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    wait_time = delay * (2 ** (attempt - 1))
                    logger.warning(
                        f"Attempt {attempt}/{retries} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
            
            # If we get here, all retries failed
            logger.error(f"All {retries} attempts failed for {func.__name__}: {str(last_exception)}")
            raise last_exception
        return wrapper
    return decorator

class ClimateDataService:
    """Service to fetch, process and store climate-related data for farmers"""
    
    def __init__(self):
        self.weather_service = WeatherService()
        self.satellite_service = SatelliteDataService()
    
    async def update_farmer_climate_data(self, farmer_id=None, force=False):
        """
        Update climate data for a specific farmer or all farmers
        Fetches latest satellite and weather data and stores in farmer model
        
        Args:
            farmer_id: Optional ID of a specific farmer to update
            force: If True, update even if data is recent
        
        Returns:
            Dictionary with success status and count of updated farmers
        """
        @sync_to_async
        def get_farmers_to_update():
            query = Farmer.objects.filter(
                latitude__isnull=False, 
                longitude__isnull=False
            )
            
            if farmer_id:
                query = query.filter(id=farmer_id)
            elif not force:
                # Get farmers with coordinates that haven't been updated in the last 7 days
                time_threshold = timezone.now() - timedelta(days=7)
                query = query.filter(
                    last_climate_update__isnull=True
                ).union(
                    Farmer.objects.filter(
                        latitude__isnull=False,
                        longitude__isnull=False,
                        last_climate_update__lt=time_threshold
                    )
                )
            
            if force and farmer_id:
                # Clear the last_climate_update field to force an update
                Farmer.objects.filter(id=farmer_id).update(last_climate_update=None)
            elif force:
                # Clear the last_climate_update field for all farmers with coordinates
                Farmer.objects.filter(
                    latitude__isnull=False, 
                    longitude__isnull=False
                ).update(last_climate_update=None)
                
            return list(query)
            
        farmers = await get_farmers_to_update()
        updates_made = 0
        errors = 0
        
        logger.info(f"Starting climate data update for {len(farmers)} farmers")
        
        for farmer in farmers:
            try:
                # Skip farmers without coordinates
                if not farmer.latitude or not farmer.longitude:
                    logger.warning(f"Skipping farmer {farmer.id} ({farmer.name}): Missing coordinates")
                    continue
                    
                # Get NDVI value from satellite data
                try:
                    ndvi = await self._get_ndvi_with_retry(
                        latitude=farmer.latitude, 
                        longitude=farmer.longitude
                    )
                except Exception as e:
                    logger.error(f"Failed to get NDVI for farmer {farmer.id}: {str(e)}")
                    ndvi = None
                
                # Get rainfall anomaly
                try:
                    rainfall_anomaly = await self._get_rainfall_anomaly_with_retry(
                        lat=farmer.latitude, 
                        lon=farmer.longitude
                    )
                except Exception as e:
                    logger.error(f"Failed to get rainfall anomaly for farmer {farmer.id}: {str(e)}")
                    rainfall_anomaly = None
                
                # Skip update if both data points failed
                if ndvi is None and rainfall_anomaly is None:
                    logger.error(f"Skipping update for farmer {farmer.id}: Failed to retrieve any climate data")
                    errors += 1
                    continue
                
                # Update farmer record and store historical data
                @sync_to_async
                def update_farmer_and_history(f, ndvi, rainfall):
                    with transaction.atomic():
                        # Update current values
                        f.ndvi_value = ndvi if ndvi is not None else f.ndvi_value
                        f.rainfall_anomaly_mm = rainfall if rainfall is not None else f.rainfall_anomaly_mm
                        f.last_climate_update = timezone.now()
                        f.save(update_fields=['ndvi_value', 'rainfall_anomaly_mm', 'last_climate_update', 'updated_at'])
                        
                        # Store in history if we have valid data
                        if ndvi is not None or rainfall is not None:
                            today = date.today()
                            
                            # Check if we already have an entry for today
                            history, created = ClimateHistory.objects.get_or_create(
                                farmer=f,
                                date=today,
                                defaults={
                                    'ndvi_value': ndvi,
                                    'rainfall_anomaly_mm': rainfall
                                }
                            )
                            
                            # If not created, update the existing record
                            if not created:
                                if ndvi is not None:
                                    history.ndvi_value = ndvi
                                if rainfall is not None:
                                    history.rainfall_anomaly_mm = rainfall
                                history.save()
                                
                    return True
                
                success = await update_farmer_and_history(farmer, ndvi, rainfall_anomaly)
                if success:
                    updates_made += 1
                    logger.info(f"Updated climate data for farmer {farmer.id} ({farmer.name})")
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error updating climate data for farmer {farmer.id}: {str(e)}")
        
        logger.info(f"Completed climate data update: {updates_made} updated, {errors} errors")
        return {
            "success": updates_made > 0 or len(farmers) == 0,
            "updated_count": updates_made,
            "error_count": errors,
            "total_farmers": len(farmers)
        }

    @retry_async(retries=3, delay=2)
    async def _get_ndvi_with_retry(self, latitude, longitude):
        """Get NDVI value with retry logic"""
        return await self.satellite_service.get_ndvi(latitude=latitude, longitude=longitude)
    
    @retry_async(retries=3, delay=2)
    async def _get_rainfall_anomaly_with_retry(self, lat, lon):
        """Get rainfall anomaly with retry logic"""
        return await self.weather_service.get_rainfall_anomaly(lat=lat, lon=lon)
        
    async def get_farmer_climate_history(self, farmer_id, days=90):
        """
        Get historical climate data for a specific farmer
        Returns real data from database or generated mock data if no records exist
        
        Args:
            farmer_id: The ID of the farmer to get history for
            days: Number of days of history to retrieve (default 90)
            
        Returns:
            List of climate history records
        """
        @sync_to_async
        def get_farmer():
            try:
                return Farmer.objects.get(id=farmer_id)
            except Farmer.DoesNotExist:
                return None
        
        @sync_to_async
        def get_history_records(farmer, days_limit):
            end_date = date.today()
            start_date = end_date - timedelta(days=days_limit)
            
            return list(ClimateHistory.objects.filter(
                farmer=farmer,
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date'))
        
        # Get farmer
        farmer = await get_farmer()
        if not farmer:
            raise ValueError(f"Farmer with ID {farmer_id} not found")
            
        # Get history records
        history_records = await get_history_records(farmer, days)
        
        # Convert to list of dictionaries
        history = []
        for record in history_records:
            history.append({
                "date": record.date.strftime("%Y-%m-%d"),
                "ndvi": record.ndvi_value,
                "rainfall_anomaly": record.rainfall_anomaly_mm,
                "notes": record.notes
            })
            
        # If no records found or not enough, generate mock data
        if len(history) < days / 30:  # Less than one record per month on average
            logger.info(f"Not enough history for farmer {farmer_id}, generating mock data")
            history = await self._generate_mock_history(farmer, days)
            
        return history
        
    async def _generate_mock_history(self, farmer, days):
        """
        Generate mock climate history data for a farmer
        Creates realistic variations based on current values
        """
        from datetime import timedelta
        import random
        
        today = date.today()
        history = []
        
        # Generate daily data points
        for i in range(days):
            record_date = today - timedelta(days=i)
            
            # Use current values as base if available
            if farmer.ndvi_value is not None:
                # Calculate seasonal variation (higher in growing season)
                month = record_date.month
                season_factor = 0.1 * math.sin((month - 3) * math.pi / 6)  # Peak in July (month 7)
                
                # Add seasonal variation and small random fluctuation
                ndvi_base = max(-0.1, min(0.9, farmer.ndvi_value + season_factor))
                ndvi = max(-0.1, min(0.9, ndvi_base + random.uniform(-0.05, 0.05)))
            else:
                ndvi = random.uniform(0.2, 0.6)  # Reasonable default range
                
            if farmer.rainfall_anomaly_mm is not None:
                # Rainfall tends to be correlated over time with gradual changes
                if i > 0 and len(history) > 0:
                    # Use previous day with small drift
                    prev_rain = history[-1]["rainfall_anomaly"]
                    rainfall_anomaly = prev_rain + random.uniform(-5, 5)
                    # Occasionally add larger weather events
                    if random.random() < 0.05:  # 5% chance
                        rainfall_anomaly += random.choice([-20, -15, 15, 20])
                else:
                    # Start with current value
                    rainfall_anomaly = farmer.rainfall_anomaly_mm + random.uniform(-10, 10)
            else:
                rainfall_anomaly = random.uniform(-30, 30)
                
            # Add to history
            history.append({
                "date": record_date.strftime("%Y-%m-%d"),
                "ndvi": round(ndvi, 2),
                "rainfall_anomaly": round(rainfall_anomaly, 1)
            })
            
        # Sort by date (oldest first)
        history.sort(key=lambda x: x["date"])
        return history

class ClimateAdaptiveLoanService:
    def __init__(self):
        self.weather_service = WeatherService()
        self.satellite_service = SatelliteDataService()
        self.climate_data_service = ClimateDataService()
        self.sms_service = SMSService()
    
    async def check_for_adverse_conditions(self):
        """Check for adverse weather conditions and adjust loan schedules"""
        # Get all active loans
        @sync_to_async
        def get_active_loans():
            return list(Loan.objects.filter(
                status='APPROVED',
                disbursement_status='COMPLETED'
            ).select_related('farmer'))
        
        loans = await get_active_loans()
        adjustments_made = 0
        logger.info(f"Checking {len(loans)} active loans for adverse climate conditions")
        
        for loan in loans:
            try:
                # Ensure we have updated climate data
                await self.climate_data_service.update_farmer_climate_data(loan.farmer.id)
                
                # Get latest weather conditions
                if loan.farmer.has_geo_coordinates:
                    conditions = await self.weather_service.get_conditions(
                        loan.farmer.location,
                        lat=loan.farmer.latitude,
                        lon=loan.farmer.longitude
                    )
                else:
                    conditions = await self.weather_service.get_conditions(loan.farmer.location)
                
                high_drought = conditions.get('drought_index', 0) > 0.7
                high_flood = conditions.get('flood_index', 0) > 0.7
                extreme_rainfall_anomaly = loan.farmer.rainfall_anomaly_mm and abs(loan.farmer.rainfall_anomaly_mm) > 30
                
                if high_drought or high_flood or extreme_rainfall_anomaly:
                    # Get upcoming payment schedules
                    @sync_to_async
                    def get_upcoming_payments():
                        return list(PaymentSchedule.objects.filter(
                            loan=loan,
                            status='PENDING',
                            due_date__lte=timezone.now() + timedelta(days=30)
                        ))
                    
                    schedules = await get_upcoming_payments()
                    
                    if not schedules:
                        continue
                    
                    # Extend payment deadlines
                    @sync_to_async
                    def extend_payments():
                        with transaction.atomic():
                            for schedule in schedules:
                                schedule.due_date = schedule.due_date + timedelta(days=30)
                                schedule.save()
                        return True
                    
                    adjustment_success = await extend_payments()
                    
                    if adjustment_success:
                        adjustments_made += 1
                        
                        # Determine the reason for adjustment
                        reason = "adverse weather conditions"
                        if high_drought:
                            reason = "drought conditions"
                        elif high_flood:
                            reason = "flood risk"
                        elif extreme_rainfall_anomaly:
                            if loan.farmer.rainfall_anomaly_mm > 0:
                                reason = "excessive rainfall"
                            else:
                                reason = "rainfall deficit"
                    
                        # Notify farmer
                        try:
                            await self.sms_service.send_sms(
                                loan.farmer.phone_number,
                                f"Due to {reason} in your area, your upcoming loan "
                                f"payment has been automatically extended by 30 days. No action is required."
                            )
                            logger.info(f"SMS notification sent to farmer {loan.farmer.id} about payment extension")
                        except Exception as e:
                            logger.error(f"Failed to send SMS to farmer {loan.farmer.id}: {str(e)}")
                        
                        # Log the adjustment
                        logger.info(f"Extended payment deadlines for loan {loan.id} due to {reason}")
            except Exception as e:
                logger.error(f"Error processing loan {loan.id} for adverse conditions: {str(e)}")
        
        return {"success": True, "adjustments_made": adjustments_made}