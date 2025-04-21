import httpx
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async
from decimal import Decimal
import numpy as np
from datetime import timedelta, datetime
import logging
from django.db.models import F
from .models import Loan, CropCycle, PaymentSchedule
from .external.weather_api import WeatherService
from .external.satellite_api import SatelliteDataService
from .climate_services import ClimateDataService

logger = logging.getLogger(__name__)

class WeatherService:
    """Service for retrieving and analyzing weather data"""
    
    async def get_weather_forecast(self, location):
        """Get weather forecast for a location"""
        try:
            # Use OpenWeatherMap API
            api_key = settings.OPENWEATHER_API_KEY
            url = f"https://api.openweathermap.org/data/2.5/forecast?q={location}&appid={api_key}&units=metric"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                data = response.json()
                
                return True, data
        except Exception as e:
            return False, str(e)
    
    async def assess_risk(self, location):
        """Assess weather risk for a location (0-100 scale, higher is more risky)"""
        success, data = await self.get_weather_forecast(location)
        
        if not success:
            # Default to medium risk if we can't get data
            return 50
        
        try:
            # Get 5-day forecast
            forecast_list = data.get('list', [])
            
            # Check for extreme weather conditions
            extreme_count = 0
            rain_total = 0
            
            for forecast in forecast_list:
                temp = forecast.get('main', {}).get('temp', 20)
                
                # Check for extreme temperatures
                if temp > 35 or temp < 5:
                    extreme_count += 1
                
                # Check for rain
                rain = forecast.get('rain', {}).get('3h', 0)
                rain_total += rain
                
                # Check for extreme weather events
                weather_id = forecast.get('weather', [{}])[0].get('id', 800)
                
                # Weather codes: https://openweathermap.org/weather-conditions
                # Severe weather: thunderstorms, heavy rain, etc.
                if weather_id < 600 and weather_id >= 200:
                    extreme_count += 1
            
            # Calculate risk score (0-100)
            # Higher number = higher risk of crop failure due to weather
            risk_score = min(100, (extreme_count * 10) + (rain_total > 50) * 30)
            
            return risk_score
        except Exception as e:
            print(f"Error assessing weather risk: {e}")
            return 50  # Default to medium risk

