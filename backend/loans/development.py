from loans.services import LoanService, SMSService
from farmers.models import Farmer
from loans.models import LoanProduct

async def test_loan_flow():
    # Create test farmer
    farmer = Farmer.objects.create(
        name="Test Farmer",
        phone_number="+250789123456",  # Sandbox number
        location="Kigali",
        farm_size=2.5
    )
    
    # Create loan product
    product = LoanProduct.objects.create(
        name="Quick Loan",
        min_amount=10000,
        max_amount=50000,
        interest_rate=15,
        term_days=30
    )
    
    # Test SMS
    success, result = await SMSService.send_sms(
        farmer.phone_number,
        "Test message from AgriFinance"
    )
    print(f"SMS Test: {success}, {result}")
    
    # Test loan application
    success, result = await LoanService.process_loan_application(
        farmer,
        product,
        20000
    )
    print(f"Loan Application: {success}, {result}")