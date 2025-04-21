from django.http import JsonResponse
from backend.farmers.models import Farmer
import os
import json
import httpx
import asyncio
import logging
from urllib.parse import urljoin
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

# Base URL for API requests
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8000/api/')

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

async def handle_ussd_request(session_id, phone_number, text):
    """
    Handle USSD requests from farmers
    Returns appropriate USSD response
    """
    # Split the text into parts (each part represents a menu level selection)
    menu_levels = text.split('*')
    
    # If no text, this is the initial request
    if not text or text == '':
        return initial_menu()
    
    main_selection = menu_levels[0]
    
    # Handle main menu selection
    if len(menu_levels) == 1:
        if main_selection == '1':
            # Loan Application Status
            return await loan_status_menu(phone_number)
        elif main_selection == '2':
            # Repayment Options
            return repayment_menu()
        elif main_selection == '3':
            # Farm Data
            return await farm_data_menu(phone_number)
        elif main_selection == '4':
            # Weather Information & Alerts
            return await weather_info_menu(phone_number)
        else:
            return "END Invalid selection. Please dial the service again."
    
    # Handle submenus
    if len(menu_levels) > 1:
        sub_selection = menu_levels[1]
        
        # Loan Status submenu
        if main_selection == '1':
            return await handle_loan_status_submenu(phone_number, sub_selection)
        
        # Repayment submenu
        elif main_selection == '2':
            return await handle_repayment_submenu(phone_number, sub_selection)
        
        # Farm Data submenu
        elif main_selection == '3':
            return await handle_farm_data_submenu(phone_number, sub_selection, menu_levels)
        
        # Weather Info submenu
        elif main_selection == '4':
            return await handle_weather_submenu(phone_number, sub_selection)
    
    return "END Invalid selection. Please dial the service again."

def initial_menu():
    """Show the initial USSD menu"""
    response = "CON Welcome to AgriFinance\n"
    response += "1. Loan Status\n"
    response += "2. Repayment Options\n"
    response += "3. Farm Data\n"
    response += "4. Weather Information"
    return response

async def loan_status_menu(phone_number):
    """Show loan status menu"""
    # Try to get the farmer's active loans
    try:
        farmer_data = await get_farmer_by_phone(phone_number)
        if not farmer_data:
            return "END No farmer account found for this phone number."
        
        loan_data = await get_active_loans(farmer_data['id'])
        
        if not loan_data or len(loan_data) == 0:
            return "CON You have no active loans.\n\n1. Apply for a loan\n2. Back to Main Menu"
        
        response = "CON Your Active Loans:\n"
        for i, loan in enumerate(loan_data, 1):
            response += f"{i}. Loan #{loan['id']} - {loan['status']}\n"
        response += f"{len(loan_data) + 1}. Back to Main Menu"
        
        return response
    except Exception as e:
        logger.error(f"Error in loan_status_menu: {e}")
        return "END Error fetching loan data. Please try again later."

async def handle_loan_status_submenu(phone_number, selection):
    """Handle loan status submenu selections"""
    try:
        farmer_data = await get_farmer_by_phone(phone_number)
        if not farmer_data:
            return "END No farmer account found for this phone number."
        
        loan_data = await get_active_loans(farmer_data['id'])
        
        if not loan_data or len(loan_data) == 0:
            if selection == '1':
                return "END Loan application feature coming soon. Please visit your local agent."
            elif selection == '2':
                return initial_menu()
            else:
                return "END Invalid selection. Please dial the service again."
        
        if selection.isdigit() and 1 <= int(selection) <= len(loan_data):
            loan_index = int(selection) - 1
            loan = loan_data[loan_index]
            
            response = "END Loan Details:\n"
            response += f"Loan ID: {loan['id']}\n"
            response += f"Amount: ${loan['amount']}\n"
            response += f"Status: {loan['status']}\n"
            
            # Add more loan details as needed
            if 'next_payment_date' in loan and loan['next_payment_date']:
                response += f"Next Payment: {loan['next_payment_date']}\n"
            if 'remaining_balance' in loan and loan['remaining_balance']:
                response += f"Remaining: ${loan['remaining_balance']}"
                
            return response
        elif selection.isdigit() and int(selection) == len(loan_data) + 1:
            return initial_menu()
        else:
            return "END Invalid selection. Please dial the service again."
    except Exception as e:
        logger.error(f"Error in handle_loan_status_submenu: {e}")
        return "END Error processing request. Please try again later."

def repayment_menu():
    """Show repayment options menu"""
    response = "CON Repayment Options:\n"
    response += "1. Check next payment date\n"
    response += "2. Make a payment\n"
    response += "3. Payment history\n"
    response += "4. Back to Main Menu"
    return response

