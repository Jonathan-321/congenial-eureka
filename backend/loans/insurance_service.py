# backend/loans/insurance_service.py

from asgiref.sync import sync_to_async
from .external.nais_api import NAISApi
from .services import SMSService

class InsuranceIntegrationService:
    def __init__(self):
        self.nais_api = NAISApi()
        self.sms_service = SMSService()
    
    async def verify_insurance(self, farmer_id):
        """Verify that a farmer has active NAIS insurance"""
        try:
            result = await self.nais_api.check_enrollment(farmer_id)
            return result.get('enrolled', False), result
        except Exception as e:
            # Log error
            print(f"Error checking NAIS enrollment: {e}")
            return False, {"error": str(e)}
    
    async def register_for_insurance(self, farmer):
        """Register a farmer for NAIS insurance"""
        try:
            result = await self.nais_api.register_farmer(
                farmer_id=farmer.id,
                name=farmer.name,
                phone=farmer.phone_number,
                location=farmer.location,
                farm_size=farmer.farm_size
            )
            
            if result.get('success', False):
                # Notify farmer of successful registration
                await self.sms_service.send_sms(
                    farmer.phone_number,
                    f"You have been successfully registered with the National Agriculture Insurance Scheme. "
                    f"Your policy number is {result.get('policy_number')}. Policy is valid from "
                    f"{result.get('coverage_start')} to {result.get('coverage_end')}."
                )
            
            return result.get('success', False), result
        except Exception as e:
            # Log error
            print(f"Error registering for NAIS: {e}")
            return False, {"error": str(e)}