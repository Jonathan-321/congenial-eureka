# backend/loans/external/nais_api.py

class NAISApi:
    """
    Mock implementation of National Agriculture Insurance Scheme API
    In production, this would integrate with the actual NAIS API
    """
    
    async def check_enrollment(self, farmer_id):
        """
        Check if a farmer is enrolled in NAIS
        Returns a dictionary with enrollment status
        """
        # In a real implementation, this would call the NAIS API
        # For testing, return mock data
        
        # Use farmer_id to determine enrollment status (for testing only)
        # In a real system, we'd check against the actual NAIS database
        import hashlib
        
        # Create a hash of the farmer ID and use it to determine enrollment
        # This gives us consistent but random-looking results for testing
        farmer_hash = hashlib.md5(str(farmer_id).encode()).hexdigest()
        enrolled = int(farmer_hash[-2:], 16) < 200  # ~78% of farmers will show as enrolled
        
        return {
            'enrolled': enrolled,
            'policy_number': f"NAIS-{farmer_hash[:8].upper()}" if enrolled else None,
            'coverage_start': '2023-01-01' if enrolled else None,
            'coverage_end': '2023-12-31' if enrolled else None
        }
    
    async def register_farmer(self, farmer_id, name, phone, location, farm_size):
        """
        Register a farmer for NAIS insurance
        Returns a dictionary with registration result
        """
        # In a real implementation, this would call the NAIS API
        # For testing, assume registration is successful
        
        import hashlib
        import uuid
        
        # Generate a policy number
        policy_hash = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()
        policy_number = f"NAIS-{policy_hash[:8].upper()}"
        
        return {
            'success': True,
            'policy_number': policy_number,
            'coverage_start': '2023-01-01',
            'coverage_end': '2023-12-31',
            'premium': farm_size * 5000  # Mock premium calculation
        }