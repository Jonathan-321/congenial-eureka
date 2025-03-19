from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView 
from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import redirect


# Add this simple view for the root URL - with AllowAny permission
@api_view(['GET'])
@permission_classes([AllowAny])  # This allows unauthenticated access
def api_root(request):
    """
    Root endpoint that provides API information and links
    """
    return Response({
        "message": "Welcome to AgriFinance API",
        "version": "1.0.0",
        "documentation": "/api/docs/",
        "endpoints": {
            "auth": "/api/auth/",
            "farmers": "/api/farmers/",
            "loans": "/api/loans/",
            "token": "/api/token/",
            "docs": "/api/docs/"
        },
        "status": "online"
    })


urlpatterns = [
    # Root URL handler - add this at the top
    path('', api_root, name='api-root'),
    
    # Your existing URLs
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/farmers/', include('farmers.urls')),
    path('api/loans/', include('loans.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/schema/', SpectacularAPIView.as_view(permission_classes=[AllowAny]), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema', permission_classes=[AllowAny]), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema', permission_classes=[AllowAny]), name='redoc'),
]