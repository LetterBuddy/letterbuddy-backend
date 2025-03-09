from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .permissions import IsAdult, IsChild
from .models import AdultProfile, User

from .serializers import *


class AdultRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = AdultRegisterSerializer


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = LogoutSerializer
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True) 
        refresh_token = serializer.validated_data["refresh_token"]
        try:
            # blacklist the refresh token
            # so that the user can no longer use it to get a new access token
            token = RefreshToken(refresh_token)
            token.blacklist()
            # 205 - the UI should reset - and remove the access token from the local storage
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)