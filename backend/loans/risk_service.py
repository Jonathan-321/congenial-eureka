import httpx
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async
from decimal import Decimal
import numpy as np
from datetime import timedelta, datetime
from .models import Loan, CropCycle

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
    """Enhanced credit scoring with multiple data points"""
    
    def __init__(self):
        self.weather_service = WeatherService()
    
    async def calculate_score(self, farmer):
        """Calculate credit score using multiple factors"""
        # Start with traditional credit score
        traditional_score = await sync_to_async(self._traditional_score)(farmer)
        
        try:
            # Get weather risk for farmer's location
            weather_risk = await self.weather_service.assess_risk(farmer.location)
            weather_score = 100 - weather_risk  # Convert risk to score (higher is better)
            
            # Get payment history score
            payment_score = await sync_to_async(self._payment_history_score)(farmer)
            
            # Get crop diversification score
            crop_score = await sync_to_async(self._crop_diversification_score)(farmer)
            
            # Get farmer experience score
            experience_score = await sync_to_async(self._farmer_experience_score)(farmer)
            
            # Calculate weighted score (adjust weights based on importance)
            final_score = (
                traditional_score * 0.3 + 
                payment_score * 0.3 + 
                crop_score * 0.2 + 
                weather_score * 0.1 + 
                experience_score * 0.1
            )
            
            return min(max(final_score, 0), 100)  # Ensure score is between 0-100
            
        except Exception as e:
            print(f"Error in enhanced credit scoring: {e}")
            # Fall back to traditional scoring if enhanced scoring fails
            return traditional_score
    
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