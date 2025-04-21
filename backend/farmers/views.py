from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Farmer
from .serializers import FarmerSerializer, ClimateDataSerializer
import asyncio
from django.db.models import Q, Avg, Min, Max
import logging

from loans.climate_services import ClimateDataService
from loans.serializers import FarmerDetailSerializer

logger = logging.getLogger(__name__)

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

    @action(detail=True, methods=['get', 'post'])
    def climate_data(self, request, pk=None):
        """
        GET: Retrieve climate data for a farmer
        POST: Update climate data for a farmer
        """
        try:
            farmer = self.get_object()
            
            # For POST request, update the climate data
            if request.method == 'POST':
                # Run the async function in a sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                climate_service = ClimateDataService()
                try:
                    # Check if farmer has coordinates, if not try to get them
                    if not farmer.has_geo_coordinates and farmer.location:
                        # Import here to avoid circular imports
                        from backend.loans.external.weather_api import WeatherService
                        weather_service = WeatherService()
                        coords = loop.run_until_complete(weather_service.get_coordinates(farmer.location))
                        if coords:
                            farmer.latitude = coords['lat']
                            farmer.longitude = coords['lon']
                            farmer.save(update_fields=['latitude', 'longitude', 'updated_at'])
                    
                    # Update climate data
                    result = loop.run_until_complete(climate_service.update_farmer_climate_data(farmer.id))
                    loop.close()
                    
                    # Refresh the farmer object
                    farmer.refresh_from_db()
                    
                    if result['updated_count'] > 0:
                        return Response({
                            'message': 'Climate data updated successfully',
                            'farmer': FarmerDetailSerializer(farmer).data
                        })
                    else:
                        return Response({
                            'message': 'No updates were made. Farmer may lack coordinates or climate data may be recent.',
                            'farmer': FarmerDetailSerializer(farmer).data
                        }, status=status.HTTP_200_OK)
                        
                except Exception as e:
                    return Response({
                        'error': f"Failed to update climate data: {str(e)}"
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                finally:
                    if loop and not loop.is_closed():
                        loop.close()
            
            # For GET request, just return the current data
            serializer = FarmerDetailSerializer(farmer)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                'error': f"Error processing request: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def climate_data(self, request):
        """Get climate data for all farmers with coordinates"""
        farmers = Farmer.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            ndvi_value__isnull=False,
            rainfall_anomaly_mm__isnull=False
        )
        
        serializer = ClimateDataSerializer(farmers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def climate_stats(self, request):
        """Get aggregated climate statistics"""
        farmers = Farmer.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            ndvi_value__isnull=False,
            rainfall_anomaly_mm__isnull=False
        )
        
        # No data available
        if not farmers.exists():
            return Response({
                "message": "No climate data available",
                "data": {}
            })
        
        # Calculate statistics
        stats = {
            "ndvi": {
                "avg": farmers.aggregate(Avg('ndvi_value'))['ndvi_value__avg'],
                "min": farmers.aggregate(Min('ndvi_value'))['ndvi_value__min'],
                "max": farmers.aggregate(Max('ndvi_value'))['ndvi_value__max'],
            },
            "rainfall_anomaly": {
                "avg": farmers.aggregate(Avg('rainfall_anomaly_mm'))['rainfall_anomaly_mm__avg'],
                "min": farmers.aggregate(Min('rainfall_anomaly_mm'))['rainfall_anomaly_mm__min'],
                "max": farmers.aggregate(Max('rainfall_anomaly_mm'))['rainfall_anomaly_mm__max'],
            },
            "total_farmers": farmers.count(),
            "locations": list(farmers.values('location').annotate(
                count=models.Count('id'),
                avg_ndvi=models.Avg('ndvi_value'),
                avg_rainfall_anomaly=models.Avg('rainfall_anomaly_mm')
            ))
        }
        
        return Response({
            "message": "Climate statistics retrieved successfully",
            "data": stats
        })
    
    @action(detail=True, methods=['get'])
    def climate_history(self, request, pk=None):
        """Get climate data history for a specific farmer"""
        try:
            farmer = self.get_object()
            
            # Check if farmer has climate data
            if not farmer.has_geo_coordinates or farmer.ndvi_value is None:
                return Response({
                    "message": "No climate data available for this farmer",
                    "data": []
                })
            
            # Use the climate service to get real or mock history data
            from loans.climate_services import ClimateDataService
            
            # Initialize service
            climate_service = ClimateDataService()
            
            # Get days parameter with default of 90 days
            days = int(request.query_params.get('days', 90))
            # Limit to reasonable range
            days = min(max(days, 7), 365)
            
            # Run async function with event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                history = loop.run_until_complete(
                    climate_service.get_farmer_climate_history(farmer.id, days)
                )
            finally:
                loop.close()
                
            return Response({
                "message": "Climate history retrieved successfully",
                "data": history
            })
            
        except Exception as e:
            logger.error(f"Error retrieving climate history: {str(e)}")
            return Response(
                {"message": f"Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )