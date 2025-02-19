from django.conf import settings
import httpx

class SMSService:
    @staticmethod
    async def send_sms(phone_number, message):
        """Send SMS using Africa's Talking API"""
        try:
            url = "https://api.africastalking.com/version1/messaging"
            headers = {
                'ApiKey': settings.AT_API_KEY,
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            data = {
                'username': settings.AT_USERNAME,
                'to': phone_number,
                'message': message
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=data, headers=headers)
                return response.json()
                
        except Exception as e:
            return {'error': str(e)}