async def handle_repayment_submenu(phone_number, selection):
    """Handle repayment submenu selections"""
    if selection == '1':
        # Check next payment date
        try:
            farmer_data = await get_farmer_by_phone(phone_number)
            if not farmer_data:
                return "END No farmer account found for this phone number."
            
            loan_data = await get_active_loans(farmer_data['id'])
            
            if not loan_data or len(loan_data) == 0:
                return "END You have no active loans with scheduled payments."
            
            response = "END Next Payment Dates:\n"
            for loan in loan_data:
                if 'next_payment_date' in loan and loan['next_payment_date']:
                    response += f"Loan #{loan['id']}: {loan['next_payment_date']}\n"
                else:
                    response += f"Loan #{loan['id']}: No scheduled payment\n"
                    
            return response
        except Exception as e:
            logger.error(f"Error checking payment dates: {e}")
            return "END Error checking payment dates. Please try again later."
    elif selection == '2':
        # Make a payment - redirect to mobile money
        return "END Please dial *182*7*1# to make a payment through Mobile Money."
    elif selection == '3':
        # Payment history
        return "END Payment history feature coming soon."
    elif selection == '4':
        # Back to main menu
        return initial_menu()
    else:
        return "END Invalid selection. Please dial the service again."

async def farm_data_menu(phone_number):
    """Show farm data menu"""
    try:
        farmer_data = await get_farmer_by_phone(phone_number)
        if not farmer_data:
            return "END No farmer account found for this phone number."
        
        response = "CON Farm Data Options:\n"
        response += "1. View farm profile\n"
        response += "2. View climate risk assessment\n"
        response += "3. Update farm location\n"
        response += "4. Back to Main Menu"
        return response
    except Exception as e:
        logger.error(f"Error in farm_data_menu: {e}")
        return "END Error fetching farm data. Please try again later."

async def handle_farm_data_submenu(phone_number, selection, menu_levels):
    """Handle farm data submenu selections"""
    try:
        farmer = await get_farmer_with_climate_data(phone_number)
        if not farmer:
            return "END No farmer account found for this phone number."
            
        if selection == '1':
            # View farm profile
            response = "END Your Farm Profile:\n"
            response += f"Name: {farmer['name']}\n"
            response += f"Location: {farmer['location']}\n"
            response += f"Farm Size: {farmer['farm_size']} hectares\n"
            
            if farmer.get('latitude') and farmer.get('longitude'):
                response += f"Coordinates: {farmer['latitude']}, {farmer['longitude']}\n"
                
            return response
            
        elif selection == '2':
            # View climate risk assessment
            if len(menu_levels) == 2:
                response = "CON Climate Data Options:\n"
                response += "1. View vegetation health (NDVI)\n"
                response += "2. View rainfall assessment\n"
                response += "3. Back to Farm Data"
                return response
                
            if len(menu_levels) == 3:
                sub_sub_selection = menu_levels[2]
                
                if sub_sub_selection == '1':
                    # Vegetation health
                    climate_data = farmer.get('climate_status', {})
                    has_data = climate_data.get('has_climate_data', False)
                    
                    if not has_data:
                        return "END No vegetation health data available yet. Please check back later."
                        
                    ndvi = climate_data.get('ndvi_value')
                    ndvi_status = climate_data.get('ndvi_status', 'Unknown')
                    
                    response = "END Vegetation Health Assessment:\n"
                    response += f"Status: {ndvi_status}\n"
                    
                    if ndvi is not None:
                        response += f"NDVI Value: {ndvi:.2f}\n"
                        
                        # Add recommendations based on NDVI
                        if ndvi < 0.2:
                            response += "\nRecommendation: Your crops may need immediate attention. Consider irrigation and soil health assessment."
                        elif ndvi < 0.4:
                            response += "\nRecommendation: Monitor your crops closely and ensure adequate water and nutrients."
                        else:
                            response += "\nRecommendation: Your vegetation appears healthy. Continue your current practices."
                            
                    return response
                    
                elif sub_sub_selection == '2':
                    # Rainfall assessment
                    climate_data = farmer.get('climate_status', {})
                    has_data = climate_data.get('has_climate_data', False)
                    
                    if not has_data:
                        return "END No rainfall data available yet. Please check back later."
                        
                    anomaly = climate_data.get('rainfall_anomaly_mm')
                    rainfall_status = climate_data.get('rainfall_status', 'Unknown')
                    
                    response = "END Rainfall Assessment:\n"
                    response += f"Status: {rainfall_status}\n"
                    
                    if anomaly is not None:
                        response += f"Deviation from normal: {anomaly:.1f}mm\n"
                        
                        # Add recommendations based on rainfall
                        if anomaly < -15:
                            response += "\nRecommendation: Consider drought-resistant crops and water conservation techniques."
                        elif anomaly > 15:
                            response += "\nRecommendation: Ensure proper drainage and consider crops that tolerate excess moisture."
                        else:
                            response += "\nRecommendation: Rainfall conditions are favorable for most crops."
                            
                    return response
                    
                elif sub_sub_selection == '3':
                    # Back to Farm Data
                    return await farm_data_menu(phone_number)
                else:
                    return "END Invalid selection. Please dial the service again."
            
        elif selection == '3':
            # Update farm location
            return "END To update your farm location, please visit your local agent or call our support line."
            
        elif selection == '4':
            # Back to main menu
            return initial_menu()
        else:
            return "END Invalid selection. Please dial the service again."
    except Exception as e:
        logger.error(f"Error in handle_farm_data_submenu: {e}")
        return "END Error processing request. Please try again later."

