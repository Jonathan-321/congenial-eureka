from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

# Create router for REST API endpoints
router = DefaultRouter()
router.register(r'', views.FarmerViewSet, basename='farmer')

# Just use router.urls since we don't have USSD views in farmers app
urlpatterns = router.urls