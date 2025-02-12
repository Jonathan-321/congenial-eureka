import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

import asyncio
import uuid
from loans.momo_integration import MoMoAPI

async def test_disbursement():
    print("\nTesting MTN MoMo Disbursement")
    print("-----------------------------")
    
    momo = MoMoAPI()
    
    try:
        # First get the token
        print("\n1. Getting access token...")
        token = await momo.get_access_token()
        print(f"✅ Token received: {token[:20]}...")
        
        # Initiate disbursement
        print("\n2. Initiating disbursement...")
        reference = str(uuid.uuid4())  # Generate unique reference
        phone = "250789123456"  # Removed + from phone number
        amount = "10.00"
        
        print(f"Phone: {phone}")
        print(f"Amount: {amount} EUR")
        print(f"Reference: {reference}")
        
        result = await momo.initiate_disbursement(
            phone_number=phone,
            amount=amount,
            reference=reference
        )
        print(f"Disbursement initiated: {result}")
        
        # Add status check
        if result['status'] == 'pending':
            print("\n3. Checking disbursement status...")
            await asyncio.sleep(5)  # Wait 5 seconds before checking
            status = await momo.check_disbursement_status(reference)
            print(f"Status: {status}")
        
    except Exception as e:
        print(f"\n❌ Error occurred:")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        
        # Print the full error details if available
        if hasattr(e, 'response'):
            print("\nResponse Details:")
            print(f"Status Code: {e.response.status_code}")
            print(f"Headers: {e.response.headers}")
            print(f"Body: {e.response.text}")

if __name__ == "__main__":
    asyncio.run(test_disbursement())