async def weather_info_menu(phone_number):
    """Show weather information menu"""
    try:
        farmer_data = await get_farmer_by_phone(phone_number)
        if not farmer_data:
            return "END No farmer account found for this phone number."
        
        response = "CON Weather Information:\n"
        response += "1. Current weather\n"
        response += "2. 7-day forecast\n"
        response += "3. Weather alerts\n"
        response += "4. Back to Main Menu"
        return response
    except Exception as e:
        logger.error(f"Error in weather_info_menu: {e}")
        return "END Error fetching weather information. Please try again later."

async def handle_weather_submenu(phone_number, selection):
    """Handle weather submenu selections"""
    try:
        farmer = await get_farmer_by_phone(phone_number)
        if not farmer:
            return "END No farmer account found for this phone number."
            
        if selection == '1':
            # Current weather
            weather_data = await get_weather(farmer['location'])
            if not weather_data:
                return "END Error fetching current weather. Please try again later."
                
            response = "END Current Weather:\n"
            response += f"Location: {farmer['location']}\n"
            response += f"Temperature: {weather_data.get('temp', 'N/A')}°C\n"
            response += f"Conditions: {weather_data.get('description', 'N/A')}\n"
            response += f"Humidity: {weather_data.get('humidity', 'N/A')}%\n"
            
            return response
            
        elif selection == '2':
            # 7-day forecast
            return "END 7-day forecast feature coming soon."
            
        elif selection == '3':
            # Weather alerts
            climate_data = await get_farmer_with_climate_data(phone_number)
            if not climate_data:
                return "END Error fetching climate data. Please try again later."
                
            climate_status = climate_data.get('climate_status', {})
            rainfall_status = climate_status.get('rainfall_status', 'Unknown')
            
            response = "END Weather Alerts:\n"
            
            # Check for alerts based on climate data
            if climate_status.get('rainfall_anomaly_mm', 0) < -15:
                response += "⚠️ DROUGHT ALERT: Rainfall significantly below normal.\n"
                response += "Consider water conservation measures.\n\n"
            elif climate_status.get('rainfall_anomaly_mm', 0) > 15:
                response += "⚠️ EXCESS RAIN ALERT: Rainfall significantly above normal.\n"
                response += "Monitor drainage and crop disease risks.\n\n"
                
            if climate_status.get('ndvi_value', 0.5) < 0.2:
                response += "⚠️ VEGETATION STRESS ALERT: Crop health may be compromised.\n"
                response += "Inspect your crops for signs of stress.\n\n"
                
            if "⚠️" not in response:
                response += "No active weather alerts for your area.\n"
                
            return response
            
        elif selection == '4':
            # Back to main menu
            return initial_menu()
        else:
            return "END Invalid selection. Please dial the service again."
    except Exception as e:
        logger.error(f"Error in handle_weather_submenu: {e}")
        return "END Error processing request. Please try again later."

# API Helper Functions

async def get_farmer_by_phone(phone_number):
    """Get farmer data by phone number"""
    try:
        url = urljoin(API_BASE_URL, f"farmers/?phone_number={phone_number}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]
        return None
    except Exception as e:
        logger.error(f"Error fetching farmer by phone: {e}")
        return None

async def get_farmer_with_climate_data(phone_number):
    """Get farmer data with climate information"""
    try:
        farmer = await get_farmer_by_phone(phone_number)
        if not farmer:
            return None
            
        # Get detailed farmer data including climate info
        url = urljoin(API_BASE_URL, f"farmers/{farmer['id']}/climate_data/")
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
        return farmer  # Fallback to basic farmer data
    except Exception as e:
        logger.error(f"Error fetching farmer climate data: {e}")
        return None

async def get_active_loans(farmer_id):
    """Get active loans for a farmer"""
    try:
        url = urljoin(API_BASE_URL, f"loans/?farmer={farmer_id}&status=APPROVED")
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
        return []
    except Exception as e:
        logger.error(f"Error fetching active loans: {e}")
        return []

async def get_weather(location):
    """Get current weather for a location"""
    try:
        # In a real implementation, this would call your actual weather API
        # For this demo, we'll return mock data
        sample_weather = {
            'temp': 25,
            'description': 'Partly cloudy',
            'humidity': 65,
            'wind_speed': 10
        }
        return sample_weather
    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        return None