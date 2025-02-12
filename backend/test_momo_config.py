import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def test_momo_configuration():
    print("Testing MTN MoMo API Configuration...")
    
    # Get credentials from .env
    subscription_key = os.getenv('MOMO_SUBSCRIPTION_KEY')
    api_user = os.getenv('MOMO_API_USER')
    api_key = os.getenv('MOMO_API_KEY')
    base_url = os.getenv('MOMO_API_URL')
    
    print("\n1. Checking credentials loaded from .env:")
    print(f"Subscription Key: {'✅ Loaded' if subscription_key else '❌ Missing'}")
    print(f"API User: {'✅ Loaded' if api_user else '❌ Missing'}")
    print(f"API Key: {'✅ Loaded' if api_key else '❌ Missing'}")
    print(f"Base URL: {'✅ Loaded' if base_url else '❌ Missing'}")

    # Test API User status
    print("\n2. Testing API User Status:")
    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "X-Target-Environment": "sandbox"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{base_url}/v1_0/apiuser/{api_user}",
                headers=headers
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("✅ API User is valid and active")
            else:
                print("❌ Error checking API User status")
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")

        # Test OAuth Token Generation
    print("\n3. Testing OAuth Token Generation:")
    import base64
    
    # Use API Key for Basic Auth
    auth_string = f"{api_user}:{api_key}"  # Using API key for Basic Auth
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Ocp-Apim-Subscription-Key": subscription_key,  # Primary subscription key
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Target-Environment": "sandbox"
    }
    
    token_url = f"{base_url}/disbursement/token/"  # Changed to disbursement instead of collection
    print(f"\nAttempting to get token from: {token_url}")
    print(f"Using API User: {api_user}")
    print(f"Using API Key for Basic Auth: {api_key[:8]}...")
    print(f"Using Subscription Key: {subscription_key[:8]}...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                token_url,
                headers=headers,
                data=""
            )
            print(f"Status Code: {response.status_code}")
            print(f"Full URL: {token_url}")
            print(f"Full Headers: {headers}")
            
            if response.status_code == 200:
                print("✅ Successfully generated OAuth token")
                print(f"Access Token: {response.json().get('access_token')[:20]}...")
            else:
                print("❌ Failed to generate OAuth token")
                print(f"Error: {response.text}")
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_momo_configuration())