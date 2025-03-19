"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView 
from django.urls import path, include
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import redirect


# Add this simple view for the root URL
@api_view(['GET'])
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
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]