from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from ..farmers.models import Loan, LoanProduct
from farmers.models import Farmer
import json

@csrf_exempt
def ussd_callback(request):
    if request.method == 'POST':
        session_id = request.POST.get('sessionId', None)
        service_code = request.POST.get('serviceCode', None)
        phone_number = request.POST.get('phoneNumber', None)
        text = request.POST.get('text', '')

        response = ""
        
        if text == "":
            # First request
            response = "CON Welcome to AgriFinance\n"
            response += "1. Apply for loan\n"
            response += "2. Check loan status\n"
            response += "3. Make payment\n"
            response += "4. Check balance"
            
        elif text == "1":
            # Show loan products
            products = LoanProduct.objects.filter(is_active=True)
            response = "CON Select loan product:\n"
            for idx, product in enumerate(products, 1):
                response += f"{idx}. {product.name} ({product.min_amount}-{product.max_amount} RWF)\n"
                
        elif text.startswith("1*"):
            # Handle loan application
            try:
                farmer = Farmer.objects.get(phone_number=phone_number)
                # Add loan application logic here
                response = "END Your loan application has been received. You will receive an SMS shortly."
            except Farmer.DoesNotExist:
                response = "END Please register as a farmer first by dialing *555#"

        return HttpResponse(response, content_type='text/plain')
    
    return HttpResponse("Method not allowed", status=405)