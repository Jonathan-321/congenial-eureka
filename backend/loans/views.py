from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from django.db.models import Sum, Count, Min, F, Q
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import asyncio
from django.shortcuts import get_object_or_404
from asgiref.sync import sync_to_async, async_to_sync

from farmers.models import Farmer

from .models import (
    Loan, LoanProduct, LoanRepayment, Transaction, PaymentSchedule,
    LoanToken, TokenTransaction, ApprovedVendor, CropCycle
)
from .serializers import (
    LoanSerializer, LoanProductSerializer, SimpleLoanSerializer, DetailedLoanSerializer,
    LoanRepaymentSerializer, TransactionSerializer, PaymentScheduleSerializer,
    LoanTokenSerializer, TokenTransactionSerializer, CropCycleSerializer, 
    HarvestScheduleSerializer, FarmerDashboardSerializer
)
from .services import LoanService, SMSService, DynamicCreditScoringService
from .tokenization_service import TokenizedLoanService
from .harvest_service import HarvestBasedLoanService
from .insurance_service import InsuranceIntegrationService
from .external.weather_api import WeatherService
from .external.market_api import MarketDataService
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .repayment_service import RepaymentService

class LoanProductViewSet(viewsets.ModelViewSet):
    """ViewSet for managing loan products"""
    queryset = LoanProduct.objects.all()
    serializer_class = LoanProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return all products for admins, only active for regular users"""
        if self.request.user.role == 'ADMIN':
            return LoanProduct.objects.all()
        return LoanProduct.objects.filter(is_active=True)


class LoanViewSet(viewsets.ModelViewSet):
    """ViewSet for managing loan resources"""
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    @action(detail=False, methods=['get'])
    async def payment_summary(self, request):
        """Get payment summary for all loans of a farmer"""
        farmer_id = request.query_params.get('farmer_id')
        if not farmer_id:
            return Response(
                {"error": "farmer_id parameter is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        @sync_to_async
        def get_payment_stats():
            loans = Loan.objects.filter(farmer_id=farmer_id)
            return {
                'total_loans': loans.count(),
                'active_loans': loans.filter(status__in=['APPROVED', 'DISBURSED', 'ACTIVE']).count(),
                'total_approved': loans.aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0,
                'total_repaid': LoanRepayment.objects.filter(loan__in=loans).aggregate(Sum('amount'))['amount__sum'] or 0,
                'upcoming_payments': PaymentSchedule.objects.filter(
                    loan__in=loans,
                    status__in=['PENDING', 'PARTIALLY_PAID']
                ).count(),
                'overdue_payments': PaymentSchedule.objects.filter(
                    loan__in=loans,
                    status='OVERDUE'
                ).count()
            }
        
        payment_stats = await get_payment_stats()
        return Response(payment_stats)
    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Apply for a loan"""
        # Get the loan product from the URL parameter
        loan_product = get_object_or_404(LoanProduct, pk=pk)
        
        # Extract amount from request data
        try:
            amount = Decimal(request.data.get('amount', '0'))
            
            # Validate amount against loan product limits
            if amount < loan_product.min_amount or amount > loan_product.max_amount:
                return Response(
                    {"error": "Amount outside allowed range"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except:
            return Response(
                {"error": "Invalid amount"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create a loan application
        farmer = Farmer.objects.get(user=request.user)
        loan = Loan.objects.create(
            farmer=farmer,
            loan_product=loan_product,
            amount_requested=amount,
            status='PENDING'
        )
        
        # Return the created loan data
        return Response({
            'status': 'PENDING',
            'loan_id': loan.id
        })

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a loan"""
        loan = self.get_object()
        loan.status = 'APPROVED'
        loan.approval_date = timezone.now()
        loan.save()
        serializer = self.get_serializer(loan)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        """Disburse a loan"""
        loan = self.get_object()
        loan.status = 'DISBURSED'
        loan.disbursement_date = timezone.now()
        loan.save()
        serializer = self.get_serializer(loan)
        return Response(serializer.data)
    
class FarmerDashboardAPIView(APIView):
    """API view for farmer dashboard data"""
    permission_classes = [IsAuthenticated]
    
    async def get(self, request, farmer_id):
        try:
            # Get the farmer
            @sync_to_async
            def get_farmer():
                return Farmer.objects.get(id=farmer_id)
            
            farmer = await get_farmer()
            
            # Check permission (only the farmer or admin can view)
            if request.user.role != 'ADMIN' and farmer.user != request.user:
                return Response(
                    {"detail": "You do not have permission to view this dashboard"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Calculate dashboard metrics
            @sync_to_async
            def get_dashboard_data():
                # Get active loans
                active_statuses = ['APPROVED', 'DISBURSED', 'ACTIVE']
                active_loans = Loan.objects.filter(
                    farmer=farmer,
                    status__in=active_statuses
                )
                
                # Calculate metrics
                active_loans_count = active_loans.count()
                total_loan_balance = active_loans.aggregate(
                    total=Sum('amount_approved')
                )['total'] or 0
                
                # Find next payment
                today = timezone.now().date()
                next_payment = PaymentSchedule.objects.filter(
                    loan__farmer=farmer,
                    loan__status__in=active_statuses,
                    status__in=['PENDING', 'PARTIALLY_PAID'],
                    due_date__gte=today
                ).order_by('due_date').first()
                
                next_payment_date = next_payment.due_date if next_payment else None
                next_payment_amount = next_payment.amount if next_payment else 0
                
                # Count active tokens
                active_tokens = LoanToken.objects.filter(
                    loan__farmer=farmer,
                    status='ACTIVE',
                    expiry_date__gte=today
                ).count()
                
                # Create data dict with computed fields
                data = {
                    'id': farmer.id,
                    'name': farmer.name,
                    'location': farmer.location,
                    'farm_size': farmer.farm_size,
                    'active_loans_count': active_loans_count,
                    'total_loan_balance': total_loan_balance,
                    'next_payment_date': next_payment_date,
                    'next_payment_amount': next_payment_amount,
                    'active_tokens': active_tokens
                }
                
                return data
            
            dashboard_data = await get_dashboard_data()
            
            # Serialize and return
            @sync_to_async
            def serialize_data():
                serializer = FarmerDashboardSerializer(data=dashboard_data)
                serializer.is_valid()
                return serializer.data
            
            serialized_data = await serialize_data()
            return Response(serialized_data)
            
        except Farmer.DoesNotExist:
            return Response(
                {"detail": "Farmer not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LoanStatusAPIView(APIView):
    """API view for detailed loan status information"""
    permission_classes = [IsAuthenticated]
    
    async def get(self, request, loan_id):
        try:
            # Get the loan with related objects
            @sync_to_async
            def get_loan():
                return Loan.objects.select_related(
                    'farmer', 'loan_product'
                ).get(id=loan_id)
            
            loan = await get_loan()
            
            # Check permission
            if request.user.role != 'ADMIN' and loan.farmer.user != request.user:
                return Response(
                    {"detail": "You do not have permission to view this loan"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Serialize the loan
            @sync_to_async
            def serialize_loan():
                serializer = DetailedLoanSerializer(loan)
                return serializer.data
            
            loan_data = await serialize_loan()
            
            # Add weather forecast if harvest schedule exists
            if hasattr(loan, 'harvest_schedule') and loan.harvest_schedule:
                # Get weather forecast for farmer's location
                weather_service = WeatherService()
                forecast = await weather_service.get_weather_forecast(
                    loan.farmer.location, days=7
                )
                
                if forecast:
                    loan_data['weather_forecast'] = forecast
            
            return Response(loan_data)
            
        except Loan.DoesNotExist:
            return Response(
                {"detail": "Loan not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TokenValidationView(APIView):
    """API view for validating tokens"""
    permission_classes = [IsAuthenticated]
    
    async def post(self, request):
        token_code = request.data.get('token')
        vendor_id = request.data.get('vendor_id')
        
        if not token_code or not vendor_id:
            return Response(
                {"detail": "Token code and vendor ID are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify token exists and is valid
        @sync_to_async
        def get_token():
            try:
                return LoanToken.objects.select_related('loan__farmer').get(
                    token=token_code,
                    status='ACTIVE'
                )
            except LoanToken.DoesNotExist:
                return None
        
        loan_token = await get_token()
        if not loan_token:
            return Response(
                {"detail": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Serialize token data
        @sync_to_async
        def serialize_token():
            serializer = LoanTokenSerializer(loan_token)
            return serializer.data
        
        token_data = await serialize_token()
        
        # Add farmer info
        @sync_to_async
        def get_farmer_info():
            return {
                'farmer_name': loan_token.loan.farmer.name,
                'farmer_phone': loan_token.loan.farmer.phone_number
            }
        
        farmer_info = await get_farmer_info()
        token_data.update(farmer_info)
        
        return Response(token_data)


# Add to backend/loans/views.py

class HarvestScheduleAPIView(APIView):
    """API view for managing harvest-based repayment schedules"""
    permission_classes = [IsAuthenticated]
    
    async def get(self, request, loan_id):
        """Get the harvest schedule for a loan"""
        try:
            @sync_to_async
            def get_schedule():
                loan = Loan.objects.get(id=loan_id)
                try:
                    schedule = loan.harvest_schedule
                    return loan, schedule
                except:
                    return loan, None
            
            loan, schedule = await get_schedule()
            
            # Check permissions
            if request.user.role != 'ADMIN' and loan.farmer.user != request.user:
                return Response(
                    {"detail": "You do not have permission to view this schedule"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if not schedule:
                return Response(
                    {"detail": "No harvest schedule exists for this loan"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            @sync_to_async
            def serialize_schedule():
                serializer = HarvestScheduleSerializer(schedule)
                return serializer.data
            
            schedule_data = await serialize_schedule()
            return Response(schedule_data)
            
        except Loan.DoesNotExist:
            return Response(
                {"detail": "Loan not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    async def post(self, request, loan_id):
        """Create a harvest-based repayment schedule for a loan"""
        try:
            crop_cycle_id = request.data.get('crop_cycle_id')
            if not crop_cycle_id:
                return Response(
                    {"detail": "crop_cycle_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            @sync_to_async
            def get_loan_and_crop():
                loan = Loan.objects.get(id=loan_id)
                crop_cycle = CropCycle.objects.get(id=crop_cycle_id)
                return loan, crop_cycle
            
            loan, crop_cycle = await get_loan_and_crop()
            
            # Check permissions
            if request.user.role != 'ADMIN' and loan.farmer.user != request.user:
                return Response(
                    {"detail": "You do not have permission to create a schedule for this loan"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Create harvest schedule
            harvest_service = HarvestBasedLoanService()
            success, result = await harvest_service.create_harvest_based_schedule(loan, crop_cycle)
            
            if not success:
                return Response(
                    {"detail": result},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            @sync_to_async
            def serialize_schedule():
                serializer = HarvestScheduleSerializer(result)
                return serializer.data
            
            schedule_data = await serialize_schedule()
            return Response(schedule_data, status=status.HTTP_201_CREATED)
            
        except Loan.DoesNotExist:
            return Response(
                {"detail": "Loan not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except CropCycle.DoesNotExist:
            return Response(
                {"detail": "Crop cycle not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WeatherForecastAPIView(APIView):
    """API view for weather forecasts"""
    permission_classes = [IsAuthenticated]
    
    async def get(self, request, location):
        try:
            days = int(request.query_params.get('days', 7))
            if days > 14:
                days = 14  # Limit forecast to 14 days
            
            weather_service = WeatherService()
            forecast = await weather_service.get_weather_forecast(location, days=days)
            
            if not forecast:
                return Response(
                    {"detail": "Unable to retrieve weather forecast for this location"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(forecast)
            
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MarketPricesAPIView(APIView):
    """API view for market prices"""
    permission_classes = [IsAuthenticated]
    
    async def get(self, request, crop_type):
        try:
            location = request.query_params.get('location')
            
            market_service = MarketDataService()
            prices = await market_service.get_crop_prices(crop_type, location)
            
            if not prices:
                return Response(
                    {"detail": "Unable to retrieve market prices for this crop"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(prices)
            
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
# Add to backend/loans/views.py

class CropCycleViewSet(viewsets.ModelViewSet):
    """ViewSet for managing crop cycles"""
    queryset = CropCycle.objects.all()
    serializer_class = CropCycleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter crop cycles by farmer if user is not admin"""
        if self.request.user.role == 'ADMIN':
            return CropCycle.objects.all()
        return CropCycle.objects.filter(farmer__user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def farmer_cycles(self, request):
        """Get all crop cycles for a specific farmer"""
        farmer_id = request.query_params.get('farmer_id')
        if not farmer_id:
            return Response(
                {"detail": "farmer_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cycles = CropCycle.objects.filter(farmer_id=farmer_id)
        serializer = self.get_serializer(cycles, many=True)
        return Response(serializer.data)
    
@api_view(['POST'])
@permission_classes([AllowAny])
async def momo_webhook(request):
    """Handle MTN Mobile Money webhook callbacks"""
    try:
        # Log the incoming webhook data for debugging
        print(f"Received MoMo webhook: {request.data}")
        
        # Adapt MTN data format to our expected format
        payment_data = {
            'reference': request.data.get('external_id') or request.data.get('transaction_id'),
            'amount': request.data.get('amount'),
            'phone_number': request.data.get('payer_phone') or request.data.get('phone_number'),
            'status': request.data.get('status')
        }
        
        # Only process successful payments
        if payment_data.get('status') not in ('SUCCESSFUL', 'COMPLETED', None):
            return Response({
                "status": "ignored", 
                "message": f"Payment not successful: {payment_data.get('status')}"
            }, status=status.HTTP_200_OK)
        
        # Process the payment
        repayment_service = RepaymentService()
        success, message = await repayment_service.process_payment(payment_data)
        
        if success:
            return Response({"status": "success", "message": message}, status=status.HTTP_200_OK)
        else:
            return Response({"status": "error", "message": message}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {"status": "error", "message": f"Webhook processing error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )