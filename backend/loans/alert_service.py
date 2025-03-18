# backend/loans/alert_service.py

from django.utils import timezone
from asgiref.sync import sync_to_async
from .external.weather_api import WeatherService
from .external.market_api import MarketDataService
from .services import SMSService
from .models import Farmer, CropCycle, Loan
from .harvest_service import HarvestBasedLoanService
import logging

logger = logging.getLogger(__name__)

class FarmerAlertService:
    """Service for sending targeted alerts to farmers"""
    
    def __init__(self):
        self.weather_service = WeatherService()
        self.market_service = MarketDataService()
        self.sms_service = SMSService()
        self.harvest_service = HarvestBasedLoanService()
    
    @sync_to_async
    def get_active_loans_with_schedule(self):
        """Get all active loans with harvest-based schedules"""
        active_statuses = ['APPROVED', 'DISBURSED', 'ACTIVE']
        return list(Loan.objects.filter(
            status__in=active_statuses,
            harvest_schedule__isnull=False
        ).select_related('farmer', 'harvest_schedule__crop_cycle'))
    
    async def check_and_send_weather_alerts(self):
        """Check weather conditions and send alerts to relevant farmers"""
        loans = await self.get_active_loans_with_schedule()
        
        for loan in loans:
            farmer = loan.farmer
            crop_cycle = loan.harvest_schedule.crop_cycle
            
            # Skip if no location data
            if not farmer.location:
                continue
            
            # Get drought risk for farmer's location
            drought_risk = await self.weather_service.get_drought_risk(farmer.location)
            
            if not drought_risk:
                continue
            
            # For high risk, send alert and adjust payment schedule
            if drought_risk['risk_level'] == 'HIGH':
                message = (
                    f"WEATHER ALERT: {drought_risk['description']}. "
                    f"This may affect your {crop_cycle.get_crop_type_display()} crop. "
                    f"We've extended your loan payment deadline by 14 days to help you adjust."
                )
                
                # Adjust payment schedule
                success, _ = await self.harvest_service.adjust_schedule_for_weather(
                    loan.harvest_schedule, 
                    delay_days=14
                )
                
                if success:
                    await self.sms_service.send_sms(farmer.phone_number, message)
                    logger.info(f"Weather alert sent to farmer {farmer.id} with schedule adjustment")
            
            # For medium risk, just send an alert
            elif drought_risk['risk_level'] == 'MEDIUM':
                message = (
                    f"WEATHER ADVISORY: {drought_risk['description']}. "
                    f"Consider additional irrigation for your {crop_cycle.get_crop_type_display()} crop "
                    f"if possible. Contact your local extension officer for advice."
                )
                
                await self.sms_service.send_sms(farmer.phone_number, message)
                logger.info(f"Weather advisory sent to farmer {farmer.id}")
    
    async def send_market_price_alerts(self):
        """Send market price alerts to farmers with relevant crops"""
        @sync_to_async
        def get_active_crop_cycles():
            today = timezone.now().date()
            return list(CropCycle.objects.filter(
                expected_harvest_date__gte=today,
                expected_harvest_date__lte=today + timezone.timedelta(days=30)
            ).select_related('farmer'))
        
        crop_cycles = await get_active_crop_cycles()
        
        for cycle in crop_cycles:
            crop_type = cycle.crop_type
            farmer = cycle.farmer
            
            # Get market data for this crop
            market_data = await self.market_service.get_crop_prices(crop_type, farmer.location)
            
            if not market_data:
                continue
            
            # If prices are rising, send alert
            if market_data['trend'] == 'RISING':
                message = (
                    f"MARKET ALERT: {crop_type} prices are rising! "
                    f"Current average price: {market_data['average_price']} RWF per {market_data['unit']}. "
                    f"Consider timing your harvest carefully for maximum returns."
                )
                
                await self.sms_service.send_sms(farmer.phone_number, message)
                logger.info(f"Market price alert sent to farmer {farmer.id} for {crop_type}")
            
            # If within 7 days of expected harvest, send best selling time info
            days_to_harvest = (cycle.expected_harvest_date - timezone.now().date()).days
            if days_to_harvest <= 7:
                selling_advice = await self.market_service.get_best_selling_time(crop_type)
                
                if selling_advice:
                    message = (
                        f"HARVEST PLANNING: For your {crop_type} crop, "
                        f"the best selling period is typically {selling_advice['best_selling_time']} "
                        f"({selling_advice['reason']}). "
                        f"Potential price increase: {selling_advice['price_increase_potential']}."
                    )
                    
                    await self.sms_service.send_sms(farmer.phone_number, message)
                    logger.info(f"Harvest timing advice sent to farmer {farmer.id} for {crop_type}")