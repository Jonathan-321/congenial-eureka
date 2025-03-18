# backend/loans/external/satellite_api.py

class SatelliteDataService:
    """
    Mock implementation of satellite data service
    In production, this would integrate with a real satellite data API
    """
    
    async def analyze_farm(self, location, farm_size):
        """
        Analyze farm health using satellite imagery
        Returns a score between 0-100
        """
        # In a real implementation, this would call a satellite imagery API
        # For now, return a mock score based on location and farm size
        
        # Mock logic: larger farms get slightly higher scores (up to +10)
        size_factor = min(farm_size * 2, 10)
        
        # Mock location-based scoring
        location_scores = {
            'Kigali': 70,
            'Musanze': 80,
            'Nyagatare': 75,
            'Kayonza': 65,
            'Huye': 70
        }
        
        base_score = location_scores.get(location, 60)  # Default if location not in our mock data
        
        # Add some randomness to simulate real-world variation
        import random
        variation = random.uniform(-5, 5)
        
        final_score = base_score + size_factor + variation
        return min(max(final_score, 0), 100)  # Ensure score is between 0-100