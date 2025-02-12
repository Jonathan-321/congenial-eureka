from django.http import JsonResponse
from backend.farmers.models import Farmer

def ussd_handler(request):
    text = request.GET.get("text", "").split("*")  # USSD input from farmer
    phone = request.GET.get("phoneNumber", "")    # Farmer's phone number

    if text == [""]:  # Initial USSD menu
        response = "CON Welcome to AgriFinance!\n1. Register\n2. Check Loan Status\n3. Repay Loan"
    elif text[0] == "1":  # Registration flow
        if len(text) == 1:  # Step 1: Ask for farmer details
            response = "CON Enter your name, location, farm size, and crops (e.g., John,Kayonza,0.5,maize)"
        elif len(text) == 2:  # Step 2: Save farmer details
            try:
                name, location, farm_size, crops = text[1].split(",")
                Farmer.objects.create(
                    name=name,
                    phone=phone,
                    location=location,
                    farm_size=float(farm_size),
                    crops=crops
                )
                response = "END Thank you for registering!"
            except Exception as e:
                response = f"END Error: {str(e)}"
    else:
        response = "END Invalid option. Please try again."

    return JsonResponse({"response": response})