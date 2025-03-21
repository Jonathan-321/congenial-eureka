# Add this to backend/loans/permissions.py
from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users.
    """
    def has_permission(self, request, view):
        return request.user and hasattr(request.user, 'role') and request.user.role == 'ADMIN'