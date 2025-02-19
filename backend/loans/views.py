from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Loan, LoanProduct, LoanRepayment, Transaction
from .serializers import (
    LoanSerializer, LoanProductSerializer,
    LoanRepaymentSerializer, TransactionSerializer
)
from .services import LoanService
from asgiref.sync import async_to_sync


class LoanViewSet(viewsets.ModelViewSet):
    """
    API endpoints for loan management
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer

    def create(self, request, *args, **kwargs):
        try:
            # Get or create farmer
            from farmers.models import Farmer
            farmer, created = Farmer.objects.get_or_create(
                user=request.user,
                defaults={
                    'name': request.user.username,
                    'phone_number': request.user.phone_number,
                    'location': 'Default Location',
                    'farm_size': 1.0
                }
            )
            
            data = request.data.copy()
            data['farmer'] = farmer.id
            serializer = self.get_serializer(data=data)
            
            if serializer.is_valid():
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Apply for a loan"""
        loan_service = LoanService()
        result = async_to_sync(loan_service.apply_for_loan)(
            farmer=request.user.farmer,
            loan_product_id=pk,
            amount=request.data.get('amount')
        )
        return Response(result)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        try:
            loan = self.get_object()
            loan_service = LoanService()
            result = async_to_sync(loan_service.approve_loan)(
                loan_id=loan.id,
                approved_amount=request.data.get('amount', loan.amount_requested)
            )
            return Response(result)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    async def process(self, request, pk=None):
        """Legacy method for processing loans"""
        loan = self.get_object()
        result = await LoanService.process_application(loan.id)
        return Response({'success': result})

    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        try:
            loan = self.get_object()
            loan_service = LoanService()
            result = async_to_sync(loan_service.disburse_loan)(loan.id)
            return Response(result)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LoanProductViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = LoanProduct.objects.all()
    serializer_class = LoanProductSerializer