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
from django.views.generic import TemplateView
from rest_framework import routers
from farmers.views import FarmerViewSet
from loans.views import LoanViewSet

# API router
router = routers.DefaultRouter()
router.register(r'farmers', FarmerViewSet, basename='farmer')
router.register(r'loans', LoanViewSet, basename='loan')

# Configure CORS headers for development
from django.conf import settings
from django.conf.urls.static import static

@api_view(['GET'])
@permission_classes([AllowAny]) 
def api_root(request):
    """
    Root endpoint that provides API information and links
    """
    base_url = request.build_absolute_uri('/').rstrip('/')
    
    return Response({
        "message": "Welcome to AgriFinance API",
        "version": "1.0.0",
        "documentation": f"{base_url}/api/docs/",
        "endpoints": {
            "auth": f"{base_url}/api/auth/",
            "farmers": f"{base_url}/api/farmers/",
            "loans": f"{base_url}/api/loans/",
            "token": f"{base_url}/api/token/",
            "docs": f"{base_url}/api/docs/"
        },
        "status": "online"
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    # Include DRF auth URLs
    path('api-auth/', include('rest_framework.urls')),
    path('api/auth/', include('authentication.urls')),
    path('api/farmers/', include('farmers.urls')),
    path('api/loans/', include('loans.urls')),
    path('api/schema/', SpectacularAPIView.as_view(permission_classes=[AllowAny]), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema', permission_classes=[AllowAny]), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema', permission_classes=[AllowAny]), name='redoc'),
    path('', TemplateView.as_view(template_name='index.html'), name='api-root'),
]

# Add debug toolbar in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass