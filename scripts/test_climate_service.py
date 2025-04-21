#!/usr/bin/env python
"""
Test script for climate data services
Run this script to test the climate data services with mock data without a full Django setup
"""

import asyncio
import logging
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("climate_test")

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

class MockFarmer:
    """Mock farmer object for testing climate data updates"""
    def __init__(self, id, name, location, latitude, longitude):
        self.id = id
        self.name = name
        self.location = location
        self.latitude = latitude
        self.longitude = longitude
        self.ndvi_value = None
        self.rainfall_anomaly_mm = None
        self.last_climate_update = None
        self.has_geo_coordinates = latitude is not None and longitude is not None

    def __str__(self):
        return f"Farmer {self.id}: {self.name} ({self.location})"

    def save(self, update_fields=None):
        """Mock save method"""
        self.last_climate_update = datetime.now()
        return True

class MockWeatherService:
    """Mock weather service for testing"""
    async def get_coordinates(self, location):
        """Return mock coordinates for a location"""
        mock_coords = {
            'Kigali': {'lat': -1.9535, 'lon': 30.0606, 'country': 'RW'},
            'Musanze': {'lat': -1.4977, 'lon': 29.6347, 'country': 'RW'},
            'Nyagatare': {'lat': -1.2978, 'lon': 30.3267, 'country': 'RW'},
        }
        return mock_coords.get(location, {'lat': -1.9535, 'lon': 30.0606, 'country': 'RW'})

    async def get_rainfall_anomaly(self, lat, lon):
        """Return mock rainfall anomaly"""
        # Generate a value between -50 and 50 based on coordinates
        value = (lat + lon) * 10 % 100 - 50
        return round(value, 1)

class MockSatelliteService:
    """Mock satellite service for testing"""
    async def get_ndvi(self, latitude, longitude):
        """Return mock NDVI value"""
        # Generate a value between -0.1 and 0.9 based on coordinates
        base = abs((latitude + longitude) % 1)
        value = -0.1 + base * 1.0
        return round(value, 2)

class MockClimateDataService:
    """Simplified climate data service for testing"""
    def __init__(self):
        self.weather_service = MockWeatherService()
        self.satellite_service = MockSatelliteService()

    async def update_farmer_climate_data(self, farmers, force=False):
        """Update climate data for a list of farmers"""
        updates_made = 0
        errors = 0

        for farmer in farmers:
            try:
                logger.info(f"Processing {farmer}")

                # Skip farmers without coordinates
                if not farmer.has_geo_coordinates:
                    logger.warning(f"Skipping farmer {farmer.id}: Missing coordinates")
                    continue

                # Get NDVI value
                try:
                    ndvi = await self.satellite_service.get_ndvi(
                        latitude=farmer.latitude,
                        longitude=farmer.longitude
                    )
                    farmer.ndvi_value = ndvi
                    logger.info(f"NDVI for {farmer.name}: {ndvi}")
                except Exception as e:
                    logger.error(f"Failed to get NDVI for farmer {farmer.id}: {str(e)}")
                    errors += 1

                # Get rainfall anomaly
                try:
                    rainfall_anomaly = await self.weather_service.get_rainfall_anomaly(
                        lat=farmer.latitude,
                        lon=farmer.longitude
                    )
                    farmer.rainfall_anomaly_mm = rainfall_anomaly
                    logger.info(f"Rainfall anomaly for {farmer.name}: {rainfall_anomaly}mm")
                except Exception as e:
                    logger.error(f"Failed to get rainfall anomaly for farmer {farmer.id}: {str(e)}")
                    errors += 1

                # Update farmer record
                farmer.save()
                updates_made += 1

            except Exception as e:
                errors += 1
                logger.error(f"Error updating climate data for farmer {farmer.id}: {str(e)}")

        return {
            "success": updates_made > 0,
            "updated_count": updates_made,
            "error_count": errors,
            "total_farmers": len(farmers)
        }

async def test_climate_service():
    """Test the climate data service with mock farmers"""
    # Create sample farmers
    farmers = [
        MockFarmer(1, "John Doe", "Kigali", -1.9535, 30.0606),
        MockFarmer(2, "Jane Smith", "Musanze", -1.4977, 29.6347),
        MockFarmer(3, "Bob Johnson", "Nyagatare", -1.2978, 30.3267),
        MockFarmer(4, "Alice Brown", "Unknown", None, None),
    ]

    # Initialize service
    service = MockClimateDataService()

    # Update climate data
    logger.info("Starting climate data update test")
    result = await service.update_farmer_climate_data(farmers)

    # Display results
    logger.info(f"Climate data update completed: {json.dumps(result, indent=2)}")

    # Display updated farmer data
    logger.info("\nUpdated farmer data:")
    for farmer in farmers:
        if farmer.has_geo_coordinates:
            logger.info(
                f"{farmer.name} (ID: {farmer.id}): "
                f"NDVI={farmer.ndvi_value}, "
                f"Rainfall Anomaly={farmer.rainfall_anomaly_mm}mm"
            )

if __name__ == "__main__":
    asyncio.run(test_climate_service()) 