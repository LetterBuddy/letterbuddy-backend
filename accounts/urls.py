from django.urls import path, include
from . import views
from .views import AdultRegisterView, LogoutView, ChildrenView, LoginView, TokenRefreshWithCookie

from rest_framework import routers

router = routers.DefaultRouter()
router.register('child', views.ChildrenView, basename='child')


urlpatterns = [
    path('', include(router.urls)),
    path('adult/', AdultRegisterView.as_view(), name='adult_register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshWithCookie.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
