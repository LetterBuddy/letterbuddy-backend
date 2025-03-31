from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import IsAuthenticatedAdult
from .serializers import AdultRegisterSerializer, LoginSerializer, LogoutSerializer, ChildRegisterSerializer, ChildSerializer

from .models import *

class AdultRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = AdultRegisterSerializer

class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    
    
# unlike APIView, GenericAPIView provide serializer_class
# which helps drf-spectacular to generate the schema
class LogoutView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = LogoutSerializer
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True) 
        refresh_token = serializer.validated_data["refresh"]
        try:
            # blacklist the refresh token
            # so that the user can no longer use it to get a new access token
            token = RefreshToken(refresh_token)
            token.blacklist()
            # 205 - the UI should reset - and remove the access token
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        

# model viewset - provides all the CRUD operations: 
# 6 endpoints: GET(all) / GET(by id) / POST / PUT / PATCH / DELETE
# POST - registering a child has a different serializer
# TODO the GET request for a specific child(by id) is pointless at this point
# TODO fix the user_id type for drf-spectacular
class ChildrenView(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticatedAdult,)
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"

    def get_serializer_class(self):
        # create - for registering a child (POST)
        # TODO create all the letter models for the child
        if self.action == 'create':
            return ChildRegisterSerializer
        return ChildSerializer
    
    # only children of the logged in adult
    def get_queryset(self):
        adult = AdultProfile.objects.get(user=self.request.user)
        return ChildProfile.objects.filter(guiding_adult=adult)