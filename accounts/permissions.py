from rest_framework.permissions import BasePermission
from .models import User

class IsAdult(BasePermission):
    def has_permission(self, request, view):
        return (request.user and request.user.role == User.Role.ADULT)

class IsChild(BasePermission):
    def has_permission(self, request, view):
        return (request.user and request.user.role == User.Role.CHILD)
    