class EnhancedCreditScoring:
    """Enhanced credit scoring with multiple data points including satellite and climate data"""
    
    def __init__(self):
        self.weather_service = WeatherService()
        self.satellite_service = SatelliteDataService()
        self.climate_data_service = ClimateDataService()
    
    async def calculate_score(self, farmer):
        """Calculate credit score using multiple factors"""
        # Start with traditional credit score
        traditional_score = await sync_to_async(self._traditional_score)(farmer)
        
        try:
            # Ensure we have up-to-date climate data for this farmer
            await self.climate_data_service.update_farmer_climate_data(farmer.id)
            
            # Get weather risk for farmer's location
            if farmer.has_geo_coordinates:
                weather_risk = await self.weather_service.assess_risk(
                    farmer.location, 
                    lat=farmer.latitude, 
                    lon=farmer.longitude
                )
                
                # Convert weather risk to score (higher risk = lower score)
                weather_score = max(0, 100 - weather_risk)
            else:
                # Fallback if no coordinates
                weather_risk = await self.weather_service.assess_risk(farmer.location)
                weather_score = max(0, 100 - weather_risk)
            
            # Get farm health score based on satellite data
            if farmer.has_geo_coordinates:
                farm_health_score = await self.satellite_service.analyze_farm(
                    farmer.location, 
                    farmer.farm_size, 
                    latitude=farmer.latitude, 
                    longitude=farmer.longitude
                )
            else:
                farm_health_score = await self.satellite_service.analyze_farm(
                    farmer.location, 
                    farmer.farm_size
                )
            
            # Get payment history score
            payment_score = await sync_to_async(self._payment_history_score)(farmer)
            
            # Get crop diversification score
            crop_score = await sync_to_async(self._crop_diversification_score)(farmer)
            
            # Get farmer experience score
            experience_score = await sync_to_async(self._farmer_experience_score)(farmer)
            
            # Calculate climate impact score using NDVI and rainfall anomaly
            climate_impact_score = await self._calculate_climate_impact_score(farmer)
            
            # Calculate weighted score (adjust weights based on importance)
            # New weighting with climate data having more influence
            final_score = (
                traditional_score * 0.20 +  # Reduced from 0.3
                payment_score * 0.25 +      # Reduced from 0.3
                crop_score * 0.15 +         # Reduced from 0.2
                weather_score * 0.10 +      # Same
                experience_score * 0.10 +   # Same
                farm_health_score * 0.10 +  # New factor
                climate_impact_score * 0.10 # New factor
            )
            
            # Log the scoring components for analysis
            logger.info(f"Credit score components for farmer {farmer.id}: "
                       f"traditional={traditional_score:.1f}, payment={payment_score:.1f}, "
                       f"crop={crop_score:.1f}, weather={weather_score:.1f}, "
                       f"experience={experience_score:.1f}, farm_health={farm_health_score:.1f}, "
                       f"climate_impact={climate_impact_score:.1f}, final={final_score:.1f}")
            
            return min(max(final_score, 0), 100)  # Ensure score is between 0-100
            
        except Exception as e:
            logger.error(f"Error in enhanced credit scoring: {str(e)}")
            # Fall back to traditional scoring if enhanced scoring fails
            return traditional_score
    
    async def _calculate_climate_impact_score(self, farmer):
        """Calculate score based on NDVI and rainfall anomaly data"""
        # Default score if no data
        if farmer.ndvi_value is None and farmer.rainfall_anomaly_mm is None:
            return 50
            
        # Calculate NDVI component (0-50 points)
        # NDVI ranges from -0.1 (poor vegetation) to 0.9 (dense vegetation)
        ndvi_score = 0
        if farmer.ndvi_value is not None:
            # Convert NDVI to 0-50 score (higher NDVI = better score)
            ndvi_score = max(0, min(50, (farmer.ndvi_value + 0.1) / 1.0 * 50))
        else:
            ndvi_score = 25  # Neutral score if no data
            
        # Calculate rainfall anomaly component (0-50 points)
        # Ideal is near 0 (normal rainfall), negative (drought) or positive (excess) are worse
        rainfall_score = 0
        if farmer.rainfall_anomaly_mm is not None:
            # Penalize abnormal rainfall (too much or too little)
            # Optimal range: -10 to +10 mm from normal
            anomaly_abs = abs(farmer.rainfall_anomaly_mm)
            if anomaly_abs <= 10:
                rainfall_score = 50  # Optimal rainfall
            else:
                # Score decreases as anomaly increases
                rainfall_score = max(0, 50 - (anomaly_abs - 10) / 2)
        else:
            rainfall_score = 25  # Neutral score if no data
            
        # Combine scores
        return (ndvi_score + rainfall_score) / 2
    
    def _traditional_score(self, farmer):
        """Calculate traditional credit score"""
        # This is just a simple implementation for demo purposes
        # In a real system, you'd have more sophisticated scoring logic
        
        # Default base score
        score = 50
        
        # Add points for farm size
        if farmer.farm_size >= 5:
            score += 15
        elif farmer.farm_size >= 2:
            score += 10
        elif farmer.farm_size >= 1:
            score += 5
        
        # Add points for previous loans
        previous_loans = Loan.objects.filter(farmer=farmer).count()
        score += min(previous_loans * 5, 20)  # Max 20 points for previous loans
        
        return min(score, 100)  # Cap at 100
    
    def _payment_history_score(self, farmer):
        """Calculate score based on payment history"""
        # Default score if no history
        if not Loan.objects.filter(farmer=farmer).exists():
            return 50
        
        # Get all completed payments
        payments = PaymentSchedule.objects.filter(
            loan__farmer=farmer,
            status__in=['PAID', 'PARTIAL']
        )
        
        if not payments.exists():
            return 50
        
        # Count on-time vs late payments
        total_payments = payments.count()
        late_payments = payments.filter(payment_date__gt=F('due_date')).count()
        
        if total_payments == 0:
            return 50
        
        on_time_rate = (total_payments - late_payments) / total_payments
        
        # Convert to score (0-100)
        return on_time_rate * 100
    
    def _crop_diversification_score(self, farmer):
        """Calculate score based on crop diversification"""
        # Get unique crops
        unique_crops = CropCycle.objects.filter(farmer=farmer).values('crop_type').distinct().count()
        
        # Score based on crop diversity
        if unique_crops >= 3:
            return 100  # Excellent diversification
        elif unique_crops == 2:
            return 75  # Good diversification
        elif unique_crops == 1:
            return 50  # Single crop
        else:
            return 25  # No crop data
    
    def _farmer_experience_score(self, farmer):
        """Calculate score based on farmer experience"""
        # Look at earliest crop cycle or loan
        earliest_crop = CropCycle.objects.filter(farmer=farmer).order_by('planting_date').first()
        earliest_loan = Loan.objects.filter(farmer=farmer).order_by('created_at').first()
        
        earliest_date = None
        if earliest_crop:
            earliest_date = earliest_crop.planting_date
        
        if earliest_loan:
            loan_date = earliest_loan.created_at
            if not earliest_date or loan_date < earliest_date:
                earliest_date = loan_date
        
        if not earliest_date:
            return 50  # No history data
        
        # Calculate years of experience
        years = (timezone.now().date() - earliest_date.date()).days / 365
        
        # Score based on years
        if years >= 5:
            return 100  # Experienced farmer
        elif years >= 3:
            return 80
        elif years >= 1:
            return 60
        else:
            return 40  # New farmer