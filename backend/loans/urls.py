from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, ussd_views

# Create router for REST API endpoints
router = DefaultRouter()
router.register(r'loans', views.LoanViewSet, basename='loan')
router.register(r'products', views.LoanProductViewSet, basename='loan-product')

# API endpoints
urlpatterns = [
    # API routes
    path('', include(router.urls)),
    
    # USSD callback
    path('ussd/callback/', ussd_views.ussd_callback, name='ussd_callback'),
]