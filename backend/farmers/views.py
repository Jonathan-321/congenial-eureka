from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Farmer
from .serializers import FarmerSerializer

class FarmerViewSet(viewsets.ModelViewSet):
    """
    API endpoints for farmer management
    """
    serializer_class = FarmerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter farmers based on user role:
        - Staff users can see all farmers
        - Regular users can only see their own farmer profile
        """
        if self.request.user.is_staff:
            return Farmer.objects.all()
        return Farmer.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        # Debug information
        print(f"User: {request.user}, Data: {request.data}")
        
        # Make sure data validation is correct
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Add try/except to identify the error
            try:
                serializer.save(user=request.user)  # Make sure user is properly associated
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(f"Error creating farmer: {str(e)}")
                return Response(
                    {"error": str(e)}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def loans(self, request, pk=None):
        """Get all loans for a specific farmer"""
        farmer = self.get_object()
        if farmer.user != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Not authorized to view these loans."},
                status=status.HTTP_403_FORBIDDEN
            )
        loans = farmer.loans.all()
        from loans.serializers import LoanSerializer
        serializer = LoanSerializer(loans, many=True)
        return Response(serializer.data)