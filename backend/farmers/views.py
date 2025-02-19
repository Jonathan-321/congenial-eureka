from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Farmer
from .serializers import FarmerSerializer

class FarmerViewSet(viewsets.ModelViewSet):
    """
    API endpoints for farmer management
    """
    queryset = Farmer.objects.all()
    serializer_class = FarmerSerializer

    def create(self, request, *args, **kwargs):
        """Register a new farmer"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def loans(self, request, pk=None):
        """Get all loans for a specific farmer"""
        farmer = self.get_object()
        loans = farmer.loans.all()
        from loans.serializers import LoanSerializer
        serializer = LoanSerializer(loans, many=True)
        return Response(serializer.data)