from django.urls import path
from accounts.views import (
    AdultRegisterView,
    )
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView
    )

urlpatterns = [
    path('register/', AdultRegisterView.as_view(), name='adult_register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),


]
