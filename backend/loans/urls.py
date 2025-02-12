from django.urls import path
from . import ussd_views

urlpatterns = [
    path('ussd/callback/', ussd_views.ussd_callback, name='ussd_callback'),
]