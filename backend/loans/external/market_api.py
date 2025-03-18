# backend/loans/external/market_api.py

import aiohttp
import os
from django.conf import settings
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

class MarketDataService:
    """Service for fetching agricultural market data"""
    
    def __init__(self):
        self.api_key = settings.MARKET_API_KEY
        self.base_url = "https://api.data.gov.rw/agriculture/markets"  # Example API
    
    async def get_crop_prices(self, crop_type, location=None):
        """Get current market prices for specific crops"""
        try:
            # In a real implementation, this would call an external API
            # For now, we'll simulate responses for demonstration
            return self._get_simulated_prices(crop_type, location)
        except Exception as e:
            logger.error(f"Error fetching market data: {str(e)}")
            return None
    
    def _get_simulated_prices(self, crop_type, location=None):
        """Simulate market price data for demonstration"""
        base_prices = {
            'MAIZE': {'min': 250, 'max': 350, 'unit': 'kg'},
            'BEANS': {'min': 600, 'max': 850, 'unit': 'kg'},
            'RICE': {'min': 900, 'max': 1200, 'unit': 'kg'},
            'CASSAVA': {'min': 200, 'max': 300, 'unit': 'kg'},
            'POTATO': {'min': 180, 'max': 280, 'unit': 'kg'},
            'COFFEE': {'min': 1800, 'max': 2500, 'unit': 'kg'},
            'TEA': {'min': 250, 'max': 450, 'unit': 'kg'}
        }
        
        location_adjustments = {
            'Kigali': 1.2,
            'Nyagatare': 0.9,
            'Musanze': 1.1,
            'Huye': 0.95
        }
        
        if crop_type.upper() not in base_prices:
            return None
        
        price_data = base_prices[crop_type.upper()]
        
        # Apply location adjustment if available
        if location and location in location_adjustments:
            adjustment = location_adjustments[location]
            price_data['min'] = int(price_data['min'] * adjustment)
            price_data['max'] = int(price_data['max'] * adjustment)
        
        return {
            'crop': crop_type,
            'min_price': price_data['min'],
            'max_price': price_data['max'],
            'average_price': (price_data['min'] + price_data['max']) // 2,
            'unit': price_data['unit'],
            'location': location or 'National average',
            'last_updated': '2023-10-01',  # Simulated date
            'trend': self._get_random_trend()
        }
    
    def _get_random_trend(self):
        """Return a random price trend for simulation"""
        import random
        trends = ['STABLE', 'RISING', 'FALLING']
        return random.choice(trends)
    
    async def get_best_selling_time(self, crop_type, forecast_months=3):
        """Predict the best time to sell based on historical data"""
        # This would normally use historical data and predictive modeling
        # For demonstration, we'll return simulated advice
        
        crop_patterns = {
            'MAIZE': {'best_month': 'August', 'reason': 'Low supply after Season A depletion'},
            'BEANS': {'best_month': 'June', 'reason': 'High demand after Season B harvest'},
            'RICE': {'best_month': 'December', 'reason': 'Holiday season demand increase'},
            'POTATO': {'best_month': 'April', 'reason': 'Limited supply before Season B harvest'}
        }
        
        if crop_type.upper() in crop_patterns:
            return {
                'crop': crop_type,
                'best_selling_time': crop_patterns[crop_type.upper()]['best_month'],
                'reason': crop_patterns[crop_type.upper()]['reason'],
                'price_increase_potential': f"{5 + (hash(crop_type) % 10)}%"
            }
        else:
            return {
                'crop': crop_type,
                'best_selling_time': 'Varies',
                'reason': 'Insufficient historical data for this crop',
                'price_increase_potential': 'Unknown'
            }