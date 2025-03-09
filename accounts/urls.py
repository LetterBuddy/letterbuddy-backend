from django.urls import path
from accounts.views import (
    AdultRegisterView, LogoutView,

    )
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView,
    )

urlpatterns = [
    path('register/adult/', AdultRegisterView.as_view(), name='adult_register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
