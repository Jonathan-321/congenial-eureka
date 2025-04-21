# backend/loans/external/weather_api.py
import aiohttp
import os
from django.conf import settings
import logging
import datetime
import json
import statistics
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Service for retrieving and analyzing weather data
    Integrates with OpenWeatherMap API for real weather data
    """
    def __init__(self):
        self.api_key = getattr(settings, 'OPENWEATHER_API_KEY', None)
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.geo_url = "http://api.openweathermap.org/geo/1.0/direct"
        self.historical_url = "https://history.openweathermap.org/data/2.5/history/city"
    
    async def get_coordinates(self, location):
        """Convert location name to coordinates"""
        try:
            if not self.api_key:
                # If no API key, return mock coordinates
                return self._get_mock_coordinates(location)
                
            async with aiohttp.ClientSession() as session:
                params = {
                    'q': location,
                    'limit': 1,
                    'appid': self.api_key
                }
                
                async with session.get(self.geo_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            return {
                                'lat': data[0]['lat'],
                                'lon': data[0]['lon'],
                                'country': data[0].get('country', 'Unknown')
                            }
                    logger.error(f"Geocoding error: {response.status}")
        except Exception as e:
            logger.error(f"Error geocoding location: {str(e)}")
            
        # Fall back to mock data if API fails
        return self._get_mock_coordinates(location)
    
    def _get_mock_coordinates(self, location):
        """Return mock coordinates for testing"""
        mock_coords = {
            'Kigali': {'lat': -1.9535, 'lon': 30.0606, 'country': 'RW'},
            'Musanze': {'lat': -1.4977, 'lon': 29.6347, 'country': 'RW'},
            'Nyagatare': {'lat': -1.2978, 'lon': 30.3267, 'country': 'RW'},
            'Kayonza': {'lat': -1.9418, 'lon': 30.5572, 'country': 'RW'},
            'Huye': {'lat': -2.6437, 'lon': 29.7448, 'country': 'RW'}
        }
        
        return mock_coords.get(location, {'lat': -1.9535, 'lon': 30.0606, 'country': 'RW'})  # Default to Kigali
    
    async def get_conditions(self, location, lat=None, lon=None):
        """
        Get current weather conditions for a location
        Returns a dictionary with weather metrics including drought and flood indices
        """
        try:
            if not lat or not lon:
                coords = await self.get_coordinates(location)
                lat, lon = coords['lat'], coords['lon']
                
            if self.api_key:
                async with aiohttp.ClientSession() as session:
                    # Get current weather
                    current_params = {
                        'lat': lat,
                        'lon': lon,
                        'appid': self.api_key,
                        'units': 'metric'
                    }
                    
                    async with session.get(f"{self.base_url}/weather", params=current_params) as current_response:
                        if current_response.status == 200:
                            current_data = await current_response.json()
                            
                            # Get forecast for next 5 days
                            forecast_params = {
                                'lat': lat,
                                'lon': lon,
                                'appid': self.api_key,
                                'units': 'metric'
                            }
                            
                            async with session.get(f"{self.base_url}/forecast", params=forecast_params) as forecast_response:
                                if forecast_response.status == 200:
                                    forecast_data = await forecast_response.json()
                                    
                                    # Calculate drought and flood indices based on real data
                                    return self._calculate_conditions(current_data, forecast_data)
        except Exception as e:
            logger.error(f"Error getting weather conditions: {str(e)}")
        
        # Fall back to mock data if API calls fail
        return await self._get_mock_conditions(location)
    
    def _calculate_conditions(self, current_data, forecast_data):
        """Calculate weather condition indices based on real data"""
        try:
            # Extract current conditions
            temp = current_data.get('main', {}).get('temp', 25)
            humidity = current_data.get('main', {}).get('humidity', 70)
            current_rain = current_data.get('rain', {}).get('1h', 0)
            current_weather_id = current_data.get('weather', [{}])[0].get('id', 800)
            
            # Extract forecast data
            forecast_list = forecast_data.get('list', [])
            rain_forecast = [item.get('rain', {}).get('3h', 0) for item in forecast_list]
            temp_forecast = [item.get('main', {}).get('temp', 25) for item in forecast_list]
            
            # Calculate drought index (0-1, higher means more drought risk)
            # Factors: current temperature, humidity, rainfall forecast, current rainfall
            temp_factor = max(0, min(1, (temp - 15) / 25))  # 15°C=0, 40°C=1
            humidity_factor = max(0, min(1, (100 - humidity) / 100))  # 100%=0, 0%=1
            
            # Calculate average rainfall from forecast (in mm)
            avg_rain_forecast = sum(rain_forecast) / len(rain_forecast) if rain_forecast else 0
            rain_factor = max(0, min(1, 1 - (avg_rain_forecast / 10)))  # 0mm=1, >=10mm=0
            
            # Combine factors (weight: temp=30%, humidity=30%, forecast=40%)
            drought_index = temp_factor * 0.3 + humidity_factor * 0.3 + rain_factor * 0.4
            
            # Calculate flood index (0-1, higher means more flood risk)
            # Factors: current rainfall, rainfall forecast, weather code
            current_rain_factor = min(1, current_rain / 20)  # 0mm=0, >=20mm=1
            forecast_rain_factor = min(1, sum(rain_forecast) / 50)  # 0mm=0, >=50mm=1
            
            # Check for severe weather in forecast (storms, heavy rain)
            severe_weather_count = sum(1 for item in forecast_list 
                                     if item.get('weather', [{}])[0].get('id', 800) < 600)
            weather_severity_factor = min(1, severe_weather_count / 10)
            
            # Combine factors (weight: current=30%, forecast=50%, severity=20%)
            flood_index = current_rain_factor * 0.3 + forecast_rain_factor * 0.5 + weather_severity_factor * 0.2
            
            return {
                'drought_index': round(drought_index, 2),
                'flood_index': round(flood_index, 2),
                'current_temp': temp,
                'current_humidity': humidity,
                'forecast_rain_mm': round(sum(rain_forecast), 1),
                'avg_forecast_temp': round(sum(temp_forecast) / len(temp_forecast), 1) if temp_forecast else None
            }
        except Exception as e:
            logger.error(f"Error calculating weather conditions: {str(e)}")
            return {'drought_index': 0.3, 'flood_index': 0.3}
    
    async def _get_mock_conditions(self, location):
        """
        Provide mock weather conditions when API is unavailable
        Returns realistic values based on location
        """
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
        import random
        variation = random.uniform(-0.1, 0.1)
        conditions['drought_index'] = max(0, min(1, conditions['drought_index'] + variation))
        conditions['flood_index'] = max(0, min(1, conditions['flood_index'] + variation))
        
        return conditions
    
    async def get_rainfall_anomaly(self, lat, lon):
        """
        Calculate rainfall anomaly (deviation from historical average)
        Returns deviation in mm (positive = more rain than average, negative = less rain)
        """
        try:
            if not self.api_key:
                return self._get_mock_rainfall_anomaly(lat, lon)
                
            # Get current month's rainfall data
            today = datetime.datetime.now()
            month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Get recent rainfall data (up to today)
            recent_rainfall = await self._get_rainfall_period(lat, lon, month_start, today)
            
            # Get historical average for same period in previous 3 years
            historical_rainfalls = []
            for year_offset in range(1, 4):  # Check last 3 years
                hist_start = month_start - relativedelta(years=year_offset)
                hist_end = today - relativedelta(years=year_offset)
                
                hist_rainfall = await self._get_rainfall_period(lat, lon, hist_start, hist_end)
                if hist_rainfall is not None:
                    historical_rainfalls.append(hist_rainfall)
            
            # Calculate average if we have data
            if historical_rainfalls:
                avg_historical = statistics.mean(historical_rainfalls)
                anomaly = recent_rainfall - avg_historical
                return round(anomaly, 1)  # Return anomaly in mm
        except Exception as e:
            logger.error(f"Error calculating rainfall anomaly: {str(e)}")
            
        # Fall back to mock data
        return self._get_mock_rainfall_anomaly(lat, lon)
    
    async def _get_rainfall_period(self, lat, lon, start_date, end_date):
        """Get total rainfall for a specific period using OpenWeatherMap"""
        try:
            if not self.api_key:
                return None
                
            # For simplicity, we'll use the daily forecast API instead of historical
            # This is a limitation but works for demo purposes
            # In production, subscribe to historical data API or use alternative sources
            
            async with aiohttp.ClientSession() as session:
                forecast_params = {
                    'lat': lat,
                    'lon': lon,
                    'appid': self.api_key,
                    'units': 'metric',
                }
                
                async with session.get(f"{self.base_url}/forecast", params=forecast_params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract rainfall data
                        total_rain = 0
                        for item in data.get('list', []):
                            # Sum rain amounts (3h periods)
                            rain_amount = item.get('rain', {}).get('3h', 0)
                            total_rain += rain_amount
                        
                        # Scale to match period length (simple approximation)
                        days_diff = (end_date - start_date).days
                        if days_diff <= 0:
                            days_diff = 1
                            
                        # Forecast is 5 days, scale accordingly
                        scaled_rain = total_rain * (days_diff / 5)
                        
                        return scaled_rain
                        
        except Exception as e:
            logger.error(f"Error getting rainfall for period: {str(e)}")
            
        return None
    
    def _get_mock_rainfall_anomaly(self, lat, lon):
        """Generate mock rainfall anomaly for testing"""
        # Use coordinates to generate a consistent but varied value
        import hashlib
        import struct
        
        # Create a hash from the coordinates
        hash_input = f"{lat},{lon}".encode('utf-8')
        hash_val = hashlib.md5(hash_input).digest()
        
        # Convert first 4 bytes to float between -1 and 1
        float_val = struct.unpack('f', hash_val[:4])[0]
        norm_val = float_val % 2 - 1  # normalize to -1 to 1
        
        # Scale to a reasonable rainfall anomaly in mm (-50 to +50)
        return round(norm_val * 50, 1)
    
    async def assess_risk(self, location, lat=None, lon=None):
        """
        Assess climate risk for a location
        Returns a score between 0-100 (higher = higher risk)
        """
        if not lat or not lon:
            coords = await self.get_coordinates(location)
            lat, lon = coords['lat'], coords['lon']
            
        # Get current conditions
        conditions = await self.get_conditions(location, lat, lon)
        
        # Get rainfall anomaly
        rainfall_anomaly = await self.get_rainfall_anomaly(lat, lon)
        
        # Calculate risk score components
        drought_risk = conditions['drought_index'] * 50  # 0-50 points
        flood_risk = conditions['flood_index'] * 30  # 0-30 points
        
        # Rainfall anomaly risk (extreme values in either direction increase risk)
        # Convert to 0-20 scale
        anomaly_risk = min(20, abs(rainfall_anomaly) / 5)  # Each 5mm deviation adds 1 point, up to 20
        
        # Combine risks (higher score = higher risk)
        risk_score = drought_risk + flood_risk + anomaly_risk
        
        return min(100, risk_score)  # Ensure score is between 0-100


    async def get_weather_forecast(self, location, days=7):
        """Get weather forecast for a location"""
        try:
            if not self.api_key:
                return self._get_mock_forecast(location, days)
                
            # Get coordinates if needed
            coords = await self.get_coordinates(location)
            lat, lon = coords['lat'], coords['lon']
            
            async with aiohttp.ClientSession() as session:
                params = {
                    'lat': lat,
                    'lon': lon,
                    'appid': self.api_key,
                    'units': 'metric',
                    'cnt': days
                }
                
                # Using one-call API which has daily forecasts
                async with session.get(f"{self.base_url}/forecast", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._process_forecast(data)
                    else:
                        logger.error(f"Weather API error: {response.status}")
                        return self._get_mock_forecast(location, days)
        except Exception as e:
            logger.error(f"Error fetching weather data: {str(e)}")
            return self._get_mock_forecast(location, days)

    def _process_forecast(self, data):
        """Process the raw forecast data into a more usable format"""
        forecast = []
        
        if 'list' in data:
            for day_data in data['list']:
                forecast.append({
                    'date': day_data['dt'],
                    'temp_min': day_data['main']['temp_min'],
                    'temp_max': day_data['main']['temp_max'],
                    'humidity': day_data['main']['humidity'],
                    'description': day_data['weather'][0]['description'],
                    'rain': day_data.get('rain', {}).get('3h', 0),
                    'weather_id': day_data['weather'][0]['id']
                })
        
        return forecast
    
    def _get_mock_forecast(self, location, days):
        """Generate a mock forecast for testing"""
        forecast = []
        today = datetime.datetime.now()
        
        for i in range(days):
            day = today + datetime.timedelta(days=i)
            
            # Use hash of location and date to create consistent but varied weather
            import hashlib
            hash_input = f"{location}_{day.strftime('%Y-%m-%d')}".encode('utf-8')
            hash_val = int(hashlib.md5(hash_input).hexdigest(), 16) % 100000
            
            # Derive weather parameters from hash
            temp_base = 25  # Base temperature
            temp_variation = (hash_val % 15) - 7  # -7 to +7 variation
            rain_chance = (hash_val % 10) / 10  # 0 to 0.9
            rain_amount = rain_chance * (hash_val % 20)  # 0 to ~18mm
            
            # Weather ID (800=clear, 500=rain, etc.)
            weather_id = 800  # Default to clear
            if rain_chance > 0.7:
                weather_id = 500 + (hash_val % 4)  # Rain
            elif rain_chance > 0.4:
                weather_id = 801 + (hash_val % 3)  # Cloudy
                
            # Description based on ID
            descriptions = {
                800: "clear sky",
                801: "few clouds",
                802: "scattered clouds",
                803: "broken clouds",
                500: "light rain",
                501: "moderate rain",
                502: "heavy rain",
                503: "very heavy rain"
            }
            
            forecast.append({
                'date': int(day.timestamp()),
                'temp_min': temp_base + temp_variation - 2,
                'temp_max': temp_base + temp_variation + 2,
                'humidity': 50 + (hash_val % 40),
                'description': descriptions.get(weather_id, "unknown"),
                'rain': rain_amount if rain_chance > 0.3 else 0,
                'weather_id': weather_id
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