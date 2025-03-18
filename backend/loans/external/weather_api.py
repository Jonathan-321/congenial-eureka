# backend/loans/external/weather_api.py
import aiohttp
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Mock implementation of weather service
    In production, this would integrate with a real weather API
    """
    def __init__(self):
        self.api_key = settings.WEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"
    
    
    async def get_conditions(self, location):
        """
        Get current weather conditions for a location
        Returns a dictionary with weather metrics
        """
        import random
        
        # Mock data based on region
        region_conditions = {
            'Kigali': {'drought_index': 0.2, 'flood_index': 0.3},
            'Musanze': {'drought_index': 0.1, 'flood_index': 0.5},
            'Nyagatare': {'drought_index': 0.6, 'flood_index': 0.1},
            'Kayonza': {'drought_index': 0.4, 'flood_index': 0.2},
            'Huye': {'drought_index': 0.3, 'flood_index': 0.4}
        }
        
        # Get base conditions for the location or use defaults
        conditions = region_conditions.get(location, {'drought_index': 0.3, 'flood_index': 0.3})
        
        # Add some randomness to simulate changing weather patterns
        variation = random.uniform(-0.1, 0.1)
        conditions['drought_index'] = max(0, min(1, conditions['drought_index'] + variation))
        conditions['flood_index'] = max(0, min(1, conditions['flood_index'] + variation))
        
        return conditions
    
    async def assess_risk(self, location):
        """
        Assess climate risk for a location
        Returns a score between 0-100 (higher = lower risk)
        """
        conditions = await self.get_conditions(location)
        
        # Calculate risk score (higher values = better conditions = lower risk)
        # 100 = perfect conditions, 0 = severe risk
        drought_risk = (1 - conditions['drought_index']) * 50
        flood_risk = (1 - conditions['flood_index']) * 50
        
        # Take the minimum of the two risks to be conservative
        return min(drought_risk + flood_risk, 100)


    async def get_weather_forecast(self, location, days=7):
        """Get weather forecast for a location"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'q': location,
                    'appid': self.api_key,
                    'units': 'metric',
                    'cnt': days
                }
                
                async with session.get(f"{self.base_url}/forecast/daily", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._process_forecast(data)
                    else:
                        logger.error(f"Weather API error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching weather data: {str(e)}")
            return None

    def _process_forecast(self, data):
        """Process the raw forecast data into a more usable format"""
        forecast = []
        
        if 'list' in data:
            for day in data['list']:
                forecast.append({
                    'date': day['dt'],
                    'temp_min': day['temp']['min'],
                    'temp_max': day['temp']['max'],
                    'humidity': day['humidity'],
                    'description': day['weather'][0]['description'],
                    'rain': day.get('rain', 0),
                    'weather_id': day['weather'][0]['id']
                })
        
        return forecast
    
    async def get_drought_risk(self, location):
        """Assess drought risk based on forecast"""
        forecast = await self.get_weather_forecast(location, days=14)
        
        if not forecast:
            return None
        
        # Simple drought assessment (can be enhanced)
        rain_days = sum(1 for day in forecast if day.get('rain', 0) > 1)
        max_temps = [day['temp_max'] for day in forecast]
        avg_max_temp = sum(max_temps) / len(max_temps)
        
        if rain_days < 2 and avg_max_temp > 30:
            return {
                'risk_level': 'HIGH',
                'description': 'High temperatures with minimal rainfall expected',
                'forecast_summary': f"{rain_days} days of rain expected in the next 14 days"
            }
        elif rain_days < 4 and avg_max_temp > 28:
            return {
                'risk_level': 'MEDIUM',
                'description': 'Warm temperatures with limited rainfall expected',
                'forecast_summary': f"{rain_days} days of rain expected in the next 14 days"
            }
        else:
            return {
                'risk_level': 'LOW',
                'description': 'Adequate rainfall or moderate temperatures expected',
                'forecast_summary': f"{rain_days} days of rain expected in the next 14 days"
            }