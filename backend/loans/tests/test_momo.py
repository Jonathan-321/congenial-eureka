import pytest
from loans.momo_integration import MoMoAPI

@pytest.mark.asyncio
async def test_momo_integration():
    momo = MoMoAPI()
    
    # First test token generation
    try:
        token = await momo.get_access_token()
        print(f"Access token obtained: {token[:20]}...")
    except Exception as e:
        print(f"Token generation failed: {str(e)}")
        raise
    
    # Test disbursement
    try:
        result = await momo.initiate_disbursement(
            phone_number="+250789123456",  # Test number for Rwanda
            amount=5000,  # Amount in RWF
            reference="TEST-LOAN-001"
        )
        print("Disbursement Test:", result)
    except Exception as e:
        print(f"Disbursement failed: {str(e)}")
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_momo_integration())