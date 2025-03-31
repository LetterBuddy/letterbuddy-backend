from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework import routers
from .views import AdultRegisterView, LogoutView, LoginView
from . import views

router = routers.DefaultRouter()
router.register('child', views.ChildrenView, basename='child')


urlpatterns = [
    # include the router urls for the viewsets(currently only child's viewset)
    path('', include(router.urls)),
    path('adult/', AdultRegisterView.as_view(), name='adult_register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
