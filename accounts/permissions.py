from rest_framework.permissions import BasePermission
from .models import User

class IsAuthenticatedAdult(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_authenticated and request.user.role == User.Role.ADULT)

class IsAuthenticatedChild(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_authenticated and request.user.role == User.Role.CHILD)
    